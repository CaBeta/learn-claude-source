<div align="center">

# 从零构建 Coding Agent

### Claude Code 源码解析与实战

```
 ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗
██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝
██║     ██║     ███████║██║   ██║██║  ██║█████╗
██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝
╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗
 ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝
```

**Don't just use the agent. Understand it. Build it.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)]()
[![Anthropic SDK](https://img.shields.io/badge/Anthropic-SDK-8A2BE2?logo=anthropic&logoColor=white)]()
[![MIT License](https://img.shields.io/badge/License-MIT-green)]()

</div>

---

## Philosophy: The Agent vs. The Harness

Most people think Claude Code is "just an API call." It's not.

```
  ┌─────────────────────────────────────────────────┐
  │              What you THINK it is               │
  │                                                 │
  │    User ──→ API ──→ Response                    │
  │                                                 │
  └─────────────────────────────────────────────────┘

                    ...vs reality...

  ┌─────────────────────────────────────────────────┐
  │              What it ACTUALLY is                │
  │                                                 │
  │  User ──→ Permission Gate ──→ Context Builder   │
  │    ↑                              │             │
  │    │              ┌───────────────┘             │
  │    │              ↓                              │
  │  Stream    ┌─→ Agent Loop ←──────────┐         │
  │  Parser    │      │                   │         │
  │    ↑       │  Tool Executor ──→ SubAgent       │
  │    │       │      │              │     │         │
  │    │       │  Permission Check   │     │         │
  │    │       │      │              │     │         │
  │    └───────┘  Result Collation ←─┘     │         │
  │            │                           │         │
  │            └──── Context Compress ─────┘         │
  │                    │                             │
  │              Session Memory                      │
  └─────────────────────────────────────────────────┘
```

The model is **the agent** -- it reasons, plans, decides.
The code around it is **the harness** -- it runs the loop, manages tools, enforces permissions, compresses context, streams output.

A coding agent is 20% model, 80% harness.

This project teaches you to build both.

---

## The Learning Path

12 sessions. 4 phases. From a bare `while True` loop to a production-grade coding agent.

```
 ╔══════════════════════════════════════════════════════════════╗
 ║                    PHASE 1 · CORE LOOP                      ║
 ║           "Make it think. Make it act. Make it flow."        ║
 ╠══════════════════════════════════════════════════════════════╣
 ║                                                              ║
 ║   s01 ──→ s02 ──→ s03                                       ║
 ║   Agent    Tool     Streaming                                ║
 ║   Loop     Use      Output                                   ║
 ║                                                              ║
 ║   The heartbeat.     Hands.      The voice.                  ║
 ║   while(true).       Bash,       Token by                   ║
 ║   Think → Act →      Read,       token, not                 ║
 ║   Observe → Think.   Write.      all at once.                ║
 ║                                                              ║
 ╚══════════════════════════════════════════════════════════════╝
                              │
                              ▼
 ╔══════════════════════════════════════════════════════════════╗
 ║                  PHASE 2 · INTELLIGENCE                     ║
 ║           "Make it smart. Make it safe. Make it scale."      ║
 ╠══════════════════════════════════════════════════════════════╣
 ║                                                              ║
 ║   s04 ──→ s05 ──→ s06                                       ║
 ║   Sub      Context   Permission                              ║
 ║   Agent    Mgmt      System                                  ║
 ║                                                              ║
 ║   Spawn a             5 layers         "Can I               ║
 ║   mini-me for         of context        run this             ║
 ║   complex tasks.      compression.      command?"            ║
 ║                                                              ║
 ╚══════════════════════════════════════════════════════════════╝
                              │
                              ▼
 ╔══════════════════════════════════════════════════════════════╗
 ║                  PHASE 3 · EXTENSION                        ║
 ║           "Make it modular. Make it pluggable. Make it multiply." ║
 ╠══════════════════════════════════════════════════════════════╣
 ║                                                              ║
 ║   s07 ──→ s08 ──→ s09                                       ║
 ║   Skills   Hooks     Multi-Agent                             ║
 ║                                                              ║
 ║   Reusable           Lifecycle        A swarm               ║
 ║   workflows.         intercepts.      of agents             ║
 ║                      Before/After.    coordinated.          ║
 ║                                                              ║
 ╚══════════════════════════════════════════════════════════════╝
                              │
                              ▼
 ╔══════════════════════════════════════════════════════════════╗
 ║                 PHASE 4 · PRODUCTION                        ║
 ║           "Make it real. Make it last. Ship it."             ║
 ╠══════════════════════════════════════════════════════════════╣
 ║                                                              ║
 ║   s10 ──→ s11 ──→ s12                                       ║
 ║   Background  Session   Production                           ║
 ║   Tasks       Memory     Agent                               ║
 ║                                                              ║
 ║   Set it and         Remember              The full          ║
 ║   forget it.         across                agent.            ║
 ║                      sessions.             Ship-ready.       ║
 ║                                                              ║
 ╚══════════════════════════════════════════════════════════════╝
```

### Session Map

| # | Session | Core Concept | Claude Code Source | What You Build |
|---|---------|-------------|-------------------|---------------|
| s01 | Agent Loop | `while(True)` + 状态机 | `query.ts` | 一个会思考的循环 |
| s02 | Tool Use | 工具注册 + 执行管线 | `Tool.ts`, `tools.ts` | 能读文件、跑命令的 agent |
| s03 | Streaming | Token-by-token 流式输出 | `QueryEngine.ts` | 实时输出，不等全部完成 |
| s04 | SubAgent | 子代理派发与回收 | `coordinator/` | 多个子代理并行工作 |
| s05 | Context Mgmt | 5 层上下文压缩 | `services/compact/` | 永远不超 token 限制 |
| s06 | Permission | 6 种权限模式 | `hooks/toolPermission/` | 安全沙箱，该问就问 |
| s07 | Skills | 可复用技能模板 | `skills/` | 自定义工作流 |
| s08 | Hooks | 生命周期拦截器 | `hooks/` | Before/After 钩子 |
| s09 | Multi-Agent | 多代理协调 | `coordinator/` | Agent 团队协作 |
| s10 | Background Tasks | 异步任务管理 | `tasks/` | 后台执行，不阻塞 |
| s11 | Session Memory | 跨会话持久记忆 | `memdir/`, `history.ts` | 记住你昨天做了什么 |
| s12 | Production Agent | 完整生产级 agent | 全部 | 可以交付的 coding agent |

---

## Quick Start

### 1. Install

```bash
pip install anthropic
```

### 2. Set your API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Run the simplest agent (s01)

```python
# agents/s01_agent_loop.py
import anthropic

client = anthropic.Anthropic()

messages = [{"role": "user", "content": "Hello, what can you do?"}]

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=messages,
)

print(response.content[0].text)
```

That's it. You just made your first agent call. Everything else in this project builds on top of this single API call.

### 4. Follow the sessions

Each session in `agents/` is a standalone, runnable Python file. Each session in `docs/` explains what changed and why.

```
agents/
  s01_agent_loop.py          # Start here
  s02_tool_use.py            # Add tools
  s03_streaming.py           # Add streaming
  ...
```

---

## Project Structure

```
learn-claude-source/
│
├── claude-code-main/            # Claude Code 源码快照 (TypeScript)
│   └── src/
│       ├── query.ts             #   Agent Loop 核心 (真正的 while-true 状态机)
│       ├── QueryEngine.ts       #   LLM 调用引擎 (~46K lines)
│       ├── Tool.ts              #   工具类型定义 (~29K lines)
│       ├── tools.ts             #   工具注册表
│       ├── commands.ts          #   命令注册表
│       ├── main.tsx             #   CLI 入口
│       ├── context.ts           #   上下文收集
│       ├── tools/               #   ~43 个工具实现
│       ├── coordinator/         #   多代理协调器
│       ├── bridge/              #   IDE 桥接系统
│       ├── skills/              #   技能加载
│       ├── hooks/               #   权限与钩子
│       ├── services/            #   外部服务集成
│       ├── components/          #   UI 组件 (React + Ink)
│       └── ...
│
├── agents/                      # 可运行的 Python 示例 (逐步构建)
│   ├── s01_agent_loop.py
│   ├── s02_tool_use.py
│   ├── s03_streaming.py
│   ├── s04_subagent.py
│   ├── s05_context_management.py
│   ├── s06_permission_system.py
│   ├── s07_skill_system.py
│   ├── s08_hook_system.py
│   ├── s09_multi_agent.py
│   ├── s10_background_tasks.py
│   ├── s11_session_memory.py
│   └── s12_production_agent.py
│
├── docs/                        # 课程文档 (中文)
│   └── zh/
│       ├── s01_agent_loop.md
│       ├── s02_tool_use.md
│       └── ...
│
├── findings.md                  # 源码分析笔记
├── task_plan.md                 # 项目规划
└── README.md                    # You are here
```

---

## Key Source Code Map

Claude Code 的源码不是教科书。它是一个**生产级系统** -- 1900+ 文件, 512,000+ 行代码。

但核心机制其实只有几个。下面是你需要理解的最重要的文件：

### The Engine

```
query.ts          ─── The Heartbeat
                     async function* generator
                     while(true) { think → act → observe }
                     7 个 continue 站点, 10 个 return 站点
                     这一个文件就是整个 agent 的灵魂

QueryEngine.ts    ─── The Voice
                     46,000 行, 处理所有 LLM API 调用
                     流式响应, tool-call 循环, thinking mode
                     retry 逻辑, token 计数
```

### The Hands

```
Tool.ts           ─── The Blueprint
                     buildTool() 工厂模式
                     validateInput → checkPermissions → canUseTool → call
                     ~43 个工具都从这里诞生

tools/            ─── The Toolbox
                     BashTool      ─── 执行 shell 命令
                     FileReadTool  ─── 读文件 (图片/PDF/Notebook)
                     FileWriteTool ─── 写文件
                     FileEditTool  ─── 精确编辑 (字符串替换)
                     GlobTool      ─── 文件搜索
                     GrepTool      ─── 内容搜索 (ripgrep)
                     AgentTool     ─── 子代理派发
                     MCPTool       ─── MCP 协议工具
                     ...还有 ~35 个
```

### The Brain

```
services/compact/ ─── The Memory Manager
                     5 层上下文压缩策略:
                     Budget → Snip → Microcompact → Collapse → Autocompact
                     确保永远不超 token 限制

coordinator/      ─── The Manager
                     多代理协调器
                     子代理派发、结果回收、并行管理
```

### The Shield

```
hooks/toolPermission/ ─── The Guard
                       6 种权限模式:
                       default | plan | acceptEdits | bypassPermissions | dontAsk | auto
                       5 阶段权限流:
                       Rule Check → Decision Dispatch → Coordinator → Swarm → Interactive
```

### The Connectors

```
bridge/           ─── IDE 桥接
                     VS Code / JetBrains 双向通信
                     bridgeMain.ts → bridgeMessaging.ts → replBridge.ts

skills/           ─── 技能系统
                     可复用工作流模板
                     用户可自定义扩展

memdir/           ─── 持久记忆
                     跨会话记忆存储
                     自动记忆提取 (services/extractMemories/)
```

---

## Design Patterns Worth Learning

Claude Code 用了一些非常漂亮的设计模式。不仅是为了炫技，而是为了解决真实问题：

### 1. Immutable State Per Iteration

```python
# Every loop iteration creates a BRAND NEW state object.
# No mutation. No shared state bugs.
# See: query.ts

state = initial_state
while True:
    state = process(state)  # 返回全新对象, 不修改旧的
    if state.should_exit:
        break
```

### 2. The Permission Pipeline

```
User Input
    │
    ▼
validate_input()     # Schema 校验
    │
    ▼
check_permissions()  # 规则匹配
    │
    ▼
can_use_tool()       # 运行时检查
    │
    ▼
call()               # 真正执行
```

### 3. Parallel Prefetch

```python
# Don't wait for things sequentially. Fire them all at once.
# See: main.tsx startup

import asyncio

mdm_settings = asyncio.create_task(load_mdm())
keychain = asyncio.create_task(prefetch_keychain())
api_preconnect = asyncio.create_task(preconnect_api())

# All three run concurrently. Startup is faster.
```

### 4. Context Compression Cascade

```
Token budget OK?  ──YES──→  Continue normally
       │
      NO
       │
       ▼
Snip old tool results  ──Still too long?──→
       │
       ▼
Microcompact conversation  ──Still?──→
       │
       ▼
Collapse to summary  ──Still?──→
       │
       ▼
Auto-compact (full rewrite)
```

---

## Tech Stack Reference

Claude Code 的技术栈值得了解，虽然我们用 Python 教学：

| Component | Claude Code Uses | We Use |
|-----------|-----------------|--------|
| Language | TypeScript (strict) | Python 3.10+ |
| Runtime | Bun | CPython |
| LLM API | Anthropic SDK (TS) | `anthropic` (Python) |
| Terminal UI | React + Ink | Terminal print |
| Schema | Zod v4 | Pydantic |
| Search | ripgrep | ripgrep (via subprocess) |

---

## Who Is This For?

- **You can use Claude Code, but want to understand how it works** -- 你是用户，但你想成为构建者
- **You're building your own AI agent** -- 你想构建自己的 agent，需要参考架构
- **You learn by reading real code** -- 你通过阅读真实代码来学习
- **You read Chinese** -- 文档以中文为主，保留英文技术术语

## What You Need

- Python 3.10+
- An Anthropic API key
- Curiosity
- ~2 hours per session

---

## Credits

This project is inspired by:

- **[shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)** -- 渐进式 agent 教学项目的先驱
- **Anthropic** -- Claude Code 的创造者。本项目中引用的源码来自一次 source map 泄露事件 (2026-03-31)，仅用于教育目的

Claude Code 源码的知识产权归 **Anthropic** 所有。本项目**不隶属于、不由 Anthropic 认可或维护**。

## License

MIT

---

<div align="center">

**"The best way to understand a system is to build it yourself."**

`s01` > `s02` > `s03` > `s04` > `s05` > `s06` > `s07` > `s08` > `s09` > `s10` > `s11` > `[ s12 ]`

</div>
