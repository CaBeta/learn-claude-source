# s09 · Multi-Agent Coordinator — 多代理协调器

```
s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > [ s09 ] > s10 > s11 > s12
────────────────────────────── EXTENSION ──────────────────────
         Skills · Hooks · Multi-Agent
```

> *"一个人走得快，一群人走得远 — 协调器指挥代理团队"*

---

## Problem

复杂任务需要不同的专长。一个 agent 不可能同时擅长研究、实现和验证。

想象一个场景：用户说"修复认证模块的 null pointer 异常"。这需要：
- 一个 worker 去调查代码，找到 bug 位置
- 一个 worker 去查找相关测试，了解覆盖情况
- 一个 coordinator 综合研究结果，制定修复方案
- 一个 worker 去执行修复
- 另一个 worker 去验证修复是否生效

单个 agent 只能串行处理，而多 agent 可以**并行研究、串行实现、独立验证**。

---

## Solution

```
                        ┌──────────────┐
                        │    User      │
                        │  "修复auth   │
                        │   bug"       │
                        └──────┬───────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Coordinator       │
                    │   (主控 Agent)       │
                    │                     │
                    │  1. 分解任务         │
                    │  2. 派发 workers     │
                    │  3. 收集结果         │
                    │  4. 综合决策         │
                    └──────┬──────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
     ┌────────────┐ ┌────────────┐ ┌────────────┐
     │  Worker A  │ │  Worker B  │ │  Worker C  │
     │  调查代码   │ │  查找测试   │ │  执行修复   │
     │            │ │            │ │            │
     │  Bash      │ │  Grep      │ │  Edit      │
     │  Read      │ │  Read      │ │  Bash      │
     └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
           │              │              │
           └──────────────┼──────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Coordinator    │
                 │  综合结果        │
                 │  决定下一步      │
                 └─────────────────┘
```

**关键设计**：
- Coordinator 不直接执行任务，只做规划和调度
- 每个 Worker 独立运行，有自己的 context
- Worker 之间不能互相通信，只能通过 Coordinator 中转
- 结果以 `<task-notification>` XML 格式返回给 Coordinator

---

## How It Works

### 1. 定义 Worker — 执行具体任务的代理

```python
class WorkerAgent:
    """执行具体子任务的 Worker Agent"""
    def __init__(self, agent_id: str, task: str):
        self.agent_id = agent_id
        self.task = task
        self.status = "pending"  # pending -> running -> completed/failed

    async def execute(self) -> TaskResult:
        self.status = "running"
        # Worker 独立调用 LLM，有自己的完整 context
        response = await call_llm(self.task)
        self.status = "completed"
        return TaskResult(agent_id=self.agent_id, output=response)
```

### 2. 定义 Coordinator — 规划和调度

```python
class CoordinatorAgent:
    """协调器 — 规划任务并派发给 Workers"""
    async def handle_request(self, user_request: str):
        # Phase 1: Research — 并行派出多个 worker 调查
        workers = [
            self.spawn_worker("调查认证模块的 null pointer"),
            self.spawn_worker("查找认证相关测试文件"),
        ]
        results = await self.collect_results(workers)

        # Phase 2: Synthesis — Coordinator 自己综合研究结果
        plan = await self.synthesize(user_request, results)

        # Phase 3: Implementation — 派出一个 worker 执行修复
        fix_result = await self.spawn_and_wait(f"修复 {plan}")

        # Phase 4: Verification — 另一个 worker 独立验证
        verify = await self.spawn_and_wait(f"验证修复: {fix_result}")
        return verify
```

### 3. 消息传递 — Worker 结果通知

```python
# Coordinator 接收 Worker 结果的格式 (XML notification)
TASK_NOTIFICATION = """
<task-notification>
  <task-id>{worker.agent_id}</task-id>
  <status>{worker.status}</status>
  <summary>{worker.task}</summary>
  <result>{worker.output}</result>
</task-notification>
"""
```

### 4. 任务生命周期

```
pending → running → completed
                  → failed
                  → killed (coordinator 主动停止)
```

---

## Claude Code 源码对照

| 机制 | 源码位置 | 说明 |
|------|----------|------|
| Coordinator 模式判断 | `coordinator/coordinatorMode.ts:36-41` | 通过 env var `CLAUDE_CODE_COORDINATOR_MODE` 和 feature gate 控制 |
| Coordinator System Prompt | `coordinator/coordinatorMode.ts:111-369` | 完整的协调器系统提示词，定义角色、工具、工作流 |
| Worker 工具列表 | `coordinator/coordinatorMode.ts:80-109` | Worker 可用的工具列表，通过 `getCoordinatorUserContext()` 注入 |
| 任务阶段定义 | `coordinator/coordinatorMode.ts:200-209` | Research → Synthesis → Implementation → Verification 四阶段 |
| 并发策略 | `coordinator/coordinatorMode.ts:211-219` | 只读并行，写操作串行，验证可与实现并行 |
| Worker Prompt 编写 | `coordinator/coordinatorMode.ts:251-336` | Coordinator 如何给 Worker 写自包含的 prompt |
| Worker 结果格式 | `coordinator/coordinatorMode.ts:142-165` | `<task-notification>` XML 格式 |
| 内部 Worker 工具 | `coordinator/coordinatorMode.ts:29-34` | TeamCreate, TeamDelete, SendMessage 等内部工具 |
| Agent 工具 | `tools/AgentTool/` | Worker 的实际 spawning 机制 |
| SendMessage 工具 | `tools/SendMessageTool/` | Coordinator 与 Worker 间的消息传递 |
| TaskStop 工具 | `tools/TaskStopTool/` | 停止正在运行的 Worker |

---

## What Changed From s08

| 维度 | s08 Hook System | s09 Multi-Agent Coordinator |
|------|-----------------|-----------------------------|
| 核心抽象 | Hook (事件拦截器) | Coordinator (任务协调器) |
| 关注点 | 生命周期管理 | 团队协作与任务分解 |
| 模式 | 单 Agent + 钩子 | 多 Agent + 消息传递 |
| 通信 | Hook → 主 Agent (单向) | Coordinator ↔ Workers (双向) |
| 新增概念 | `before_hook`, `after_hook` | `spawn_worker`, `collect_results`, `synthesize` |
| 复杂度 | O(n) hooks | O(n) workers + O(n²) 消息 |
| 错误处理 | Hook 阻断或放行 | Worker 失败后 continue 或换方案 |

---

## Try It

1. **修改任务分解策略**：在 `CoordinatorAgent.plan_tasks()` 中尝试不同的分解方式。比如按文件分解（每个 worker 负责不同文件）vs 按阶段分解（研究/实现/验证）。哪种对特定任务更有效？

2. **添加 Worker 超时**：给每个 Worker 设置最大执行时间。如果超时，Coordinator 应该如何处理？是重新派发、换方案、还是直接报错？

3. **实现 Worker 间接力**：Worker A 完成后，Coordinator 用 `SendMessage` 将 A 的关键发现传递给 Worker B，让 B 在 A 的基础上继续工作，而不是从零开始。

4. **对比单 Agent vs 多 Agent**：同一个复杂任务，分别用单 agent 和多 agent 完成。比较 token 消耗、总时间、结果质量。在什么场景下多 agent 更优？
