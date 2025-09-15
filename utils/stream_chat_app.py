# utils/stream_chat_app.py

import json
import logging
from typing import AsyncGenerator
from colorama import init
import httpx

from config.config import CLIENT_CONFIGS
from config.models import model_registry
from utils.chat_history import ChatHistory
from utils.message_builder import build_messages
from utils.print_messages_colored import print_messages_colored

# -----------------------------
# 初始化 colorama
# -----------------------------
init(autoreset=True)

# -----------------------------
# 日志配置
# -----------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# -----------------------------
# 全局变量
# -----------------------------
chat_history = ChatHistory(max_entries=50)  # 只保留最近 50 条对话
MAX_HISTORY_ENTRIES = 1                   # 最近 10 条对话传给模型
SAVE_STORY_SUMMARY_ONLY = True             # 只保存摘要，避免文件太大

# -----------------------------
# 流式调用模型
# -----------------------------
async def execute_model_for_app(
    model_name: str,
    user_input: str,
    system_instructions: str,
    personas: list[str],
    web_input: str = "",
    nsfw: bool = True,
) -> AsyncGenerator[str, None]:

    print("nsfw = ", nsfw)
    # 构建 messages
    messages = build_messages(system_instructions, personas, chat_history, user_input, web_input, nsfw=nsfw, max_history_entries=MAX_HISTORY_ENTRIES)

    print_messages_colored(messages)

    # 模型配置
    model_details = model_registry(model_name)
    client_settings = CLIENT_CONFIGS[model_details["client_name"]]
    payload = {"model": model_details["label"], "stream": True, "messages": messages}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {client_settings['api_key']}"}

    full_response_text = ""
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", client_settings["base_url"], headers=headers, json=payload) as response:
                if response.status_code != 200:
                    logger.error(f"模型接口返回非200状态码: {response.status_code}")
                    return

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str in ("", "[DONE]"):
                        continue
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices")
                        if choices and len(choices) > 0:
                            delta = choices[0].get("delta", {})
                            delta_content = delta.get("content")
                            if delta_content:
                                full_response_text += delta_content
                                yield delta_content
                    except json.JSONDecodeError:
                        logger.warning(f"无效 JSON: {data_str}")
                        continue
    except httpx.RequestError as e:
        logger.error(f"[网络错误] 请求模型接口异常: {e}")
        return

    # 保存历史
    if full_response_text.strip():
        if SAVE_STORY_SUMMARY_ONLY:
            summary = chat_history._extract_summary_from_assistant(full_response_text)
            if summary:
                chat_history.add_entry(user_input, summary)
        else:
            chat_history.add_entry(user_input, full_response_text)
        chat_history.save_history()
