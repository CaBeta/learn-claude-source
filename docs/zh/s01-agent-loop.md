# Session 01: Agent Loop — 代理的核心循环

---

```
进度: [■□□□□□□□□□] 10%   s01 ──► s02 ──► s03 ──► s04 ──► ...
         你在这里
```

---

> *一切始于一个循环 — call model, check stop, repeat*

---

## Problem — 我们在解决什么问题?

一次 API 调用不是 agent。你问它一个问题,它回答,结束。但真正的 coding agent 需要能够 **连续思考和行动**:

- 用户说 "帮我创建一个项目"
- Agent 思考 → 需要先看看目录结构 → 调用工具
- 拿到结果 → 继续思考 → 需要创建文件 → 调用工具
- 拿到结果 → 继续思考 → 任务完成 → 输出总结

这个 **不断循环、直到任务完成** 的过程,就是 Agent Loop。

---

## Solution — 核心架构

```
                    ┌──────────────────────────────────┐
                    │         Agent Loop                │
                    │                                  │
    ┌──────────────►│   ┌──────────────────────┐       │
    │               │   │  1. Build Messages    │       │
    │               │   │     (user + history)  │       │
    │               │   └──────────┬───────────┘       │
    │               │              │                    │
    │               │   ┌──────────▼───────────┐       │
    │               │   │  2. Call Model        │       │
    │               │   │     (Anthropic API)   │       │
    │               │   └──────────┬───────────┘       │
    │               │              │                    │
    │               │   ┌──────────▼───────────┐       │
    │               │   │  3. Check stop_reason │       │
    │               │   └──────┬───────┬────────┘      │
    │               │          │       │                │
    │               │   end_turn│   tool_use            │
    │               │          │       │                │
    │               │   ┌──────▼──┐ ┌───▼────────┐     │
    │               │   │ 4a.输出  │ │ 4b.执行工具 │     │
    │               │   │  文本    │ │  拿到结果   │     │
    │               │   │  结束!   │ │            │     │
    │               │   └─────────┘ └───┬────────┘     │
    │               │                    │              │
    │               │          把结果加入消息历史         │
    └───────────────┼────────────────────┘              │
                    │                                  │
                    └──────────────────────────────────┘
```

---

## How It Works — 逐步拆解

### Step 1: 接收用户输入

用户的输入是整个 loop 的起点。它被封装成一条 `message` 放入消息历史:

```python
messages = [{"role": "user", "content": "帮我创建一个 hello.py 文件"}]
```

### Step 2: 调用模型

把整个消息历史发给 Anthropic API,拿到模型的回复:

```python
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=messages,
)
```

### Step 3: 检查 stop_reason

模型回复中有一个关键字段 `stop_reason`,它决定了下一步做什么:

| stop_reason     | 含义                         | 下一步         |
|-----------------|------------------------------|----------------|
| `"end_turn"`    | 模型想说话,任务完成或需要用户输入 | 输出文本,结束循环 |
| `"tool_use"`    | 模型想调用工具                 | 执行工具,继续循环 |
| `"max_tokens"`  | token 用完了                  | 截断,结束循环    |

### Step 4a: end_turn — 输出并结束

如果 `stop_reason` 是 `end_turn`,说明模型觉得话说完了:

```python
if response.stop_reason == "end_turn":
    print(response.content[0].text)
    break  # 退出 while True 循环
```

### Step 4b: tool_use — 执行工具并循环

如果 `stop_reason` 是 `tool_use`,说明模型想调用工具。但目前我们还没有工具,所以先打印出来:

```python
if response.stop_reason == "tool_use":
    print("模型想要调用工具,但我们还没有工具实现...")
    break  # s02 会实现真正的工具调用
```

### Step 5: 消息历史的维护

每一轮循环,模型的回复和工具的结果都会被追加到 `messages` 中:

```python
# 模型的回复加入历史
messages.append({"role": "assistant", "content": response.content})
# 工具执行结果加入历史 (s02 详细展开)
messages.append({"role": "user", "content": tool_results})
```

---

## Claude Code 源码对照

Claude Code 的核心循环在 `query.ts` 中:

| 概念              | 文件              | 行号    | 说明                           |
|-------------------|-------------------|---------|--------------------------------|
| while(true) 主循环 | `query.ts`        | ~307    | `while (true) { ... }` 经典结构 |
| query 函数入口    | `query.ts`        | ~219    | async generator,接收消息历史    |
| stop_reason 判断  | `query.ts`        | ~320    | 检查 `stop_reason` 决定下一步    |
| 消息历史管理      | `query.ts`        | ~340    | assistant/user 消息交替追加      |

关键源码片段 (简化):

```typescript
// query.ts ~307
while (true) {
  // 1. 调用 API
  const response = await callAPI(messages, tools, options)

  // 2. 检查 stop_reason
  if (response.stop_reason === "end_turn") {
    yield { type: "assistant", content: response.content }
    break
  }

  // 3. 处理 tool_use
  if (response.stop_reason === "tool_use") {
    const toolResults = await executeTools(response.content)
    messages.push({ role: "assistant", content: response.content })
    messages.push({ role: "user", content: toolResults })
    // 继续循环...
  }
}
```

注意 Claude Code 使用的是 **async generator** (`yield`),这样可以逐步产出中间结果,而不是等到全部完成。

---

## What Changed From s00

| 方面            | s00 (之前)        | s01 (本节)               |
|-----------------|-------------------|--------------------------|
| 调用方式        | 单次 API 调用      | while(true) 循环调用      |
| 消息历史        | 无               | 维护完整 messages 数组     |
| stop_reason     | 不处理            | 检查并分支处理             |
| 工具调用        | 无               | 识别 tool_use 但不执行     |
| 输出            | 直接打印          | 区分文本输出和工具需求      |

---

## Try It — 动手练习

1. **运行基础 agent**:
   ```bash
   export ANTHROPIC_API_KEY="your-key"
   python agents/s01_agent_loop.py
   ```
   输入一些简单问题,观察模型的 `stop_reason` 和回复。

2. **观察循环次数**:
   在代码中加入一个计数器,打印每一轮循环的序号。对于没有工具的 agent,你会发现它几乎总是在第一轮就 `end_turn`。

3. **思考题**: 为什么没有工具的 agent 只会循环一次? 模型在什么情况下才会返回 `tool_use`?

4. **进阶挑战**: 试着把 `while True` 改成递归调用。思考哪种方式更好,为什么 Claude Code 选择了 `while True`。

---

**下一节**: [s02 - Tool Use](./s02-tool-use.md) — 给 agent 装上双手,让它能读写文件。
