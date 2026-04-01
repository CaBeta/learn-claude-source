"""
s11 · Session & Memory — 会话记忆

演示如何实现跨会话的记忆系统。
Agent 自动提取对话中的关键信息，持久化到文件，在新会话中注入记忆。

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python s11_session_memory.py
"""

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"

# ---------------------------------------------------------------------------
# Memory File — 结构化记忆模板
# ---------------------------------------------------------------------------

# 类比: services/SessionMemory/prompts.ts:11-41
MEMORY_TEMPLATE = """# Session Title
_A short 5-10 word descriptive title for the session_

# Current State
_What is actively being worked on right now? Pending tasks, next steps._

# Task Specification
_What did the user ask to build? Design decisions, architecture choices._

# Files and Functions
_Important files, what they contain, why they are relevant._

# Errors & Corrections
_Errors encountered and how they were fixed. Approaches that failed._

# Learnings
_What worked well? What did not? Things to avoid in future._

# Worklog
_Step by step summary of what was attempted and done._
"""


class MemoryFile:
    """
    记忆文件管理器。
    类比: services/SessionMemory/sessionMemory.ts + prompts.ts

    记忆以 Markdown 格式存储，包含结构化分区。
    每次 memory extraction 时，用 LLM 分析对话并更新文件。
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self.path.write_text(MEMORY_TEMPLATE, encoding="utf-8")

    def read(self) -> str:
        """读取当前记忆内容"""
        return self.path.read_text(encoding="utf-8")

    def write(self, content: str):
        """写入新的记忆内容"""
        self.path.write_text(content, encoding="utf-8")

    def update_section(self, section: str, content: str):
        """更新特定分区的记忆"""
        current = self.read()
        lines = current.split("\n")
        in_section = False
        new_lines = []
        section_header = f"# {section}"

        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip() == section_header:
                in_section = True
                new_lines.append(line)
                # 跳过描述行（以 _ 开头的斜体）
                i += 1
                if i < len(lines) and lines[i].strip().startswith("_"):
                    new_lines.append(lines[i])
                    i += 1
                # 替换内容
                new_lines.append(content)
                # 跳过旧内容直到下一个分区
                while i < len(lines) and not lines[i].startswith("# "):
                    i += 1
                continue
            else:
                new_lines.append(line)
                i += 1

        self.write("\n".join(new_lines))


# ---------------------------------------------------------------------------
# SessionStore — 会话持久化
# ---------------------------------------------------------------------------

class SessionStore:
    """
    管理会话历史和记忆文件。
    类比: utils/sessionStorage.ts + services/SessionMemory/sessionMemoryUtils.ts
    """

    def __init__(self, base_dir: str = ".session_data"):
        self.base_dir = Path(base_dir)
        self.sessions_dir = self.base_dir / "sessions"
        self.memory_dir = self.base_dir / "memory"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session_id: str, messages: list[dict]):
        """保存完整会话历史"""
        path = self.sessions_dir / f"{session_id}.json"
        path.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_session(self, session_id: str) -> list[dict]:
        """加载之前的会话"""
        path = self.sessions_dir / f"{session_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return []

    def get_memory_file(self, project: str = "default") -> MemoryFile:
        """获取项目的记忆文件"""
        return MemoryFile(str(self.memory_dir / f"{project}_memory.md"))

    def list_sessions(self) -> list[str]:
        """列出所有会话"""
        return [p.stem for p in self.sessions_dir.glob("*.json")]


# ---------------------------------------------------------------------------
# Memory Extractor — 记忆提取器
# ---------------------------------------------------------------------------

@dataclass
class ExtractionState:
    """追踪记忆提取的状态"""
    last_extraction_msg_count: int = 0
    last_extraction_tool_calls: int = 0
    last_extraction_tokens: int = 0
    total_tool_calls: int = 0
    is_initialized: bool = False


# 类比: sessionMemoryUtils.ts:32-36
EXTRACTION_CONFIG = {
    "minimum_tokens_to_init": 2000,     # 首次提取的最低 token 数
    "minimum_tokens_between_updates": 1000,  # 两次提取间的最少 token 增长
    "tool_calls_between_updates": 3,     # 两次提取间的最少工具调用数
}


class MemoryExtractor:
    """
    从对话中提取关键信息，更新记忆文件。
    类比: services/SessionMemory/sessionMemory.ts

    触发条件:
    - Token 增长超过阈值 AND (工具调用超过阈值 OR 自然断点)
    """

    def __init__(self, memory_file: MemoryFile):
        self.memory_file = memory_file
        self.state = ExtractionState()

    def _count_tool_calls(self, messages: list[dict]) -> int:
        """统计消息中的工具调用次数"""
        count = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        count += 1
        return count

    def _estimate_tokens(self, messages: list[dict]) -> int:
        """粗略估算 token 数"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        total += len(str(block)) // 4
                    else:
                        total += len(str(block)) // 4
        return total

    def should_extract(self, messages: list[dict]) -> bool:
        """
        判断是否需要提取记忆。
        类比: sessionMemory.ts:134-181 shouldExtractMemory()
        """
        current_tokens = self._estimate_tokens(messages)

        # 检查初始化阈值
        if not self.state.is_initialized:
            if current_tokens < EXTRACTION_CONFIG["minimum_tokens_to_init"]:
                return False
            self.state.is_initialized = True

        # 检查 token 增长
        tokens_since = current_tokens - self.state.last_extraction_tokens
        token_met = tokens_since >= EXTRACTION_CONFIG["minimum_tokens_between_updates"]

        # 检查工具调用
        tool_calls = self._count_tool_calls(messages)
        tools_since = tool_calls - self.state.last_extraction_tool_calls
        tools_met = tools_since >= EXTRACTION_CONFIG["tool_calls_between_updates"]

        # 检查自然断点（最后一条消息不是工具调用）
        last_msg = messages[-1] if messages else {}
        last_content = last_msg.get("content", "")
        has_recent_tool = False
        if isinstance(last_content, list):
            has_recent_tool = any(
                isinstance(b, dict) and b.get("type") == "tool_use"
                for b in last_content
            )

        natural_break = not has_recent_tool

        # 触发条件: (token + tools) OR (token + natural_break)
        should = (token_met and tools_met) or (token_met and natural_break)

        if should:
            self.state.last_extraction_tokens = current_tokens
            self.state.last_extraction_tool_calls = tool_calls

        return should

    async def extract(self, messages: list[dict]) -> Optional[str]:
        """
        执行记忆提取。
        类比: sessionMemory.ts:272-350 extractSessionMemory()
        """
        current_memory = self.memory_file.read()

        extraction_prompt = f"""Analyze the following conversation and update the session notes.

Current notes:
<current_notes>
{current_memory}
</current_notes>

Conversation summary (last {len(messages)} messages):
"""

        for msg in messages[-6:]:  # 只取最近 6 条消息
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            parts.append(f"[Tool: {block.get('name', '')}]")
                        elif block.get("type") == "tool_result":
                            parts.append(f"[Result: {str(block.get('content', ''))[:100]}]")
                    else:
                        parts.append(str(block))
                content = " ".join(parts)

            extraction_prompt += f"\n[{role}]: {content[:300]}\n"

        extraction_prompt += """

Based on the conversation above, provide an updated version of the session notes.
Output the COMPLETE updated notes in markdown format, preserving all section headers.
Only update sections where there is new information. Keep info-dense content."""

        try:
            import asyncio
            response = await asyncio.to_thread(
                client.messages.create,
                model=MODEL,
                max_tokens=2048,
                messages=[{"role": "user", "content": extraction_prompt}],
            )

            updated = response.content[0].text
            self.memory_file.write(updated)
            print(f"  [Memory] 提取完成, 记忆文件已更新 ({len(updated)} chars)")
            return updated

        except Exception as e:
            print(f"  [Memory] 提取失败: {e}")
            return None


# ---------------------------------------------------------------------------
# Agent with Session Memory
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_WITH_MEMORY = """You are a helpful coding assistant with session memory.

{memory_context}

You have access to previous session notes above. Use this context to provide
continuity across conversations. Reference past work when relevant."""


def run_agent_with_memory(
    user_message: str,
    session_store: SessionStore,
    project: str = "default",
) -> str:
    """带记忆的 Agent"""
    memory_file = session_store.get_memory_file(project)
    memory_content = memory_file.read()

    # 注入记忆到 system prompt
    memory_context = ""
    if memory_content.strip() != MEMORY_TEMPLATE.strip():
        memory_context = f"""<session-memory>
{memory_content}
</session-memory>"""

    system = SYSTEM_PROMPT_WITH_MEMORY.format(memory_context=memory_context)

    messages = [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
    )

    reply = response.content[0].text
    return reply


# ---------------------------------------------------------------------------
# Main — 演示会话记忆系统
# ---------------------------------------------------------------------------

async def main():
    import asyncio

    print("=" * 60)
    print("s11 · Session & Memory")
    print("=" * 60)

    session_store = SessionStore()
    memory_file = session_store.get_memory_file("demo")
    extractor = MemoryExtractor(memory_file)

    # 模拟对话 1 — 积累信息
    print("\n--- 模拟会话 1: 积累信息 ---")
    conversation_1 = [
        {"role": "user", "content": "我在做一个 Python Web 项目，用 FastAPI 框架。"},
        {"role": "assistant", "content": "好的，FastAPI 是个好选择。你的项目结构是什么样的？"},
        {"role": "user", "content": "项目在 /app 目录下。main.py 是入口，routes/ 放路由，models/ 放数据模型。"},
        {"role": "assistant", "content": "了解。你有数据库配置吗？"},
        {"role": "user", "content": "用 SQLAlchemy + PostgreSQL。连接字符串在 config.py 里。之前有个坑：async engine 需要用 create_async_engine 而不是 create_engine，花了我半天时间才搞明白。"},
        {"role": "assistant", "content": "这是个常见的坑！async SQLAlchemy 确实需要 create_async_engine。"},
    ]

    # 检查是否应该提取记忆
    print(f"  Token 估算: {extractor._estimate_tokens(conversation_1)}")
    print(f"  是否触发提取: {extractor.should_extract(conversation_1)}")

    # 手动触发提取（演示用，正常由阈值控制）
    print("\n--- 记忆提取 ---")
    await extractor.extract(conversation_1)

    # 查看提取结果
    print("\n--- 记忆内容 ---")
    memory_content = memory_file.read()
    print(memory_content[:800])

    # 模拟对话 2 — 新会话，利用记忆
    print("\n\n--- 模拟会话 2: 新会话，利用记忆 ---")
    print("新会话启动，自动注入记忆到 system prompt...")

    new_user_message = "继续我之前的项目。帮我检查一下数据库连接配置是否正确。"
    print(f"用户: {new_user_message}")

    # 实际场景中会调用 run_agent_with_memory，这里展示记忆注入逻辑
    memory_for_injection = memory_file.read()
    if memory_for_injection.strip() != MEMORY_TEMPLATE.strip():
        print(f"\n注入的记忆 ({len(memory_for_injection)} chars):")
        print(memory_for_injection[:500] + "...")

    print("\nAgent 可以看到之前的记忆，知道:")
    print("  - 项目用 FastAPI + SQLAlchemy + PostgreSQL")
    print("  - 目录结构: main.py, routes/, models/, config.py")
    print("  - 之前的坑: async engine 需要用 create_async_engine")

    # 保存会话
    session_id = f"session-{uuid.uuid4().hex[:6]}"
    session_store.save_session(session_id, conversation_1)
    print(f"\n会话已保存: {session_id}")
    print(f"所有会话: {session_store.list_sessions()}")

    print("\n" + "=" * 60)
    print("演示完成。会话记忆让 Agent 跨会话保持上下文连续性。")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
