"""
s10 · Background Tasks — 后台任务

演示如何实现非阻塞的后台任务系统。
Agent 可以启动长时间运行的任务，继续响应用户，按需查询结果。

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python s10_background_tasks.py
"""

import json
import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"

# ---------------------------------------------------------------------------
# BackgroundTask — 单个后台任务
# ---------------------------------------------------------------------------

@dataclass
class BackgroundTask:
    """
    一个在后台执行的任务。
    类比: tools/TaskCreateTool + tools/TaskGetTool + tools/TaskUpdateTool
    """

    task_id: str
    description: str
    fn: Callable[[], Any]
    status: str = "pending"          # pending -> running -> completed -> failed
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def execute(self):
        """在后台线程中执行任务"""
        self.status = "running"
        self.started_at = time.time()
        try:
            self.result = str(self.fn())
            self.status = "completed"
        except Exception as e:
            self.error = str(e)
            self.status = "failed"
        finally:
            self.completed_at = time.time()

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    def summary(self) -> str:
        """返回任务摘要"""
        lines = [f"Task {self.task_id}: [{self.status}] {self.description}"]
        if self.duration:
            lines.append(f"  Duration: {self.duration:.1f}s")
        if self.result:
            lines.append(f"  Result: {self.result[:200]}")
        if self.error:
            lines.append(f"  Error: {self.error}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# TaskQueue — 管理所有后台任务
# ---------------------------------------------------------------------------

class TaskQueue:
    """
    后台任务队列。
    类比: TaskCreate/TaskGet/TaskUpdate/TaskList/TaskStop 工具集合
    """

    def __init__(self):
        self.tasks: dict[str, BackgroundTask] = {}
        self._lock = threading.Lock()

    def submit(self, description: str, fn: Callable[[], Any]) -> str:
        """提交新任务，立即返回 task_id（非阻塞）"""
        task_id = f"task-{uuid.uuid4().hex[:6]}"
        task = BackgroundTask(
            task_id=task_id,
            description=description,
            fn=fn,
        )

        with self._lock:
            self.tasks[task_id] = task

        # 在独立线程中执行
        thread = threading.Thread(target=task.execute, daemon=True)
        thread.start()

        return task_id

    def get(self, task_id: str) -> Optional[BackgroundTask]:
        """查询任务状态"""
        with self._lock:
            return self.tasks.get(task_id)

    def list_all(self) -> list[BackgroundTask]:
        """列出所有任务"""
        with self._lock:
            return list(self.tasks.values())

    def stop(self, task_id: str) -> bool:
        """停止任务（简化实现：仅标记状态）"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status == "running":
                task.status = "cancelled"
                task.completed_at = time.time()
                return True
        return False

    def completed_since(self, last_check: float) -> list[BackgroundTask]:
        """返回自上次检查以来完成的任务"""
        with self._lock:
            return [
                t for t in self.tasks.values()
                if t.completed_at and t.completed_at > last_check
            ]


# ---------------------------------------------------------------------------
# Agent with Background Tasks
# ---------------------------------------------------------------------------

# 模拟长时间运行的操作
def slow_operation(name: str, duration: float) -> Callable:
    """创建一个模拟耗时操作的函数"""
    def _run():
        time.sleep(duration)
        return f"{name} completed after {duration:.1f}s"
    return _run


def run_shell_command(cmd: str) -> Callable:
    """创建一个运行 shell 命令的函数"""
    def _run():
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout[:500] if result.returncode == 0 else f"Error: {result.stderr[:200]}"
    return _run


BACKGROUND_TOOLS = [
    {
        "name": "task_create",
        "description": (
            "Create a background task. Returns task_id immediately. "
            "Use task_get to check status and get results. "
            "Available task types: 'sleep' (simulate work), 'shell' (run command)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Short description of the task",
                },
                "task_type": {
                    "type": "string",
                    "enum": ["sleep", "shell"],
                    "description": "Type of task to create",
                },
                "command": {
                    "type": "string",
                    "description": "Command for shell type tasks",
                },
                "duration": {
                    "type": "number",
                    "description": "Duration in seconds for sleep type tasks",
                },
            },
            "required": ["description", "task_type"],
        },
    },
    {
        "name": "task_get",
        "description": "Get the status and result of a background task by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to query",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "task_list",
        "description": "List all background tasks and their statuses.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]

SYSTEM_PROMPT = """You are an agent that can manage background tasks.

You have these tools:
- task_create: Start a background task (returns immediately)
- task_get: Check a task's status and result
- task_list: See all tasks

When the user asks you to do something time-consuming, create a background task.
Then tell the user the task_id and check back later.
You can also list all tasks to give a status overview."""


def handle_tool_call(name: str, input_data: dict, queue: TaskQueue) -> str:
    """处理工具调用"""
    if name == "task_create":
        task_type = input_data.get("task_type", "sleep")
        desc = input_data.get("description", "Unnamed task")

        if task_type == "shell":
            cmd = input_data.get("command", "echo 'hello'")
            task_id = queue.submit(desc, run_shell_command(cmd))
        else:
            duration = input_data.get("duration", 2.0)
            task_id = queue.submit(desc, slow_operation(desc, duration))

        return json.dumps({
            "task_id": task_id,
            "status": "submitted",
            "message": f"Task '{desc}' submitted. Use task_get with id '{task_id}' to check.",
        })

    elif name == "task_get":
        task_id = input_data.get("task_id", "")
        task = queue.get(task_id)
        if not task:
            return json.dumps({"error": f"Task {task_id} not found"})
        return json.dumps({
            "task_id": task.task_id,
            "status": task.status,
            "result": task.result,
            "error": task.error,
            "duration": task.duration,
        }, default=str)

    elif name == "task_list":
        tasks = queue.list_all()
        return json.dumps([
            {
                "task_id": t.task_id,
                "status": t.status,
                "description": t.description,
                "duration": t.duration,
            }
            for t in tasks
        ], default=str)

    return json.dumps({"error": f"Unknown tool: {name}"})


def agent_loop(user_message: str, queue: TaskQueue) -> str:
    """带后台任务能力的 Agent Loop"""
    messages = [{"role": "user", "content": user_message}]

    for _ in range(5):  # 最多 5 轮工具调用
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=BACKGROUND_TOOLS,
            messages=messages,
        )

        # 收集回复内容
        text_parts = []
        tool_use_blocks = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_use_blocks.append(block)

        # 如果没有工具调用，返回文本回复
        if not tool_use_blocks:
            return "\n".join(text_parts)

        # 执行工具调用
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for block in tool_use_blocks:
            print(f"  [Tool Call] {block.name}({json.dumps(block.input)})")
            result = handle_tool_call(block.name, block.input, queue)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

    return "Agent reached maximum iterations."


# ---------------------------------------------------------------------------
# Main — 演示后台任务系统
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("s10 · Background Tasks")
    print("=" * 60)

    queue = TaskQueue()

    # 场景 1: 启动多个后台任务
    print("\n--- 场景 1: 并行启动后台任务 ---")
    result1 = agent_loop(
        "请同时帮我做三件事: (1) 睡眠 3 秒模拟构建, "
        "(2) 睡眠 2 秒模拟测试, (3) 睡眠 1 秒模拟 lint。"
        "启动后告诉我它们的 task_id。",
        queue,
    )
    print(f"\nAgent 回复:\n{result1}")

    # 等待所有任务完成
    print("\n--- 等待后台任务完成 ---")
    for _ in range(10):
        pending = [t for t in queue.list_all() if t.status in ("pending", "running")]
        if not pending:
            break
        print(f"  等待 {len(pending)} 个任务...")
        time.sleep(0.5)

    # 场景 2: 查询任务结果
    print("\n--- 场景 2: 查询任务结果 ---")
    task_ids = [t.task_id for t in queue.list_all()]
    ids_str = ", ".join(task_ids)
    result2 = agent_loop(
        f"查看这些任务的结果: {ids_str}。告诉我每个任务的状态。",
        queue,
    )
    print(f"\nAgent 回复:\n{result2}")

    # 场景 3: 列出所有任务
    print("\n--- 场景 3: 任务列表 ---")
    for task in queue.list_all():
        print(f"  {task.summary()}")

    print("\n" + "=" * 60)
    print("演示完成。后台任务系统让 Agent 可以非阻塞地执行长时间操作。")


if __name__ == "__main__":
    main()
