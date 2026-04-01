"""
Session 03: Streaming — 实时流式输出

在 s02 的工具 agent 基础上改为流式输出:
- 使用 client.messages.stream() 获取实时事件
- 文本逐字打印
- 工具调用实时显示进度
- 简易控制台渲染器

运行: python s03_streaming.py
依赖: pip install anthropic
"""

import os
import sys
import json
from anthropic import Anthropic

# ---------------------------------------------------------------------------
# 初始化客户端
# ---------------------------------------------------------------------------
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

# ===========================================================================
# 工具定义 (与 s02 相同)
# ===========================================================================

TOOLS = [
    {
        "name": "read_file",
        "description": "读取指定路径的文件内容。",
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
        "description": "将内容写入文件。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "文件内容"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "列出目录下的文件和子目录。",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "目录路径"},
            },
            "required": [],
        },
    },
]


# ===========================================================================
# 工具实现 (与 s02 相同)
# ===========================================================================

def handle_read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"错误: 文件不存在 '{path}'"
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
        return f"目录 '{directory}' 内容:\n" + "\n".join(lines)
    except Exception as e:
        return f"错误: {e}"


DISPATCH_MAP = {
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "list_files": handle_list_files,
}


# ===========================================================================
# 简易控制台渲染器
# ===========================================================================

# ANSI 颜色码
CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def render_tool_start(name: str):
    """渲染工具调用开始提示"""
    print(f"\n{CYAN}{BOLD}[工具]{RESET} {YELLOW}{name}{RESET}", end=" ")


def render_tool_result(summary: str):
    """渲染工具结果摘要"""
    # 只显示第一行或前 80 字符
    first_line = summary.split("\n")[0]
    if len(first_line) > 80:
        first_line = first_line[:77] + "..."
    print(f"{GREEN}✓{RESET} {DIM}{first_line}{RESET}")


# ===========================================================================
# Agent Loop (流式)
# ===========================================================================


def run_agent(user_input: str) -> str:
    """
    流式 Agent Loop。

    相比 s02 的变化:
    - 使用 messages.stream() 替代 messages.create()
    - 实时处理流式事件
    - 逐字打印文本
    - 工具调用实时显示
    """
    messages = [{"role": "user", "content": user_input}]
    turn = 0

    while True:
        turn += 1
        if turn > 1:
            print(f"\n{DIM}--- Turn {turn} ---{RESET}")

        # ---- 流式调用 API ----
        tool_uses = []          # 收集本轮所有 tool_use blocks
        current_tool_input = "" # 当前正在接收的 tool JSON

        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=TOOLS,
            messages=messages,
        ) as stream:

            # 实时打印文本
            for text in stream.text_stream:
                print(text, end="", flush=True)

            # 获取完整响应 (流结束后)
            final_message = stream.get_final_message()

        print()  # 文本输出后换行

        # ---- 检查 stop_reason ----
        if final_message.stop_reason == "end_turn":
            # 提取完整文本
            full_text = "".join(
                block.text for block in final_message.content
                if block.type == "text"
            )
            return full_text

        if final_message.stop_reason == "tool_use":
            # 把 assistant 回复加入历史
            messages.append({"role": "assistant", "content": final_message.content})

            # 执行所有工具调用
            tool_results = []
            for block in final_message.content:
                if block.type == "tool_use":
                    render_tool_start(block.name)

                    handler = DISPATCH_MAP.get(block.name)
                    if handler:
                        result = handler(**block.input)
                    else:
                        result = f"错误: 未知工具 '{block.name}'"

                    # 截断过长结果
                    if len(result) > 10000:
                        result = result[:10000] + f"\n... (截断,共 {len(result)} 字符)"

                    render_tool_result(result)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # 工具结果加入历史,继续循环
            messages.append({"role": "user", "content": tool_results})
            continue

        # 其他情况
        full_text = "".join(
            block.text for block in final_message.content
            if block.type == "text"
        )
        return full_text or "(异常终止)"


# ===========================================================================
# 主入口
# ===========================================================================

def main():
    print(f"{BOLD}Session 03: Streaming Agent{RESET}")
    print("输入任务开始,输入 'quit' 退出\n")

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
        except Exception as e:
            print(f"\n{BOLD}Agent 出错:{RESET} {e}")
            continue


if __name__ == "__main__":
    main()
