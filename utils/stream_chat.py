# utils/stream_chat.py
import json
import asyncio
from datetime import datetime

import httpx
import logging
from typing import AsyncGenerator
from config.config import CLIENT_CONFIGS
from config.models import model_registry, list_model_ids
from utils.chat_history import ChatHistory
from prompt.get_system_prompt import get_system_prompt
from utils.persona_loader import select_personas, load_persona, get_default_personas

# -----------------------------
# 日志配置
# -----------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# -----------------------------
# 全局变量
# -----------------------------
chat_history = ChatHistory(max_entries=10)  # 保存最近 10 条对话

MAX_HISTORY_ENTRIES = 10  # 系统 prompt 中最多包含最近几条历史记录
SAVE_STORY_SUMMARY_ONLY = True  # True=仅保存故事摘要，False=保存全部内容

# -----------------------------
# 角色加载简化函数
# -----------------------------
def append_personas_to_messages(messages: list[dict], personas: list[str]) -> None:
    """
    将指定角色信息加载到 messages 中（作为 system message），只返回数据，不打印。

    Args:
        messages: 消息列表，函数会直接 append
        personas: 角色名称列表
    """
    persona_info = "玩家角色: 常亮\n"

    for name in personas:
        try:
            persona_data = load_persona(name)
            if isinstance(persona_data, dict):
                key_info = []
                for k in ["性别", "年龄", "职业", "外貌"]:
                    if k in persona_data:
                        key_info.append(f"{k}:{persona_data[k]}")
                persona_info += f"{name}: {', '.join(key_info)}\n"
            else:
                persona_info += f"{name}: {str(persona_data)}\n"
        except KeyError:
            # 未找到的 NPC 直接跳过
            continue

    messages.append({"role": "system", "content": f"出场人物信息:\n{persona_info}"})

# -----------------------------
# 核心功能：调用模型并流式返回
# -----------------------------
async def execute_model(
        model_name: str,
        user_input: str,
        system_instructions: str,
        personas: list[str]
) -> AsyncGenerator[str, None]:
    """
    调用指定模型并流式返回生成内容
    - 系统规则放 system prompt
    - 历史对话放 messages 的 user/assistant
    - 流式输出
    - 完成后保存聊天历史
    """
    model_details = model_registry(model_name)
    client_key = model_details["client_name"]
    client_settings = CLIENT_CONFIGS[client_key]

    base_url = client_settings["base_url"]
    api_key = client_settings["api_key"]
    model_label = model_details["label"]

    logger.info(f"[调用模型] {model_label} @ {base_url}")

    # -----------------------------
    # 系统 prompt 拼接（仅规则/世界观）
    # -----------------------------
    system_prompt = system_instructions

    # -----------------------------
    # 消息列表
    # -----------------------------
    messages = [{"role": "system", "content": system_prompt}]

    # -----------------------------
    # 出场人物信息加载（简化版）
    # -----------------------------
    append_personas_to_messages(messages, personas)

    # -----------------------------
    # 最近历史对话（放 messages 中）
    # -----------------------------
    history_entries = chat_history.entries[-MAX_HISTORY_ENTRIES:]
    for e in history_entries:
        messages.append({"role": "user", "content": e["user"]})
        messages.append({"role": "assistant", "content": e["assistant"]})

    # 当前用户输入
    messages.append({"role": "user", "content": f"注意输出格式，正文+摘要,{user_input}"})

    payload = {
        "model": model_label,
        "stream": True,
        "messages": messages
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    full_response_text = ""

    # -----------------------------
    # 异步请求模型接口（流式输出）
    # -----------------------------
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", base_url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    logger.error(f"模型接口返回非200状态码: {response.status_code}")
                    return

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

    except httpx.RequestError as e:
        logger.error(f"请求模型接口异常: {e}")
        logger.error("请求模型失败，请检查网络或接口设置。")

    # -----------------------------
    # 保存历史
    # -----------------------------
    if full_response_text.strip():
        if SAVE_STORY_SUMMARY_ONLY:
            summary = chat_history._extract_summary_from_assistant(full_response_text)
            if summary:
                chat_history.add_entry(user_input, summary)
                logger.info("[对话已保存] 用户输入 + 故事摘要")
            else:
                logger.info("[跳过保存] 未找到故事摘要")
        else:
            chat_history.add_entry(user_input, full_response_text)
            logger.info("[对话已保存] 用户输入 + 模型回复")

# -----------------------------
# 模型选择
# -----------------------------
async def select_model() -> str:
    """让用户选择模型"""
    available_models = list_model_ids()
    print("\n可用模型：")
    for i, m in enumerate(available_models):
        print(f"{i + 1}. {m}")

    while True:
        try:
            idx = int(input("请选择模型编号: ")) - 1
            if 0 <= idx < len(available_models):
                model_name = available_models[idx]
                logger.info(f"[已选择模型] {model_name}")
                return model_name
            else:
                print("无效选择，请重新输入。")
                logger.warning(f"[选择错误] 用户选择了无效的模型编号: {idx + 1}")
        except ValueError:
            print("请输入数字。")
            logger.warning("[选择错误] 用户输入了非数字内容")

# -----------------------------
# 主循环（仅命令行用）
# -----------------------------
async def main_loop():
    """主交互循环"""
    current_personas = get_default_personas()
    model_name = await select_model()
    system_instructions = get_system_prompt("prompt_test")
    logger.info(f"[默认出场人物] {current_personas}")
    logger.info(f"[历史保存模式] {'仅故事摘要' if SAVE_STORY_SUMMARY_ONLY else '完整内容'}")

    while True:
        user_input = input("\n请输入内容 (命令: {clear}, {history}, {switch}, {personas}): ").strip()
        logger.info(f"[用户输入] {user_input[:50]}{'...' if len(user_input) > 50 else ''}")

        if user_input == "{clear}":
            chat_history.clear_history()
            logger.info("[操作] 历史记录已清空")
            continue

        if user_input == "{history}":
            logger.info("[操作] 查看历史记录")
            history_text = chat_history.format_history(MAX_HISTORY_ENTRIES)
            logger.info(f"[历史记录]\n{history_text}")
            continue

        if user_input.startswith("{switch}"):
            model_name = await select_model()
            continue

        if user_input.startswith("{personas}"):
            current_personas = await select_personas()
            logger.info(f"[人物更新] 当前出场人物: {current_personas}")
            continue

        logger.info("[开始生成] 调用模型生成回复...")
        async for text_chunk in execute_model(model_name, user_input, system_instructions, current_personas):
            print(text_chunk, end="", flush=True)
        logger.info("\n[生成完成] 模型回复已输出完成")

if __name__ == "__main__":
    logger.info("[启动] Stream Chat 应用启动")
    asyncio.run(main_loop())
