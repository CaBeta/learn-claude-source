# S05: Context Management — 上下文管理

> s01 > s02 > s03 > s04 > **[ s05 ]** > s06 > s07 > s08 > s09 > s10 > s11 > s12

*记忆是有限的 — 聪明的代理知道该忘记什么*

## Problem

代理在运行过程中会不断积累上下文：读取的文件内容、执行的命令输出、工具返回的结果。假设你的代理读了 30 个文件、跑了 20 条命令，context window 里已经堆积了 100K+ tokens。模型的 context window 是有限的（比如 200K tokens），一旦超出，API 调用就会报错。

你需要一套机制来管理这些不断膨胀的对话历史 — 在保留关键信息的同时，丢弃不再需要的内容。

## Solution

```
messages (原始对话历史)
  |
  v
+----------------------------------------------------------+
|                  5-Layer Context Pipeline                 |
|                                                          |
|  [1] Budget Layer                                        |
|      控制 tool result 的总大小                            |
|      |                                                   |
|  [2] Snip Layer                                          |
|      截断过长的历史 tool output                           |
|      |                                                   |
|  [3] Microcompact Layer                                  |
|      将旧 tool 结果替换为简短摘要                         |
|      |                                                   |
|  [4] Collapse Layer                                      |
|      投影折叠视图 (保留结构，省略细节)                    |
|      |                                                   |
|  [5] Autocompact Layer                                   |
|      完整上下文压缩 → 生成 summary 替换历史              |
|                                                          |
+----------------------------------------------------------+
  |
  v
messagesForQuery (处理后，送入 API)
```

## How It Works

### 1. Token Counting — 估算对话大小

在做任何管理之前，你需要知道当前对话有多少 tokens。精确计数需要调用 tokenizer，但估算更快：

```python
def estimate_tokens(text: str) -> int:
    """Rough estimation: ~4 chars per token for English, ~2 for CJK."""
    cjk_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - cjk_chars
    return int(other_chars / 4 + cjk_chars / 2)

def count_messages_tokens(messages: list[dict]) -> int:
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total += estimate_tokens(str(block))
    return int(total * 1.33)  # 4/3 padding for safety
```

### 2. Budget Layer — 控制 Tool Result 总量

最简单的策略：给每个 tool result 设定大小上限，超出的直接截断。

```python
def apply_tool_result_budget(messages: list[dict], max_tokens: int = 5000) -> list[dict]:
    """Truncate individual tool results that exceed the budget."""
    result = []
    for msg in messages:
        if msg.get("role") == "user" and isinstance(msg.get("content"), list):
            new_content = []
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    text = str(block.get("content", ""))
                    if estimate_tokens(text) > max_tokens:
                        half = len(text) // 2
                        block = {**block, "content": text[:half] + "\n...[truncated]...\n" + text[-half:]}
                new_content.append(block)
            result.append({**msg, "content": new_content})
        else:
            result.append(msg)
    return result
```

### 3. Snip Layer — 截断旧输出

当整体 token 数接近阈值时，从最旧的 tool result 开始截断：

```python
def snip_old_results(messages: list[dict], max_tokens: int) -> tuple[list[dict], int]:
    """Snip (truncate) old tool results to free tokens."""
    total = count_messages_tokens(messages)
    if total <= max_tokens:
        return messages, 0
    freed = 0
    result = []
    for msg in messages:
        if total - freed <= max_tokens:
            result.append(msg)
            continue
        # Truncate old tool results
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
```

### 4. Microcompact — 用摘要替换旧结果

比截断更聪明的策略：调用模型把旧 tool result 总结成一句话。

```python
def microcompact_messages(messages: list[dict], max_age: int = 3) -> list[dict]:
    """Replace old tool results with brief summaries."""
    result = []
    tool_result_count = 0
    for msg in messages:
        if msg.get("role") == "user" and isinstance(msg.get("content"), list):
            new_content = []
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tool_result_count += 1
                    if tool_result_count <= max_age:
                        new_content.append(block)  # Keep recent results
                    else:
                        text = str(block.get("content", ""))
                        summary = text[:100] + "...[summarized]"
                        new_content.append({**block, "content": summary})
                else:
                    new_content.append(block)
            result.append({**msg, "content": new_content})
        else:
            result.append(msg)
    return result
```

### 5. Autocompact — 完整上下文压缩

当以上所有措施都不够时，最后一道防线：把整个对话历史压缩成一个 summary。

```python
async def autocompact(client, messages: list[dict], system_prompt: str) -> list[dict]:
    """Compress entire conversation into a summary."""
    conversation_text = ""
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(str(b) for b in content)
        conversation_text += f"[{role}]: {content[:500]}\n"

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content":
            f"Summarize this conversation, preserving key decisions, code changes, "
            f"and current state:\n\n{conversation_text}"}],
    )
    summary = response.content[0].text

    # Replace messages with summary
    return [
        {"role": "user", "content": f"[Previous conversation summary]:\n{summary}"},
        messages[-1] if messages else {"role": "user", "content": "Continue."},
    ]
```

### 6. 串联所有层 — Context Manager

```python
class ContextManager:
    def __init__(self, max_tokens: int = 100000, tool_budget: int = 5000):
        self.max_tokens = max_tokens
        self.tool_budget = tool_budget

    async def manage(self, client, messages: list[dict]) -> list[dict]:
        # Layer 1: Budget
        msgs = apply_tool_result_budget(messages, self.tool_budget)
        # Layer 2: Snip
        msgs, freed = snip_old_results(msgs, self.max_tokens)
        # Layer 3: Microcompact
        msgs = microcompact_messages(msgs)
        # Layer 5: Autocompact (last resort)
        if count_messages_tokens(msgs) > self.max_tokens:
            msgs = await autocompact(client, msgs, "")
        return msgs
```

## Claude Code 源码对照

| 机制 | 源文件 | 关键行 |
|------|--------|--------|
| 5 层管线入口 | `query.ts` | L369-543 (循环体开头) |
| Budget Layer | `utils/toolResultStorage.ts` → `query.ts` | L379: `applyToolResultBudget()` |
| Snip Layer | `services/compact/snipCompact.ts` → `query.ts` | L396-410: `snipCompactIfNeeded()` |
| Microcompact | `services/compact/microCompact.ts` | L253: `microcompactMessages()` |
| Microcompact token 估算 | `services/compact/microCompact.ts` | L164: `estimateMessageTokens()` |
| 可压缩工具列表 | `services/compact/microCompact.ts` | L41-50: `COMPACTABLE_TOOLS` |
| Time-based microcompact | `services/compact/microCompact.ts` | L422: `evaluateTimeBasedTrigger()` |
| Cached microcompact | `services/compact/microCompact.ts` | L305: `cachedMicrocompactPath()` |
| Context Collapse | `services/contextCollapse/index.ts` → `query.ts` | L440-447: `applyCollapsesIfNeeded()` |
| Autocompact 主逻辑 | `services/compact/autoCompact.ts` | L241: `autoCompactIfNeeded()` |
| Autocompact 阈值计算 | `services/compact/autoCompact.ts` | L72: `getAutoCompactThreshold()` |
| Token 警告状态 | `services/compact/autoCompact.ts` | L93: `calculateTokenWarningState()` |
| Circuit breaker | `services/compact/autoCompact.ts` | L70: `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES` |
| 完整压缩 (生成 summary) | `services/compact/compact.ts` | L313: `compactConversation()` |
| while(true) 循环入口 | `query.ts` | L307: `while (true) {` |

## What Changed From s04

| 特性 | s04 SubAgent | s05 Context Management |
|------|-------------|----------------------|
| 核心关注 | 子代理调度 | 上下文大小控制 |
| 新增组件 | SubAgent dispatch | ContextManager (5层管线) |
| Token 感知 | 无 | 全程跟踪 token 数量 |
| 对话压缩 | 无 | Snip / Microcompact / Autocompact |
| 安全阈值 | 无 | Warning / Error / Blocking 三级阈值 |
| 压缩失败恢复 | 无 | Circuit breaker (最多连续失败3次) |

## Try It

1. **修改 `max_tokens` 阈值**：把 `ContextManager` 的 `max_tokens` 设为很小的值（比如 500），观察 autocompact 如何被触发。观察压缩前后的消息数量变化。

2. **实现自定义 Snip 策略**：当前 snip 只是简单截断。试着实现一个"智能 snip"——保留文件路径和关键错误信息，只删掉大量代码输出。提示：在 snip 前 parse tool result，识别文件路径（以 `/` 或 `./` 开头的行）。

3. **添加 Warning 机制**：参考 Claude Code 的 `calculateTokenWarningState()`，在 token 使用量达到 80% 时打印警告，90% 时打印错误，95% 时阻止继续。把这些阈值做成可配置的。

4. **对比不同压缩策略**：用同一段长对话，分别只用 snip、只用 microcompact、只用 autocompact，对比压缩后的 token 数和模型回答质量的差异。
