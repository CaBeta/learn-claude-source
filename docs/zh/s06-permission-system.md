# S06: Permission System — 权限系统

> s01 > s02 > s03 > s04 > s05 > **[ s06 ]** > s07 > s08 > s09 > s10 > s11 > s12

*信任但验证 — 每个工具调用都需要通过安全检查*

---

## Problem

你的代理拥有强大的能力：可以读写文件、执行 Shell 命令、发送网络请求。如果不加限制，一个错误的工具调用就可能删除重要文件、泄露敏感信息、甚至执行恶意代码。

你需要一套权限系统，在每次工具执行前进行检查：这个操作安全吗？用户是否允许？是否符合预设的安全规则？

---

## Solution

```
tool_use block (来自模型)
  |
  v
+----------------------------------------------------------+
|                 Permission Pipeline                       |
|                                                          |
|  [1] Schema Validation                                   |
|      输入参数类型检查                                     |
|      |                                                   |
|  [2] Tool validateInput                                  |
|      工具自定义业务逻辑验证                               |
|      |                                                   |
|  [3] Pre-tool Hooks                                      |
|      用户配置的前置钩子 (可修改/阻止)                     |
|      |                                                   |
|  [4] checkPermissions                                    |
|      工具级权限检查 (rule-based)                          |
|      |                                                   |
|  [5] canUseTool                                          |
|      通用权限决策 (结合 mode + 用户交互)                  |
|      |                                                   |
|  [6] tool.call()                                         |
|      实际执行                                             |
|      |                                                   |
|  [7] Post-tool Hooks                                     |
|      后置钩子 (记录日志/修改结果)                         |
|                                                          |
+----------------------------------------------------------+
  |
  v
tool_result message
```

---

## How It Works

### 1. PermissionRule — 权限规则

每条规则定义了"谁在什么条件下可以做什么"：

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class PermissionRule:
    """一条权限规则：匹配工具名和参数模式."""
    tool_name: str                    # 工具名，支持通配符 "*"
    behavior: Literal["allow", "deny", "ask"]  # 决策行为
    pattern: str | None = None        # 参数匹配模式 (如路径/命令)
    source: str = "user"              # 规则来源: user / project / policy

    def matches(self, tool_name: str, tool_input: dict) -> bool:
        """检查规则是否匹配当前工具调用."""
        if self.tool_name != "*" and self.tool_name != tool_name:
            return False
        if self.pattern:
            input_str = str(tool_input)
            return self.pattern in input_str
        return True
```

### 2. PermissionChecker — 规则求值器

按优先级检查所有规则，找到第一个匹配的规则：

```python
class PermissionChecker:
    """按优先级检查权限规则."""
    def __init__(self, rules: list[PermissionRule] | None = None):
        self.rules: list[PermissionRule] = rules or []
        # 按优先级排序: policy > project > user
        self._sort_rules()

    def _sort_rules(self):
        priority = {"policy": 0, "project": 1, "user": 2}
        self.rules.sort(key=lambda r: priority.get(r.source, 99))

    def check(self, tool_name: str, tool_input: dict) -> str:
        """检查权限，返回 'allow' / 'deny' / 'ask'."""
        for rule in self.rules:
            if rule.matches(tool_name, tool_input):
                return rule.behavior
        return "ask"  # 默认行为: 询问用户
```

### 3. Permission Modes — 权限模式

不同的运行模式决定权限系统的默认行为：

```python
class PermissionMode:
    DEFAULT = "default"              # 危险操作需要确认
    PLAN = "plan"                    # 只读操作自动放行
    ACCEPT_EDITS = "acceptEdits"     # 自动接受文件编辑
    BYPASS = "bypassPermissions"     # 跳过所有检查 (CI/headless)
    DONT_ASK = "dontAsk"             # 不询问，使用缓存决策
    AUTO = "auto"                    # 基于分类器自动决策
```

### 4. Interactive Prompt — 交互式确认

当规则返回 "ask" 时，提示用户确认：

```python
async def interactive_check(tool_name: str, tool_input: dict) -> str:
    """交互式权限确认."""
    input_summary = str(tool_input)[:100]
    print(f"\n[Permission] {tool_name}: {input_summary}")
    choice = input("  Allow? (y/n/always/never): ").strip().lower()

    if choice in ("y", "yes"):
        return "allow"
    elif choice in ("n", "no"):
        return "deny"
    elif choice == "always":
        return "allow_permanent"  # 写入规则
    elif choice == "never":
        return "deny_permanent"   # 写入规则
    return "deny"
```

### 5. 预定义安全规则

为常见工具设置合理的默认规则：

```python
DEFAULT_RULES = [
    PermissionRule("read_file", "allow", source="project"),      # 读文件：自动允许
    PermissionRule("glob", "allow", source="project"),           # 文件搜索：自动允许
    PermissionRule("grep", "allow", source="project"),           # 内容搜索：自动允许
    PermissionRule("write_file", "ask", source="project"),       # 写文件：询问
    PermissionRule("edit_file", "ask", source="project"),        # 编辑文件：询问
    PermissionRule("run_command", "ask", source="project"),      # Shell 命令：询问
    PermissionRule("run_command", "deny", pattern="rm -rf", source="policy"),  # 危险命令：禁止
    PermissionRule("run_command", "deny", pattern="drop table", source="policy"),
]
```

### 6. 完整权限管线

```python
class PermissionSystem:
    def __init__(self, mode: str = "default"):
        self.mode = mode
        self.checker = PermissionChecker(DEFAULT_RULES)

    async def check_permission(self, tool_name: str, tool_input: dict) -> bool:
        if self.mode == "bypassPermissions":
            return True

        # Step 1: 规则检查
        decision = self.checker.check(tool_name, tool_input)

        # Step 2: Mode 覆盖
        if self.mode == "plan" and tool_name in ("read_file", "glob", "grep"):
            return True  # Plan 模式下只读工具自动放行
        if self.mode == "acceptEdits" and tool_name in ("write_file", "edit_file"):
            return True

        # Step 3: 交互式确认
        if decision == "allow":
            return True
        elif decision == "deny":
            print(f"  [Denied by rule] {tool_name}")
            return False
        else:  # ask
            result = await interactive_check(tool_name, tool_input)
            if "permanent" in result:
                behavior = "allow" if "allow" in result else "deny"
                self.checker.rules.append(
                    PermissionRule(tool_name, behavior, source="session"))
            return "allow" in result
```

---

## Claude Code 源码对照

| 机制 | 源文件 | 关键行 |
|------|--------|--------|
| 权限模式定义 | `types/permissions.ts` | L16-22: `EXTERNAL_PERMISSION_MODES` |
| PermissionBehavior 类型 | `types/permissions.ts` | L44: `'allow' \| 'deny' \| 'ask'` |
| PermissionRule 类型 | `types/permissions.ts` | L75-79: `PermissionRule` |
| PermissionResult 类型 | `types/permissions.ts` | L251-266: 含 `passthrough` |
| 决策原因类型 | `types/permissions.ts` | L271-324: 11 种 `PermissionDecisionReason` |
| Tool 权限上下文 | `types/permissions.ts` | L427-441: `ToolPermissionContext` |
| 权限管线入口 | `services/tools/toolExecution.ts` | L599: `checkPermissionsAndCallTool()` |
| Schema Validation | `services/tools/toolExecution.ts` | L615: `tool.inputSchema.safeParse()` |
| 实际权限决策 | `services/tools/toolExecution.ts` | L510-557: `runToolUse()` 调用链 |
| React 权限 Hook | `hooks/useCanUseTool.ts` | `canUseTool()` 通用权限决策 |
| 权限上下文求值 | `hooks/toolPermission/PermissionContext.ts` | 规则求值逻辑 |
| buildTool 默认权限 | `Tool.ts` | L757-769: `TOOL_DEFAULTS.checkPermissions` |

---

## What Changed From s05

| 特性 | s05 Context Management | s06 Permission System |
|------|----------------------|----------------------|
| 核心关注 | 控制 token 数量 | 控制操作安全性 |
| 新增组件 | ContextManager | PermissionChecker + PermissionSystem |
| 决策类型 | 保留/截断/压缩 | allow/deny/ask |
| 规则来源 | 无 | user / project / policy / session |
| 用户交互 | 无 | 交互式确认 (y/n/always/never) |
| 模式支持 | 无 | 6 种 PermissionMode |
| 安全默认值 | 无 | 危险命令自动禁止 |

---

## Try It

1. **添加更多安全规则**：为 `run_command` 添加规则，禁止包含 `sudo`、`curl | bash`、`mkfs` 等危险模式的命令。为 `write_file` 添加规则，禁止写入 `/etc/`、`/usr/` 等系统目录。

2. **实现 PermissionMode.PLAN**：在 Plan 模式下，所有只读工具（`read_file`、`glob`、`grep`）自动放行，所有写操作自动拒绝。提示：给每个工具添加 `is_readonly` 属性。

3. **实现分类器模式 (PermissionMode.AUTO)**：不要求真正调用模型，而是实现一个简单的基于模式的分类器。例如：包含 `test` 的命令归为 "safe"，包含 `deploy` 的归为 "risky"，包含 `delete` 的归为 "dangerous"。

4. **实现权限缓存**：当用户选择 "always" 或 "never" 时，将决策写入一个 JSON 文件，下次启动时自动加载。注意：需要区分 session 级别和永久级别的缓存。
