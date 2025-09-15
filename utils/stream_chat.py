# utils/stream_chat.py
import json
import asyncio
import httpx
import logging
from typing import AsyncGenerator
from colorama import init, Fore, Style
from config.config import CLIENT_CONFIGS
from config.models import model_registry, list_model_ids
from utils.chat_history import ChatHistory
from prompt.get_system_prompt import get_system_prompt
from utils.persona_loader import select_personas, get_default_personas
from utils.message_builder import build_messages
from utils.print_messages_colored import print_messages_colored

# 初始化颜色输出
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
MAX_HISTORY_ENTRIES = 1                     # 最近 10 条对话传给模型
SAVE_STORY_SUMMARY_ONLY = True              # 只保存摘要，避免文件太大

# -----------------------------
# 初始剧情
# -----------------------------
# AUTO_START_MESSAGE = (
#     "末日降临第一天，你意外绑定了无敌避难所。当外界还在为取暖、物资发愁时，你正悠闲地坐在恒温20度的避难所里，享用着鲜嫩多汁的牛排和醇香的红酒。"
#     "手机屏幕不断闪烁，避难所物业群里信息爆炸：\n"
#     "[避难所物业群] 王佩佩：外面冷得要死，谁能帮我的把暖气修好？\n"
#     "物业张静：请大家保持冷静。我正在检查供暖系统，暂时请大家穿厚一些。\n"
#     "刘焕琴：谁有退烧药？我妹妹发高烧了，有退烧药的私聊我，我……我可以提供“特殊”补偿！\n"
#     "就在你浏览群消息时，一条私聊突然弹出：\n"
#     "[私聊] 梁红： 学长，你还好吗？我已经一天没吃东西了，快饿死了...你那里有吃的吗？求求你，帮帮我吧。\n"
#     "我看着手机，准备先不回复手机里的任何消息，需要好好想想到底应该如何办"
# )
AUTO_START_MESSAGE = "你好"

# -----------------------------
# 调用模型并流式返回
# -----------------------------
async def execute_model(
    model_name: str,
    user_input: str,
    system_instructions: str,
    personas: list[str],
) -> AsyncGenerator[str, None]:
    model_details = model_registry(model_name)
    client_key = model_details["client_name"]
    client_settings = CLIENT_CONFIGS[client_key]

    logger.info(f"[调用模型] {model_details['label']} @ {client_settings['base_url']}")

    messages = build_messages(system_instructions, personas, chat_history, user_input)

    print_messages_colored(messages)

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
                    if not (line and line.startswith("data: ")):
                        continue
                    data_str = line[len("data: "):].strip()
                    if data_str in ("[DONE]", ""):
                        continue
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices")
                        if not choices or len(choices) == 0:  # 避免 IndexError
                            continue
                        delta = choices[0].get("delta", {})
                        delta_content = delta.get("content")
                        if delta_content:
                            full_response_text += delta_content
                            yield delta_content
                    except json.JSONDecodeError:
                        logger.warning(f"无效 JSON: {data_str}")
                        continue
    except httpx.RequestError as e:
        logger.error(f"请求模型接口异常: {e}")

    # 保存历史
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
            print("无效选择，请重新输入。")
        except ValueError:
            print("请输入数字。")

# -----------------------------
# 主循环
# -----------------------------
async def main_loop():
    current_personas = get_default_personas()           # 人物加载
    model_name = await select_model()                   # 模型选择
    system_instructions = get_system_prompt("nsxt")     # 获取默认配置文件
    logger.info(f"[默认出场人物] {current_personas}")

    # 自动输入初始剧情
    logger.info(f"[自动输入] {AUTO_START_MESSAGE}")
    async for text_chunk in execute_model(model_name, AUTO_START_MESSAGE, system_instructions, current_personas):
        print(text_chunk, end="", flush=True)
    logger.info("\n[生成完成] 初始剧情输出完成")

    while True:
        user_input = input("\n请输入内容 (命令: {clear}, {history}, {switch}, {personas}): ").strip()
        if user_input == "{clear}":
            chat_history.clear_history()
            logger.info("[操作] 历史记录已清空")
            continue
        if user_input == "{history}":
            print(chat_history.format_history(MAX_HISTORY_ENTRIES))
            continue
        if user_input.startswith("{switch}"):
            model_name = await select_model()
            continue
        if user_input.startswith("{personas}"):
            current_personas = await select_personas()
            logger.info(f"[人物更新] 当前出场人物: {current_personas}")
            continue

        async for text_chunk in execute_model(model_name, user_input, system_instructions, current_personas):
            print(text_chunk, end="", flush=True)
        logger.info("\n[生成完成] 模型回复已输出完成")

if __name__ == "__main__":
    asyncio.run(main_loop())
