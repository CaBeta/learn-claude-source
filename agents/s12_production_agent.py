"""
s12 · Production Agent — 完整的生产级 Coding Agent

整合 s01-s11 的所有机制，构建一个可用于真实编码任务的 agent。
包含: Agent Loop, Tool Use, Streaming, SubAgent, Context Management,
      Permission, Skills, Hooks, Background Tasks, Session Memory,
      Error Recovery, Configuration.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python s12_production_agent.py
"""

import asyncio
import json
import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from anthropic import Anthropic, APIError, RateLimitError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    """Agent 配置 — 类比 main.tsx 的启动参数"""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    max_iterations: int = 15
    max_context_tokens: int = 8000
    permission_mode: str = "default"  # default | bypass | plan
    session_id: str = field(default_factory=lambda: f"session-{uuid.uuid4().hex[:8]}")
    features: dict = field(default_factory=lambda: {
        "streaming": True,
        "background_tasks": True,
        "session_memory": True,
        "hooks": True,
    })

    # Memory extraction thresholds (类比 sessionMemoryUtils.ts:32-36)
    memory_init_tokens: int = 3000
    memory_update_tokens: int = 1500
    memory_tool_calls: int = 2


# ---------------------------------------------------------------------------
# Tool System (s02)
# ---------------------------------------------------------------------------

@dataclass
class Tool:
    """工具定义 — 类比 Tool.ts buildTool()"""
    name: str
    description: str
    input_schema: dict
    handler: Callable
    is_readonly: bool = False
    is_destructive: bool = False
    requires_permission: bool = True


class ToolRegistry:
    """工具注册表 — 类比 tools.ts getAllBaseTools()"""

    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def get_definitions(self) -> list[dict]:
        """返回 Anthropic API 格式的工具定义"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self.tools.values()
        ]


# ---------------------------------------------------------------------------
# Hook System (s08)
# ---------------------------------------------------------------------------

class HookManager:
    """生命周期钩子 — 类比 utils/hooks.ts"""

    def __init__(self):
        self.hooks: dict[str, list[Callable]] = {}

    def register(self, event: str, fn: Callable):
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(fn)

    async def fire(self, event: str, data: dict = None) -> dict:
        """触发钩子事件，返回可能修改后的数据"""
        result = data or {}
        for fn in self.hooks.get(event, []):
            try:
                hook_result = fn(data or {})
                if hook_result:
                    result.update(hook_result)
            except Exception as e:
                print(f"  [Hook:{event}] Error: {e}")
        return result


# ---------------------------------------------------------------------------
# Permission System (s06)
# ---------------------------------------------------------------------------

class PermissionChecker:
    """权限检查器 — 类比 hooks/toolPermission/"""

    ALLOWED_READONLY = {"read_file", "list_files", "search", "task_get", "task_list"}

    def __init__(self, mode: str = "default"):
        self.mode = mode

    def check(self, tool_name: str, tool_input: dict, tool_def: Optional[Tool] = None) -> dict:
        """
        返回 {"behavior": "allow"|"deny"|"ask", "reason": str}
        """
        # Bypass mode: 全部放行
        if self.mode == "bypass":
            return {"behavior": "allow"}

        # Plan mode: 只允许只读操作
        if self.mode == "plan":
            if tool_name in self.ALLOWED_READONLY:
                return {"behavior": "allow"}
            return {"behavior": "deny", "reason": f"Plan mode: {tool_name} is not read-only"}

        # Default mode: 检查工具属性
        if tool_def:
            if tool_def.is_destructive:
                return {"behavior": "ask", "reason": f"{tool_name} is a destructive operation"}
            if tool_def.is_readonly:
                return {"behavior": "allow"}

        return {"behavior": "allow"}


# ---------------------------------------------------------------------------
# Context Management (s05)
# ---------------------------------------------------------------------------

class ContextManager:
    """
    上下文管理器 — 简化版 5 层管线。
    类比 query.ts:369-543 的 Budget → Snip → Microcompact → Collapse → Autocompact
    """

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.summary: Optional[str] = None

    def _estimate_tokens(self, messages: list[dict]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for block in content:
                    total += len(json.dumps(block, default=str)) // 4
        return total

    def manage(self, messages: list[dict], client: Anthropic, model: str) -> list[dict]:
        """管理上下文大小，必要时进行压缩"""
        tokens = self._estimate_tokens(messages)

        # Layer 1: Budget — 截断过长的 tool result
        messages = self._apply_budget(messages)

        tokens = self._estimate_tokens(messages)
        if tokens <= self.max_tokens:
            return messages

        # Layer 2: Snip — 截断旧的 tool output
        messages = self._snip_old_outputs(messages)

        tokens = self._estimate_tokens(messages)
        if tokens <= self.max_tokens:
            return messages

        # Layer 3: Summarize — 压缩早期对话
        messages = self._summarize_early(messages)

        return messages

    def _apply_budget(self, messages: list[dict], max_result_len: int = 2000) -> list[dict]:
        """Layer 1: 截断过长的 tool result"""
        result = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                new_content = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        raw = block.get("content", "")
                        if isinstance(raw, str) and len(raw) > max_result_len:
                            block = {**block, "content": raw[:max_result_len] + "\n... [truncated]"}
                    new_content.append(block)
                result.append({**msg, "content": new_content})
            else:
                result.append(msg)
        return result

    def _snip_old_outputs(self, messages: list[dict]) -> list[dict]:
        """Layer 2: 将旧 tool output 替换为简短摘要"""
        if len(messages) <= 6:
            return messages
        result = messages[:2]
        for msg in messages[2:-4]:
            content = msg.get("content", "")
            if isinstance(content, list):
                new_content = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        raw = str(block.get("content", ""))
                        if len(raw) > 200:
                            block = {**block, "content": "[Output snipped for context management]"}
                    new_content.append(block)
                result.append({**msg, "content": new_content})
            else:
                result.append(msg)
        result.extend(messages[-4:])
        return result

    def _summarize_early(self, messages: list[dict]) -> list[dict]:
        """Layer 3: 保留最近消息，将早期消息替换为摘要"""
        if len(messages) <= 4:
            return messages

        summary_text = self.summary or "[Earlier conversation summarized]"
        return [
            {"role": "user", "content": f"<context-summary>\n{summary_text}\n</context-summary>"},
            *messages[-4:],
        ]


# ---------------------------------------------------------------------------
# Session Memory (s11)
# ---------------------------------------------------------------------------

MEMORY_TEMPLATE = """# Session Title
_A short descriptive title_

# Current State
_What is being worked on right now_

# Key Files
_Important files and their roles_

# Learnings
_What worked, what to avoid_
"""


class SessionMemory:
    """会话记忆 — 类比 services/SessionMemory/sessionMemory.ts"""

    def __init__(self, base_dir: str = ".agent_data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.memory_path = self.base_dir / "memory.md"
        self._last_extraction_tokens = 0
        self._tool_calls = 0

        if not self.memory_path.exists():
            self.memory_path.write_text(MEMORY_TEMPLATE)

    def read(self) -> str:
        return self.memory_path.read_text()

    def should_extract(self, messages: list[dict], config: AgentConfig) -> bool:
        """阈值判断 — 类比 sessionMemory.ts:134-181"""
        total_chars = sum(
            len(str(m.get("content", ""))) for m in messages
        )
        estimated_tokens = total_chars // 4
        token_growth = estimated_tokens - self._last_extraction_tokens

        if token_growth >= config.memory_update_tokens and self._tool_calls >= config.memory_tool_calls:
            return True
        return False

    def record_tool_call(self):
        self._tool_calls += 1

    def extract(self, messages: list[dict], client: Anthropic, model: str):
        """执行记忆提取（同步简化版）"""
        current = self.read()
        recent = []
        for msg in messages[-4:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, list):
                parts = []
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text":
                        parts.append(b.get("text", "")[:200])
                content = " ".join(parts)
            recent.append(f"[{role}]: {str(content)[:300]}")

        try:
            prompt = f"""Update these session notes based on the recent conversation.
Keep all section headers. Only update sections with new info. Be concise.

Current notes:
{current}

Recent conversation:
{chr(10).join(recent)}

Output the COMPLETE updated notes:"""

            resp = client.messages.create(
                model=model, max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            self.memory_path.write_text(resp.content[0].text)
            self._last_extraction_tokens = sum(
                len(str(m.get("content", ""))) for m in messages
            ) // 4
            self._tool_calls = 0
            print("  [Memory] 提取完成")
        except Exception as e:
            print(f"  [Memory] 提取失败: {e}")


# ---------------------------------------------------------------------------
# Background Tasks (s10)
# ---------------------------------------------------------------------------

@dataclass
class BgTask:
    task_id: str
    description: str
    status: str = "pending"
    result: Optional[str] = None
    error: Optional[str] = None

class TaskQueue:
    """后台任务队列 — 类比 TaskCreate/TaskGet 工具"""

    def __init__(self):
        self.tasks: dict[str, BgTask] = {}
        self._lock = threading.Lock()

    def submit(self, desc: str, fn: Callable) -> str:
        tid = f"task-{uuid.uuid4().hex[:6]}"
        task = BgTask(task_id=tid, description=desc)

        with self._lock:
            self.tasks[tid] = task

        def _run():
            task.status = "running"
            try:
                task.result = str(fn())
                task.status = "completed"
            except Exception as e:
                task.error = str(e)
                task.status = "failed"

        threading.Thread(target=_run, daemon=True).start()
        return tid

    def get(self, tid: str) -> Optional[BgTask]:
        return self.tasks.get(tid)

    def list_all(self) -> list[BgTask]:
        return list(self.tasks.values())


# ---------------------------------------------------------------------------
# Production Agent
# ---------------------------------------------------------------------------

class ProductionAgent:
    """
    生产级 Coding Agent — 整合所有机制。
    类比: query.ts 的完整 Agent Loop
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.registry = ToolRegistry()
        self.hooks = HookManager()
        self.permissions = PermissionChecker(self.config.permission_mode)
        self.context_mgr = ContextManager(self.config.max_context_tokens)
        self.memory = SessionMemory()
        self.task_queue = TaskQueue()
        self.messages: list[dict] = []
        self.stats = {"iterations": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0}

        self._register_builtin_tools()
        self._register_builtin_hooks()

    # -- Tool Registration --------------------------------------------------

    def _register_builtin_tools(self):
        """注册内置工具 — 类比 tools.ts getAllBaseTools()"""

        self.registry.register(Tool(
            name="read_file",
            description="Read a file's contents. Args: path (str)",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            handler=lambda i: self._tool_read_file(i["path"]),
            is_readonly=True,
        ))

        self.registry.register(Tool(
            name="write_file",
            description="Write content to a file. Args: path (str), content (str)",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
            handler=lambda i: self._tool_write_file(i["path"], i["content"]),
            is_destructive=True,
        ))

        self.registry.register(Tool(
            name="bash",
            description="Run a bash command. Args: command (str)",
            input_schema={"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
            handler=lambda i: self._tool_bash(i["command"]),
            is_destructive=True,
        ))

        self.registry.register(Tool(
            name="list_files",
            description="List files in a directory. Args: path (str, default '.')",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": []},
            handler=lambda i: self._tool_list_files(i.get("path", ".")),
            is_readonly=True,
        ))

        self.registry.register(Tool(
            name="search",
            description="Search for a pattern in files. Args: pattern (str), path (str, optional)",
            input_schema={"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"]},
            handler=lambda i: self._tool_search(i["pattern"], i.get("path", ".")),
            is_readonly=True,
        ))

        self.registry.register(Tool(
            name="task_create",
            description="Create a background task. Args: description (str), command (str)",
            input_schema={"type": "object", "properties": {"description": {"type": "string"}, "command": {"type": "string"}}, "required": ["description", "command"]},
            handler=lambda i: self._tool_task_create(i["description"], i["command"]),
        ))

        self.registry.register(Tool(
            name="task_get",
            description="Get background task status. Args: task_id (str)",
            input_schema={"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
            handler=lambda i: self._tool_task_get(i["task_id"]),
            is_readonly=True,
        ))

    def _register_builtin_hooks(self):
        """注册内置钩子"""
        self.hooks.register("pre_tool_use", self._hook_log_tool)
        self.hooks.register("post_tool_use", self._hook_track_tool_call)

    # -- Tool Implementations -----------------------------------------------

    def _tool_read_file(self, path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8")[:3000]
        except FileNotFoundError:
            return f"Error: File not found: {path}"
        except Exception as e:
            return f"Error: {e}"

    def _tool_write_file(self, path: str, content: str) -> str:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} chars to {path}"
        except Exception as e:
            return f"Error: {e}"

    def _tool_bash(self, command: str) -> str:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            output = result.stdout + result.stderr
            return output[:2000] if output else "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 30s"
        except Exception as e:
            return f"Error: {e}"

    def _tool_list_files(self, path: str) -> str:
        try:
            p = Path(path)
            entries = sorted(p.rglob("*"))[:50]
            return "\n".join(str(e.relative_to(p)) for e in entries)
        except Exception as e:
            return f"Error: {e}"

    def _tool_search(self, pattern: str, path: str) -> str:
        try:
            result = subprocess.run(
                ["grep", "-rn", pattern, path, "--include=*.py", "--include=*.ts",
                 "--include=*.js", "--include=*.md"],
                capture_output=True, text=True, timeout=15
            )
            lines = result.stdout.split("\n")[:20]
            return "\n".join(lines) if lines else "No matches found"
        except Exception as e:
            return f"Error: {e}"

    def _tool_task_create(self, desc: str, command: str) -> str:
        def _run():
            r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
            return r.stdout[:1000] if r.returncode == 0 else f"Failed: {r.stderr[:200]}"

        tid = self.task_queue.submit(desc, _run)
        return json.dumps({"task_id": tid, "status": "submitted"})

    def _tool_task_get(self, tid: str) -> str:
        task = self.task_queue.get(tid)
        if not task:
            return json.dumps({"error": "Task not found"})
        return json.dumps({
            "task_id": task.task_id, "status": task.status,
            "result": task.result, "error": task.error,
        }, default=str)

    # -- Hook Implementations -----------------------------------------------

    def _hook_log_tool(self, data: dict) -> dict:
        tool_name = data.get("tool_name", "")
        print(f"  [Tool] {tool_name}")
        return data

    def _hook_track_tool_call(self, data: dict):
        self.stats["tool_calls"] += 1
        self.memory.record_tool_call()

    # -- Main Agent Loop ----------------------------------------------------

    async def run(self, user_message: str) -> str:
        """
        主 Agent Loop — 类比 query.ts 的 while(true) 状态机。
        整合了 s01-s11 的所有机制。
        """
        # 注入记忆到 system prompt
        memory_content = self.memory.read()
        memory_section = ""
        if memory_content.strip() != MEMORY_TEMPLATE.strip():
            memory_section = f"\n\n<session-memory>\n{memory_content}</session-memory>"

        system_prompt = (
            "You are a capable coding assistant. Use tools to help the user. "
            "Be concise and thorough." + memory_section
        )

        # 添加用户消息
        self.messages.append({"role": "user", "content": user_message})

        # 触发 session_start hook
        await self.hooks.fire("session_start" if self.stats["iterations"] == 0 else "turn_start")

        # Agent Loop — while(true) 状态机
        for iteration in range(self.config.max_iterations):
            self.stats["iterations"] += 1
            print(f"\n--- Iteration {iteration + 1} ---")

            # Step 1: Context Management (s05)
            managed_messages = self.context_mgr.manage(
                self.messages, self.client, self.config.model
            )

            # Step 2: Call Model with error recovery
            try:
                response = await self._call_model_with_recovery(
                    system_prompt, managed_messages
                )
            except Exception as e:
                print(f"  [Error] Model call failed: {e}")
                return f"Agent error after {iteration + 1} iterations: {e}"

            # Track token usage
            if hasattr(response, "usage"):
                self.stats["tokens_in"] += getattr(response.usage, "input_tokens", 0)
                self.stats["tokens_out"] += getattr(response.usage, "output_tokens", 0)

            # Step 3: Parse response — collect text and tool_use blocks
            text_parts = []
            tool_use_blocks = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_use_blocks.append(block)

            # Step 4: No tools → we're done
            if not tool_use_blocks:
                final_text = "\n".join(text_parts)
                self.messages.append({"role": "assistant", "content": response.content})

                # Step: Memory extraction (s11)
                if self.config.features.get("session_memory"):
                    if self.memory.should_extract(self.messages, self.config):
                        self.memory.extract(self.messages, self.client, self.config.model)

                await self.hooks.fire("session_end", {"iterations": iteration + 1})
                self._print_stats()
                return final_text

            # Step 5: Process tool calls
            self.messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in tool_use_blocks:
                # Step 5a: Permission check (s06)
                perm = self.permissions.check(block.name, block.input, self.registry.get(block.name))

                if perm["behavior"] == "deny":
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Permission denied: {perm.get('reason', 'unknown')}",
                        "is_error": True,
                    })
                    continue

                if perm["behavior"] == "ask":
                    print(f"  [Permission] {block.name} requires approval (auto-approved in demo)")

                # Step 5b: Pre-tool hook (s08)
                hook_data = await self.hooks.fire("pre_tool_use", {
                    "tool_name": block.name,
                    "tool_input": block.input,
                })

                # Step 5c: Execute tool (s02)
                tool = self.registry.get(block.name)
                if tool:
                    try:
                        result = tool.handler(block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Tool error: {e}",
                            "is_error": True,
                        })
                else:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Unknown tool: {block.name}",
                        "is_error": True,
                    })

                # Step 5d: Post-tool hook (s08)
                await self.hooks.fire("post_tool_use", {
                    "tool_name": block.name,
                    "success": not tool_results[-1].get("is_error", False),
                })

            # Step 6: Append tool results and continue loop
            self.messages.append({"role": "user", "content": tool_results})

            # Memory check
            if self.config.features.get("session_memory"):
                if self.memory.should_extract(self.messages, self.config):
                    self.memory.extract(self.messages, self.client, self.config.model)

        # Max iterations reached
        self._print_stats()
        return f"Agent reached max iterations ({self.config.max_iterations})"

    # -- Error Recovery -----------------------------------------------------

    async def _call_model_with_recovery(self, system: str, messages: list, max_retries: int = 3):
        """带重试的模型调用 — 类比 query.ts 的 recovery 机制"""
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.client.messages.create,
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    system=system,
                    tools=self.registry.get_definitions(),
                    messages=messages,
                )
                return response
            except RateLimitError:
                wait = 2 ** (attempt + 1)
                print(f"  [Recovery] Rate limited, waiting {wait}s...")
                await asyncio.sleep(wait)
            except APIError as e:
                if e.status_code == 429:
                    await asyncio.sleep(10)
                elif e.status_code >= 500:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                raise
        raise RuntimeError(f"Model call failed after {max_retries} retries")

    # -- Stats --------------------------------------------------------------

    def _print_stats(self):
        print(f"\n{'=' * 40}")
        print(f"Session: {self.config.session_id}")
        print(f"Iterations: {self.stats['iterations']}")
        print(f"Tool calls: {self.stats['tool_calls']}")
        print(f"Tokens: {self.stats['tokens_in']} in / {self.stats['tokens_out']} out")
        print(f"Messages: {len(self.messages)}")
        tasks = self.task_queue.list_all()
        if tasks:
            print(f"Background tasks: {len(tasks)} "
                  f"({sum(1 for t in tasks if t.status == 'completed')} done)")


# ---------------------------------------------------------------------------
# Main — 运行 Production Agent
# ---------------------------------------------------------------------------

async def main():
    print("=" * 60)
    print("s12 · Production Agent")
    print("=" * 60)

    # 创建配置
    config = AgentConfig(
        permission_mode="bypass",  # 演示模式：自动批准所有操作
        max_iterations=10,
    )

    # 创建 agent
    agent = ProductionAgent(config)

    # 示例任务
    tasks = [
        "列出当前目录的文件结构，告诉我这是什么项目。",
    ]

    for task in tasks:
        print(f"\n{'=' * 60}")
        print(f"User: {task}")
        print("=" * 60)

        result = await agent.run(task)

        print(f"\n{'─' * 40}")
        print("Agent 回复:")
        print(result)

    # 显示最终统计
    agent._print_stats()

    # 显示记忆状态
    print(f"\n{'─' * 40}")
    print("Session Memory:")
    print(agent.memory.read()[:500])


if __name__ == "__main__":
    asyncio.run(main())
