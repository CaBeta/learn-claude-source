# S08: Hook System — 钩子系统

> s01 > s02 > s03 > s04 > s05 > s06 > s07 > **[ s08 ]** > s09 > s10 > s11 > s12

*在每个关键时刻介入 — 钩子让你定制代理的每个行为*

---

## Problem

你已经有了工具系统、权限系统和技能系统。但你还缺少一种机制，在关键的生命周期节点插入自定义逻辑：

- 在每次工具调用前，验证输入参数
- 在每次工具调用后，记录日志到审计系统
- 在写入敏感文件时，自动备份
- 在模型输出包含敏感信息时，自动脱敏

你需要一个事件驱动的钩子系统，让用户能在不修改核心代码的情况下定制代理行为。

---

## Solution

```
Agent Loop
  |
  +-- while (true):
  |     |
  |     +-- [PreToolUse Hooks]  <-- 工具执行前
  |     |     可以: approve / block / 修改 input
  |     |
  |     +-- tool.call()         <-- 实际执行
  |     |
  |     +-- [PostToolUse Hooks] <-- 工具执行后
  |     |     可以: 记录日志 / 修改结果 / 触发后续操作
  |     |
  |     +-- [PostToolUseFailure Hooks]  <-- 工具执行失败后
  |           可以: 记录错误 / 重试 / 通知
  |
  +-- [SessionStart Hooks]      <-- 会话开始
  +-- [SessionEnd Hooks]        <-- 会话结束
  +-- [Stop Hooks]              <-- 代理停止时
```

---

## How It Works

### 1. Hook Event Types — 钩子事件类型

定义代理生命周期中的所有可拦截事件：

```python
from enum import Enum
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

class HookEvent(str, Enum):
    PRE_TOOL_USE = "PreToolUse"           # 工具调用前
    POST_TOOL_USE = "PostToolUse"         # 工具调用后
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"  # 工具调用失败
    SESSION_START = "SessionStart"        # 会话开始
    SESSION_END = "SessionEnd"            # 会话结束
    STOP = "Stop"                         # 代理停止
    USER_PROMPT_SUBMIT = "UserPromptSubmit"  # 用户提交 prompt
```

### 2. HookContext — 钩子上下文

每次钩子执行时携带的上下文信息：

```python
@dataclass
class HookContext:
    """钩子执行的上下文."""
    event: HookEvent               # 事件类型
    tool_name: str | None = None   # 相关工具名
    tool_input: dict | None = None # 工具输入 (PreToolUse 可修改)
    tool_output: str | None = None # 工具输出 (PostToolUse 可修改)
    error: str | None = None       # 错误信息 (Failure 时)
    metadata: dict = None          # 额外元数据
```

### 3. HookResult — 钩子返回值

钩子通过返回值控制后续流程：

```python
@dataclass
class HookResult:
    """钩子执行结果."""
    continue_execution: bool = True   # 是否继续 (False = 阻止)
    decision: str | None = None       # "approve" / "block"
    updated_input: dict | None = None # 修改后的工具输入
    updated_output: str | None = None # 修改后的工具输出
    message: str | None = None        # 给用户/模型的提示消息
```
```

### 4. Hook — 钩子定义

```python
HookCallback = Callable[[HookContext], Awaitable[HookResult]]

@dataclass
class Hook:
    """一个钩子定义."""
    event: HookEvent               # 监听的事件
    callback: HookCallback         # 回调函数
    matcher: str | None = None     # 工具名匹配 (如只对 "Bash" 生效)
    priority: int = 0              # 优先级 (数字越小越先执行)
    name: str = ""                 # 钩子名称 (用于日志)
```

### 5. HookManager — 钩子管理器

```python
class HookManager:
    """管理所有注册的钩子."""

    def __init__(self):
        self.hooks: list[Hook] = []

    def register(self, hook: Hook):
        self.hooks.append(hook)
        self.hooks.sort(key=lambda h: h.priority)

    async def execute(self, context: HookContext) -> HookResult:
        """执行所有匹配的钩子，聚合结果."""
        aggregated = HookResult()

        for hook in self.hooks:
            # 检查事件类型和 matcher
            if hook.event != context.event:
                continue
            if hook.matcher and context.tool_name != hook.matcher:
                continue

            result = await hook.callback(context)

            # 聚合: 如果任一钩子阻止，则整体阻止
            if not result.continue_execution:
                aggregated.continue_execution = False
                if result.message:
                    aggregated.message = result.message
                return aggregated  # 短路: 立即返回

            # 聚合: 最后一个修改 input/output 的胜出
            if result.updated_input:
                aggregated.updated_input = result.updated_input
                context.tool_input = result.updated_input  # 传递给下一个钩子
            if result.updated_output:
                aggregated.updated_output = result.updated_output
            if result.decision:
                aggregated.decision = result.decision
            if result.message:
                aggregated.message = result.message

        return aggregated
```

### 6. 内置钩子示例

```python
async def logging_hook(ctx: HookContext) -> HookResult:
    """记录所有工具调用的日志."""
    if ctx.event == HookEvent.PRE_TOOL_USE:
        print(f"  [HOOK:log] -> {ctx.tool_name}({json.dumps(ctx.tool_input, default=str)[:80]})")
    elif ctx.event == HookEvent.POST_TOOL_USE:
        print(f"  [HOOK:log] <- {ctx.tool_name}: {str(ctx.tool_output)[:80]}")
    return HookResult()

async def input_validation_hook(ctx: HookContext) -> HookResult:
    """验证工具输入参数."""
    if ctx.tool_name == "run_command":
        cmd = ctx.tool_input.get("command", "")
        dangerous = ["rm -rf /", "drop table", ":(){ :|:& };:"]
        for pattern in dangerous:
            if pattern in cmd.lower():
                return HookResult(
                    continue_execution=False,
                    decision="block",
                    message=f"Blocked dangerous command: contains '{pattern}'",
                )
    return HookResult()

async def auto_approval_hook(ctx: HookContext) -> HookResult:
    """自动批准只读操作."""
    readonly_tools = {"read_file", "glob", "grep"}
    if ctx.tool_name in readonly_tools:
        return HookResult(decision="approve")
    return HookResult()
```

### 7. 将 Hooks 集成到 Agent Loop

```python
async def agent_loop_with_hooks(client, messages, hook_manager):
    while True:
        response = await client.messages.create(...)
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        for block in tool_uses:
            # PreToolUse hooks
            pre_ctx = HookContext(
                event=HookEvent.PRE_TOOL_USE,
                tool_name=block.name,
                tool_input=block.input,
            )
            pre_result = await hook_manager.execute(pre_ctx)

            if not pre_result.continue_execution:
                # Hook 阻止了执行
                result_msg = pre_result.message or "Blocked by hook"
                # ... 返回 tool_result: denied
                continue

            # 使用可能被修改的 input
            actual_input = pre_result.updated_input or block.input

            # 执行工具
            output = tool.call(actual_input)

            # PostToolUse hooks
            post_ctx = HookContext(
                event=HookEvent.POST_TOOL_USE,
                tool_name=block.name,
                tool_input=actual_input,
                tool_output=output,
            )
            post_result = await hook_manager.execute(post_ctx)
            final_output = post_result.updated_output or output
```

---

## Claude Code 源码对照

| 机制 | 源文件 | 关键行 |
|------|--------|--------|
| 27 种 Hook 事件定义 | `entrypoints/agentSdkTypes.ts` | HOOK_EVENTS 数组 |
| Hook JSON 输出 Schema | `types/hooks.ts` | L50-166: `syncHookResponseSchema` |
| Hook 回调类型 | `types/hooks.ts` | L211-226: `HookCallback` |
| Hook 执行结果 | `types/hooks.ts` | L260-275: `HookResult` |
| 聚合结果 | `types/hooks.ts` | L277-290: `AggregatedHookResult` |
| Hook 进度事件 | `types/hooks.ts` | L234-241: `HookProgress` |
| PreToolUse 输出 | `types/hooks.ts` | L73-77: `updatedInput`, `permissionDecision` |
| PostToolUse 输出 | `types/hooks.ts` | L101-107: `updatedMCPToolOutput` |
| 核心执行逻辑 | `utils/hooks.ts` | L1952: `async function* executeHooks()` |
| Matcher 匹配 | `utils/hooks.ts` | L2004: `getMatchingHooks()` |
| 短路阻止 | `utils/hooks.ts` | executeHooks 中 `continue=false` 时 break |
| 异步 Hook 支持 | `utils/hooks.ts` | L171-175: `asyncHookResponseSchema` |
| Timeout 控制 | `utils/hooks.ts` | L1957: `timeoutMs` 参数 |
| 工作区信任检查 | `utils/hooks.ts` | L1994: `shouldSkipHookDueToTrust()` |
| REPL 外 Hook | `utils/hooks.ts` | L3003: `executeHooksOutsideREPL()` |
| PreToolUse 入口 | `utils/hooks.ts` | L3426: `yield* executeHooks(...)` |
| PostToolUse 入口 | `utils/hooks.ts` | L3469: `yield* executeHooks(...)` |
| SessionStart 入口 | `utils/hooks.ts` | L3554: `yield* executeHooks(...)` |
| Stop 入口 | `utils/hooks.ts` | L3587: `await executeHooksOutsideREPL(...)` |

---

## What Changed From s07

| 特性 | s07 Skill System | s08 Hook System |
|------|-----------------|-----------------|
| 核心关注 | 知识复用 | 行为定制 |
| 新增组件 | SkillLoader + SkillManager | HookManager |
| 触发方式 | 用户主动调用 /skill | 事件驱动，自动触发 |
| 执行时机 | 加载时 | 生命周期节点 (pre/post) |
| 可修改内容 | system prompt | 工具输入、输出、执行决策 |
| 阻止能力 | 无 | 可以阻止工具执行 |
| 注册方式 | SKILL.md 文件 | 代码注册 hook.register() |
| 优先级 | 无 | 数字优先级 (越小越先) |
| 短路行为 | 无 | 一旦阻止，后续钩子不执行 |

---

## Try It

1. **实现敏感文件保护钩子**：写一个 PreToolUse hook，当 `write_file` 或 `edit_file` 的路径匹配 `.env`、`credentials.json`、`id_rsa` 等敏感文件时，阻止写入并警告用户。

2. **实现审计日志钩子**：写一对 Pre/Post hook，将所有工具调用的名称、输入、输出、时间戳写入一个 JSONL 文件。每行一个 JSON 对象，便于后续分析。

3. **实现输入净化钩子**：写一个 PreToolUse hook，当 `run_command` 的命令包含 `\n`（换行注入）或 `&&`（命令链）时，自动拆分为独立的命令或警告用户。

4. **实现自定义审批钩子**：结合 s06 的权限系统，将权限检查逻辑从 PermissionChecker 移到 PreToolUse hook 中。这样权限系统就变成了钩子系统的一个插件 — 展示了钩子系统的可扩展性。
