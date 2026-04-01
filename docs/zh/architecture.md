# Claude Code 源码架构深度解析

> 基于 `claude-code-main/src/` 源码的逆向分析。所有文件路径相对于 `src/` 目录，行号基于源码原文。

---

## 1. 总体架构

Claude Code 是一个基于 TypeScript 的 AI Agent CLI，其核心架构可以概括为 **"一个巨大的启动器 + 一个精巧的状态机"**。

很多人看到 `main.tsx` 有 4683 行、803KB，会误以为它包含了整个 Agent Loop。但事实上，`main.tsx` 只是一个 **CLI 路由器和启动编排器**，它的体积来自于对数十种命令行模式（`-p`、`--resume`、`--print`、SDK 模式等）的分发处理。真正的 Agent Loop 隐藏在 `query.ts` 中。

### 核心文件一览

| 文件 | 行数 | 职责 |
|------|------|------|
| `main.tsx` | 4683 | CLI 入口、参数解析、模式路由、启动编排 |
| `query.ts` | 1729 | Agent Loop 核心：`async function* query()` 生成器 |
| `Tool.ts` | 792 | Tool 接口定义、`buildTool()` 工厂函数 |
| `tools.ts` | 389 | Tool 注册表，`getAllBaseTools()` 返回所有内置工具 |
| `commands.ts` | 754 | Slash 命令分发框架 |
| `commands/` | ~101 文件 | 各个 slash 命令的实现 |

### 顶层调用链

```
用户输入
  |
  v
main.tsx::main()                      (L585)
  |-- 解析 CLI 参数
  |-- 根据 -p / --resume / --print / SDK 等模式路由
  |-- 调用 launchRepl() 启动 REPL    (L3134, L3176, L3242, ...)
  |
  v
replLauncher.tsx::launchRepl()        (L12)
  |-- 创建 REPL React 组件
  |-- 绑定 query() 到用户输入流
  |
  v
query.ts::query()                     (L219)
  |-- async generator，yield 流式事件
  |-- 委托给 queryLoop()              (L241)
  |
  v
query.ts::queryLoop()                 (L241)
  |-- while(true) 状态机              (L307)
  |-- 调用模型 API -> 解析 tool_use -> 执行工具 -> 循环
```

### ASCII 架构总览

```
+------------------------------------------------------------------+
|                         main.tsx (4683L)                          |
|   CLI Arg Parsing | Mode Routing | Plugin Init | Auth Bootstrap   |
+-------+------------------+------------------+---------------------+
        |                  |                  |
        v                  v                  v
   Print Mode         REPL Mode          SDK Mode
   (one-shot)    +------------+    (headless API)
        |        |  REPL.tsx  |         |
        |        | (React UI) |         |
        |        +-----+------+         |
        |              |                |
        +------+-------+--------+------+
               |                |
               v                v
      +----------------------------------------+
      |       query.ts (1729L)                 |
      |  async function* query() {             |
      |    yield* queryLoop(params)            |
      |  }                                     |
      |                                        |
      |  +-----------------------------------+ |
      |  | while (true) {                    | |
      |  |   1. Context Management (5层)     | |
      |  |   2. Call Model API (streaming)   | |
      |  |   3. Collect tool_use blocks      | |
      |  |   4. Execute tools (parallel)     | |
      |  |   5. Update state -> continue     | |
      |  | }                                 | |
      |  +-----------------------------------+ |
      +------+-----------------+---------------+
             |                 |
             v                 v
    +------------------+  +---------------------+
    |  StreamingTool   |  |   runTools()        |
    |  Executor        |  |   (sequential)      |
    |  (parallel)      |  |                     |
    +--------+---------+  +----------+----------+
             |                        |
             v                        v
    +--------------------------------------------+
    |         toolExecution.ts                   |
    |    runToolUse() -> checkPermissionsAndCall |
    |    Tool() -> validateInput -> call()       |
    +--------------------------------------------+
```

---

## 2. Agent Loop 详解 (query.ts)

`query.ts` 是 Claude Code 最核心的文件。它实现了一个基于 `async generator` 的 Agent Loop，通过 `yield` 向外暴露流式事件。

### 2.1 函数签名

```typescript
// query.ts:219
export async function* query(
  params: QueryParams,
): AsyncGenerator<
  | StreamEvent
  | RequestStartEvent
  | Message
  | TombstoneMessage
  | ToolUseSummaryMessage,
  Terminal
>
```

`query()` 本身只是一个薄包装，真正的工作委托给 `queryLoop()`（L241）。这种设计使得 `query()` 可以在 `queryLoop()` 正常返回后执行清理工作（通知已消费的命令 UUID）。

### 2.2 State 对象与不可变状态模式

在 `queryLoop()` 的顶部，状态被组织为一个 `State` 对象（L268-279）：

```typescript
let state: State = {
  messages: params.messages,
  toolUseContext: params.toolUseContext,
  maxOutputTokensOverride: params.maxOutputTokensOverride,
  autoCompactTracking: undefined,
  stopHookActive: undefined,
  maxOutputTokensRecoveryCount: 0,
  hasAttemptedReactiveCompact: false,
  turnCount: 1,
  pendingToolUseSummary: undefined,
  transition: undefined,
}
```

每次循环迭代开始时，State 被解构（L311-321）：

```typescript
while (true) {
  let { toolUseContext } = state
  const {
    messages,
    autoCompactTracking,
    maxOutputTokensRecoveryCount,
    // ...
  } = state
```

**关键设计**：所有 `continue` 点都通过 `state = { ... }` 创建全新的 State 对象，而不是逐个字段修改。这确保了每次迭代的状态是 **原子的、不可变的**，避免了跨迭代的意外状态泄漏。

源码中的注释（L265-267）明确说明了这一设计意图：

> Mutable cross-iteration state. The loop body destructures this at the top of each iteration so reads stay bare-name. Continue sites write `state = { ... }` instead of 9 separate assignments.

### 2.3 循环体流程

```
while (true) {
  |
  +-- 1. 解构 State
  |     let { toolUseContext, messages, ... } = state     (L311-321)
  |
  +-- 2. 上下文管理 (5 层压缩管线)
  |     Budget -> Snip -> Microcompact -> Collapse -> Autocompact
  |     (L369-543)
  |
  +-- 3. 创建 StreamingToolExecutor (如果启用)
  |     streamingToolExecutor = new StreamingToolExecutor(...)  (L563-568)
  |
  +-- 4. 阻塞限制检查
  |     如果 context window 溢出 -> return { reason: 'blocking_limit' }  (L646)
  |
  +-- 5. 调用模型 API (streaming)
  |     for await (const message of deps.callModel({...})) { ... }  (L659-863)
  |     - 收集 assistant messages
  |     - 收集 tool_use blocks
  |     - 如果有 StreamingToolExecutor，立即投递 tool_use blocks
  |     - yield 流式消息给外部消费者
  |
  +-- 6. 后流式决策 (Post-streaming decisions)
  |     - 如果 aborted -> return { reason: 'aborted_streaming' }  (L1051)
  |     - 如果 !needsFollowUp (没有 tool_use):
  |       - 尝试 PTL/media recovery  (L1062-1183)
  |       - max_output_tokens recovery  (L1188-1256)
  |       - Stop hooks  (L1267-1306)
  |       - Token budget check  (L1308-1355)
  |       - return { reason: 'completed' }  (L1357)
  |
  +-- 7. Tool 执行
  |     const toolUpdates = streamingToolExecutor
  |       ? streamingToolExecutor.getRemainingResults()  (L1381)
  |       : runTools(...)  (L1382)
  |     for await (const update of toolUpdates) { ... }  (L1384-1408)
  |
  +-- 8. 构建 Tool Use Summary (异步不阻塞)
  |     nextPendingToolUseSummary = generateToolUseSummary({...})  (L1469-1481)
  |
  +-- 9. 处理 Attachments & 排队命令
  |     for await (const attachment of getAttachmentMessages(...)) { ... }  (L1580)
  |
  +-- 10. 更新 State 并 continue
  |     state = { messages: [...], toolUseContext, ... }  (L1640-1655)
  |     continue
}
```

### 2.4 Continue 与 Return 站点

Agent Loop 中有 **7 个 continue 站点** 和 **约 10 个 return 站点**：

**Continue 站点**（循环回到 `while(true)` 顶部）：

| # | 位置 | 原因 |
|---|------|------|
| 1 | L950 | 模型 fallback 后重试（`FallbackTriggeredError`） |
| 2 | L1115 | Context collapse drain 后重试（PTL recovery） |
| 3 | L1165 | Reactive compact 后重试（PTL/media recovery） |
| 4 | L1220 | max_output_tokens 升级到 64k 后重试 |
| 5 | L1251 | max_output_tokens recovery 注入续写消息后重试 |
| 6 | L1305 | Stop hook 阻断错误后重试 |
| 7 | L1340 | Token budget 继续决策后重试 |

**Return 站点**（退出循环，结束 query）：

| # | 位置 | 原因 |
|---|------|------|
| 1 | L646 | 阻塞限制（context window 溢出且无法压缩） |
| 2 | L977 | 图片大小/调整错误 |
| 3 | L996 | 模型错误（API 抛出异常） |
| 4 | L1051 | 用户中断（abort during streaming） |
| 5 | L1175 | PTL/media recovery 失败 |
| 6 | L1182 | PTL recovery 失败（collapse 路径） |
| 7 | L1264 | API 错误消息（rate limit 等） |
| 8 | L1279 | Stop hook 阻止继续 |
| 9 | L1357 | 正常完成（无 tool_use，无 recovery 需求） |
| 10 | L1515 | 用户中断（abort during tool execution） |
| 11 | L1520 | Hook 停止继续 |

### 2.5 5 层上下文管理管线

这是 Agent Loop 中最精巧的设计之一。每次循环迭代开始时，messages 会依次经过 5 层压缩/管理，以控制 context window 的大小：

```
messages (原始)
  |
  v
[1] Budget Layer (L376-394)
  |  applyToolResultBudget() -- 控制 tool result 的总大小
  v
[2] Snip Layer (L401-410)
  |  snipCompactIfNeeded() -- 截断过长的历史 tool output
  |  (feature gate: HISTORY_SNIP)
  v
[3] Microcompact Layer (L413-426)
  |  deps.microcompact() -- 将旧 tool 结果替换为简短摘要
  |  支持 cached microcompact（cache editing）
  v
[4] Collapse Layer (L440-447)
  |  contextCollapse.applyCollapsesIfNeeded() -- 投影折叠视图
  |  (feature gate: CONTEXT_COLLAPSE)
  v
[5] Autocompact Layer (L453-543)
  |  deps.autocompact() -- 完整的上下文压缩，生成 summary
  |  如果触发压缩，替换 messagesForQuery 并重置 tracking
  v
messagesForQuery (处理后，送入 API)
```

**设计亮点**：

- Snip 在 Microcompact 之前运行，因为 `tokenCountWithEstimation` 无法感知 snip 释放的 token 数，需要显式传递 `snipTokensFreed`
- Collapse 在 Autocompact 之前运行，这样如果 collapse 已经将 context 压到阈值以下，autocompact 就是 no-op，保留了更细粒度的上下文
- Autocompact 触发后会生成全新的 summary messages，替换掉原来的消息历史

---

## 3. Tool 系统

### 3.1 Tool 接口 (`Tool.ts`)

`Tool.ts` 定义了 Claude Code 的 Tool 接口。每个 Tool 是一个包含以下核心方法的对象：

```
Tool {
  name: string                    -- 工具名称（如 "Bash"、"Read"）
  inputSchema: ZodSchema          -- 输入验证 schema
  call(input, context): Promise   -- 实际执行逻辑

  // 可被 buildTool() 提供默认值的方法：
  isEnabled(): boolean            -- 是否启用（默认 true）
  isConcurrencySafe(input): bool  -- 是否可并行执行（默认 false）
  isReadOnly(input): boolean      -- 是否只读（默认 false）
  isDestructive(input): boolean   -- 是否破坏性操作（默认 false）
  checkPermissions(input, ctx)    -- 权限检查（默认 allow）
  toAutoClassifierInput(input)    -- 分类器输入（默认空字符串）
  userFacingName(input)           -- 用户可见名称（默认 = name）
}
```

### 3.2 buildTool() 工厂函数 (`Tool.ts:783`)

`buildTool()` 是一个 **安全默认值工厂**，它接收一个 partial Tool 定义，填充安全的默认值：

```typescript
// Tool.ts:757-769
const TOOL_DEFAULTS = {
  isEnabled: () => true,
  isConcurrencySafe: (_input?: unknown) => false,    // 假设不安全
  isReadOnly: (_input?: unknown) => false,             // 假设有写操作
  isDestructive: (_input?: unknown) => false,
  checkPermissions: (input, _ctx) =>
    Promise.resolve({ behavior: 'allow', updatedInput: input }),
  toAutoClassifierInput: (_input?: unknown) => '',
  userFacingName: (_input?: unknown) => '',            // 后被覆盖为 name
}

// Tool.ts:783-792
export function buildTool<D extends AnyToolDef>(def: D): BuiltTool<D> {
  return {
    ...TOOL_DEFAULTS,
    userFacingName: () => def.name,    // 覆盖默认的空字符串
    ...def,                            // 用户的定义覆盖默认值
  } as BuiltTool<D>
}
```

**关键设计原则**：
- `isConcurrencySafe` 默认为 `false` -- 不明确的工具不能并行执行
- `isReadOnly` 默认为 `false` -- 假设工具可能有副作用
- `checkPermissions` 默认为 `allow` -- 延迟到通用权限系统处理
- `toAutoClassifierInput` 默认为空 -- 安全相关的工具必须显式覆盖

### 3.3 Tool 注册表 (`tools.ts`)

`tools.ts` 中的 `getAllBaseTools()` 函数（L193）是所有内置工具的注册中心：

```typescript
// tools.ts:193
export function getAllBaseTools(): Tools {
  return [
    AgentTool,
    TaskOutputTool,
    BashTool,
    FileEditTool,
    FileReadTool,
    FileWriteTool,
    GlobTool,
    NotebookEditTool,
    WebFetchTool,
    // ... ~43 个工具
  ]
}
```

### 3.4 内置工具清单

`src/tools/` 目录下包含约 **43 个工具目录**（含共享工具和测试工具）：

**文件操作类**：
- `BashTool` - Shell 命令执行
- `FileReadTool` - 读取文件
- `FileEditTool` - 编辑文件（精确字符串替换）
- `FileWriteTool` - 写入文件
- `GlobTool` - 文件模式匹配
- `GrepTool` - 内容搜索
- `NotebookEditTool` - Jupyter Notebook 编辑

**任务管理类**：
- `TaskCreateTool` / `TaskGetTool` / `TaskUpdateTool` / `TaskListTool` / `TaskStopTool` - 任务 CRUD
- `TaskOutputTool` - 获取任务输出

**Agent 类**：
- `AgentTool` - 子 Agent 调度
- `SendMessageTool` - Agent 间通信
- `TeamCreateTool` / `TeamDeleteTool` - 团队管理

**搜索类**：
- `WebSearchTool` - 网络搜索
- `WebFetchTool` - 网页抓取
- `ToolSearchTool` - 工具发现

**MCP 类**：
- `MCPTool` - MCP 工具代理
- `ListMcpResourcesTool` / `ReadMcpResourceTool` - MCP 资源
- `McpAuthTool` - MCP 认证

**其他**：
- `AskUserQuestionTool` - 向用户提问
- `SkillTool` - 技能调用
- `ConfigTool` - 配置管理
- `EnterPlanModeTool` / `ExitPlanModeTool` - 计划模式切换
- `EnterWorktreeTool` / `ExitWorktreeTool` - Git worktree 管理
- `TodoWriteTool` - Todo 列表
- `BriefTool` - 生成摘要
- `LSPTool` - 语言服务器协议

**Feature-gated 工具**（通过 `feature()` 或 `process.env` 控制启用）：
- `REPLTool` - REPL 模式（`USER_TYPE=ant`）
- `SleepTool` - 主动等待（`PROACTIVE` 或 `KAIROS` feature）
- `WorkflowTool` - 工作流脚本（`WORKFLOW_SCRIPTS` feature）
- `PowerShellTool` - PowerShell 执行（平台检测）

### 3.5 权限管线

当一个 tool_use block 到达时，它会经过一个严格的权限管线（在 `services/tools/toolExecution.ts` 中实现）：

```
tool_use block (来自模型)
  |
  v
[1] Schema Validation (L615)
  |  tool.inputSchema.safeParse(input)
  |  -- Zod 验证，拒绝类型错误
  v
[2] Tool validateInput (L683)
  |  tool.validateInput?.(parsedInput, context)
  |  -- 工具自定义的业务逻辑验证
  v
[3] Speculative Classifier Check (L740-752)
  |  startSpeculativeClassifierCheck() -- 仅 BashTool
  |  -- 在权限对话框期间并行运行分类器
  v
[4] Pre-tool Hooks (toolHooks.ts)
  |  执行用户配置的 PreToolUse hooks
  |  -- 可以 approve/block/修改 input
  v
[5] checkPermissions (L599 -> L510)
  |  tool.checkPermissions(input, ctx)
  |  -- 工具级权限检查
  v
[6] canUseTool (useCanUseTool.tsx)
  |  通用权限决策函数
  |  -- 结合 permission mode 和用户交互
  v
[7] tool.call(input, context)  -- 实际执行
  |
  v
[8] Post-tool Hooks
  |  执行 PostToolUse hooks
  v
tool_result message
```

### 3.6 并发控制与 StreamingToolExecutor

`StreamingToolExecutor`（`services/tools/StreamingToolExecutor.ts`）是并行工具执行的核心：

```
模型流式输出:
  assistant message: [text, tool_use_1, text, tool_use_2, tool_use_3, text]
                                      |              |              |
                                      v              v              v
                              StreamingToolExecutor.addTool()
                                      |              |              |
                              +-------+------+-------+------+-------+
                              |              |              |       |
                              v              v              v       |
                        isConcurrencySafe?  isConcurrencySafe?    |
                        YES -> 并行     YES -> 并行               |
                        NO  -> 排队     NO  -> 排队               |
                              |              |              |       |
                              +-------+------+-------+------+-------+
                                      |
                                      v
                              getRemainingResults()
                              -- 等待所有工具完成
                              -- yield tool_result messages
```

- `isConcurrencySafe(input)` 返回 `true` 的工具可以在模型流式输出期间立即开始执行
- 返回 `false` 的工具会被排队，等待之前的不安全工具完成后再执行
- `discard()` 方法用于在模型 fallback 时丢弃已开始但未完成的工具结果

---

## 4. Permission 系统

### 4.1 Permission 模式

Claude Code 支持 6 种权限模式（定义在 `types/permissions.ts:16-22`）：

| 模式 | 说明 |
|------|------|
| `default` | 默认模式，危险操作需要用户确认 |
| `plan` | 计划模式，只读操作自动放行 |
| `acceptEdits` | 自动接受文件编辑 |
| `bypassPermissions` | 跳过所有权限检查（CI/headless） |
| `dontAsk` | 不询问用户，使用缓存的决策 |
| `auto` | 基于分类器自动决策（feature gate: `TRANSCRIPT_CLASSIFIER`） |

内部还有两个额外模式：`auto` 和 `bubble`（用于子 Agent 权限冒泡）。

### 4.2 Permission 行为

每个工具调用的权限决策有三种行为（L44）：

```typescript
type PermissionBehavior = 'allow' | 'deny' | 'ask'
```

### 4.3 权限规则系统

权限规则（`types/permissions.ts:50-88`）允许用户在 `settings.json` 中配置细粒度的权限策略：

```typescript
type PermissionRuleValue = {
  behavior: PermissionBehavior    // 'allow' | 'deny' | 'ask'
  argument?: string               // 工具参数匹配
}

type PermissionRule = {
  tool: string                    // 工具名称（如 "Bash"、"Edit"）
  rule: PermissionRuleValue
  source: PermissionRuleSource    // 规则来源（project / user / etc.）
}
```

### 4.4 Classifier 集成

当 `TRANSCRIPT_CLASSIFIER` feature 启用时，权限系统会集成一个分类器（`jobs/classifier.ts`），对工具调用进行自动分类和决策：

1. BashTool 的命令会通过 `startSpeculativeClassifierCheck()` 提前开始分类（L740-752）
2. 分类器在权限对话框显示期间并行运行
3. 分类结果影响 `canUseTool` 的最终决策

---

## 5. 服务与扩展

### 5.1 Slash 命令系统 (`commands.ts` + `commands/`)

Claude Code 内置约 **101 个命令文件**（`src/commands/` 目录），覆盖了从基本的 `/help` 到复杂的 `/review` 等各种功能：

**常用命令**：
- `commit` / `review` - Git 工作流
- `compact` - 手动触发上下文压缩
- `config` - 配置管理
- `help` - 帮助信息
- `resume` - 恢复会话
- `mcp` - MCP 服务器管理
- `plan` - 计划模式
- `tasks` - 任务管理
- `doctor` - 诊断工具

**高级命令**：
- `bridge` - IDE 远程连接
- `hooks` - Hook 配置
- `skills` - 技能管理
- `voice` - 语音输入
- `vim` - Vim 模式

### 5.2 Multi-Agent 协调 (`coordinator/`)

`coordinator/coordinatorMode.ts` 实现了多 Agent 编排：

- Coordinator 模式允许一个主 Agent 管理多个子 Agent
- 通过 `SendMessageTool` 在 Agent 间传递消息
- `TeamCreateTool` / `TeamDeleteTool` 管理团队生命周期
- 每个子 Agent 有自己的 `agentId`，消息队列通过 `agentId` 进行路由

### 5.3 IDE Bridge (`bridge/`)

`bridge/` 目录实现了 Claude Code 与 IDE 的远程控制协议：

```
IDE (VS Code / JetBrains)
  |
  | WebSocket / stdio
  v
bridge/
  |-- bridgeMain.ts         -- 主入口
  |-- bridgeApi.ts          -- API 定义
  |-- bridgeMessaging.ts    -- 消息协议
  |-- bridgeConfig.ts       -- 配置同步
  |-- bridgePermissionCallbacks.ts -- 权限回调
  |-- bridgeUI.ts           -- UI 状态同步
  |-- bridgePointer.ts      -- 光标/选区同步
  |-- bridgeDebug.ts        -- 调试支持
  |-- initReplBridge.ts     -- REPL 桥接初始化
  |-- createSession.ts      -- 会话创建
  |-- codeSessionApi.ts     -- 代码会话 API
  |-- inboundMessages.ts    -- 入站消息处理
  |-- inboundAttachments.ts -- 入站附件处理
```

### 5.4 Skills 系统 (`skills/`)

Skills 是 Claude Code 的可扩展技能加载机制：

```
skills/
  |-- bundledSkills.ts      -- 内置技能注册
  |-- loadSkillsDir.ts      -- 磁盘技能加载
  |-- mcpSkillBuilders.ts   -- MCP 技能构建器
  |-- bundled/              -- 内置技能实现
```

技能有四种来源：
1. **Bundled** - 编译时打包的内置技能
2. **Disk-based** - 从用户目录加载的技能
3. **MCP** - 通过 Model Context Protocol 提供的技能
4. **Plugin** - 通过插件系统加载的技能

### 5.5 Hooks 系统

Hooks 是 Claude Code 的事件驱动扩展机制。在 `entrypoints/sdk/coreTypes.ts:25-53` 中定义了 **27 种 hook 事件**：

```typescript
export const HOOK_EVENTS = [
  'PreToolUse',          // 工具调用前
  'PostToolUse',         // 工具调用后
  'PostToolUseFailure',  // 工具调用失败后
  'Notification',        // 通知事件
  'UserPromptSubmit',    // 用户提交 prompt
  'SessionStart',        // 会话开始
  'SessionEnd',          // 会话结束
  'Stop',                // Agent 停止
  'StopFailure',         // Agent 停止失败
  'SubagentStart',       // 子 Agent 启动
  'SubagentStop',        // 子 Agent 停止
  'PreCompact',          // 压缩前
  'PostCompact',         // 压缩后
  'PermissionRequest',   // 权限请求
  'PermissionDenied',    // 权限拒绝
  'Setup',               // 设置完成
  'TeammateIdle',        // 队友空闲
  'TaskCreated',         // 任务创建
  'TaskCompleted',       // 任务完成
  'Elicitation',         // 弹出提问
  'ElicitationResult',   // 弹出提问结果
  'ConfigChange',        // 配置变更
  'WorktreeCreate',      // Worktree 创建
  'WorktreeRemove',      // Worktree 删除
  'InstructionsLoaded',  // 指令加载
  'CwdChanged',          // 工作目录变更
  'FileChanged',         // 文件变更
] as const
```

Hooks 的执行流程（在 `utils/hooks.ts` 中实现）：

```
Hook Event 触发
  |
  v
查找匹配的 hook 配置
  |-- settings.json 中的 hooks 配置
  |-- .claude/hooks.json 中的项目级配置
  |-- plugin 注册的 hooks
  |
  v
执行 hook (子进程)
  |-- 传入 JSON payload（tool name, input, etc.）
  |-- 收集 stdout/stderr
  |
  v
解析 hook 响应
  |-- continue: true/false  -- 是否继续
  |-- decision: approve/block -- 工具调用决策
  |-- updatedInput: {...}    -- 修改后的工具输入
  |-- systemMessage: "..."   -- 给用户的警告消息
```

---

## 6. 核心调用链完整追踪

以下是 Claude Code 从用户输入到工具执行的完整调用链：

```
[用户输入]
  |
  v
main.tsx::main()                                 (L585)
  |-- 解析 CLI 参数                               (L610+)
  |-- 初始化 feature gates / statsig
  |-- 根据 mode 路由到不同的 launchRepl() 调用
  |     (L3134 / L3176 / L3242 / L3338 / L3487 / L3733 / L3798)
  |
  v
replLauncher.tsx::launchRepl()                   (L12)
  |-- 创建 React Root
  |-- 渲染 REPL 组件
  |
  v
screens/REPL.tsx
  |-- 用户在 prompt 输入消息
  |-- 创建 query() generator
  |
  v
query.ts::query()                                (L219)
  |-- yield* queryLoop(params, consumedCommandUuids)
  |
  v
query.ts::queryLoop()                            (L241)
  |
  |-- [State 初始化]                              (L268-279)
  |
  |-- while (true) {                              (L307)
  |     |
  |     |-- [解构 State]                          (L311-321)
  |     |
  |     |-- [5层上下文管理]                        (L369-543)
  |     |     Budget -> Snip -> Microcompact -> Collapse -> Autocompact
  |     |
  |     |-- [阻塞限制检查]                        (L628-648)
  |     |
  |     |-- [调用模型 API]                        (L659)
  |     |     for await (const message of deps.callModel({...}))
  |     |       |
  |     |       |-- yield 流式消息给 REPL
  |     |       |-- 收集 tool_use blocks
  |     |       |-- 投递到 StreamingToolExecutor
  |     |
  |     |-- [Post-streaming 决策]                 (L1062-1357)
  |     |     如果没有 tool_use:
  |     |       |-- PTL/media recovery
  |     |       |-- max_output_tokens recovery
  |     |       |-- Stop hooks
  |     |       |-- Token budget check
  |     |       |-- return { reason: 'completed' }
  |     |
  |     |-- [Tool 执行]                           (L1366-1409)
  |     |     const toolUpdates = streamingToolExecutor
  |     |       ? streamingToolExecutor.getRemainingResults()
  |     |       : runTools(toolUseBlocks, ...)
  |     |           |
  |     |           v
  |     |     services/tools/toolExecution.ts
  |     |     runToolUse()                        (L337)
  |     |       |-- 查找 tool
  |     |       |-- checkPermissionsAndCallTool() (L599)
  |     |             |-- Zod schema validation
  |     |             |-- tool.validateInput()
  |     |             |-- Classifier check (BashTool)
  |     |             |-- Pre-tool hooks
  |     |             |-- tool.checkPermissions()
  |     |             |-- canUseTool() (用户交互)
  |     |             |-- tool.call(input, ctx)   <-- 实际执行
  |     |             |-- Post-tool hooks
  |     |
  |     |-- [Attachments 处理]                    (L1580)
  |     |-- [State 更新]                          (L1640-1655)
  |     |-- continue
  |   }
  |
  v
[query() generator 结束]
  |-- 通知已消费的命令 UUID                        (L235-237)
  |-- return terminal
```

---

## 7. 关键设计模式总结

### 7.1 Async Generator 作为核心抽象

`query()` 使用 `async function*` 而非普通的 `async function`，这使得：
- 流式消息可以通过 `yield` 实时传递给 UI
- 外部可以通过 `.return()` 取消正在进行的操作
- Generator 天然支持背压（backpressure）

### 7.2 不可变 State 模式

每次循环迭代通过 `state = { ... }` 创建新对象，而非修改字段。这种模式：
- 避免了 7 个 continue 站点之间的状态干扰
- 使调试更容易（每次迭代的状态是独立的）
- 天然适合 future 的状态快照/回滚

### 7.3 Feature Gate 驱动的条件编译

大量功能通过 `feature('FEATURE_NAME')` 控制，配合 Bun 的 bundle tree-shaking：
- 外部构建会完全消除未启用的代码
- 条件导入使用 `require()` 动态加载，避免循环依赖

### 7.4 防御性恢复策略

Agent Loop 中有大量的 recovery 机制（PTL recovery、max_output_tokens recovery、model fallback），每个 recovery 路径都有：
- 最大重试次数限制
- 防无限循环的 circuit breaker
- 详细的 analytics event 记录

### 7.5 工具安全默认值

`buildTool()` 的默认值策略是 **fail-closed**：
- 不确定是否并发安全 -> 默认 `false`（串行执行）
- 不确定是否有副作用 -> 默认 `false`（假设有写操作）
- 不确定是否需要权限 -> 默认 `allow`（由通用权限系统处理）

---

## 附录：源码文件索引

| 路径 | 说明 |
|------|------|
| `src/main.tsx` | CLI 入口，4683 行 |
| `src/query.ts` | Agent Loop，1729 行 |
| `src/Tool.ts` | Tool 接口与 buildTool 工厂，792 行 |
| `src/tools.ts` | Tool 注册表，389 行 |
| `src/commands.ts` | Slash 命令框架，754 行 |
| `src/replLauncher.tsx` | REPL 启动器 |
| `src/types/permissions.ts` | 权限类型定义 |
| `src/types/hooks.ts` | Hook 类型定义 |
| `src/entrypoints/sdk/coreTypes.ts` | SDK 核心类型，27 种 Hook 事件 |
| `src/services/tools/toolExecution.ts` | 工具执行管线 |
| `src/services/tools/StreamingToolExecutor.ts` | 并行工具执行器 |
| `src/services/compact/autoCompact.ts` | 自动上下文压缩 |
| `src/services/compact/microCompact.ts` | 微压缩 |
| `src/utils/hooks/hookEvents.ts` | Hook 事件系统 |
| `src/coordinator/coordinatorMode.ts` | 多 Agent 协调 |
| `src/bridge/bridgeMain.ts` | IDE 远程控制 |
| `src/skills/bundledSkills.ts` | 内置技能注册 |
