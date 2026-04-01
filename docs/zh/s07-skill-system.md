# S07: Skill System — 技能系统

> s01 > s02 > s03 > s04 > s05 > s06 > **[ s07 ]** > s08 > s09 > s10 > s11 > s12

*一次学会，终身受用 — 技能让代理拥有专业能力*

---

## Problem

你的代理已经能做很多事了，但有些复杂工作流需要反复执行：比如代码审查、生成 commit message、诊断错误、编写测试。每次都要给模型详细指令，既浪费 token，又不够可靠。

你希望有一种机制，把"专家知识"打包成可复用的技能。模型需要时自动加载，不需要时不占用 context window。

---

## Solution

```
用户输入: "/commit 修改了登录逻辑"
  |
  v
+----------------------------------------------------------+
|                  Skill Loading Pipeline                   |
|                                                          |
|  [1] Skill Discovery                                     |
|      扫描 skills/ 目录和内置注册表                        |
|      |                                                   |
|  [2] Skill Matching                                      |
|      按名称/别名匹配用户请求                              |
|      |                                                   |
|  [3] Lazy Loading                                        |
|      只加载 frontmatter (name, description)               |
|      完整 prompt 按需加载                                 |
|      |                                                   |
|  [4] Prompt Injection                                    |
|      将技能 prompt 注入 system prompt                     |
|      |                                                   |
|  [5] Model Execution                                     |
|      模型按照技能指令执行                                 |
|                                                          |
+----------------------------------------------------------+
  |
  v
模型输出 (按技能指引的结构化响应)
```

---

## How It Works

### 1. Skill Definition — 技能定义

每个技能是一个 Markdown 文件，包含 YAML frontmatter 和 prompt body：

```markdown
---
name: code-review
description: Review code changes and provide feedback
aliases: [review, cr]
when-to-use: "When the user asks to review code or check code quality"
allowed-tools: [read_file, glob, grep]
---

You are a senior code reviewer. Analyze the provided code changes and:

1. **Correctness**: Check for logic errors, edge cases
2. **Security**: Look for injection, XSS, auth issues
3. **Performance**: Identify unnecessary loops, N+1 queries
4. **Style**: Check naming, comments, structure

Output format:
- Use a bullet list for each finding
- Rate severity: [CRITICAL] / [WARNING] / [INFO]
- Suggest fixes for each issue
```

### 2. Skill Class — Python 技能模型

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Skill:
    """一个技能定义."""
    name: str                          # 技能名 (如 "code-review")
    description: str                   # 一句话描述
    prompt: str                        # 完整 prompt 模板
    aliases: list[str] = None          # 别名列表
    when_to_use: str = ""              # 何时使用
    allowed_tools: list[str] = None    # 允许使用的工具
    source: str = "disk"               # disk / bundled / mcp

    def matches(self, query: str) -> bool:
        """检查技能是否匹配查询."""
        query_lower = query.lower()
        if query_lower == self.name.lower():
            return True
        if self.aliases:
            return any(a.lower() == query_lower for a in self.aliases)
        return False
```

### 3. SkillLoader — 从磁盘加载技能

```python
class SkillLoader:
    """从磁盘目录加载技能."""
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self._cache: dict[str, Skill] = {}

    def discover_skills(self) -> list[Skill]:
        """扫描目录，发现所有技能 (只读 frontmatter)."""
        skills = []
        if not self.skills_dir.exists():
            return skills
        for skill_dir in self.skills_dir.iterdir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skill = self._parse_skill(skill_file)
                if skill:
                    skills.append(skill)
        return skills

    def load_skill(self, name: str) -> Skill | None:
        """按需加载完整技能."""
        if name in self._cache:
            return self._cache[name]
        skill_file = self.skills_dir / name / "SKILL.md"
        if skill_file.exists():
            skill = self._parse_skill(skill_file)
            if skill:
                self._cache[name] = skill
            return skill
        return None

    def _parse_skill(self, path: Path) -> Skill | None:
        """解析 SKILL.md 文件."""
        content = path.read_text()
        frontmatter, body = self._split_frontmatter(content)
        meta = self._parse_yaml(frontmatter)
        return Skill(
            name=meta.get("name", path.parent.name),
            description=meta.get("description", ""),
            prompt=body.strip(),
            aliases=meta.get("aliases", []),
            when_to_use=meta.get("when-to-use", ""),
            allowed_tools=meta.get("allowed-tools", []),
            source="disk",
        )
```

### 4. SkillManager — 技能管理器

```python
class SkillManager:
    """管理所有技能的加载、匹配和注入."""
    def __init__(self):
        self.loader = SkillLoader()
        self.bundled: list[Skill] = []
        self._load_bundled_skills()

    def _load_bundled_skills(self):
        """注册内置技能."""
        self.bundled.append(Skill(
            name="commit",
            description="Generate a git commit message",
            prompt="Analyze the staged changes and generate a conventional commit message...",
            aliases=["git-commit"],
            source="bundled",
        ))
        self.bundled.append(Skill(
            name="code-review",
            description="Review code for quality issues",
            prompt="You are a senior code reviewer...",
            aliases=["review", "cr"],
            source="bundled",
        ))

    def find_skill(self, query: str) -> Skill | None:
        """查找匹配的技能."""
        for skill in self.bundled:
            if skill.matches(query):
                return skill
        disk_skill = self.loader.load_skill(query)
        if disk_skill:
            return disk_skill
        return None

    def get_skill_descriptions(self) -> str:
        """获取所有技能的摘要 (用于 system prompt)."""
        lines = ["Available skills (use /skill-name to invoke):"]
        for skill in self.bundled + self.loader.discover_skills():
            lines.append(f"  /{skill.name}: {skill.description}")
        return "\n".join(lines)

    def inject_skill_prompt(self, system_prompt: str, skill: Skill) -> str:
        """将技能 prompt 注入到 system prompt."""
        return f"{system_prompt}\n\n---\n[Active Skill: {skill.name}]\n{skill.prompt}"
```

### 5. 在 Agent Loop 中集成技能

```python
SYSTEM_PROMPT_WITH_SKILLS = f"""You are a helpful coding agent.
{skill_manager.get_skill_descriptions()}

When the user types /skill-name, invoke that skill's instructions.
"""

async def agent_loop(client, user_message, skill_manager):
    # 检查是否是技能调用
    skill = None
    if user_message.startswith("/"):
        skill_name = user_message[1:].split()[0]
        skill = skill_manager.find_skill(skill_name)
        if skill:
            user_message = user_message[len(skill_name) + 2:].strip() or "Run this skill."

    # 构建 system prompt
    system = SYSTEM_PROMPT
    if skill:
        system = skill_manager.inject_skill_prompt(system, skill)

    # ... 正常 agent loop ...
```

---

## Claude Code 源码对照

| 机制 | 源文件 | 关键行 |
|------|--------|--------|
| 内置技能注册 | `skills/bundledSkills.ts` | L15: `BundledSkillDefinition` 类型 |
| 注册函数 | `skills/bundledSkills.ts` | L53: `registerBundledSkill()` |
| 获取所有内置技能 | `skills/bundledSkills.ts` | L106: `getBundledSkills()` |
| 技能文件提取 | `skills/bundledSkills.ts` | L131: `extractBundledSkillFiles()` |
| 磁盘技能加载 | `skills/loadSkillsDir.ts` | L407: `loadSkillsFromSkillsDir()` |
| SKILL.md 解析 | `skills/loadSkillsDir.ts` | L447: `parseFrontmatter()` |
| 技能 Command 创建 | `skills/loadSkillsDir.ts` | L270: `createSkillCommand()` |
| Frontmatter 字段解析 | `skills/loadSkillsDir.ts` | L185: `parseSkillFrontmatterFields()` |
| Token 估算 | `skills/loadSkillsDir.ts` | L100: `estimateSkillFrontmatterTokens()` |
| 动态技能发现 | `skills/loadSkillsDir.ts` | L861: `discoverSkillDirsForPaths()` |
| 条件技能激活 | `skills/loadSkillsDir.ts` | L997: `activateConditionalSkillsForPaths()` |
| 技能目录去重 | `skills/loadSkillsDir.ts` | L728-763: 按 realpath 去重 |
| Legacy commands 加载 | `skills/loadSkillsDir.ts` | L566: `loadSkillsFromCommandsDir()` |
| MCP 技能构建器 | `skills/mcpSkillBuilders.ts` | MCP 协议技能注册 |
| 内置技能实现 | `skills/bundled/` | 16 个内置技能目录 |
| SkillTool (按需注入) | `tools/SkillTool/` | 工具调用时的技能加载 |

---

## What Changed From s06

| 特性 | s06 Permission System | s07 Skill System |
|------|---------------------|-----------------|
| 核心关注 | 操作安全控制 | 专家知识复用 |
| 新增组件 | PermissionChecker | SkillLoader + SkillManager |
| 存储格式 | 内存中的规则列表 | Markdown 文件 (SKILL.md) |
| 加载策略 | 启动时全量加载 | Lazy loading (frontmatter 先, body 按需) |
| 扩展方式 | 添加规则 | 创建 skill-name/SKILL.md |
| 用户交互 | y/n 确认 | /skill-name 命令 |
| Token 开销 | 规则描述 (~100 tokens) | 仅 frontmatter (~50 tokens/skill) |

---

## Try It

1. **创建自定义技能**：在 `skills/` 目录下创建一个新的技能目录，比如 `skills/test-writer/SKILL.md`。让它包含完整的测试编写指南：测试命名规范、断言策略、边界条件覆盖要求。然后在 agent 中用 `/test-writer` 调用它。

2. **实现技能别名匹配**：当前 `matches()` 只做精确匹配。实现一个模糊匹配：如果用户输入 `/rev`，应该匹配到 `code-review`（因为 "rev" 是 "review" 的前缀）。提示：可以用 `difflib.get_close_matches()`。

3. **实现 Token 预算**：参考 Claude Code 的 `estimateSkillFrontmatterTokens()`，在将技能列表注入 system prompt 前，估算占用的 token 数。如果超过预算，只保留最相关的 N 个技能描述。

4. **实现动态技能发现**：当模型调用 `read_file` 读取某个目录下的文件时，自动扫描该目录的 `.claude/skills/` 子目录，加载新发现的技能。参考 `discoverSkillDirsForPaths()` 的实现。
