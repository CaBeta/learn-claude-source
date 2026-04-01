# Findings & Decisions

## Requirements
- 解析本地 Claude Code 源码 (claude-code-main/)
- 借鉴 learn-claude-code 项目的展示方式
- 从零开始教学构建 Coding Agent
- 渐进式课程（12个Session）
- 可运行的 Python 代码示例
- 中英双语文档

## Research Findings

### 参考项目 (shareAI-lab/learn-claude-code) 的展示风格
- **Motto**: 每个session一句格言
- **Problem**: 用通俗语言描述问题
- **Solution**: ASCII 架构图
- **How It Works**: 编号步骤 + 内联代码片段
- **What Changed**: 前后对比表
- **Try It**: 3-4个练习
- 面包屑导航: `s01 > s02 > [ s03 ] > s04 > ...`
- Phase 分组: THE LOOP | PLANNING & KNOWLEDGE | PERSISTENCE | TEAMS

### Claude Code 核心架构发现
- main.tsx: CLI 路由和启动编排器（非代理循环）
- query.ts: 真正的代理循环（while(true) 状态机）
- Tool.ts: 工具类型定义（buildTool 工厂模式）
- tools.ts: 工具注册表
- coordinator/: 多代理协调器
- bridge/: IDE 桥接系统
- skills/: 技能加载系统
- permissions/: 权限系统（6种模式）

### Agent Loop 核心机制 (query.ts)
- async function* generator 模式
- 状态每轮迭代都是全新对象（不可变状态模式）
- 7个 continue 站点，10个 return 站点
- 5层上下文管理: Budget -> Snip -> Microcompact -> Collapse -> Autocompact
- 流式工具执行 + 批量工具执行双模式
- FallbackTriggeredError 模型降级恢复
- Prompt-Too-Long (413) 三级恢复

### Tool 系统架构
- buildTool() 工厂 + safe defaults
- 权限管线: validateInput -> checkPermissions -> canUseTool -> call
- 并发控制: isConcurrencySafe 分离读写工具
- StreamingToolExecutor 管理并发执行
- ~43个内置工具

### Permission 系统
- 6种模式: default, plan, acceptEdits, bypassPermissions, dontAsk, auto
- 5阶段权限流: Rule Check -> Decision Dispatch -> Coordinator Check -> Swarm Check -> Interactive
- 分类器集成: BASH_CLASSIFIER, TRANSCRIPT_CLASSIFIER
- 11种决策原因类型

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 12个Session渐进式 | 平衡深度和可学习性 |
| s01-s03聚焦核心循环 | 先建立基础：循环、工具、流式 |
| s04-s06聚焦智能增强 | 子代理、上下文、权限让agent变聪明 |
| s07-s09聚焦扩展 | 技能、钩子、多代理让agent可扩展 |
| s10-s12聚焦生产化 | 后台任务、记忆持久化、完整代理 |

## Resources
- 参考项目: https://github.com/shareAI-lab/learn-claude-code
- Claude Code 源码: ./claude-code-main/
- 核心文件: main.tsx, query.ts, Tool.ts, tools.ts, commands.ts
