"""
S07: Skill System — 技能系统

从 Markdown 文件加载技能, 按需注入 system prompt。
技能让 agent 拥有可复用的专业能力。

运行: export ANTHROPIC_API_KEY=your-key && python s07_skill_system.py
依赖: pip install anthropic
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict

try:
    from anthropic import Anthropic
except ImportError:
    print("请安装 anthropic: pip install anthropic")
    raise


# ---------------------------------------------------------------------------
# 1. Skill — 技能定义
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    """
    一个技能 = YAML frontmatter (元数据) + body (prompt 模板).
    类比 Claude Code: skills/loadSkillsDir.ts 中的 SKILL.md 格式.
    """
    name: str
    description: str
    prompt_template: str                      # 技能的完整 prompt
    when_to_use: str = ""                     # 什么时候触发 (给模型看的摘要)
    argument_hint: str = ""                   # 参数提示, e.g. "<file-path>"
    allowed_tools: List[str] = field(default_factory=list)  # 限制可用工具

    def render(self, args: str = "") -> str:
        """渲染技能 prompt, 替换参数占位符."""
        result = self.prompt_template
        # 替换 ${args} 占位符
        result = result.replace("${args}", args)
        # 替换 ${CLAUDE_SKILL_DIR}
        result = result.replace("${CLAUDE_SKILL_DIR}", ".")
        return result


# ---------------------------------------------------------------------------
# 2. SkillLoader — 从文件加载技能
# ---------------------------------------------------------------------------

class SkillLoader:
    """
    从目录加载 .md 文件作为技能.
    类比 Claude Code: skills/loadSkillsDir.ts
    """

    @staticmethod
    def parse_frontmatter(content: str) -> dict:
        """解析 YAML-like frontmatter (简化版, 不依赖 pyyaml)."""
        metadata = {}
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not match:
            return metadata

        for line in match.group(1).strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace('-', '_')
                value = value.strip().strip('"').strip("'")
                if value.startswith('[') and value.endswith(']'):
                    value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(',')]
                metadata[key] = value

        return metadata

    @classmethod
    def load_from_markdown(cls, filepath: Path) -> Optional[Skill]:
        """从 Markdown 文件加载一个技能."""
        if not filepath.exists():
            return None

        content = filepath.read_text(encoding='utf-8')
        metadata = cls.parse_frontmatter(content)

        # 提取 body (frontmatter 之后的内容)
        body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL).strip()

        name = metadata.get('name', filepath.stem)
        description = metadata.get('description', '')
        when_to_use = metadata.get('when_to_use', '')

        # 解析 allowed_tools
        allowed_tools = metadata.get('allowed_tools', [])
        if isinstance(allowed_tools, str):
            allowed_tools = [allowed_tools]

        return Skill(
            name=name,
            description=description,
            prompt_template=body,
            when_to_use=when_to_use,
            argument_hint=metadata.get('argument_hint', ''),
            allowed_tools=allowed_tools,
        )

    @classmethod
    def load_from_directory(cls, skills_dir: Path) -> List[Skill]:
        """从目录加载所有技能."""
        skills = []
        if not skills_dir.exists():
            return skills

        for md_file in skills_dir.glob("**/*.md"):
            skill = cls.load_from_markdown(md_file)
            if skill:
                skills.append(skill)

        return skills


# ---------------------------------------------------------------------------
# 3. SkillManager — 技能管理器
# ---------------------------------------------------------------------------

class SkillManager:
    """
    管理所有技能: 注册、发现、按需注入.
    类比 Claude Code: SkillTool 的工作方式.
    """

    def __init__(self):
        self.skills: Dict[str, Skill] = {}

    def register(self, skill: Skill):
        """注册一个技能."""
        self.skills[skill.name] = skill

    def discover(self, query: str) -> List[Skill]:
        """根据查询发现相关技能 (简化: 关键词匹配)."""
        results = []
        query_lower = query.lower()
        for skill in self.skills.values():
            # 匹配名称、描述、when_to_use
            searchable = f"{skill.name} {skill.description} {skill.when_to_use}".lower()
            if any(word in searchable for word in query_lower.split()):
                results.append(skill)
        return results

    def get_skill_list_text(self, budget: int = 500) -> str:
        """生成技能列表文本, 用于注入 system prompt (类比 Claude Code 的字符预算)."""
        lines = ["Available skills:"]
        for skill in self.skills.values():
            entry = f"  - /{skill.name}: {skill.description}"
            if skill.when_to_use:
                entry += f" ({skill.when_to_use})"
            lines.append(entry)
        text = '\n'.join(lines)
        if len(text) > budget:
            text = text[:budget] + "..."
        return text

    def inject_skill_prompt(self, skill_name: str, args: str = "") -> Optional[str]:
        """注入技能的完整 prompt (类比 Claude Code: SkillTool 调用时注入)."""
        skill = self.skills.get(skill_name)
        if not skill:
            return None
        return skill.render(args)


# ---------------------------------------------------------------------------
# 4. Built-in Skills — 内置技能
# ---------------------------------------------------------------------------

def create_builtin_skills() -> List[Skill]:
    """创建内置技能示例."""
    return [
        Skill(
            name="code-review",
            description="Review code for quality, bugs, and improvements",
            when_to_use="when user asks to review code or check quality",
            argument_hint="<file-path>",
            prompt_template="""You are a senior code reviewer. Review the following code thoroughly.

Focus on:
1. **Correctness**: Logic errors, edge cases, off-by-one errors
2. **Security**: Injection vulnerabilities, XSS, SQL injection
3. **Performance**: Unnecessary allocations, N+1 queries
4. **Readability**: Naming, structure, comments
5. **Maintainability**: Coupling, cohesion, testability

File to review: ${args}

Provide specific, actionable feedback with line references.""",
        ),
        Skill(
            name="commit",
            description="Create a well-formatted git commit",
            when_to_use="when user wants to commit changes",
            prompt_template="""You are creating a git commit. Follow these steps:

1. Run `git status` and `git diff --staged` to see what changed
2. Write a clear, conventional commit message:
   - type(scope): description
   - Types: feat, fix, refactor, docs, test, chore
3. Keep the subject line under 72 characters
4. Add a body if the change needs explanation

${args}""",
        ),
        Skill(
            name="debug",
            description="Systematically debug an issue",
            when_to_use="when user reports a bug or error",
            argument_hint="<error-description>",
            prompt_template="""You are a debugging assistant. Follow this systematic approach:

1. **Reproduce**: Understand and reproduce the error
2. **Read the error**: Parse stack traces, error messages
3. **Hypothesize**: Form 2-3 possible root causes
4. **Test**: Read relevant code to confirm/eliminate hypotheses
5. **Fix**: Propose minimal, targeted fix

Issue to debug: ${args}

Start by reading the error message carefully.""",
        ),
    ]


# ---------------------------------------------------------------------------
# 5. Agent with Skills — 带技能的 Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful coding assistant.

You can use skills by responding with: USE_SKILL: <skill-name> <args>

{skill_list}

When you see a task that matches a skill, use it.
"""

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
]


def run_agent_with_skills(
    client: Anthropic,
    user_input: str,
    skill_manager: SkillManager,
):
    """带技能发现的 Agent 循环."""
    # 注入技能列表到 system prompt
    skill_list_text = skill_manager.get_skill_list_text()
    system_prompt = SYSTEM_PROMPT.format(skill_list=skill_list_text)

    messages = [{"role": "user", "content": user_input}]

    print("=" * 60)
    print("S07: Skill System Demo")
    print("=" * 60)
    print(f"\nLoaded skills: {list(skill_manager.skills.keys())}")
    print(f"\nSkill list injected into prompt:\n{skill_list_text}\n")

    turn = 0
    while turn < 5:
        turn += 1
        print(f"\n--- Turn {turn} ---")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        )

        # 检查是否有 USE_SKILL 指令
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        messages.append({"role": "assistant", "content": text})

        # 解析 USE_SKILL 指令
        if "USE_SKILL:" in text:
            for line in text.split("\n"):
                if "USE_SKILL:" in line:
                    parts = line.split("USE_SKILL:")[1].strip().split(maxsplit=1)
                    skill_name = parts[0]
                    args = parts[1] if len(parts) > 1 else ""

                    print(f"  [Skill invoked] {skill_name}({args})")
                    skill_prompt = skill_manager.inject_skill_prompt(skill_name, args)

                    if skill_prompt:
                        print(f"  [Injecting prompt] ({len(skill_prompt)} chars)")
                        # 把技能 prompt 作为上下文注入
                        messages.append({
                            "role": "user",
                            "content": f"[Skill: {skill_name}]\n{skill_prompt}"
                        })
                    else:
                        print(f"  [Skill not found] {skill_name}")
                    break
        else:
            print(f"\nAgent: {text[:200]}...")
            break

    return messages


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # 创建技能管理器
    manager = SkillManager()

    # 注册内置技能
    for skill in create_builtin_skills():
        manager.register(skill)
        print(f"  Registered skill: {skill.name}")

    # 演示技能发现
    print("\n--- Skill Discovery ---")
    results = manager.discover("I have a bug in my code")
    for r in results:
        print(f"  Found: {r.name} - {r.description}")

    results = manager.discover("review my code")
    for r in results:
        print(f"  Found: {r.name} - {r.description}")

    # 运行带技能的 agent
    print("\n--- Agent with Skills ---")
    run_agent_with_skills(
        client,
        "I need to review the code in main.py",
        manager,
    )


if __name__ == "__main__":
    demo()
