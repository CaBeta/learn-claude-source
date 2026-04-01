# s12 · Production Agent — 生产级代理

```
s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > [ s12 ]
────────────────────────────────── PRODUCTION ──────────────────────────────
         Background Tasks · Session Memory · Full Agent
```

> *"从原型到产品 — 一个完整的生产级 Coding Agent"*

---

## Problem

我们用 11 个 session 构建了各种机制——Agent Loop、Tool Use、Streaming、SubAgent、Context Management、Permission、Skills、Hooks、Multi-Agent、Background Tasks、Session Memory。

但它们是分散的。一个真正的生产级 agent 需要把所有这些机制**有机地组合**在一起，同时还要处理：

- **错误恢复**：API 限流、网络超时、模型幻觉——生产环境中什么都会出错
- **优雅降级**：某个子系统失败时，整个 agent 不应该崩溃
- **配置化**：不同场景需要不同的行为（开发 vs CI vs 演示）
- **可观测性**：知道 agent 在做什么、花了多少 token、卡在哪里

---

## Solution

```
┌────────────────────────────────────────────────────────────────────┐
│                    Production Agent 完整架构                        │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Configuration                              │  │
│  │   model · max_tokens · permission_mode · features            │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                      │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │                    Agent Loop (s01)                           │  │
│  │   while True:                                                │  │
│  │     ├── Context Management (s05)                             │  │
│  │     │     Budget → Snip → Summarize → Inject Memory (s11)   │  │
│  │     ├── Call Model (Streaming s03)                           │  │
│  │     ├── Collect tool_use blocks                              │  │
│  │     ├── Permission Check (s06)                               │  │
│  │     ├── Pre-Hooks (s08)                                      │  │
│  │     ├── Dispatch Tools (s02)                                 │  │
│  │     │     ├── Bash, Read, Write, Edit...                     │  │
│  │     │     ├── Skill invocation (s07)                         │  │
│  │     │     ├── SubAgent spawn (s04)                           │  │
│  │     │     └── Background task (s10)                          │  │
│  │     ├── Post-Hooks (s08)                                     │  │
│  │     ├── Multi-Agent coord (s09)                              │  │
│  │     ├── Error Recovery                                       │  │
│  │     └── State Update → continue                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │  Session Store   │  │  Memory Files    │  │  Task Queue      │  │
│  │  (s11)           │  │  (s11)           │  │  (s10)           │  │
│  └─────────────────┘  └─────────────────┘  └──────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Error Recovery                             │  │
│  │   Rate Limit → Retry · Timeout → Retry · Error → Report     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## How It Works

### 1. Configuration — 一切可配置

```python
@dataclass
class AgentConfig:
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    max_iterations: int = 20
    permission_mode: str = "default"  # default | bypass | plan
    features: dict = field(default_factory=lambda: {
        "streaming": True,
        "background_tasks": True,
        "session_memory": True,
        "subagents": True,
    })
```

### 2. Agent Loop — 完整的循环

```python
async def agent_loop(config: AgentConfig):
    while True:
        # 1. Context management
        messages = manage_context(messages, config)

        # 2. Call model (with streaming)
        response = await call_model_streaming(messages, config)

        # 3. Collect tool calls
        tool_calls = [b for b in response if b.type == "tool_use"]

        # 4. No tools = done
        if not tool_calls:
            return response.text

        # 5. Permission check
        approved = check_permissions(tool_calls, config)

        # 6. Execute tools (with hooks)
        results = await execute_tools_with_hooks(approved)

        # 7. Update state
        messages.append(assistant_msg)
        messages.append(tool_results_msg)
```

### 3. Error Recovery — 防御性编程

```python
async def call_with_recovery(fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await fn()
        except RateLimitError:
            wait = 2 ** attempt  # 指数退避
            await asyncio.sleep(wait)
        except TimeoutError:
            if attempt == max_retries - 1:
                raise
            continue
        except APIError as e:
            if e.status_code == 429:  # rate limit
                await asyncio.sleep(60)
            else:
                raise
```

### 4. 所有 11 个 Session 的集成点

| Session | 在 Production Agent 中的角色 |
|---------|------------------------------|
| s01 Agent Loop | `ProductionAgent.run()` — 主循环 |
| s02 Tool Use | `ToolRegistry` + `dispatch_tool()` |
| s03 Streaming | `call_model_streaming()` — 逐 token 输出 |
| s04 SubAgent | `spawn_subagent()` — 委派复杂子任务 |
| s05 Context Mgmt | `manage_context()` — token budget 控制 |
| s06 Permission | `check_permissions()` — 安全关卡 |
| s07 Skills | `SkillLoader` — 加载自定义工作流 |
| s08 Hooks | `HookManager` — 生命周期事件 |
| s09 Multi-Agent | `Coordinator` — 多 worker 协作 |
| s10 Background | `TaskQueue` — 异步任务执行 |
| s11 Memory | `MemoryExtractor` + `SessionStore` |

---

## Claude Code 源码对照

| 机制 | 源码位置 | 说明 |
|------|----------|------|
| 完整 Agent Loop | `query.ts:219-1655` | 1729 行的 `async function* query()` 生成器 |
| 状态初始化 | `query.ts:268-279` | `State` 对象的 9 个字段 |
| 上下文管理 5 层 | `query.ts:369-543` | Budget → Snip → Microcompact → Collapse → Autocompact |
| 模型调用 | `query.ts:659-863` | 流式 API 调用 + tool_use 收集 |
| 后流式决策 | `query.ts:1062-1357` | PTL recovery, max_output_tokens, stop hooks |
| 工具执行 | `query.ts:1366-1409` | StreamingToolExecutor 或 runTools |
| 权限管线 | `services/tools/toolExecution.ts` | validate → classify → hooks → permissions → call |
| 工具注册 | `tools.ts:193` | `getAllBaseTools()` — 约 43 个工具 |
| 错误恢复 | `query.ts:950, 1115, 1220` | 7 个 continue 站点 + 多个 return 站点 |
| 不可变状态 | `query.ts:265-267` | 每轮迭代 `state = {...}` 创建新对象 |
| CLI 入口 | `main.tsx` | 4683 行的启动器和模式路由 |

---

## What Changed From s11

| 维度 | s11 Session & Memory | s12 Production Agent |
|------|----------------------|----------------------|
| 核心抽象 | `MemoryFile` + `SessionStore` | `ProductionAgent` (全部集成) |
| 代码量 | ~150 行 | ~300 行 |
| 机制数 | 1 (记忆提取) | 11 (所有 session 的机制) |
| 错误处理 | 简单 try/catch | 重试 + 降级 + 恢复 |
| 配置 | 硬编码 | `AgentConfig` 可配置 |
| 可观测性 | print | 结构化日志 + token 追踪 |
| 就绪程度 | 演示/教学 | 可用于真实编码任务 |

---

## Try It

1. **添加 MCP 支持**：Model Context Protocol 允许 agent 调用外部工具服务器。在 `ToolRegistry` 中添加 MCP 工具加载器，从配置文件读取 MCP server 列表，动态注册工具。类比 Claude Code 的 `MCPTool`。

2. **实现 Plan Mode**：添加 `--plan` 模式，agent 只分析不执行。相当于 `permission_mode="plan"`，所有写操作自动拒绝，只读操作自动放行。如何在不修改工具定义的情况下实现只读模式？

3. **添加 Token 预算**：给每次对话设置总 token 预算（比如 100K）。当接近预算时，自动触发 context compression。当超过预算时，优雅终止而不是崩溃。类比 Claude Code 的 `applyToolResultBudget()`。

4. **性能基准测试**：用同一个复杂任务（比如"给这个项目添加单元测试"），对比你的 Production Agent 和裸 API 调用的效果。记录 token 消耗、任务完成率、错误次数。生产级 agent 应该在哪里投入更多 token？

---

**Previous:** [s11 Session & Memory](./s11-session-memory.md)

---

## Course Complete

```
s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > [ s12 ]
  ✓      ✓      ✓      ✓      ✓      ✓      ✓      ✓      ✓      ✓      ✓      ✓
```

你用 12 个 session，从零构建了一个完整的 Coding Agent。它包含：

1. **Agent Loop** — `while(true)` 状态机，让 agent 能持续思考和行动
2. **Tool Use** — 工具注册和执行，让 agent 能操作文件和命令
3. **Streaming** — 逐 token 输出，让用户不用等待
4. **SubAgent** — 子代理派发，让 agent 能分解复杂任务
5. **Context Management** — 5 层压缩，让 agent 永远不超 token 限制
6. **Permission** — 安全关卡，让 agent 不做危险操作
7. **Skills** — 可复用技能，让 agent 能扩展能力
8. **Hooks** — 生命周期钩子，让 agent 能被定制
9. **Multi-Agent** — 协调器模式，让 agent 团队协作
10. **Background Tasks** — 异步执行，让 agent 不阻塞
11. **Session Memory** — 跨会话记忆，让 agent 能持续学习
12. **Production Agent** — 全部整合，一个可以交付的 coding agent

Claude Code 有 512,000+ 行代码实现这些机制。你用 ~2000 行 Python 理解了核心架构。从理解到构建，这就是进步。
