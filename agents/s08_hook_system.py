"""
S08: Hook System — 钩子系统

在工具调用的生命周期关键点注入自定义逻辑。
Pre/Post hooks 让你在不修改工具代码的情况下改变行为。

运行: export ANTHROPIC_API_KEY=your-key && python s08_hook_system.py
依赖: pip install anthropic
"""

import os
import json
import re
import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Callable

try:
    from anthropic import Anthropic
except ImportError:
    print("请安装 anthropic: pip install anthropic")
    raise


# ---------------------------------------------------------------------------
# 1. HookEvent — 钩子事件类型
# ---------------------------------------------------------------------------

class HookEvent(str, Enum):
    """类比 Claude Code: utils/hooks.ts 中的 20+ 事件类型."""
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


# ---------------------------------------------------------------------------
# 2. Hook — 钩子定义
# ---------------------------------------------------------------------------

@dataclass
class Hook:
    """一个钩子 = 匹配规则 + 回调函数."""
    name: str
    event: HookEvent
    callback: Callable[[Dict], Dict]
    matcher: Optional[str] = None     # 匹配特定工具名
    priority: int = 0

    def matches(self, context: Dict) -> bool:
        if self.matcher is None:
            return True
        return self.matcher == context.get("tool_name", "")


# ---------------------------------------------------------------------------
# 3. HookResult — 钩子返回结果
# ---------------------------------------------------------------------------

@dataclass
class HookResult:
    """钩子执行结果 (类比 Claude Code: hook stdout JSON)."""
    continue_execution: bool = True
    decision: Optional[str] = None
    updated_input: Optional[Dict] = None
    reason: Optional[str] = None
    system_message: Optional[str] = None


# ---------------------------------------------------------------------------
# 4. HookManager — 钩子管理器
# ---------------------------------------------------------------------------

class HookManager:
    """管理和执行钩子 (类比 Claude Code: executeHooks)."""

    def __init__(self):
        self.hooks: List[Hook] = []

    def register(self, hook: Hook):
        self.hooks.append(hook)
        self.hooks.sort(key=lambda h: h.priority)

    async def execute(self, event: HookEvent, context: Dict) -> HookResult:
        """执行所有匹配的钩子."""
        result = HookResult()

        for hook in self.hooks:
            if hook.event != event:
                continue
            if not hook.matches(context):
                continue

            try:
                hook_output = hook.callback(context)

                if isinstance(hook_output, dict):
                    if hook_output.get("continue") is False:
                        result.continue_execution = False
                        result.reason = hook_output.get("reason", "Blocked by hook")
                        return result

                    if hook_output.get("decision") == "block":
                        result.continue_execution = False
                        result.reason = hook_output.get("reason", "Blocked by hook")
                        return result

                    if "updated_input" in hook_output:
                        result.updated_input = hook_output["updated_input"]

                    if "system_message" in hook_output:
                        result.system_message = hook_output["system_message"]

            except Exception as e:
                print(f"  [Hook error] {hook.name}: {e}")

        return result


# ---------------------------------------------------------------------------
# 5. Built-in Hooks
# ---------------------------------------------------------------------------

def create_builtin_hooks() -> List[Hook]:
    def logging_hook(context: Dict) -> Dict:
        tool_name = context.get("tool_name", "unknown")
        tool_input = context.get("tool_input", {})
        print(f"  [LOG] {tool_name}({json.dumps(tool_input, ensure_ascii=False)[:60]})")
        return {"continue": True}

    def input_validation_hook(context: Dict) -> Dict:
        path = context.get("tool_input", {}).get("path", "")
        if ".." in path:
            return {"continue": False, "reason": f"Path traversal: {path}"}
        return {"continue": True}

    def dangerous_command_hook(context: Dict) -> Dict:
        command = context.get("tool_input", {}).get("command", "")
        for pattern in ["rm -rf /", "mkfs", "dd if="]:
            if pattern in command:
                return {"decision": "block", "reason": f"Dangerous: {command[:40]}"}
        return {"continue": True}

    def sensitive_file_hook(context: Dict) -> Dict:
        path = context.get("tool_input", {}).get("path", "")
        for kw in [".env", "credentials", "secret"]:
            if kw in path.lower():
                return {"continue": False, "reason": f"Sensitive: {path}"}
        return {"continue": True}

    return [
        Hook("logging", HookEvent.PRE_TOOL_USE, logging_hook, priority=0),
        Hook("validation", HookEvent.PRE_TOOL_USE, input_validation_hook, priority=1),
        Hook("dangerous_cmd", HookEvent.PRE_TOOL_USE, dangerous_command_hook, matcher="run_command", priority=2),
        Hook("sensitive_file", HookEvent.PRE_TOOL_USE, sensitive_file_hook, matcher="read_file", priority=3),
    ]


# ---------------------------------------------------------------------------
# 6. Agent with Hooks
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful coding assistant.
Tools: read_file(path), write_file(path, content), run_command(command)"""

TOOLS = [
    {"name": "read_file", "description": "Read a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "run_command", "description": "Run a command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
]


def execute_tool(name: str, input_data: dict) -> str:
    if name == "read_file":
        return f"[Content of {input_data.get('path', '?')}]: ..."
    elif name == "write_file":
        return f"[Wrote to {input_data.get('path', '?')}]"
    elif name == "run_command":
        return f"[Ran: {input_data.get('command', '?')}]"
    return f"Unknown: {name}"


async def agent_loop_with_hooks(
    client: Anthropic,
    user_message: str,
    hook_manager: HookManager,
    messages: Optional[List[Dict]] = None,
) -> List[Dict]:
    """带钩子的 Agent 循环."""
    if messages is None:
        messages = []
    messages.append({"role": "user", "content": user_message})

    await hook_manager.execute(HookEvent.SESSION_START, {"user_message": user_message})

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_use_blocks = [b for b in response.content if hasattr(b, "type") and b.type == "tool_use"]

        if not tool_use_blocks:
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\nAssistant: {block.text}")
            break

        tool_results = []
        for block in tool_use_blocks:
            tool_input = dict(block.input) if hasattr(block, 'input') else {}
            hook_ctx = {"tool_name": block.name, "tool_input": tool_input}

            # Pre-tool-use hook
            pre = await hook_manager.execute(HookEvent.PRE_TOOL_USE, hook_ctx)

            if not pre.continue_execution:
                reason = pre.reason or "Blocked"
                print(f"  [BLOCKED] {block.name}: {reason}")
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": f"Error: {reason}", "is_error": True})
                continue

            if pre.updated_input:
                tool_input = pre.updated_input

            result = execute_tool(block.name, tool_input)
            print(f"  [OK] {block.name}")

            # Post-tool-use hook
            post_ctx = {"tool_name": block.name, "tool_input": tool_input, "result": result}
            post = await hook_manager.execute(HookEvent.POST_TOOL_USE, post_ctx)

            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})

        messages.append({"role": "user", "content": tool_results})

    await hook_manager.execute(HookEvent.SESSION_END, {"messages": len(messages)})
    return messages


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def demo():
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    print("=" * 60)
    print("S08: Hook System Demo")
    print("=" * 60)

    manager = HookManager()
    for hook in create_builtin_hooks():
        manager.register(hook)
        print(f"  Registered: {hook.name} ({hook.event.value})")

    # Test hooks
    print("\n--- Hook Tests ---")
    r = await manager.execute(HookEvent.PRE_TOOL_USE, {"tool_name": "read_file", "tool_input": {"path": "../../etc/passwd"}})
    print(f"  Path traversal: blocked={not r.continue_execution}")

    r = await manager.execute(HookEvent.PRE_TOOL_USE, {"tool_name": "run_command", "tool_input": {"command": "rm -rf /"}})
    print(f"  Dangerous cmd: blocked={not r.continue_execution}")

    r = await manager.execute(HookEvent.PRE_TOOL_USE, {"tool_name": "read_file", "tool_input": {"path": ".env"}})
    print(f"  Sensitive file: blocked={not r.continue_execution}")

    r = await manager.execute(HookEvent.PRE_TOOL_USE, {"tool_name": "read_file", "tool_input": {"path": "/tmp/test.py"}})
    print(f"  Normal read: allowed={r.continue_execution}")

    # Run agent
    print("\n--- Agent with Hooks ---")
    await agent_loop_with_hooks(
        client,
        "Read the file config.json and show me what's in it.",
        manager,
    )
    print("\n--- Done ---")


if __name__ == "__main__":
    asyncio.run(demo())
