import re

from colorama import Fore, Style
import textwrap

# -----------------------------
# 彩色打印 messages
# -----------------------------
def print_messages_colored(messages):
    print("\n--- 构建好的消息列表 messages ---")
    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        color = {
            "system": Fore.CYAN,
            "user": Fore.GREEN,
            "assistant": Fore.MAGENTA
        }.get(role, Fore.WHITE)
        print(f"{color}[{i}] {role.upper()}:\n{content}\n{Style.RESET_ALL}")
    print("--- End of messages ---\n")

# -----------------------------
# 彩色打印模型输出（带缓冲池）
# -----------------------------
def print_model_output_colored(text, color: str = Fore.WHITE):
    """
    打印模型输出，『』或「」之间的文字用蓝色高亮
    :param text: 模型对话返回的文本片段 BLUE/LIGHTBLACK_EX
    :param color: 默认输出颜色 YELLOW/WHITE
    """
    # 正则匹配 『...』 和 「...」
    pattern = r"(『.*?』|「.*?」|“.*?”|\".*?\")"

    last_end = 0
    for match in re.finditer(pattern, text):
        start, end = match.span()

        # 打印前面的普通文本
        if start > last_end:
            print(f"{color}{text[last_end:start]}{Style.RESET_ALL}", end="", flush=True)

        # 打印高亮部分
        print(f"{Fore.WHITE}{match.group(0)}{Style.RESET_ALL}", end="", flush=True)

        last_end = end

    # 打印剩余的普通文本  我看着静静，她害羞的走过来说我帮老公，就这样她赤裸的穿着围圈背对我在做早餐我闻着她的体香，慢慢的插入她的骚逼里，糯糯起来后看见我在厨房干着张静赤裸着主动走过来在后面抱着我用大乳房帮我助兴
    if last_end < len(text):
        print(f"{color}{text[last_end:]}{Style.RESET_ALL}", end="", flush=True)
