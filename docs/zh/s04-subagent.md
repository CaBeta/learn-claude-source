# Session 04: SubAgent — 派出子代理

```
进度: [■■■■□□□□□□] 40%   s01 ──► s02 ──► s03 ──► s04 ──► ...
                                            你在这里
```

> *大任务拆小 — 每个子任务获得干净的上下文*

## Problem — 我们在解决什么问题?

随着任务变复杂,单个 agent 会出现问题:

1. **上下文膨胀**: 消息历史越来越长,模型注意力分散
2. **任务混淆**: "读取 A 文件,然后修改 B 文件,同时检查 C 文件的测试" — 一条消息里塞了太多任务
3. **错误累积**: 前面步骤的小错误会污染后续所有步骤

解决方案: **SubAgent (子代理)**。主 agent 分析任务后,把子任务派给独立的子代理:
- 子代理有 **干净的上下文** — 只看到自己任务相关的内容
- 子代理有 **独立的循环** — 完成后返回结果
- 子代理的结果 **汇回主 agent** — 主 agent 继续决策

就像项目经理把任务分配给工程师,每个工程师独立完成自己的部分。

## Solution — 子代理架构

```
    ┌─────────────────────────────────────────────────────────────┐
    │                    Parent Agent                              │
    │                                                             │
    │   用户: "帮我重构 src/utils.py 并更新所有引用"                │
    │                                                             │
    │   ┌─────────────────────────────────────────┐               │
    │   │  Parent 思考:                             │               │
    │   │  1. 先读取 utils.py 了解当前结构           │               │
    │   │  2. 找到所有引用 utils.py 的文件           │               │
    │   │  3. 派子代理: "重构 utils.py"             │               │
    │   │  4. 派子代理: "更新 main.py 的引用"       │               │
    │   │  5. 汇总结果                              │               │
    │   └─────────────────────────────────────────┘               │
    │                                                             │
    │        │ spawn                    │ spawn                    │
    │        ▼                          ▼                          │
    │   ┌──────────────┐          ┌──────────────┐                │
    │   │  SubAgent A  │          │  SubAgent B  │                │
    │   │              │          │              │                │
    │   │  任务:       │          │  任务:       │                │
    │   │  重构utils.py│          │  更新引用     │                │
    │   │              │          │              │                │
    │   │  独立上下文:  │          │  独立上下文:  │                │
    │   │  只有utils.py│          │  只有main.py │                │
    │   │  的内容      │          │  和新API     │                │
    │   │              │          │              │                │
    │   └──────┬───────┘          └──────┬───────┘                │
    │          │                         │                        │
    │          └──────── 汇回结果 ────────┘                        │
    │                                                             │
    │   Parent 汇总 → 输出最终结果给用户                            │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘
```

## How It Works — 逐步拆解

### Step 1: 理解为什么需要干净上下文

主 agent 的消息历史可能已经有 20 条消息。如果直接在里面继续处理子任务:
- 模型需要处理大量无关信息
- 前面的对话可能误导子任务执行
- token 浪费在无关内容上

子代理从一个 **全新的消息列表** 开始:

```python
# 主 agent 的消息历史 — 可能很长
parent_messages = [msg1, msg2, ..., msg20]

# 子代理的消息历史 — 只有任务描述
subagent_messages = [
    {
        "role": "user",
        "content": f"请完成以下任务:\n{task_description}\n\n相关上下文:\n{context}"
    }
]
```

### Step 2: spawn_subagent 函数

创建子代理的核心函数:

```python
def spawn_subagent(task: str, context: str = "", depth: int = 0) -> str:
    """
    派生子代理执行任务。

    Args:
        task: 子任务描述
        context: 相关上下文信息
        depth: 当前递归深度 (防止无限嵌套)

    Returns:
        子代理的执行结果 (文本)
    """
    if depth >= MAX_DEPTH:
        return "错误: 达到最大递归深度"

    # 构建子代理的独立消息历史
    messages = [{"role": "user", "content": f"{task}\n\n上下文:\n{context}"}]

    # 子代理有自己的 agent loop
    while True:
        response = client.messages.create(...)
        # ... 标准的 agent loop 逻辑
```

### Step 3: 把子代理包装成工具

为了让主 agent 能调用子代理,我们把它注册为一个 "工具":

```python
{
    "name": "spawn_subagent",
    "description": "派生一个子代理来执行子任务。子代理有独立的上下文。",
    "input_schema": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "子任务描述"},
            "context": {"type": "string", "description": "相关上下文"},
        },
        "required": ["task"],
    },
}
```

### Step 4: 递归深度限制

子代理本身也是一个 agent,它也可以调用 `spawn_subagent` — 这就是递归。为了防止无限递归:

```python
MAX_DEPTH = 3  # 最多嵌套 3 层

def spawn_subagent(task, context="", depth=0):
    if depth >= MAX_DEPTH:
        return "错误: 达到最大递归深度,无法继续派生子代理"
    # ... 子代理的 tools 中也包含 spawn_subagent,但 depth + 1
```

### Step 5: 结果汇回主 agent

子代理完成后,它的输出作为 `tool_result` 返回给主 agent:

```python
# 主 agent 调用 spawn_subagent 工具
# 子代理执行完毕,返回结果
# 结果被包装为 tool_result:
{
    "type": "tool_result",
    "tool_use_id": "toolu_xxx",
    "content": "子代理完成: utils.py 已重构,新增了 validate() 函数..."
}
# 主 agent 看到结果,继续决策
```

## Claude Code 源码对照

| 概念                | 文件                           | 说明                                |
|---------------------|--------------------------------|--------------------------------------|
| AgentTool           | `src/tools/Agent/`             | 子代理工具的完整实现                  |
| agentTypes.ts       | `agentTypes.ts`                | 子代理的类型定义                      |
| 上下文隔离          | AgentTool                      | 子代理获得独立的 message history      |
| 深度限制            | AgentTool                      | 限制子代理嵌套层数                    |
| 结果汇总            | streamingToolExecutor          | 子代理结果注入父 agent 的消息历史     |

Claude Code 的 AgentTool 实现要点:
- 子代理继承父代理的工具集 (但可以定制)
- 有专门的 system prompt 区分 "你是子代理" vs "你是主代理"
- 子代理的输出会被摘要 (防止结果过长)
- 支持流式输出 — 主 agent 能实时看到子代理的进度

## What Changed From s03

| 方面              | s03 (上一节)                | s04 (本节)                           |
|-------------------|----------------------------|--------------------------------------|
| 架构              | 单一 agent                 | 主 agent + 可派生的子 agent           |
| 上下文            | 所有任务共享一个历史        | 每个子任务获得独立上下文               |
| 工具              | 文件操作工具               | 新增 spawn_subagent 工具              |
| 递归              | 无                         | 子代理可嵌套,有深度限制               |
| 任务分配          | 一个 agent 做所有事         | 主 agent 分配,子 agent 执行           |
| 适用场景          | 简单任务                   | 复杂多步骤任务                        |

## Try It — 动手练习

1. **运行子代理 agent**:
   ```bash
   export ANTHROPIC_API_KEY="your-key"
   python agents/s04_subagent.py
   ```
   试试输入需要多步骤的复杂任务。

2. **观察上下文隔离**: 在代码中打印子代理的 messages 数量,对比主代理的 messages 数量。注意子代理只看到自己的任务。

3. **测试深度限制**: 故意给 agent 一个需要多层嵌套的任务,观察达到 MAX_DEPTH 时的行为。

4. **进阶挑战**:
   - 给子代理添加专门的 system prompt (例如 "你是一个只做代码审查的专家")
   - 实现子代理结果的摘要功能 (而不是返回完整输出)
   - 添加子代理的超时机制 (防止某个子任务卡住)

5. **思考题**: 子代理和主代理应该共享同一个工具集吗? 在什么情况下你想给子代理一个更受限的工具集?
