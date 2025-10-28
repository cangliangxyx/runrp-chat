import asyncio
import json
import logging
from typing import AsyncGenerator

import httpx
from colorama import init, Fore

from config.config import CLIENT_CONFIGS
from config.models import model_registry, list_model_ids
from prompt.get_system_prompt import get_system_prompt
from utils.chat_history import ChatHistory
from utils.message_builder import build_messages
from utils.print_messages_colored import print_messages_colored, print_model_output_colored

# 初始化颜色输出
init(autoreset=True)

# -----------------------------
# 日志配置
# -----------------------------
def setup_logger():
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

logger = setup_logger()

# -----------------------------
# 常量定义
# -----------------------------
chat_history = ChatHistory(max_entries=50)  # 只保留最近 50 条对话
MAX_HISTORY_ENTRIES = 5                     # 最近几条对话传给模型
SAVE_SUMMARY_ONLY = False                   # 是否仅保存摘要

# -----------------------------
# 统一的流解析函数
# -----------------------------
def parse_stream_chunk(data_str: str) -> str | None:
    """
    解析模型流式返回的内容片段，兼容 OpenAI / Gemini 风格。
    """
    try:
        chunk = json.loads(data_str)
        # OpenAI 风格
        if "choices" in chunk:
            choices = chunk.get("choices")
            if not isinstance(choices, list) or not choices:
                return None
            choice = choices[0]
            if "delta" not in choice:
                return None
            delta = choice.get("delta", {})
            return delta.get("content")
        # Gemini 风格
        elif "candidates" in chunk:
            parts = chunk["candidates"][0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts if "text" in p)
        else:
            return None
    except json.JSONDecodeError:
        if data_str.strip() != "[DONE]":
            logger.warning(f"[系统] 无效 JSON: {data_str}")
        return None

# -----------------------------
# 调用模型并流式返回
# -----------------------------
async def execute_model(
    model_name: str,
    user_input: str,
    system_instructions: str,
    stream: bool = False,
    personas = None
) -> AsyncGenerator[str, None]:
    """
    调用指定模型进行对话，支持流式和非流式输出。
    统一处理异常和日志，返回生成的内容片段。
    """
    model_info = model_registry(model_name)
    client_key = model_info["client_name"]
    client_settings = CLIENT_CONFIGS[client_key]

    logger.info(f"[系统] 正在调用模型: {model_info['label']} @ {client_settings['base_url']}")
    messages = build_messages(
        system_instructions, personas, chat_history, user_input,
        max_history_entries=MAX_HISTORY_ENTRIES, optional_message=""
    )
    # 添加当前用户输入
    # messages.append({"role": "user", "content": user_input})

    print_messages_colored(messages)

    payload = {"model": model_info["label"], "stream": stream, "messages": messages}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {client_settings['api_key']}"
    }

    response_text = ""
    got_done = False
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            if stream:
                async with client.stream("POST", client_settings["base_url"], headers=headers, json=payload) as resp:
                    if resp.status_code != 200:
                        logger.error(f"[系统] 模型接口返回非200状态码: {resp.status_code}")
                        return
                    print(Fore.CYAN + "\n--- 模型响应开始 ---\n" + Fore.RESET)
                    async for line in resp.aiter_lines():
                        if not (line and line.startswith("data: ")):
                            continue
                        data_str = line[len("data: "):].strip()
                        if data_str == "[DONE]":
                            got_done = True
                            break
                        chunk_text = parse_stream_chunk(data_str)
                        if chunk_text:
                            response_text += chunk_text
                            print_model_output_colored(chunk_text, color=Fore.LIGHTBLACK_EX)
                            yield chunk_text
                    print(Fore.CYAN + "\n--- 模型响应结束 ---\n" + Fore.RESET)
            else:
                resp = await client.post(client_settings["base_url"], headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.error(f"[系统] 模型接口返回非200状态码: {resp.status_code}")
                    return
                data = resp.json()
                if "choices" in data and data["choices"]:
                    print(Fore.CYAN + "\n--- 模型响应开始 ---\n" + Fore.RESET)
                    for choice in data["choices"]:
                        text = choice.get("message", {}).get("content") or choice.get("text") or ""
                        response_text += text
                    print_model_output_colored(response_text, color=Fore.LIGHTBLACK_EX)
                    print(Fore.CYAN + "\n--- 模型响应结束 ---\n" + Fore.RESET)
                    yield response_text
                got_done = True
    except httpx.RequestError as exc:
        logger.error(f"[系统] 请求模型接口异常: {exc}")

    await asyncio.sleep(0.05)

    if not got_done:
        logger.warning("[系统] 流式传输未检测到 [DONE]，输出可能不完整")

    # 保存历史
    if response_text.strip():
        if SAVE_SUMMARY_ONLY:
            summary = chat_history._extract_summary_from_assistant(response_text)
            if summary:
                chat_history.add_entry(user_input, summary)
                logger.info("[系统] 对话已保存（用户输入 + 故事摘要）")
            else:
                logger.info("[系统] 跳过保存，未找到故事摘要")
        else:
            chat_history.add_entry(user_input, response_text)
            logger.info("[系统] 对话已保存（用户输入 + 模型回复）")

# -----------------------------
# 模型选择
# -----------------------------
async def select_model() -> str:
    """
    控制台选择模型，返回模型名。
    """
    available_models = list_model_ids()
    print("\n可用模型：")
    for i, m in enumerate(available_models):
        print(f"{i + 1}. {m}")
    while True:
        try:
            idx = int(input("请选择模型编号: ")) - 1
            if 0 <= idx < len(available_models):
                model_name = available_models[idx]
                logger.info(f"[系统] 已选择模型: {model_name}")
                return model_name
            print("无效选择，请重新输入。")
        except ValueError:
            print("请输入数字。")

# -----------------------------
# 主循环
# -----------------------------
async def main_loop():
    """
    控制台主对话循环，处理用户输入和特殊命令。
    """
    model_name = await select_model()
    system_instructions = get_system_prompt("prompt")
    while True:
        print("\n请输入内容 (命令: {clear}, {history}, {switch}, {personas}):")
        lines = []
        empty_count = 0
        while True:
            line = input()
            if line.strip() == "END":
                break
            if line.strip() == "":
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
            lines.append(line)
        user_input = "\n".join(lines).strip()
        if user_input == "{clear}":
            chat_history.clear_history()
            logger.info("[系统] 历史记录已清空")
            continue
        if user_input == "{history}":
            print(chat_history.format_history(MAX_HISTORY_ENTRIES))
            continue
        if user_input.startswith("{switch}"):
            model_name = await select_model()
            continue
        logger.info("[系统] 正在调用模型...")
        async for text_chunk in execute_model(model_name, user_input, system_instructions):
            # 输出已经在execute_model中处理，这里不重复打印
            pass
        # 移除重复的生成完成日志

if __name__ == "__main__":
    asyncio.run(main_loop())
