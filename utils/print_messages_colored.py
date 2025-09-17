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
def print_model_output_colored(text, color: str = Fore.CYAN):
    """
    打印模型输出，仅改变颜色，不做换行处理
    :param text: 模型返回的文本片段
    :param color: 输出颜色
    """
    print(f"{color}{text}{Style.RESET_ALL}", end="", flush=True)
