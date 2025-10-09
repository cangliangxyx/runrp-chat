# prompt/stream_api.py
import asyncio
from openai import OpenAI
import logging
from colorama import init, Fore
from config.config import CLIENT_CONFIGS
from config.models import model_registry, list_model_ids
from utils.chat_history import ChatHistory
from prompt.get_system_prompt import get_system_prompt
from utils.persona_loader import select_personas, get_default_personas
from utils.message_builder import build_messages
from utils.print_messages_colored import print_messages_colored, print_model_output_colored

# -----------------------------
# 初始化颜色输出
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
chat_history = ChatHistory(max_entries=50)
MAX_HISTORY_ENTRIES = 1
SAVE_STORY_SUMMARY_ONLY = True

# -----------------------------
# 一次性调用模型
# -----------------------------
async def call_model_once(model_name: str, user_input: str, system_prompt: str, personas: list[str]) -> str:
    """调用模型，一次性返回完整文本"""
    model_info = model_registry(model_name)
    client_key = model_info["client_name"]
    client_settings = CLIENT_CONFIGS[client_key]
    base_url = client_settings["base_url"].rstrip("/chat/completions")

    messages = build_messages(
        system_prompt,
        personas,
        chat_history,
        user_input,
        max_history_entries=MAX_HISTORY_ENTRIES,
        optional_message=""
    )
    print_messages_colored(messages)

    client = OpenAI(api_key=client_settings["api_key"], base_url=base_url)

    try:
        response = client.chat.completions.create(
            model=model_info["label"],
            messages=messages
        )
        text = response.choices[0].message.content
        return text
    except Exception as e:
        logger.error(f"[模型调用失败] {e}")
        return ""

# -----------------------------
# 执行模型并保存历史
# -----------------------------
async def execute_model(model_name: str, user_input: str, system_prompt: str, personas: list[str]):
    full_text = await call_model_once(model_name, user_input, system_prompt, personas)

    if full_text.strip():
        if SAVE_STORY_SUMMARY_ONLY:
            summary = chat_history._extract_summary_from_assistant(full_text)
            if summary:
                chat_history.add_entry(user_input, summary)
                logger.info("[对话已保存] 用户输入 + 摘要")
        else:
            chat_history.add_entry(user_input, full_text)
            logger.info("[对话已保存] 用户输入 + 完整回复")

    print_model_output_colored(full_text, color=Fore.LIGHTBLACK_EX)
    logger.info("[模型回复完成]\n")

# -----------------------------
# 模型选择
# -----------------------------
async def select_model() -> str:
    models = list_model_ids()
    print("\n可用模型：")
    for idx, m in enumerate(models, start=1):
        print(f"{idx}. {m}")

    while True:
        try:
            choice = int(input("请选择模型编号: ")) - 1
            if 0 <= choice < len(models):
                logger.info(f"[已选择模型] {models[choice]}")
                return models[choice]
            print("无效选择，请重新输入。")
        except ValueError:
            print("请输入数字。")

# -----------------------------
# 自动填充初始剧情
# -----------------------------
async def auto_fill_initial_story(model_name: str, system_prompt: str, personas: list[str]):
    if chat_history.is_empty():
        start_message = "这是一个测试故事的起点。"
        logger.info(f"[自动输入] {start_message}")
        await execute_model(model_name, start_message, system_prompt, personas)
        logger.info("[初始剧情输出完成]")
    else:
        logger.info("[跳过] 历史记录非空")

# -----------------------------
# 主循环
# -----------------------------
async def main_loop():
    personas = get_default_personas()
    model_name = await select_model()
    system_prompt = get_system_prompt("安清雪")
    logger.info(f"[默认出场人物] {personas}")

    await auto_fill_initial_story(model_name, system_prompt, personas)

    while True:
        user_input = input("\n请输入内容 (命令: {clear}, {history}, {switch}, {personas}): ").strip()

        if user_input == "{clear}":
            chat_history.clear_history()
            logger.info("[历史记录已清空]")
            continue
        if user_input == "{history}":
            print(chat_history.format_history(MAX_HISTORY_ENTRIES))
            continue
        if user_input.startswith("{switch}"):
            model_name = await select_model()
            continue
        if user_input.startswith("{personas}"):
            personas = await select_personas()
            logger.info(f"[人物更新] {personas}")
            continue

        await execute_model(model_name, user_input, system_prompt, personas)

if __name__ == "__main__":
    asyncio.run(main_loop())
