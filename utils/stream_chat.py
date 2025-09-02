# utils/stream_chat.py

import json
import asyncio
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
current_personas: list[str] = get_default_personas()  # 默认玩家主角 + 刘焕琴

MAX_HISTORY_ENTRIES = 10  # 系统 prompt 中最多包含最近几条历史记录

# -----------------------------
# 核心功能：调用模型并流式返回
# -----------------------------
async def execute_model(model_name: str, user_input: str, system_instructions: str) -> AsyncGenerator[str, None]:
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

    # 出场人物信息作为 system message
    persona_info = "玩家角色: 常亮\n"
    if current_personas:
        for name in current_personas:
            try:
                persona_info += f"{name}: {load_persona(name)}\n"
            except KeyError:
                logger.warning(f"未找到 NPC {name}，忽略")
    else:
        logger.info("[提示] 当前未选择 NPC 出场，仅包含玩家主角 常亮")
    messages.append({"role": "system", "content": f"出场人物信息:\n{persona_info}"})

    # -----------------------------
    # 最近历史对话（放 messages 中）
    # -----------------------------
    history_entries = chat_history.entries[-MAX_HISTORY_ENTRIES:]
    for e in history_entries:
        messages.append({"role": "user", "content": e["user"]})
        messages.append({"role": "assistant", "content": e["assistant"]})

    # 当前用户输入
    messages.append({"role": "user", "content": user_input})

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
        print("请求模型失败，请检查网络或接口设置。")

    # -----------------------------
    # 保存历史
    # -----------------------------
    if full_response_text.strip():
        chat_history.add_entry(user_input, full_response_text)
        logger.info("[对话已保存] 用户输入 + 模型回复")


# -----------------------------
# 模型选择
# -----------------------------
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


# -----------------------------
# 主循环
# -----------------------------
async def main_loop():
    """主交互循环"""
    global current_personas
    model_name = await select_model()
    system_instructions = get_system_prompt("prompt_test")

    print(f"\n默认出场人物: {current_personas}")

    while True:
        user_input = input("\n请输入内容 (命令: {clear}, {history}, {switch}, {personas}): ").strip()

        # -----------------------------
        # 系统命令处理
        # -----------------------------
        if user_input == "{clear}":
            chat_history.clear_history()
            print("历史记录已清空")
            logger.info("[操作] 历史记录已清空")
            continue

        if user_input == "{history}":
            print("当前历史记录：")
            print(chat_history.format_history(MAX_HISTORY_ENTRIES))
            logger.info("[操作] 查看历史记录")
            continue

        if user_input.startswith("{switch}"):
            # 支持 switch 2 直接切换
            model_name = await select_model()
            continue

        if user_input.startswith("{personas}"):
            # 支持 personas 1,3 快速选择
            current_personas = await select_personas()
            continue

        # -----------------------------
        # 调用模型并流式打印回复
        # -----------------------------
        async for text_chunk in execute_model(model_name, user_input, system_instructions):
            print(text_chunk, end="", flush=True)


# -----------------------------
# 脚本入口
# -----------------------------
if __name__ == "__main__":
    asyncio.run(main_loop())
