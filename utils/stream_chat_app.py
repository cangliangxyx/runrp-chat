# utils/stream_chat_app.py

import json
import logging
from datetime import datetime
from typing import AsyncGenerator
from colorama import init, Fore, Style

import httpx
from config.config import CLIENT_CONFIGS
from config.models import model_registry
from utils.chat_history import ChatHistory
from utils.persona_loader import load_persona

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# -----------------------------
# 独立 chat_history（只给 Web 用）
# -----------------------------
chat_history = ChatHistory(max_entries=50) # 只保留最近 50 条对话。
MAX_HISTORY_ENTRIES = 10 # 最近 10 条对话传给模型
SAVE_STORY_SUMMARY_ONLY = True  # 只保存摘要，避免文件太大


# -----------------------------
# 角色加载简化函数
# -----------------------------
def append_personas_to_messages(messages: list[dict], personas: list[str]) -> None:
    """
    将指定角色信息加载到 messages 中（作为 system message），完整返回所有字段。

    Args:
        messages: 消息列表，函数会直接 append
        personas: 角色名称列表
    """
    persona_info = "玩家角色: 常亮\n"

    for name in personas:
        try:
            persona_data = load_persona(name)
            if isinstance(persona_data, dict):
                # 将所有字段拼接为 key: value
                info_lines = [f"{k}:{v}" for k, v in persona_data.items()]
                persona_info += f"{name}: {', '.join(info_lines)}\n"
        except KeyError:
            # 未找到的 NPC 直接跳过
            continue

    messages.append({"role": "system", "content": f"出场人物信息:\n{persona_info}"})


async def execute_model_for_app(
    model_name: str,
    user_input: str,
    system_instructions: str,
    personas: list[str],
) -> AsyncGenerator[str, None]:
    """
    专供 Web 使用的模型执行器
    1. 插入占位记录（用户输入 + 空回复）
    2. 流式请求模型 -> yield 片段给前端
    3. 结束后更新最后一条 assistant 字段并保存
    4. 出错则回滚
    """

    # 1 插入占位
    chat_history.entries.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_input.strip(),
        "assistant": ""
    })
    if len(chat_history.entries) > chat_history.max_entries:
        chat_history.entries = chat_history.entries[-chat_history.max_entries:]

    # 2 构建消息列表

    # --- 1. 读取模型配置 ---
    model_details = model_registry(model_name)
    client_settings = CLIENT_CONFIGS[model_details["client_name"]]
    base_url = client_settings["base_url"]
    api_key = client_settings["api_key"]

    # --- 2. 初始化 messages 列表 ---
    messages = []

    # ① 系统规则
    messages.append({"role": "system", "content": system_instructions})

    # ② 出场人物
    append_personas_to_messages(messages, personas)

    # ③ 历史对话（不包含当前占位）
    history_entries = chat_history.entries[-MAX_HISTORY_ENTRIES:-1]
    if history_entries:
        summary_text = "\n".join([f"{e['assistant']}" for e in history_entries if e['assistant']])
        if summary_text:
            messages.append({"role": "system", "content": f"历史摘要（仅参考，不要重复）：\n{summary_text}"})

    # ④ 当前用户输入
    current_user_message = {
        "role": "user",
        "content": f"输出文字不少于3000字，注意输出格式正文+摘要，用户输入内容：{user_input}。未经指令禁止射精、高潮、切换场景或结束剧情"
    }
    messages.append(current_user_message)

    # 打印彩色消息列表
    print_messages_colored(messages)

    # --- 3. 组装 payload 和 headers ---
    payload = {
        "model": model_details["label"],
        "stream": True,
        "messages": messages
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # --- 4. 结果缓存，用于流式拼接 ---
    full_response_text = ""

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", base_url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    logger.error(f"模型接口返回非200状态码: {response.status_code}")
                    chat_history.entries.pop()  # 回滚占位
                    return

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    data_str = line[6:].strip()
                    if data_str in ("", "[DONE]"):
                        continue

                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.warning(f"无效 JSON: {data_str}")
                        continue

                    # 安全获取 delta_content
                    delta_content = None
                    choices = chunk.get("choices")
                    if choices and isinstance(choices, list) and len(choices) > 0:
                        delta = choices[0].get("delta")
                        if isinstance(delta, dict):
                            delta_content = delta.get("content")

                    if delta_content:
                        full_response_text += delta_content
                        logger.debug(f"[流式输出 chunk] {delta_content[:50]}{'...' if len(delta_content) > 50 else ''}")
                        yield delta_content

    except httpx.RequestError as e:
        logger.error(f"[网络错误] 请求模型接口异常: {e}")
        chat_history.entries.pop()
        return

    # 3 更新最后一条历史
    if full_response_text.strip():
        if SAVE_STORY_SUMMARY_ONLY:
            summary = chat_history._extract_summary_from_assistant(full_response_text)
            if summary:
                chat_history.entries[-1]["assistant"] = summary
                chat_history.save_history()
                logger.info("[对话已保存] 用户输入 + 故事摘要")
            else:
                logger.info("[跳过保存] 未找到故事摘要")
        else:
            chat_history.entries[-1]["assistant"] = full_response_text
            chat_history.save_history()
            logger.info("[对话已保存] 用户输入 + 模型完整回复")
    else:
        chat_history.entries.pop()  # 没有生成内容就移除占位



init(autoreset=True)  # 初始化 colorama

def print_messages_colored(messages):
    print("\n--- 构建好的消息列表 messages ---")
    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        # 给不同角色加颜色
        if role == "system":
            color = Fore.CYAN
        elif role == "user":
            color = Fore.GREEN
        elif role == "assistant":
            color = Fore.MAGENTA
        else:
            color = Fore.WHITE

        print(f"{color}[{i}] {role.upper()}:\n{content}\n{Style.RESET_ALL}")
    print("--- End of messages ---\n")