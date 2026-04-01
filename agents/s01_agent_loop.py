"""
Session 01: Agent Loop — 代理的核心循环

一个最简 agent: while(true) 循环调用模型,检查 stop_reason,决定下一步。
没有工具,没有流式输出,只有最核心的循环模式。

运行: python s01_agent_loop.py
依赖: pip install anthropic
"""

import os
from anthropic import Anthropic

# ---------------------------------------------------------------------------
# 初始化客户端
# ---------------------------------------------------------------------------
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096


def run_agent(user_input: str) -> str:
    """
    核心 Agent Loop。

    流程:
        1. 把用户输入放入消息历史
        2. while True:
            a. 调用 API
            b. 检查 stop_reason
            c. end_turn → 返回文本结果
            d. tool_use → (本节暂不处理) 退出循环
    """
    # Step 1: 初始化消息历史
    messages = [
        {
            "role": "user",
            "content": user_input,
        }
    ]

    turn = 0  # 循环计数器

    print("=" * 60)
    print("Agent Loop 启动")
    print("=" * 60)

    # Step 2: while True 主循环
    while True:
        turn += 1
        print(f"\n--- Turn {turn} ---")

        # Step 2a: 调用模型
        print(f"[调用模型] messages 数量: {len(messages)}")
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=messages,
        )

        # Step 2b: 检查 stop_reason
        print(f"[stop_reason] {response.stop_reason}")

        # Step 3: 分支处理
        if response.stop_reason == "end_turn":
            # 模型说完话了,输出文本,结束循环
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content += block.text

            print(f"[输出] 模型返回文本 ({len(text_content)} 字符)")
            print("=" * 60)
            return text_content

        elif response.stop_reason == "tool_use":
            # 模型想调用工具 — s02 会实现真正的工具执行
            print("[工具请求] 模型想要调用工具,但本节尚未实现")
            print("[提示] 请继续学习 s02_tool_use.py")

            # 把模型回复加入历史 (即使不执行工具也要记录)
            messages.append({"role": "assistant", "content": response.content})

            # 打印模型想调用什么
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  工具名: {block.name}")
                    print(f"  参数:   {block.input}")

            # 没有工具实现,无法继续,退出
            print("[退出] 无法继续循环 (缺少工具实现)")
            print("=" * 60)
            return "(agent 请求了工具但未实现)"

        elif response.stop_reason == "max_tokens":
            print("[警告] 达到 max_tokens 上限,回复被截断")
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content += block.text
            print("=" * 60)
            return text_content

        else:
            print(f"[未知] stop_reason: {response.stop_reason}")
            print("=" * 60)
            return "(遇到未知的 stop_reason)"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main():
    print("Session 01: Agent Loop")
    print("输入问题开始对话,输入 'quit' 退出\n")

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
