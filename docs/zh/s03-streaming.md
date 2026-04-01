# Session 03: Streaming — 实时流式输出

---

```
进度: [■■■□□□□□□□] 30%   s01 ──► s02 ──► s03 ──► s04 ──► ...
                                   你在这里
```

---

> *等待是毒药 — 流式输出让用户看到思考的过程*

---

## Problem — 我们在解决什么问题?

s02 的 agent 能用工具了,但用户体验很差: **用户盯着空白屏幕,等待完整响应返回**。

考虑这个场景:
- Agent 需要读取 3 个文件,分析后写一个总结
- 整个过程可能需要 15-20 秒
- 在这段时间里,用户什么都看不到

这就像打电话时对方沉默 20 秒然后突然说一大段话 — 你会以为断了线。

**Streaming (流式输出)** 解决了这个问题:
- 文字生成时,逐字/逐句显示
- 工具调用时,实时显示进度
- 用户能感知 agent 在 "思考" 和 "工作"

---

## Solution — 流式事件架构

```
    ┌─────────────────────────────────────────────────────┐
    │              Streaming Event Flow                    │
    │                                                     │
    │   Anthropic API                                     │
    │   ┌──────────┐                                      │
    │   │ stream   │                                      │
    │   │ = True   │                                      │
    │   └────┬─────┘                                      │
    │        │                                            │
    │        │  事件流 (Server-Sent Events)                │
    │        │                                            │
    │        ├──► message_start                           │
    │        │     (response 元信息)                       │
    │        │                                            │
    │        ├──► content_block_start                     │
    │        │     type: "text"                           │
    │        ├──► content_block_delta  ──► 逐字输出        │
    │        │     delta: { text: "你" }     "你"         │
    │        ├──► content_block_delta  ──► "你好"         │
    │        │     delta: { text: "好" }                  │
    │        ├──► content_block_stop                     │
    │        │                                            │
    │        ├──► content_block_start                     │
    │        │     type: "tool_use"                       │
    │        ├──► content_block_delta                     │
    │        │     delta: { partial_json: ... }           │
    │        ├──► content_block_stop                     │
    │        │                                            │
    │        ├──► message_delta                           │
    │        │     stop_reason: "end_turn"                │
    │        └──► message_stop                            │
    │                                                     │
    └─────────────────────────────────────────────────────┘
```

---

## How It Works — 逐步拆解

### Step 1: 从 create 切换到 stream

把 `client.messages.create()` 换成 `client.messages.stream()`:

```python
# 之前 (s02): 等完整响应
response = client.messages.create(...)

# 现在 (s03): 流式获取
with client.messages.stream(...) as stream:
    for event in stream:
        # 实时处理每个事件
        handle_event(event)
```

或者使用 `create(stream=True)`:

```python
response = client.messages.create(stream=True, ...)
with response as stream:
    for line in stream.iter_lines():
        ...
```

### Step 2: 理解事件类型

Anthropic streaming API 会发送以下事件:

| 事件                         | 含义                   | 包含数据               |
|------------------------------|------------------------|------------------------|
| `message_start`              | 响应开始               | model, usage 信息      |
| `content_block_start`        | 一个内容块开始          | type (text/tool_use)   |
| `content_block_delta`        | 内容增量               | text 或 partial_json   |
| `content_block_stop`         | 内容块结束             | 无                     |
| `message_delta`              | 消息级更新             | stop_reason            |
| `message_stop`               | 响应结束               | 无                     |

### Step 3: 处理 text delta

文本增量是用户最直接感受到的:

```python
if event.type == "content_block_delta":
    if event.delta.type == "text_delta":
        # 逐字打印,不换行
        print(event.delta.text, end="", flush=True)
```

### Step 4: 处理 tool_use

工具调用在流式中是增量式传输 JSON 的:

```python
if event.type == "content_block_start":
    if event.content_block.type == "tool_use":
        print(f"\n[调用工具: {event.content_block.name}]")

if event.type == "content_block_delta":
    if event.delta.type == "input_json_delta":
        # JSON 是逐步到达的,需要拼接
        partial_json += event.delta.partial_json
```

### Step 5: 使用 SDK 的 get_final_message()

Anthropic Python SDK 提供了便利方法:

```python
with client.messages.stream(...) as stream:
    # 可以实时读取 text
    for text in stream.text_stream:
        print(text, end="", flush=True)

    # 获取完整的最终消息
    final_message = stream.get_final_message()
```

---

## Claude Code 源码对照

| 概念                    | 文件                      | 说明                               |
|-------------------------|---------------------------|-------------------------------------|
| 流式消息处理             | `query.ts` ~652-997      | 处理 SSE 事件流的核心逻辑           |
| StreamingToolExecutor   | `streamingToolExecutor.ts`| 流式场景下的工具执行器               |
| 文本增量显示             | UI 层                     | 实时渲染 markdown 和工具进度        |
| 工具调用流式解析         | `query.ts`               | 从 delta 中逐步解析 tool_use JSON   |

Claude Code 的流式处理比我们复杂得多:
- 它需要实时渲染 Markdown (代码高亮、表格)
- 工具执行时显示进度条和 spinner
- 流式接收的同时需要解析完整的 tool_use 结构
- 需要处理网络断线重连

---

## What Changed From s02

| 方面              | s02 (上一节)              | s03 (本节)                          |
|-------------------|--------------------------|-------------------------------------|
| API 调用方式      | `messages.create()`      | `messages.stream()`                 |
| 响应处理          | 等完整响应后处理          | 逐事件实时处理                       |
| 文本输出          | 一次性打印全部            | 逐字流式打印                         |
| 工具调用          | 完整 JSON 一次拿到        | 增量 JSON 拼接                       |
| 用户体验          | 等待空白屏幕              | 实时看到进度                         |
| 事件类型          | 只有 response 对象        | message_start/delta/stop 等          |

---

## Try It — 动手练习

1. **运行流式 agent**:
   ```bash
   export ANTHROPIC_API_KEY="your-key"
   python agents/s03_streaming.py
   ```
   观察文字是如何逐字显示的。

2. **对比体验**: 先用 s02 的 agent 问一个需要多步操作的问题,再用 s03 问同样的问题。感受等待和实时输出的区别。

3. **添加颜色**: 在文本流中,尝试检测代码块 (`\`\`\``) 并用 ANSI 颜色码高亮显示。

4. **思考题**: 流式输出中,如何在还没有收到完整 `stop_reason` 的时候就判断模型要调用工具? (提示: 看 `content_block_start` 中的 type)

---

**上一节**: [s02 - Tool Use](./s02-tool-use.md)
**下一节**: [s04 - SubAgent](./s04-subagent.md) — 拆分大任务,让子代理处理。
