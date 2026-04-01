"""
s09 · Multi-Agent Coordinator — 多代理协调器

演示如何构建一个 Coordinator-Worker 模式的多 Agent 系统。
Coordinator 负责任务分解和结果综合，Worker 负责具体执行。

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python s09_multi_agent.py
"""

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"

# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class TaskResult:
    """Worker 执行结果"""
    agent_id: str
    task_description: str
    status: str          # "completed" | "failed"
    output: str
    usage: dict = field(default_factory=dict)

    def to_notification(self) -> str:
        """转换为 Claude Code 风格的 task-notification XML"""
        return f"""<task-notification>
<task-id>{self.agent_id}</task-id>
<status>{self.status}</status>
<summary>Worker "{self.task_description}" {self.status}</summary>
<result>{self.output}</result>
</task-notification>"""


@dataclass
class WorkerSpec:
    """Worker 规格 — Coordinator 派发任务时创建"""
    agent_id: str
    description: str
    prompt: str
    status: str = "pending"   # pending -> running -> completed -> failed


# ---------------------------------------------------------------------------
# Worker Agent
# ---------------------------------------------------------------------------

class WorkerAgent:
    """
    执行具体子任务的 Worker Agent。
    每个 Worker 有独立的 LLM 调用和 context。
    类比: coordinator/coordinatorMode.ts 中的 "Workers"
    """

    def __init__(self, spec: WorkerSpec):
        self.spec = spec
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    async def execute(self) -> TaskResult:
        """Worker 独立执行任务"""
        self.spec.status = "running"
        print(f"  [Worker {self.spec.agent_id}] 开始: {self.spec.description}")

        system_prompt = (
            "You are a focused worker agent executing a specific task. "
            "Do exactly what is asked. Be concise and thorough. "
            "Report findings clearly with file paths, line numbers, and specifics."
        )

        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=MODEL,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": self.spec.prompt}],
            )

            output = response.content[0].text
            self.spec.status = "completed"
            print(f"  [Worker {self.spec.agent_id}] 完成")

            return TaskResult(
                agent_id=self.spec.agent_id,
                task_description=self.spec.description,
                status="completed",
                output=output,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            )
        except Exception as e:
            self.spec.status = "failed"
            print(f"  [Worker {self.spec.agent_id}] 失败: {e}")
            return TaskResult(
                agent_id=self.spec.agent_id,
                task_description=self.spec.description,
                status="failed",
                output=str(e),
            )


# ---------------------------------------------------------------------------
# Coordinator Agent
# ---------------------------------------------------------------------------

COORDINATOR_SYSTEM_PROMPT = """You are a coordinator agent that orchestrates \
software engineering tasks across multiple workers.

Your role:
1. Break down complex tasks into subtasks
2. Delegate subtasks to workers (you will be given worker results)
3. Synthesize findings and make decisions
4. Never fabricate worker results — wait for actual results to arrive

When you receive worker results (in <task-notification> XML), read them carefully \
and synthesize before deciding next steps.

Be concise. Focus on actionable instructions."""


class CoordinatorAgent:
    """
    协调器 Agent — 规划任务并派发给 Workers。
    类比: coordinator/coordinatorMode.ts 中的 Coordinator 系统

    工作流:
        Research (并行) → Synthesis (Coordinator) → Implementation (Worker) → Verification (Worker)
    """

    def __init__(self):
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.conversation: list[dict] = []

    # -- Phase 1: Plan tasks ------------------------------------------------

    async def plan_tasks(self, user_request: str) -> list[WorkerSpec]:
        """Phase 1: 分解用户请求为多个 Worker 任务"""
        print("\n[Coordinator] Phase 1: 规划任务...")

        plan_prompt = f"""Given this user request, break it down into research subtasks.
Each subtask will be assigned to an independent worker.

Rules:
- Output ONLY a JSON array of objects
- Each object has "description" (short name) and "prompt" (detailed instructions for worker)
- Workers CANNOT see each other or the original conversation
- Each prompt must be self-contained with all context needed
- Focus on RESEARCH tasks first (investigation, finding files, understanding code)

User request: {user_request}

Output format:
```json
[
  {{"description": "...", "prompt": "..."}},
  ...
]
```"""

        self.conversation = [
            {"role": "user", "content": plan_prompt}
        ]

        response = await asyncio.to_thread(
            self.client.messages.create,
            model=MODEL,
            max_tokens=2048,
            system=COORDINATOR_SYSTEM_PROMPT,
            messages=self.conversation,
        )

        raw = response.content[0].text
        self.conversation.append({"role": "assistant", "content": raw})

        # 解析 JSON
        specs = self._parse_worker_specs(raw)
        for spec in specs:
            print(f"  Worker: {spec.description}")
        return specs

    # -- Phase 2: Execute workers in parallel -------------------------------

    async def execute_parallel(self, specs: list[WorkerSpec]) -> list[TaskResult]:
        """Phase 2: 并行执行所有 Worker"""
        print(f"\n[Coordinator] Phase 2: 并行启动 {len(specs)} 个 Workers...")

        workers = [WorkerAgent(spec) for spec in specs]
        results = await asyncio.gather(*[w.execute() for w in workers])

        return list(results)

    # -- Phase 3: Synthesize results ----------------------------------------

    async def synthesize(
        self, user_request: str, results: list[TaskResult]
    ) -> str:
        """Phase 3: 综合 Worker 结果，生成最终回答或后续计划"""
        print("\n[Coordinator] Phase 3: 综合结果...")

        # 将 Worker 结果以 notification 格式注入对话
        notifications = "\n\n".join(r.to_notification() for r in results)

        synth_prompt = f"""The workers have returned their results.

Original request: {user_request}

Worker results:
{notifications}

Based on these results, provide a clear, comprehensive answer to the user.
Include specific details from the worker findings."""

        self.conversation.append({"role": "user", "content": synth_prompt})

        response = await asyncio.to_thread(
            self.client.messages.create,
            model=MODEL,
            max_tokens=2048,
            system=COORDINATOR_SYSTEM_PROMPT,
            messages=self.conversation,
        )

        synthesized = response.content[0].text
        self.conversation.append({"role": "assistant", "content": synthesized})
        return synthesized

    # -- Helpers ------------------------------------------------------------

    def _parse_worker_specs(self, raw: str) -> list[WorkerSpec]:
        """从 LLM 输出解析 Worker 规格"""
        # 提取 JSON block
        json_str = raw
        if "```json" in raw:
            json_str = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            json_str = raw.split("```")[1].split("```")[0]

        try:
            items = json.loads(json_str.strip())
        except json.JSONDecodeError:
            # fallback: 创建单个 research worker
            return [WorkerSpec(
                agent_id=f"worker-{uuid.uuid4().hex[:6]}",
                description="Research task",
                prompt=raw,
            )]

        specs = []
        for item in items[:5]:  # 最多 5 个 worker
            specs.append(WorkerSpec(
                agent_id=f"worker-{uuid.uuid4().hex[:6]}",
                description=item.get("description", "Unnamed task"),
                prompt=item.get("prompt", ""),
            ))
        return specs


# ---------------------------------------------------------------------------
# Main — 演示多 Agent 协调流程
# ---------------------------------------------------------------------------

async def main():
    print("=" * 60)
    print("s09 · Multi-Agent Coordinator")
    print("=" * 60)

    # 用户请求 — 一个需要多方面调查的复杂任务
    user_request = (
        "分析 Python 项目中常见的设计模式。"
        "找出 3 个最重要的设计模式，解释每个的应用场景，"
        "并给出简短的代码示例。"
    )
    print(f"\n用户请求: {user_request}")

    coordinator = CoordinatorAgent()

    # Phase 1: 规划
    specs = await coordinator.plan_tasks(user_request)

    # Phase 2: 并行执行
    results = await coordinator.execute_parallel(specs)

    # Phase 3: 综合
    final_answer = await coordinator.synthesize(user_request, results)

    # 输出最终结果
    print("\n" + "=" * 60)
    print("最终回答:")
    print("=" * 60)
    print(final_answer)

    # 统计
    total_input = sum(r.usage.get("input_tokens", 0) for r in results)
    total_output = sum(r.usage.get("output_tokens", 0) for r in results)
    print(f"\n--- 统计 ---")
    print(f"Workers: {len(specs)}")
    print(f"成功: {sum(1 for r in results if r.status == 'completed')}")
    print(f"失败: {sum(1 for r in results if r.status == 'failed')}")
    print(f"Worker tokens: {total_input} in / {total_output} out")


if __name__ == "__main__":
    asyncio.run(main())
