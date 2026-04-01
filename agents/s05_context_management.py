"""
S05: Context Management -- 上下文管理

运行方式:
    export ANTHROPIC_API_KEY=your-key
    python s05_context_management.py

功能:
    - Token 估算与计数
    - 5 层上下文管理管线: Budget -> Snip -> Microcompact -> Autocompact
    - 滑动窗口 + 摘要压缩
    - 三级阈值警告: Warning -> Error -> Blocking

依赖: pip install anthropic
"""

import os
import asyncio
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any, Union

try:
    from anthropic import AsyncAnthropic
except ImportError:
    print("请安装 anthropic: pip install anthropic")
    raise


# ---------------------------------------------------------------------------
# 1. Token Estimation
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """粗略估算: 英文 ~4 chars/token, 中文 ~2 chars/token."""
    if not text:
        return 0
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    other = len(text) - cjk
    return int(other / 4 + cjk / 2)


def count_messages_tokens(messages: List[Dict]) -> int:
    """估算消息列表的总 token 数，加 4/3 安全余量."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total += estimate_tokens(
                        block.get("content", "") or block.get("text", "") or str(block)
                    )
    return int(total * 1.33)


# ---------------------------------------------------------------------------
# 2. Budget Layer -- 单个 tool result 大小控制
# ---------------------------------------------------------------------------

def apply_tool_result_budget(messages: List[Dict], max_tokens: int = 5000) -> List[Dict]:
    """截断超过预算的 tool result,保留头尾."""
    result = []
    for msg in messages:
        if msg.get("role") == "user" and isinstance(msg.get("content"), list):
            new_content = []
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    text = str(block.get("content", ""))
                    if estimate_tokens(text) > max_tokens:
                        half = len(text) // 2
                        text = text[:half] + "\n...[budget truncated]...\n" + text[-half:]
                        block = {**block, "content": text}
                new_content.append(block)
            result.append({**msg, "content": new_content})
        else:
            result.append(msg)
    return result


# ---------------------------------------------------------------------------
# 3. Snip Layer -- 截断旧 tool output
# ---------------------------------------------------------------------------

def snip_old_results(messages: List[Dict], max_tokens: int) -> Tuple[List[Dict], int]:
    """从最旧的 tool result 开始截断，直到总 token 数低于阈值."""
    total = count_messages_tokens(messages)
    if total <= max_tokens:
        return messages, 0
    freed = 0
    result = []
    for msg in messages:
        if total - freed <= max_tokens:
            result.append(msg)
            continue
        if msg.get("role") == "user" and isinstance(msg.get("content"), list):
            new_content = []
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    text = str(block.get("content", ""))
                    tokens = estimate_tokens(text)
                    if tokens > 200:
                        snippet = text[:200] + "\n...[snipped]"
                        freed += tokens - estimate_tokens(snippet)
                        block = {**block, "content": snippet}
                new_content.append(block)
            result.append({**msg, "content": new_content})
        else:
            result.append(msg)
    return result, freed


# ---------------------------------------------------------------------------
# 4. Microcompact -- 用摘要替换旧 tool result
# ---------------------------------------------------------------------------

def microcompact_messages(messages: List[Dict], keep_recent: int = 3) -> List[Dict]:
    """保留最近 N 个 tool result,其余替换为简短摘要."""
    tool_result_count = 0
    result = []
    for msg in messages:
        if msg.get("role") == "user" and isinstance(msg.get("content"), list):
            new_content = []
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tool_result_count += 1
                    if tool_result_count <= keep_recent:
                        new_content.append(block)
                    else:
                        text = str(block.get("content", ""))
                        summary = text[:100] + "...[microcompacted]"
                        new_content.append({**block, "content": summary})
                else:
                    new_content.append(block)
            result.append({**msg, "content": new_content})
        else:
            result.append(msg)
    return result


# ---------------------------------------------------------------------------
# 5. Autocompact -- 完整上下文压缩
# ---------------------------------------------------------------------------

async def autocompact(
    client: AsyncAnthropic, messages: List[Dict]
) -> List[Dict]:
    """把整个对话历史压缩成一个 summary (最后一条消息保留)."""
    conversation_parts = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, list):
            parts = []
            for b in content:
                if isinstance(b, dict):
                    parts.append(str(b.get("content", b.get("text", "")))[:300])
                else:
                    parts.append(str(b)[:300])
            content = " ".join(parts)
        conversation_parts.append(f"[{role}]: {content[:500]}")

    conversation_text = "\n".join(conversation_parts)

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": (
                "Summarize this conversation. Preserve key decisions, "
                "file names, code changes, and the current task state. "
                "Be concise but complete enough to continue work:\n\n"
                + conversation_text
            ),
        }],
    )
    summary = response.content[0].text
    print(f"  [autocompact] Generated summary ({estimate_tokens(summary)} tokens)")

    # 用 summary 替换历史，保留最后一条用户消息
    last_user = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user = msg
            break

    compacted = [{
        "role": "user",
        "content": "[Previous conversation summary]:\n" + summary,
    }]
    if last_user and last_user != messages[0]:
        compacted.append(last_user)
    return compacted


# ---------------------------------------------------------------------------
# 6. ContextManager -- 串联所有层
# ---------------------------------------------------------------------------

@dataclass
class TokenThresholds:
    """三级 token 阈值配置."""
    warning_pct: float = 0.80   # 80% 打印警告
    error_pct: float = 0.90     # 90% 打印错误
    blocking_pct: float = 0.95  # 95% 阻止继续


class ContextManager:
    """5 层上下文管理管线 (对应 Claude Code query.ts L369-543)."""

    def __init__(
        self,
        max_tokens: int = 100_000,
        tool_budget: int = 5_000,
        keep_recent: int = 3,
        thresholds: Optional[TokenThresholds] = None,
    ):
        self.max_tokens = max_tokens
        self.tool_budget = tool_budget
        self.keep_recent = keep_recent
        self.thresholds = thresholds or TokenThresholds()

    def check_token_state(self, token_count: int) -> str:
        """检查 token 使用状态,返回 'ok' / 'warning' / 'error' / 'blocking'."""
        pct = token_count / self.max_tokens
        if pct >= self.thresholds.blocking_pct:
            return "blocking"
        elif pct >= self.thresholds.error_pct:
            return "error"
        elif pct >= self.thresholds.warning_pct:
            return "warning"
        return "ok"

    async def manage(self, client: AsyncAnthropic, messages: List[Dict]) -> List[Dict]:
        """运行完整的上下文管理管线."""
        original_tokens = count_messages_tokens(messages)
        print(f"  [context] Before management: {original_tokens} tokens")

        # 检查 token 状态
        state = self.check_token_state(original_tokens)
        if state == "warning":
            print(f"  [context] WARNING: {original_tokens}/{self.max_tokens} tokens used")
        elif state == "error":
            print(f"  [context] ERROR: {original_tokens}/{self.max_tokens} tokens used!")
        elif state == "blocking":
            print(f"  [context] BLOCKING: Force autocompact!")

        # Layer 1: Budget
        msgs = apply_tool_result_budget(messages, self.tool_budget)
        after_budget = count_messages_tokens(msgs)
        if after_budget < original_tokens:
            print(f"  [budget] {original_tokens} -> {after_budget} tokens")

        # Layer 2: Snip
        msgs, freed = snip_old_results(msgs, self.max_tokens)
        if freed > 0:
            print(f"  [snip] Freed {freed} tokens")

        # Layer 3: Microcompact
        msgs = microcompact_messages(msgs, self.keep_recent)
        after_micro = count_messages_tokens(msgs)
        if after_micro < after_budget - freed:
            print(f"  [microcompact] Further reduced to {after_micro} tokens")

        # Layer 5: Autocompact (last resort)
        if count_messages_tokens(msgs) > self.max_tokens:
            print("  [autocompact] Threshold exceeded, compressing...")
            msgs = await autocompact(client, msgs)

        final_tokens = count_messages_tokens(msgs)
        print(f"  [context] After management: {final_tokens} tokens "
              + f"({len(msgs)} messages, saved {original_tokens - final_tokens})")
        return msgs


# ---------------------------------------------------------------------------
# 7. Agent with Context Management
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful coding assistant. You have tools available.
When the user asks you to do something, use the appropriate tool."""

TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file and return its contents.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"],
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command and return the output.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "Shell command"}},
            "required": ["command"],
        },
    },
]


async def agent_loop(
    client: AsyncAnthropic,
    user_message: str,
    context_manager: ContextManager,
    messages: Optional[List[Dict]] = None,
) -> List[Dict]:
    """带上下文管理的 Agent Loop."""
    if messages is None:
        messages = []

    messages.append({"role": "user", "content": user_message})

    # 每轮循环开始前运行上下文管理 (对应 query.ts L369)
    messages = await context_manager.manage(client, messages)

    # 调用模型
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages,
    )

    # 收集助手回复
    assistant_content = response.content
    messages.append({"role": "assistant", "content": assistant_content})

    # 处理 tool calls (简化版: 只执行一轮)
    tool_blocks = [b for b in assistant_content if b.type == "tool_use"]
    if tool_blocks:
        tool_results = []
        for block in tool_blocks:
            # 模拟工具执行
            if block.name == "read_file":
                path = block.input.get("path", "")
                result = f"[Contents of {path}]: ... (simulated file content)"
            elif block.name == "run_command":
                cmd = block.input.get("command", "")
                result = f"[Output of `{cmd}`]: ... (simulated command output)"
            else:
                result = f"Unknown tool: {block.name}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

        # 再次调用模型获取最终回复
        messages = await context_manager.manage(client, messages)
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

    return messages


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def demo():
    client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # 使用极小的 max_tokens 来演示压缩效果
    context_manager = ContextManager(
        max_tokens=2000,       # 极小阈值,便于触发压缩
        tool_budget=500,
        keep_recent=2,
    )

    print("=" * 60)
    print("S05: Context Management Demo")
    print("=" * 60)

    messages: List[Dict] = []

    # 模拟一段长对话
    fake_history = [
        ("Read the file src/main.py", "[file content]: import os... (2000 chars)"),
        ("Run pytest tests/", "[test output]: 50 tests passed... (3000 chars)"),
        ("Read src/utils.py", "[file content]: def helper()... (1500 chars)"),
    ]

    for user_msg, tool_output in fake_history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": [
            {"type": "text", "text": f"I'll process: {user_msg}"},
            {"type": "tool_use", "id": f"tu_{len(messages)}", "name": "read_file",
             "input": {"path": "simulated"}},
        ]})
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": f"tu_{len(messages)}",
             "content": tool_output * 5},  # 放大以制造 token 压力
        ]})

    print(f"\nBefore context management: {count_messages_tokens(messages)} tokens, "
          + f"{len(messages)} messages\n")

    # 运行上下文管理
    managed = await context_manager.manage(client, messages)

    print(f"\nAfter context management: {count_messages_tokens(managed)} tokens, "
          + f"{len(managed)} messages")

    # 展示压缩结果
    print("\n--- Managed messages preview ---")
    for i, msg in enumerate(managed):
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for b in content:
                if isinstance(b, dict):
                    text_parts.append(str(b.get("content", b.get("text", "")))[:80])
            content = " | ".join(text_parts)
        print(f"  [{i}] {role}: {str(content)[:120]}...")

    # 现在用真实用户输入继续对话
    print("\n--- Now continuing with a real query ---")
    messages = await agent_loop(
        client,
        "What files did we just look at? Summarize what you found.",
        context_manager,
        managed,
    )

    # 打印最终回复
    last = messages[-1]
    if isinstance(last.get("content"), list):
        for block in last["content"]:
            if hasattr(block, "text"):
                print(f"\nAssistant: {block.text}")


if __name__ == "__main__":
    asyncio.run(demo())
