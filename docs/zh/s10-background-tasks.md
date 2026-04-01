# s10 · Background Tasks — 后台任务

```
s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > [ s10 ] > s11 > s12
───────────────────────────────── PRODUCTION ─────────────────────────────
         Background Tasks · Session Memory · Full Agent
```

> *"不让用户等待 — 后台执行，前台响应"*

---

## Problem

有些操作需要几分钟才能完成——跑测试套件、构建项目、搜索整个代码库。如果 agent 阻塞等待，用户就只能盯着空白屏幕。

真实场景：
- 运行 `pytest` 需要 2 分钟，agent 在此期间无法响应
- 搜索 10,000 个文件，用户想同时问别的问题
- 并行跑多个长时间任务（lint + test + build）

我们需要一种机制：**启动任务后立即返回，需要时再查看结果**。

---

## Solution

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Loop                            │
│                                                         │
│   User: "跑一下测试"                                      │
│     │                                                   │
│     ▼                                                   │
│   Agent 调用 TaskCreate("run tests")                     │
│     │                     │                              │
│     │                     ▼                              │
│     │            ┌─────────────────┐                     │
│     │            │ Background Task  │                     │
│     │            │  Thread/Async    │                     │
│     │            │  status: running │                     │
│     │            │                  │                     │
│     │            │  $ pytest ...    │                     │
│     │            └────────┬─────────┘                     │
│     │                     │ (非阻塞)                       │
│     ▼                     ▼                              │
│   立即回复: "测试已在后台           │                      │
│    运行，ID=task-001"               │                     │
│                                    │                     │
│   User: "结果怎么样？"               │                     │
│     │                              │                     │
│     ▼                              ▼                     │
│   TaskGet("task-001")         status: completed          │
│     │                         result: "42 passed"        │
│     ▼                                                   │
│   回复: "测试全部通过，42 个 ✓"                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**关键设计**：
- 任务在独立线程中执行，不阻塞 Agent Loop
- 任务有完整的生命周期：`pending → running → completed/failed`
- 通过 Task ID 查询状态和结果
- 支持任务列表和取消

---

## How It Works

### 1. BackgroundTask — 单个后台任务

```python
class BackgroundTask:
    """一个在后台执行的任务"""
    def __init__(self, task_id: str, description: str, fn: callable):
        self.task_id = task_id
        self.description = description
        self.fn = fn                    # 要执行的函数
        self.status = "pending"         # pending -> running -> completed/failed
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None

    def execute(self):
        self.status = "running"
        self.started_at = time.time()
        try:
            self.result = self.fn()     # 在后台线程中执行
            self.status = "completed"
        except Exception as e:
            self.error = str(e)
            self.status = "failed"
        finally:
            self.completed_at = time.time()
```

### 2. TaskQueue — 管理所有后台任务

```python
class TaskQueue:
    """后台任务队列 — 管理任务的生命周期"""
    def __init__(self):
        self.tasks: dict[str, BackgroundTask] = {}

    def submit(self, description: str, fn: callable) -> str:
        """提交新任务，立即返回 task_id"""
        task = BackgroundTask(task_id=uuid(), description=description, fn=fn)
        self.tasks[task.task_id] = task

        # 在独立线程中执行
        thread = threading.Thread(target=task.execute, daemon=True)
        thread.start()

        return task.task_id  # 立即返回，不等待完成
```

### 3. Agent 集成 — 注册为 Tool

```python
# 将后台任务注册为 Agent 的工具
tools = [
    {
        "name": "task_create",
        "description": "创建后台任务",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "command": {"type": "string"},
            },
        },
    },
    {
        "name": "task_get",
        "description": "查询任务状态和结果",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
            },
        },
    },
]
```

### 4. 任务生命周期

```
   pending ──→ running ──→ completed
                      ──→ failed
                      ──→ cancelled
```

每次 Agent Loop 迭代开始时，可以检查所有后台任务的状态，如果有完成的任务，将结果注入到对话中。

---

## Claude Code 源码对照

| 机制 | 源码位置 | 说明 |
|------|----------|------|
| Agent 异步模式 | `tools/AgentTool/` | Agent 工具支持异步执行 (`subagent_type: "worker"`) |
| TaskCreate 工具 | `tools/TaskCreateTool/` | 创建任务，分配 task_id |
| TaskGet 工具 | `tools/TaskGetTool/` | 查询任务状态和结果 |
| TaskUpdate 工具 | `tools/TaskUpdateTool/` | 更新任务状态（pending → in_progress → completed） |
| TaskList 工具 | `tools/TaskListTool/` | 列出所有任务 |
| TaskStop 工具 | `tools/TaskStopTool/` | 停止运行中的任务 |
| TaskOutput 工具 | `tools/TaskOutputTool/` | 获取任务输出 |
| 异步执行器 | `utils/forkedAgent.ts` | 在 forked context 中运行后台 agent |
| 后台线程执行 | `StreamingToolExecutor.ts` | 并行工具执行器，管理并发任务 |

---

## What Changed From s09

| 维度 | s09 Multi-Agent | s10 Background Tasks |
|------|-----------------|----------------------|
| 核心抽象 | Coordinator + Workers | TaskQueue + BackgroundTask |
| 执行模式 | 并行但同步等待结果 | 提交后立即返回，按需查询 |
| 阻塞性 | `await gather()` 等待所有 worker | `submit()` 返回 ID，`get()` 查询 |
| 通信 | Worker 通过 XML notification 回报 | 轮询 task status 获取结果 |
| 适用场景 | 复杂任务分解 | 长时间运行的操作 |
| 新增概念 | `WorkerSpec`, `TaskResult` | `BackgroundTask`, `TaskQueue`, `task_id` |
| 错误处理 | Worker 失败后 Coordinator 换方案 | 任务失败记录 error，可重试 |

---

## Try It

1. **实现任务优先级**：给 `TaskQueue.submit()` 添加优先级参数。高优先级任务先执行，低优先级排队等待。如何在不阻塞的情况下实现优先级调度？

2. **添加进度报告**：给 `BackgroundTask` 添加进度回调。对于长时间任务（如跑测试），Worker 可以定期报告进度（"已跑 30/100 个测试"）。提示：使用 `Queue` 在主线程和后台线程间传递消息。

3. **实现任务依赖**：任务 B 依赖任务 A 的结果。只有当 A 完成后 B 才能开始。如何在 `TaskQueue` 中表达和执行这种依赖关系？

4. **添加超时和取消**：如果任务执行超过 30 秒，自动标记为 `failed`。用户也可以通过 `task_stop` 主动取消。如何安全地中断正在运行的线程？

---

**Previous:** [s09 Multi-Agent Coordinator](./s09-multi-agent.md) · **Next:** [s11 Session & Memory](./s11-session-memory.md)
