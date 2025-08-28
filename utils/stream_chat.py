# utils/stream_chat.py

import json
from datetime import datetime
import asyncio
import httpx
from typing import AsyncGenerator
from config.config import CLIENT_CONFIGS
from config.models import model_registry
from utils.chat_history import ChatHistory
import logging

logger = logging.getLogger(__name__)

chat_history = ChatHistory(max_entries=10)

async def execute_model(model_name: str, user_input: str, system_instructions: str) -> AsyncGenerator[str, None]:
    """调用指定模型并流式返回生成内容"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    model_details = model_registry(model_name)
    client_key = model_details.get("client_name")
    client_settings = CLIENT_CONFIGS[client_key]

    base_url = client_settings["base_url"]
    api_key = client_settings["api_key"]
    model_label = model_details.get("label")

    logger.info(f"[call] Model: {model_label}, 请求目标: {base_url}")

    system_prompt = f"{system_instructions}\n"
    recent_summaries = chat_history.format_history()
    full_user_prompt = f"历史记录:\n{recent_summaries}\n用户输入:{user_input}"

    payload = {
        "model": model_label,
        "stream": True,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_user_prompt}
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    full_response_text = ""

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", base_url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[len("data: "):].strip()
                if data_str in ("[DONE]", ""):
                    continue  # 跳过流结束标识或空行

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    logger.warning(f"跳过无效 JSON: {data_str}")
                    continue

                choices = chunk.get("choices", [])
                if choices and "delta" in choices[0]:
                    delta_content = choices[0]["delta"].get("content")
                    if delta_content:
                        full_response_text += delta_content
                        yield delta_content

    # 流结束后尝试匹配时间戳并保存历史
    match = ChatHistory.TIMESTAMP_PATTERN.search(full_response_text)
    if match:
        chat_history.add_entry(match.group(1).strip())  # group(1) 是内容



from prompt.get_system_prompt import get_system_prompt
from config.models import list_model_ids


async def main_loop():
    available_models = list_model_ids()
    print("可用模型：")
    [print(f"{i + 1}. {model}") for i, model in enumerate(available_models)]

    while True:
        try:
            selected_index = int(input("请选择模型编号: ")) - 1
            if 0 <= selected_index < len(available_models):
                model_name = available_models[selected_index]
                break
            else:
                print("无效选择，请重新输入。")
        except ValueError:
            print("请输入数字。")

    system_instructions = get_system_prompt("prompt02")

    while True:
        user_input = input("\n请输入内容: ")
        async for text_chunk in execute_model(model_name, user_input, system_instructions):
            print(text_chunk, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main_loop())
