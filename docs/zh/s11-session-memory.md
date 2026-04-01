# s11 · Session & Memory — 会话记忆

```
s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > [ s11 ] > s12
────────────────────────────────── PRODUCTION ──────────────────────────────
         Background Tasks · Session Memory · Full Agent
```

> *"记住过去，才能规划未来 — 会话记忆让代理持续进化"*

---

## Problem

每次对话都从零开始。Agent 忘记了昨天学到的所有东西：
- 上次修复了哪个 bug，怎么修的
- 项目结构是什么样的，哪些文件重要
- 哪些方法行不通，哪些坑要避免
- 用户偏好什么风格、什么命名约定

没有记忆的 agent，就像每天失忆的程序员——每天重新读代码、重新理解项目、重新犯同样的错误。

---

## Solution

```
┌──────────────────────────────────────────────────────────────┐
│                     Session Memory 系统                       │
│                                                              │
│  ┌────────────┐     ┌────────────────┐     ┌─────────────┐  │
│  │  会话 A     │     │  Memory 文件    │     │  会话 B      │  │
│  │            │     │  (持久化存储)    │     │             │  │
│  │  修复了     │────→│               │────→│  读取记忆:   │  │
│  │  auth bug  │ 写入 │ # Session     │ 注入 │  "上次修复了 │  │
│  │            │     │ # Title       │     │  auth bug"   │  │
│  │            │     │ # Files       │     │             │  │
│  └────────────┘     │ # Errors      │     │  继续从上次  │  │
│                     │ # Learnings   │     │  的进度开始  │  │
│  ┌────────────┐     │               │     └─────────────┘  │
│  │  会话 C     │     │               │                       │
│  │            │     └────────────────┘     ┌─────────────┐  │
│  │  读取记忆  │───────────────────────────→│  CLAUDE.md  │  │
│  │  更新发现  │───────────────────────────→│  (项目级)   │  │
│  └────────────┘                            └─────────────┘  │
│                                                              │
│  记忆提取触发条件:                                            │
│  ├─ Token 阈值: 上下文增长超过 5000 tokens                    │
│  ├─ 工具调用阈值: 累计超过 3 次工具调用                        │
│  └─ 自然断点: 最后一轮没有工具调用时                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**关键设计**：
- 记忆以 Markdown 文件存储，结构化分区
- 后台提取：用一个 forked agent 异步更新记忆，不阻塞主对话
- 阈值触发：不是每句话都更新，而是积累了足够信息后才提取
- 新会话启动时自动注入记忆，让 agent "记得" 过去

---

## How It Works

### 1. Memory 文件 — 结构化记忆模板

```python
MEMORY_TEMPLATE = """
# Session Title
_A short 5-10 word title for the session_

# Current State
_What is actively being worked on right now?_

# Task Specification
_What did the user ask to build? Design decisions._

# Files and Functions
_Important files and what they contain._

# Errors & Corrections
_Errors encountered and how they were fixed._

# Learnings
_What worked well? What to avoid?_
"""
```

类比 Claude Code 的 `DEFAULT_SESSION_MEMORY_TEMPLATE`，包含 Session Title、Current State、Task Specification、Files and Functions、Workflow、Errors & Corrections、Codebase Documentation、Learnings、Key Results、Worklog 等分区。

### 2. SessionStore — 会话持久化

```python
class SessionStore:
    """管理会话历史和记忆文件"""
    def save_session(self, session_id: str, messages: list):
        """保存完整会话历史"""
        with open(f"sessions/{session_id}.json", "w") as f:
            json.dump(messages, f)

    def load_session(self, session_id: str) -> list:
        """加载之前的会话"""
        ...
```

### 3. Memory 提取 — 后台异步更新

```python
async def extract_memory(messages: list, memory_path: str):
    """从对话中提取关键信息，更新记忆文件"""
    # 读取当前记忆
    current = read_file(memory_path)

    # 用 LLM 分析对话，提取关键信息
    prompt = f"Based on the conversation, update the session notes..."
    update = await call_llm(prompt)

    # 编辑记忆文件
    write_file(memory_path, update)
```

类比 Claude Code 使用 **forked agent**（`runForkedAgent`）在后台异步执行记忆提取，不阻塞主对话。

### 4. 阈值触发机制

```python
def should_extract(messages, last_extraction) -> bool:
    """判断是否需要提取记忆"""
    # 条件 1: Token 增长超过阈值
    tokens_since = count_tokens(messages) - last_extraction.tokens
    token_met = tokens_since >= 5000

    # 条件 2: 工具调用超过阈值
    tool_calls = count_tool_calls_since(messages, last_extraction.msg_id)
    tools_met = tool_calls >= 3

    # 条件 3: 自然断点（最后一条消息没有工具调用）
    natural_break = not has_tool_calls_in_last_turn(messages)

    # 触发: (token + tool_calls) OR (token + natural_break)
    return (token_met and tools_met) or (token_met and natural_break)
```

---

## Claude Code 源码对照

| 机制 | 源码位置 | 说明 |
|------|----------|------|
| Session Memory 主逻辑 | `services/SessionMemory/sessionMemory.ts:1-496` | 完整的记忆提取系统，包含初始化、阈值检查、forked agent 执行 |
| 记忆模板 | `services/SessionMemory/prompts.ts:11-41` | `DEFAULT_SESSION_MEMORY_TEMPLATE`，包含 10 个分区 |
| 记忆更新 Prompt | `services/SessionMemory/prompts.ts:43-81` | 给 forked agent 的指令：如何分析对话并更新记忆文件 |
| 工具函数 | `services/SessionMemory/sessionMemoryUtils.ts` | 阈值配置、提取状态追踪、内容加载 |
| 默认配置 | `sessionMemoryUtils.ts:32-36` | `minimumMessageTokensToInit: 10000`, `minimumTokensBetweenUpdate: 5000`, `toolCallsBetweenUpdates: 3` |
| 阈值判断 | `sessionMemory.ts:134-181` | `shouldExtractMemory()` — token + tool call 双阈值 |
| Forked Agent | `utils/forkedAgent.ts` | `runForkedAgent()` 在隔离 context 中执行记忆提取 |
| 初始化钩子 | `sessionMemory.ts:357-375` | `initSessionMemory()` 注册 post-sampling hook |
| 记忆文件权限 | `sessionMemory.ts:460-482` | `createMemoryFileCanUseTool()` — forked agent 只能编辑记忆文件 |
| 手动提取 | `sessionMemory.ts:387-453` | `manuallyExtractSessionMemory()` — `/summary` 命令触发 |
| 分区截断 | `prompts.ts:256-324` | `truncateSessionMemoryForCompact()` — 压缩时截断过大的分区 |
| CLAUDE.md 记忆 | `utils/memoryFileDetection.ts` | 4 级记忆文件：managed / user / project / local |

---

## What Changed From s10

| 维度 | s10 Background Tasks | s11 Session & Memory |
|------|----------------------|----------------------|
| 核心抽象 | `BackgroundTask` + `TaskQueue` | `SessionStore` + `MemoryFile` |
| 关注点 | 非阻塞执行 | 跨会话持久化 |
| 数据存储 | 内存中，进程结束即消失 | 文件系统，重启后仍存在 |
| 新增能力 | 异步任务管理 | 记忆提取、上下文注入、跨会话学习 |
| 触发机制 | 用户请求 | Token 阈值 + 工具调用阈值 + 自然断点 |
| 关键模式 | submit → poll | accumulate → extract → inject |

---

## Try It

1. **自定义记忆模板**：修改 `MEMORY_TEMPLATE`，添加对你有用的分区。比如 `# User Preferences`（用户偏好）或 `# Architecture Decisions`（架构决策）。不同的项目可能需要不同的记忆结构。

2. **实现记忆重要性评分**：不是所有信息都值得记住。给每条记忆添加重要性分数。当记忆文件接近 token 上限时，优先保留高重要性内容，丢弃低重要性的。类比 Claude Code 的 `truncateSessionMemoryForCompact()`。

3. **多级记忆系统**：实现 Claude Code 的 4 级记忆：`managed`（系统管理）、`user`（用户全局）、`project`（项目级）、`local`（会话级）。不同级别的记忆有不同的生命周期和可见范围。

4. **记忆去重**：当多次提取产生重复信息时，如何合并而不丢失细节？提示：在提取 prompt 中包含当前记忆内容，让 LLM 基于现有内容做增量更新而非重写。
