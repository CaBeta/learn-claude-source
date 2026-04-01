"""
Session 04: SubAgent — 派出子代理

在 s03 的流式工具 agent 基础上新增子代理能力:
- spawn_subagent(task, context): 派生子代理执行子任务
- 子代理拥有独立的上下文和消息历史
- 递归深度限制,防止无限嵌套
- 子代理结果汇回主 agent 继续决策

核心思想: 大任务拆小,每个子任务获得干净的上下文。

运行: python s04_subagent.py
依赖: pip install anthropic
"""

import os
import json
from anthropic import Anthropic

# ---------------------------------------------------------------------------
# 初始化客户端
# ---------------------------------------------------------------------------
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
MAX_DEPTH = 3  # 子代理最大递归深度

# ===========================================================================
# ANSI 颜色
# ===========================================================================
CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
DIM = "\033[2m"
BOLD = "\033[1m"
MAGENTA = "\033[95m"
RESET = "\033[0m"


# ===========================================================================
# 基础工具定义与实现
# ===========================================================================

FILE_TOOLS = [
    {
        "name": "read_file",
        "description": "读取文件内容。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "写入文件。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "内容"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "列出目录内容。",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "目录路径"},
            },
            "required": [],
        },
    },
]


def handle_read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"错误: {e}"


def handle_write_file(path: str, content: str) -> str:
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"成功写入 {len(content)} 字符到 '{path}'"
    except Exception as e:
        return f"错误: {e}"


def handle_list_files(directory: str = ".") -> str:
    try:
        entries = os.listdir(directory)
        lines = []
        for entry in sorted(entries):
            full = os.path.join(directory, entry)
            if os.path.isdir(full):
                lines.append(f"  [DIR]  {entry}/")
            else:
                size = os.path.getsize(full)
                lines.append(f"  [FILE] {entry}  ({size} bytes)")
        return f"目录 '{directory}':\n" + "\n".join(lines)
    except Exception as e:
        return f"错误: {e}"


BASE_DISPATCH = {
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "list_files": handle_list_files,
}


# ===========================================================================
# 子代理系统
# ===========================================================================


def spawn_subagent(task: str, context: str = "", depth: int = 0) -> str:
    """
    派生子代理执行子任务。

    Args:
        task: 子任务描述
        context: 相关上下文信息
        depth: 当前递归深度

    Returns:
        子代理的执行结果
    """
    if depth >= MAX_DEPTH:
        return f"错误: 已达到最大递归深度 ({MAX_DEPTH}),无法继续派生子代理"

    indent = "  " * (depth + 1)
    print(f"\n{MAGENTA}{indent}╔{'═' * 50}╗")
    print(f"{MAGENTA}{indent}║ SubAgent (depth={depth}) 启动")
    print(f"{MAGENTA}{indent}║ 任务: {task[:60]}{'...' if len(task) > 60 else ''}")
    print(f"{MAGENTA}{indent}╚{'═' * 50}╝{RESET}")

    # ---- 构建子代理的独立消息历史 ----
    user_content = f"请完成以下任务:\n\n{task}"
    if context:
        user_content += f"\n\n--- 相关上下文 ---\n{context}"

    messages = [{"role": "user", "content": user_content}]

    # ---- 子代理的工具集 ----
    # 子代理可以使用文件工具,也可以继续派生子代理
    sub_tools = list(FILE_TOOLS)  # 复制基础工具

    # 如果还没到最大深度,子代理也可以派生自己的子代理
    if depth + 1 < MAX_DEPTH:
        sub_tools.append({
            "name": "spawn_subagent",
            "description": "派生一个子代理来执行子任务。子代理拥有独立的上下文。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "子任务描述",
                    },
                    "context": {
                        "type": "string",
                        "description": "相关上下文信息 (可选)",
                    },
                },
                "required": ["task"],
            },
        })

    # ---- 子代理的 dispatch map ----
    sub_dispatch = dict(BASE_DISPATCH)

    def _spawn_child(task: str, context: str = "") -> str:
        return spawn_subagent(task, context, depth=depth + 1)

    if depth + 1 < MAX_DEPTH:
        sub_dispatch["spawn_subagent"] = _spawn_child

    # ---- 子代理 Loop ----
    turn = 0
    max_turns = 10  # 子代理最大循环次数,防止失控

    while turn < max_turns:
        turn += 1
        print(f"{DIM}{indent}  [子代理 Turn {turn}]{RESET}")

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=sub_tools,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            # 子代理完成任务
            result = "".join(
                b.text for b in response.content if b.type == "text"
            )
            print(f"{GREEN}{indent}  SubAgent 完成{RESET}")
            return result

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    handler = sub_dispatch.get(block.name)
                    if handler:
                        result = handler(**block.input)
                    else:
                        result = f"错误: 未知工具 '{block.name}'"

                    if len(result) > 10000:
                        result = result[:10000] + "... (截断)"

                    print(
                        f"{DIM}{indent}    {block.name}: "
                        f"{result[:80]}{'...' if len(result) > 80 else ''}{RESET}"
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
            continue

        # 其他情况
        result = "".join(
            b.text for b in response.content if b.type == "text"
        )
        return result or "(子代理异常终止)"

    return f"子代理达到最大循环次数 ({max_turns}),强制终止"


# ===========================================================================
# 主 Agent Loop (带子代理)
# ===========================================================================

# spawn_subagent 工具定义 (供主 agent 使用)
SPAWN_TOOL = {
    "name": "spawn_subagent",
    "description": (
        "派生一个子代理来执行子任务。子代理拥有独立、干净的上下文,不会看到主对话的完整历史。"
        "适用于需要聚焦处理的子任务,如: 分析单个文件、执行特定重构、搜索代码等。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "子任务描述。要具体、明确。",
            },
            "context": {
                "type": "string",
                "description": "传递给子代理的上下文信息。例如文件内容、API 文档等。",
            },
        },
        "required": ["task"],
    },
}

# 主 agent 的完整工具集
MAIN_TOOLS = list(FILE_TOOLS) + [SPAWN_TOOL]

# 主 agent 的 dispatch map
MAIN_DISPATCH = dict(BASE_DISPATCH)
MAIN_DISPATCH["spawn_subagent"] = lambda task, context="": spawn_subagent(
    task, context, depth=0
)


def run_agent(user_input: str) -> str:
    """
    带子代理的 Agent Loop。
    """
    messages = [{"role": "user", "content": user_input}]
    turn = 0

    while True:
        turn += 1
        if turn > 1:
            print(f"\n{DIM}--- Turn {turn} ---{RESET}")

        # 流式调用
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=MAIN_TOOLS,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
            final_message = stream.get_final_message()

        print()

        if final_message.stop_reason == "end_turn":
            full_text = "".join(
                b.text for b in final_message.content if b.type == "text"
            )
            return full_text

        if final_message.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": final_message.content})

            tool_results = []
            for block in final_message.content:
                if block.type == "tool_use":
                    if block.name == "spawn_subagent":
                        task = block.input.get("task", "")
                        context = block.input.get("context", "")
                        print(f"\n{MAGENTA}{BOLD}[派生子代理]{RESET} {task[:80]}")
                        result = spawn_subagent(task, context, depth=0)
                        print(f"{MAGENTA}{BOLD}[子代理返回]{RESET} {result[:100]}{'...' if len(result) > 100 else ''}{RESET}")
                    else:
                        handler = MAIN_DISPATCH.get(block.name)
                        if handler:
                            result = handler(**block.input)
                        else:
                            result = f"错误: 未知工具 '{block.name}'"

                    if len(result) > 10000:
                        result = result[:10000] + "... (截断)"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
            continue

        full_text = "".join(
            b.text for b in final_message.content if b.type == "text"
        )
        return full_text or "(异常终止)"


# ===========================================================================
# 主入口
# ===========================================================================

def main():
    print(f"{BOLD}Session 04: SubAgent{RESET}")
    print("支持子代理的 Agent。输入复杂任务试试!")
    print("输入 'quit' 退出\n")

    while True:
        try:
            user_input = input(f"{BOLD}You:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("再见!")
            break

        try:
            result = run_agent(user_input)
            print(f"\n{BOLD}最终结果:{RESET}\n{result}\n")
        except Exception as e:
            print(f"\n{BOLD}出错:{RESET} {e}\n")


if __name__ == "__main__":
    main()
