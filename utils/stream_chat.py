import json
import asyncio
import httpx
import logging
from typing import AsyncGenerator
from config.config import CLIENT_CONFIGS
from config.models import model_registry, list_model_ids
from utils.chat_history import ChatHistory
from prompt.get_system_prompt import get_system_prompt

# 日志配置
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 全局聊天历史（保存最近 10 条对话）
chat_history = ChatHistory(max_entries=10)


async def execute_model(model_name: str, user_input: str, system_instructions: str) -> AsyncGenerator[str, None]:
    """
    调用指定模型并流式返回生成内容
    - 支持上下文拼接
    - 每次调用结束后存储完整对话
    """
    model_details = model_registry(model_name)
    client_key = model_details["client_name"]
    client_settings = CLIENT_CONFIGS[client_key]

    base_url = client_settings["base_url"]
    api_key = client_settings["api_key"]
    model_label = model_details["label"]

    logger.info(f"[调用模型] {model_label} @ {base_url}")

    # 拼接 prompt
    system_prompt = f"{system_instructions}\n"
    recent_history = chat_history.format_history()
    full_user_prompt = f"历史记录:\n{recent_history}\n用户输入:{user_input}"

    payload = {
        "model": model_label,
        "stream": True,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_user_prompt}
        ]
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    full_response_text = ""

    # 异步请求模型接口（流式输出）
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", base_url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[len("data: "):].strip()
                if data_str in ("[DONE]", ""):
                    continue

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    logger.warning(f"无效 JSON: {data_str}")
                    continue

                choices = chunk.get("choices", [])
                if choices and "delta" in choices[0]:
                    delta_content = choices[0]["delta"].get("content")
                    if delta_content:
                        full_response_text += delta_content
                        yield delta_content

    # 调用完成后保存历史
    if full_response_text.strip():
        chat_history.add_entry(user_input, full_response_text)
        logger.info("[对话已保存] 用户输入 + 模型回复")


async def select_model() -> str:
    """让用户选择模型"""
    available_models = list_model_ids()
    print("\n可用模型：")
    [print(f"{i + 1}. {m}") for i, m in enumerate(available_models)]

    while True:
        try:
            idx = int(input("请选择模型编号: ")) - 1
            if 0 <= idx < len(available_models):
                model_name = available_models[idx]
                logger.info(f"[已选择模型] {model_name}")
                return model_name
            else:
                print("无效选择，请重新输入。")
        except ValueError:
            print("请输入数字。")


async def main_loop():
    """主交互循环"""
    model_name = await select_model()
    system_instructions = get_system_prompt("prompt02")

    while True:
        user_input = input("\n请输入内容 (命令: {clear}, {history}, {switch}): ").strip()

        # 系统命令处理
        if user_input == "{clear}":
            chat_history.clear_history()
            print("历史记录已清空")
            logger.info("[操作] 历史记录已清空")
            continue

        if user_input == "{history}":
            print("当前历史记录：")
            print(chat_history.format_history())
            logger.info("[操作] 查看历史记录")
            continue

        if user_input == "{switch}":
            model_name = await select_model()
            continue

        # 调用模型并流式打印回复
        async for text_chunk in execute_model(model_name, user_input, system_instructions):
            print(text_chunk, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main_loop())
