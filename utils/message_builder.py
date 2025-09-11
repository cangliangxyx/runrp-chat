# utils/message_builder.py

from utils.persona_loader import load_persona

MAX_HISTORY_ENTRIES = 10  # 最近几条对话传给模型

def append_personas_to_messages(messages: list[dict], personas: list[str]) -> None:
    """
    将指定角色信息加载到 messages 中（作为 system message）
    """
    persona_info = "玩家角色: 常亮\n"
    for name in personas:
        try:
            persona_data = load_persona(name)
            if isinstance(persona_data, dict):
                info_lines = [f"{k}:{v}" for k, v in persona_data.items()]
                persona_info += f"{name}: {', '.join(info_lines)}\n"
        except KeyError:
            continue
    messages.append({"role": "system", "content": f"出场人物信息:\n{persona_info}"})


def build_messages(system_instructions: str, personas: list[str], chat_history, user_input: str, web_input: str = ""):
    """
    构建 messages 列表，供模型调用
    Args:
        system_instructions: 系统规则
        personas: 出场人物
        chat_history: ChatHistory 对象
        user_input: 用户输入
        web_input: 可选的 Web 前端输入（用于区分）
    """
    messages = []

    # ① 系统规则
    messages.append({"role": "system", "content": system_instructions})

    # ② 出场人物
    append_personas_to_messages(messages, personas)

    # ③ 历史摘要
    history_entries = chat_history.entries[-MAX_HISTORY_ENTRIES:-1]
    if history_entries:
        summary_text = "\n".join([f"{e['assistant']}" for e in history_entries if e['assistant']])
        if summary_text:
            messages.append({"role": "system", "content": f"历史摘要（仅参考，不要重复描写内容）：\n{summary_text}"})

    # ④ 当前输入
    current_user_message = {
        "role": "user",
        "content": f"{web_input} 用户输入内容：{user_input}" if web_input else user_input
    }
    messages.append(current_user_message)

    return messages

if __name__ == "__main__":
    from utils.persona_loader import get_default_personas
    from utils.chat_history import ChatHistory

    # 准备测试数据
    system_prompt = "系统提示：一个测试消息。"
    user_input = "用户输入测试"
    personas = get_default_personas()
    chat_history = ChatHistory(max_entries=MAX_HISTORY_ENTRIES)

    # 构建 messages
    messages = build_messages(system_prompt, personas, chat_history, user_input)

    print("\n=== 构建结果 ===")
    for i, msg in enumerate(messages, 1):
        print(f"[{i}] {msg['role'].upper()}:\n{msg['content']}\n")
    print("=== 测试结束 ===")
