# utils/message_builder.py

from utils.persona_loader import load_persona

# MAX_HISTORY_ENTRIES = 1  # 最近几条对话传给模型

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
    messages.append({"role": "system", "content": f"人物信息(不需要在正文输出):\n{persona_info}"})


def build_messages(system_instructions: str, personas: list[str], chat_history, user_input: str, web_input: str = "", nsfw: bool = False, max_history_entries: int = 10,optional_message: str = None ):
    """
    构建 messages 列表，供模型调用
    Args:
        system_instructions: 系统规则
        personas: 出场人物
        chat_history: ChatHistory 对象
        user_input: 用户输入
        web_input: 可选的 Web 前端输入（用于区分）
        optional_message: 可选消息，如果有值则插入
    """
    MAX_HISTORY_ENTRIES = max_history_entries
    messages = []

    # ① 系统规则
    messages.append({"role": "system", "content": system_instructions})

    # ② NSFW 内容
    if nsfw:
        from prompt.get_system_prompt import get_system_prompt
        try:
            nsfw_prompt = get_system_prompt("nsfw")  # 确保 PROMPT_FILES 中有 "nsfw" 键
            messages.append({"role": "system", "content": nsfw_prompt})
        except KeyError:
            messages.append({"role": "system", "content": "NSFW 模式已开启，但未找到 nsfw 提示内容。"})
    # ③ 出场人物
    append_personas_to_messages(messages, personas)

    # ④ 历史摘要
    history_entries = chat_history.entries[-MAX_HISTORY_ENTRIES:]
    if history_entries:
        # 提取非空的 assistant 内容
        assistant_texts = [e['assistant'] for e in history_entries if e['assistant']]
        if assistant_texts:
            # 将历史摘要整理成一段清晰说明
            summary_text = "\n".join(assistant_texts)
            summary_content = (
                "以下是之前的故事进展和角色状态：\n"
                f"{summary_text}\n"
                "##"
            )
            messages.append({"role": "assistant", "content": summary_content})

    # ⑤ 当前输入
    current_user_message = {
        "role": "user",
        "content": f"{web_input} 用户输入内容：{user_input}" if web_input else user_input
    }
    messages.append(current_user_message)

    # ⑥ 可选插入消息
    if optional_message:  # 只有有值才插入
        messages.append({"role": "system", "content": optional_message})

    return messages

if __name__ == "__main__":
    from utils.persona_loader import get_default_personas
    from utils.chat_history import ChatHistory

    MAX_HISTORY_ENTRIES = 1

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