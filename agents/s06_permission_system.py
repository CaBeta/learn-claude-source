"""
S06: Permission System — 权限系统

给 agent 加上安全门: 每个工具调用都需要通过权限检查。
6 种权限模式, 规则匹配, 交互确认。

运行: export ANTHROPIC_API_KEY=your-key && python s06_permission_system.py
依赖: pip install anthropic
"""

import os
import json
import asyncio
from dataclasses import dataclass, field
from typing import Literal, Optional, List, Dict, Any

try:
    from anthropic import AsyncAnthropic
except ImportError:
    print("请安装 anthropic: pip install anthropic")
    raise


# ---------------------------------------------------------------------------
# 1. PermissionRule — 权限规则
# ---------------------------------------------------------------------------

@dataclass
class PermissionRule:
    """一条权限规则: 匹配工具名 + 可选的参数模式."""
    tool_name: str                                    # 工具名, "*" 匹配全部
    behavior: Literal["allow", "deny", "ask"]         # 决策
    pattern: Optional[str] = None                     # 参数匹配模式
    source: str = "user"                              # 规则来源: policy/project/user/session

    def matches(self, tool_name: str, tool_input: dict) -> bool:
        if self.tool_name != "*" and self.tool_name != tool_name:
            return False
        if self.pattern:
            input_str = json.dumps(tool_input, ensure_ascii=False)
            return self.pattern.lower() in input_str.lower()
        return True


# ---------------------------------------------------------------------------
# 2. PermissionChecker — 规则求值器
# ---------------------------------------------------------------------------

class PermissionChecker:
    """按优先级检查权限规则 (policy > project > user > session)."""
    PRIORITY = {"policy": 0, "project": 1, "user": 2, "session": 3}

    def __init__(self, rules: Optional[List[PermissionRule]] = None):
        self.rules: List[PermissionRule] = list(rules) if rules else []
        self._sort_rules()

    def _sort_rules(self):
        self.rules.sort(key=lambda r: self.PRIORITY.get(r.source, 99))

    def add_rule(self, rule: PermissionRule):
        self.rules.append(rule)
        self._sort_rules()

    def check(self, tool_name: str, tool_input: dict) -> str:
        """Return 'allow' / 'deny' / 'ask'."""
        for rule in self.rules:
            if rule.matches(tool_name, tool_input):
                return rule.behavior
        return "ask"


# ---------------------------------------------------------------------------
# 3. Permission Modes — 6 种权限模式
# ---------------------------------------------------------------------------

class PermissionMode:
    DEFAULT = "default"
    PLAN = "plan"
    ACCEPT_EDITS = "acceptEdits"
    BYPASS = "bypassPermissions"
    DONT_ASK = "dontAsk"
    AUTO = "auto"


READONLY_TOOLS = {"read_file", "glob", "grep"}
WRITE_TOOLS = {"write_file", "edit_file", "delete_file"}
DANGEROUS_PATTERNS = [
    "rm -rf", "rm -r /", "mkfs", "dd if=",
    "drop table", "truncate table", "> /dev/sd",
    "format ",
]


# ---------------------------------------------------------------------------
# 4. Default Safety Rules — 内置安全规则
# ---------------------------------------------------------------------------

DEFAULT_RULES: List[PermissionRule] = [
    # 读操作: 自动放行
    PermissionRule("read_file", "allow", source="project"),
    PermissionRule("glob", "allow", source="project"),
    PermissionRule("grep", "allow", source="project"),
    # 写操作: 需要询问
    PermissionRule("write_file", "ask", source="project"),
    PermissionRule("edit_file", "ask", source="project"),
    PermissionRule("delete_file", "ask", source="project"),
    # Shell 命令: 需要询问
    PermissionRule("run_command", "ask", source="project"),
] + [
    # 危险命令: 在 policy 层级直接拒绝
    PermissionRule("run_command", "deny", pattern=p, source="policy")
    for p in DANGEROUS_PATTERNS
]


# ---------------------------------------------------------------------------
# 5. PermissionSystem — 完整权限管线
# ---------------------------------------------------------------------------

class PermissionSystem:
    """完整的权限检查系统.

    管线: Rule Check -> Mode Override -> Interactive Prompt
    类比 Claude Code: hasPermissionsToUseTool -> useCanUseTool -> handleInteractivePermission
    """

    def __init__(self, mode: str = PermissionMode.DEFAULT):
        self.mode = mode
        self.checker = PermissionChecker(DEFAULT_RULES)
        self._cached_decisions: Dict[str, str] = {}

    async def check_permission(self, tool_name: str, tool_input: dict) -> bool:
        """完整权限检查管线."""

        # Bypass 模式: 跳过所有检查
        if self.mode == PermissionMode.BYPASS:
            return True

        # Plan 模式: 只允许读操作
        if self.mode == PermissionMode.PLAN:
            if tool_name in READONLY_TOOLS:
                return True
            if tool_name in WRITE_TOOLS or tool_name == "run_command":
                print(f"  [Plan mode] Write/command blocked: {tool_name}")
                return False

        # AcceptEdits 模式: 文件编辑自动放行
        if self.mode == PermissionMode.ACCEPT_EDITS:
            if tool_name in WRITE_TOOLS:
                return True

        # DontAsk 模式: 使用缓存决策
        if self.mode == PermissionMode.DONT_ASK:
            cached = self._cached_decisions.get(tool_name)
            if cached:
                return cached == "allow"

        # Step 1: 规则检查
        decision = self.checker.check(tool_name, tool_input)
        if decision == "allow":
            self._cached_decisions[tool_name] = "allow"
            return True
        elif decision == "deny":
            print(f"  [Denied by rule] {tool_name}: {tool_input}")
            self._cached_decisions[tool_name] = "deny"
            return False

        # Step 2: 交互确认 (decision == "ask")
        return await self._interactive_check(tool_name, tool_input)

    async def _interactive_check(self, tool_name: str, tool_input: dict) -> bool:
        """交互式权限确认 (类比 Claude Code 的 handleInteractivePermission)."""
        input_summary = json.dumps(tool_input, ensure_ascii=False)[:100]
        print(f"\n  [Permission Required] {tool_name}")
        print(f"    Input: {input_summary}")

        if self.mode == PermissionMode.DONT_ASK:
            print("    -> Denied (dontAsk mode, no cached decision)")
            return False

        try:
            choice = input("    Allow? (y/n/always/never): ").strip().lower()
        except EOFError:
            return False

        if choice in ("y", "yes"):
            return True
        elif choice in ("n", "no"):
            return False
        elif choice == "always":
            self.checker.add_rule(
                PermissionRule(tool_name, "allow", source="session")
            )
            self._cached_decisions[tool_name] = "allow"
            print("    -> Rule saved: always allow")
            return True
        elif choice == "never":
            self.checker.add_rule(
                PermissionRule(tool_name, "deny", source="session")
            )
            self._cached_decisions[tool_name] = "deny"
            print("    -> Rule saved: always deny")
            return False
        return False


# ---------------------------------------------------------------------------
# 6. Agent with Permissions — 带权限检查的 Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful coding assistant with file and shell access.

You have these tools:
- read_file(path): Read a file
- write_file(path, content): Write content to a file
- run_command(command): Run a shell command
"""

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
]


def execute_tool(name: str, input_data: dict) -> str:
    """模拟工具执行."""
    if name == "read_file":
        return f"[Content of {input_data['path']}]: ... (simulated)"
    elif name == "write_file":
        return f"[Wrote {len(input_data['content'])} chars to {input_data['path']}]"
    elif name == "run_command":
        return f"[Output of `{input_data['command']}`]: ... (simulated)"
    return f"Unknown tool: {name}"


async def agent_loop(
    client: AsyncAnthropic,
    user_message: str,
    perm: PermissionSystem,
    messages: Optional[List[Dict]] = None,
) -> List[Dict]:
    """带权限检查的 Agent 循环."""
    if messages is None:
        messages = []
    messages.append({"role": "user", "content": user_message})

    while True:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_use_blocks = [
            b for b in response.content
            if hasattr(b, "type") and b.type == "tool_use"
        ]

        if not tool_use_blocks:
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\nAssistant: {block.text}")
            break

        tool_results = []
        for block in tool_use_blocks:
            print(f"\n  Tool call: {block.name}({json.dumps(block.input, ensure_ascii=False)[:80]})")

            # 权限检查 — 这是核心!
            allowed = await perm.check_permission(block.name, block.input)

            if allowed:
                result = execute_tool(block.name, block.input)
                print(f"  -> Executed: {result[:80]}")
            else:
                result = f"Permission denied for {block.name}"
                print(f"  -> Blocked: {result}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

    return messages


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def demo():
    client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    print("=" * 60)
    print("S06: Permission System Demo")
    print("=" * 60)

    # --- 测试 1: 规则匹配 ---
    print("\n--- Testing permission rules ---")

    perm = PermissionSystem(mode=PermissionMode.BYPASS)
    assert await perm.check_permission("read_file", {"path": "/tmp/test.py"})
    print("  [PASS] read_file -> allow (bypass mode)")

    perm2 = PermissionSystem()  # default mode
    result = perm2.checker.check("run_command", {"command": "rm -rf /"})
    assert result == "deny"
    print("  [PASS] run_command(rm -rf) -> deny by rule")

    result = perm2.checker.check("run_command", {"command": "ls -la"})
    assert result == "ask"
    print("  [PASS] run_command(ls -la) -> ask")

    perm_plan = PermissionSystem(mode=PermissionMode.PLAN)
    assert await perm_plan.check_permission("read_file", {"path": "test.py"})
    print("  [PASS] Plan mode: read_file -> allow")

    # --- 测试 2: 带 agent 运行 ---
    print("\n--- Running agent with permissions ---")
    perm_agent = PermissionSystem(mode=PermissionMode.BYPASS)
    messages = await agent_loop(
        client,
        "Read the file config.json and tell me what's in it.",
        perm_agent,
    )
    print(f"\n--- Done (total messages: {len(messages)}) ---")


if __name__ == "__main__":
    asyncio.run(demo())
