# Task Plan: 从零构建 Coding Agent — Claude Code 源码解析与实战

## Goal
借鉴 shareAI-lab/learn-claude-code 项目的展示方式，解析本地 Claude Code 源码，从零开始教学如何构建一个 Coding Agent，包含渐进式课程、可运行代码和详细文档。

## Current Phase
Phase 1

## Phases

### Phase 1: 项目规划与结构设计
- [x] 研究参考项目 (shareAI-lab/learn-claude-code) 的展示方式
- [x] 分析本地 Claude Code 源码核心架构
- [x] 设计课程结构与章节划分
- [x] 创建项目目录结构
- **Status:** complete

### Phase 2: 编写渐进式课程文档 (12个Session)
- [ ] s01 - Agent Loop（代理循环）
- [ ] s02 - Tool Use（工具使用）
- [ ] s03 - Streaming（流式输出）
- [ ] s04 - SubAgent（子代理）
- [ ] s05 - Context Management（上下文管理）
- [ ] s06 - Permission System（权限系统）
- [ ] s07 - Skill System（技能系统）
- [ ] s08 - Hook System（钩子系统）
- [ ] s09 - Multi-Agent Coordinator（多代理协调）
- [ ] s10 - Background Tasks（后台任务）
- [ ] s11 - Session & Memory（会话与记忆）
- [ ] s12 - Production Agent（生产级代理）
- **Status:** in_progress

### Phase 3: 编写可运行的 Python 示例代码
- [ ] s01_agent_loop.py
- [ ] s02_tool_use.py
- [ ] s03_streaming.py
- [ ] s04_subagent.py
- [ ] s05_context_management.py
- [ ] s06_permission_system.py
- [ ] s07_skill_system.py
- [ ] s08_hook_system.py
- [ ] s09_multi_agent.py
- [ ] s10_background_tasks.py
- [ ] s11_session_memory.py
- [ ] s12_production_agent.py
- **Status:** pending

### Phase 4: 编写 README 和总览文档
- [ ] 主 README.md（项目介绍、哲学、学习路径）
- [ ] 源码架构总览 (architecture.md)
- **Status:** pending

### Phase 5: 最终审查
- [ ] 检查所有文档的一致性
- [ ] 确保代码示例可运行
- [ ] 交付
- **Status:** pending

## Key Questions
1. 如何将 Claude Code 的复杂架构拆解为渐进式学习路径？
2. 每个 session 应该聚焦哪个核心机制？
3. Python 实现中如何保持简洁又体现关键模式？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 使用 Python 而非 TypeScript | 参考项目用 Python，更易理解，依赖更少 |
| 12个渐进式 Session | 参考项目的渐进模式很有效，每个加一个机制 |
| 中英双语文档 | 项目面向中文开发者，但保留英文术语 |
| 聚焦 Claude Code 真实源码 | 不只是教学，而是解析实际架构 |
| 使用 Anthropic Python SDK | 与 Claude Code 实际使用的 API 一致 |

## Notes
- 参考项目风格：motto + problem + solution(ASCII图) + how it works + what changed + try it
- 每个session的Python代码必须独立可运行
- 文档要包含对Claude Code源码的具体引用（文件名:行号）
