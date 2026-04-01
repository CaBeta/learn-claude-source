# Session 02: Tool Use — 给代理装上双手

```
进度: [■■□□□□□□□□] 20%   s01 ──► s02 ──► s03 ──► s04 ──► ...
                          你在这里
```

> *没有工具的代理只是聊天机器人 — 给它手,它才能干活*

## Problem — 我们在解决什么问题?

s01 的 agent 能循环了,但它只会说话。它不能读文件、不能写文件、不能执行命令。它是一个只会聊天的 agent — 本质上和 ChatGPT 没区别。

真正的 coding agent 需要 **工具 (Tools)**:
- 读取项目中的文件
- 写入新文件或修改文件
- 列出目录结构
- 执行 shell 命令

有了工具,agent 就能 **感知环境并采取行动**。

## Solution — Dispatch Map 架构

```
                    ┌──────────────────────────────────────────┐
                    │            Tool Use Flow                 │
                    │                                          │
                    │   ┌───────────────────────┐              │
                    │   │  Model Response        │              │
                    │   │  stop_reason: tool_use │              │
                    │   └───────────┬───────────┘              │
                    │               │                          │
                    │               │  提取 tool_use blocks     │
                    │               ▼                          │
                    │   ┌───────────────────────┐              │
                    │   │  Dispatch Map          │              │
                    │   │                        │              │
                    │   │  "read_file"  ──► read_file()        │
                    │   │  "write_file" ──► write_file()       │
                    │   │  "list_files" ──► list_files()       │
                    │   │                        │              │
                    │   └───────────┬───────────┘              │
                    │               │                          │
                    │               ▼                          │
                    │   ┌───────────────────────┐              │
                    │   │  Execute & Collect     │              │
                    │   │  工具返回结果           │              │
                    │   └───────────┬───────────┘              │
                    │               │                          │
                    │               ▼                          │
                    │   ┌───────────────────────┐              │
                    │   │  tool_result message   │              │
                    │   │  送回模型继续循环       │              │
                    │   └───────────────────────┘              │
                    │                                          │
                    └──────────────────────────────────────────┘
```

## How It Works — 逐步拆解

### Step 1: 定义工具 Schema

每个工具需要一个 **JSON Schema** 描述,告诉模型:
- 工具叫什么名字
- 做什么事 (description)
- 需要什么参数 (parameters)

```python
tools = [
    {
        "name": "read_file",
        "description": "读取指定路径的文件内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径",
                }
            },
            "required": ["path"],
        },
    }
]
```

### Step 2: 把工具列表传给 API

调用 `messages.create` 时传入 `tools` 参数:

```python
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=tools,        # <-- 传入工具定义
    messages=messages,
)
```

### Step 3: 构建 Dispatch Map

一个简单的字典,把工具名映射到处理函数:

```python
dispatch_map = {
    "read_file":  handle_read_file,
    "write_file": handle_write_file,
    "list_files": handle_list_files,
}
```

当模型返回 `tool_use` block 时,根据 `block.name` 查找对应的处理函数。

### Step 4: 执行工具,收集结果

```python
tool_results = []
for block in response.content:
    if block.type == "tool_use":
        # 查表,调用对应的处理函数
        handler = dispatch_map[block.name]
        result = handler(**block.input)
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result,
        })
```

### Step 5: 将结果送回模型

工具执行结果以 `tool_result` 消息的形式追加到消息历史:

```python
# 1. 先加入 assistant 的回复 (包含 tool_use 请求)
messages.append({"role": "assistant", "content": response.content})
# 2. 再加入工具执行结果
messages.append({"role": "user", "content": tool_results})
# 3. 继续循环,让模型看到工具结果后继续思考
```

## Claude Code 源码对照

| 概念              | 文件                    | 说明                                |
|-------------------|------------------------|-------------------------------------|
| 工具基类/工厂      | `Tool.ts`              | `buildTool` 工厂函数,统一工具接口     |
| 工具注册          | `tools.ts`             | `getAllBaseTools()` 返回所有可用工具   |
| 工具执行          | `toolExecution.ts`     | `runToolUse()` 执行单个工具调用       |
| Schema 定义       | 各工具目录              | 每个工具有自己的 `schema` 导出        |
| 结果处理          | `query.ts`             | tool_result 消息组装并追加到历史      |

Claude Code 的工具体系远比我们的复杂:
- 每个工具是一个 TypeScript class,有 `execute()` 和 `schema` 方法
- 工具有权限系统 (read/write/execute)
- 工具结果有截断机制 (防止超长输出)
- 有 `AgentTool` 用于子代理 (s04 会讲到)

## What Changed From s01

| 方面            | s01 (上一节)              | s02 (本节)                        |
|-----------------|--------------------------|-----------------------------------|
| API 调用        | 无工具                   | 传入 `tools` 参数                  |
| tool_use 处理   | 打印后退出               | 通过 dispatch map 执行真实工具      |
| 消息历史        | 只有 user/assistant      | 增加 tool_result 消息类型          |
| 文件操作        | 无                      | read_file, write_file, list_files  |
| 循环次数        | 几乎只有 1 轮             | 可多轮循环完成复杂任务              |

## Try It — 动手练习

1. **运行工具 agent**:
   ```bash
   export ANTHROPIC_API_KEY="your-key"
   python agents/s02_tool_use.py
   ```
   试试让 agent 帮你读取一个文件、列出当前目录、创建新文件。

2. **添加新工具**: 参考现有工具,添加一个 `delete_file(path)` 工具。
   - 定义 JSON Schema
   - 实现处理函数
   - 注册到 dispatch map

3. **观察多轮循环**: 输入 "读取当前目录的文件,然后总结项目结构"。观察 agent 会:
   - 第 1 轮: 调用 list_files
   - 第 2 轮: 可能调用 read_file 读几个文件
   - 第 3 轮: 输出总结 (end_turn)

4. **思考题**: 如果工具执行出错怎么办? 目前的代码是如何处理错误的? 如果模型传了错误的参数会怎样?
