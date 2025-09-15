from colorama import Fore, Style

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