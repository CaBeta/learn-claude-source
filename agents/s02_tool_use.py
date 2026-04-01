"""
Session 02: Tool Use — 给代理装上双手

在 s01 的 agent loop 基础上加入工具系统:
- read_file(path): 读取文件内容
- write_file(path, content): 写入文件
- list_files(directory): 列出目录内容

核心模式: Dispatch Map — 工具名 → 处理函数 的映射字典。

运行: python s02_tool_use.py
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

# ===========================================================================
# 工具定义 (JSON Schema)
# ===========================================================================

TOOLS = [
    {
        "name": "read_file",
        "description": "读取指定路径的文件内容。返回文件的完整文本。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要读取的文件路径",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "将内容写入指定路径的文件。如果文件已存在则覆盖。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要写入的文件路径",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的文件内容",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "列出指定目录下的文件和子目录。",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "要列出的目录路径,默认为当前目录",
                }
            },
            "required": [],  # directory 可选
        },
    },
]

# ===========================================================================
# 工具实现 (Handler Functions)
# ===========================================================================


def handle_read_file(path: str) -> str:
    """读取文件内容"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return f"错误: 文件不存在 '{path}'"
    except Exception as e:
        return f"错误: {type(e).__name__}: {e}"


def handle_write_file(path: str, content: str) -> str:
    """写入文件"""
    try:
        # 确保父目录存在
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"成功写入 {len(content)} 字符到 '{path}'"
    except Exception as e:
        return f"错误: {type(e).__name__}: {e}"


def handle_list_files(directory: str = ".") -> str:
    """列出目录内容"""
    try:
        entries = os.listdir(directory)
        result_lines = []
        for entry in sorted(entries):
            full_path = os.path.join(directory, entry)
            if os.path.isdir(full_path):
                result_lines.append(f"  [DIR]  {entry}/")
            else:
                size = os.path.getsize(full_path)
                result_lines.append(f"  [FILE] {entry}  ({size} bytes)")
        return f"目录 '{directory}' 内容:\n" + "\n".join(result_lines)
    except FileNotFoundError:
        return f"错误: 目录不存在 '{directory}'"
    except Exception as e:
        return f"错误: {type(e).__name__}: {e}"


# ===========================================================================
# Dispatch Map — 工具名 → 处理函数
# ===========================================================================

DISPATCH_MAP = {
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "list_files": handle_list_files,
}


# ===========================================================================
# Agent Loop (带工具)
# ===========================================================================


def run_agent(user_input: str) -> str:
    """
    带工具的 Agent Loop。

    相比 s01 的变化:
    - API 调用时传入 tools 参数
    - 处理 tool_use stop_reason: 查 dispatch map 执行工具
    - 把 tool_result 加入消息历史,继续循环
    """
    messages = [{"role": "user", "content": user_input}]
    turn = 0

    print("=" * 60)
    print("Agent Loop 启动 (带工具)")
    print("=" * 60)

    while True:
        turn += 1
        print(f"\n--- Turn {turn} ---")

        # 调用模型 (带上工具定义)
        print(f"[调用模型] messages: {len(messages)}, tools: {len(TOOLS)}")
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=TOOLS,
            messages=messages,
        )

        print(f"[stop_reason] {response.stop_reason}")

        # --- end_turn: 输出文本,结束 ---
        if response.stop_reason == "end_turn":
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content += block.text
            print("[完成] 模型返回最终文本")
            print("=" * 60)
            return text_content

        # --- tool_use: 执行工具,继续循环 ---
        if response.stop_reason == "tool_use":
            # 1. 把 assistant 回复加入历史
            messages.append({"role": "assistant", "content": response.content})

            # 2. 遍历所有 tool_use blocks,执行工具
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [工具调用] {block.name}({json.dumps(block.input, ensure_ascii=False)})")

                    # 查 dispatch map
                    handler = DISPATCH_MAP.get(block.name)
                    if handler:
                        result = handler(**block.input)
                    else:
                        result = f"错误: 未知工具 '{block.name}'"

                    # 截断过长的结果 (防止 token 爆炸)
                    MAX_RESULT_LEN = 10000
                    if len(result) > MAX_RESULT_LEN:
                        result = result[:MAX_RESULT_LEN] + f"\n... (截断,共 {len(result)} 字符)"

                    print(f"  [工具结果] {result[:200]}{'...' if len(result) > 200 else ''}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # 3. 把工具结果加入历史,继续循环
            messages.append({"role": "user", "content": tool_results})
            continue

        # --- max_tokens 或其他 ---
        print(f"[异常] stop_reason: {response.stop_reason}")
        text_content = ""
        for block in response.content:
            if block.type == "text":
                text_content += block.text
        print("=" * 60)
        return text_content or "(异常终止)"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main():
    print("Session 02: Tool Use Agent")
    print("输入任务开始,输入 'quit' 退出\n")
    print("可用工具: read_file, write_file, list_files")
    print("示例: '列出当前目录的文件' 或 '读取 README.md'\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("再见!")
            break

        result = run_agent(user_input)
        print(f"\nAgent: {result}\n")


if __name__ == "__main__":
    main()
