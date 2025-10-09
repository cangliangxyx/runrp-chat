# prompt/stream_chat.py

import json
import asyncio

import httpx
import logging
from typing import AsyncGenerator
from colorama import init, Fore
from config.config import CLIENT_CONFIGS
from config.models import model_registry, list_model_ids
from utils.chat_history import ChatHistory
from prompt.get_system_prompt import get_system_prompt
from utils.persona_loader import select_personas, get_default_personas
from utils.message_builder import build_messages
from utils.print_messages_colored import print_messages_colored, print_model_output_colored


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
MAX_HISTORY_ENTRIES = 1                     # 最近几条对话传给模型
SAVE_STORY_SUMMARY_ONLY = True              # 只保存摘要，避免文件太大
# SAVE_STORY_SUMMARY_ONLY = False               # 保存所有内容


# -----------------------------
# 统一的流解析函数
# -----------------------------
def parse_stream_chunk(data_str: str) -> str | None:
    """
    兼容 OpenAI / Gemini 流式返回，解析内容片段
    """
    try:
        chunk = json.loads(data_str)

        # OpenAI 风格
        if "choices" in chunk:
            choices = chunk.get("choices")
            # 防御性判断：必须是非空列表
            if not isinstance(choices, list) or len(choices) == 0:
                logger.debug(f"[空或非法 choices] {chunk}")
                return None

            choice = choices[0]
            # 有些 chunk 只包含 finish_reason，不包含 delta
            if "delta" not in choice:
                logger.debug(f"[无 delta 字段] {chunk}")
                return None

            delta = choice.get("delta", {})
            return delta.get("content")

        # Gemini 风格
        elif "candidates" in chunk:
            parts = chunk["candidates"][0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts if "text" in p)

        else:
            logger.debug(f"[未知结构] {chunk}")
            return None

    except json.JSONDecodeError:
        # 忽略流结束标志 [DONE]
        if data_str.strip() == "[DONE]":
            logger.debug("检测到流结束标志 [DONE]")
        else:
            logger.warning(f"无效 JSON: {data_str}")
        return None


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
    messages = build_messages(system_instructions, personas, chat_history, user_input, max_history_entries=MAX_HISTORY_ENTRIES, optional_message="")
    print_messages_colored(messages)

    payload = {"model": model_details["label"], "stream": True, "messages": messages}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {client_settings['api_key']}"}

    full_response_text = ""
    got_done_flag = False  # 标记是否检测到流正常结束

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

                    # 检测流式结束信号
                    if data_str == "[DONE]":
                        got_done_flag = True
                        logger.debug(" 检测到 [DONE] 信号，流式传输结束")
                        break

                    # 调用统一解析器
                    delta_content = parse_stream_chunk(data_str)
                    if delta_content:
                        full_response_text += delta_content
                        yield delta_content

    except httpx.RequestError as e:
        logger.error(f"请求模型接口异常: {e}")

    # 等待输出缓冲刷新，防止终端打印被截断
    await asyncio.sleep(0.05)

    # 检查流是否完整
    if not got_done_flag:
        logger.warning("流式传输未检测到 [DONE]，可能中途被中断，输出可能不完整")

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

    logger.info("\n[生成完成] 模型回复已输出完成")


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
async def auto_fill_initial_story(model_name, system_instructions, current_personas):
    """仅在历史记录为空时填充初始剧情"""
    if chat_history.is_empty():
        AUTO_START_MESSAGE = '''
        冰冷的雨水无情地敲打着瀛洲市的柏油路面，霓虹灯的光晕在积水中化开，显得既绚烂又疏离。
        你就这样撑着伞，在街角遇见了她。
        丰满的乳房和翘臀，腰肢却细得让人心惊。盈盈一握这个词用在她身上都显得保守，那几乎是一种非人类的纤细，仿佛造物主最偏心的杰作。谁能拒绝一个巨乳萝莉般的诱惑？
        安清雪，那个曾经在财经杂志上出现过的名字，此刻却像一只被遗弃的湿漉漉的小猫，蜷缩在冰冷的墙角。她身上那件曾经名贵的连衣裙早已被雨水和污渍弄得不成样子，乌黑的长发紧贴着苍白的脸颊，嘴唇冻得发紫，整个人都在不住地颤抖。
        你的脚步停在了她的面前。
        她似乎察觉到了阴影，缓缓抬起头。那是一张即使在如此狼狈的情况下，依然美得惊心动魄的脸。她的眼神空洞，但在看清你的瞬间，那死寂的眼眸里猛地爆发出了一丝求生的星光。
        她扶着墙，用尽全身力气站了起来，踉跄地向你走近一步，声音沙哑而急切：
        “您……等，等一下。”
        她深吸一口气，雨水顺着她的下颌滴落，仿佛用尽了一生的勇气，对着你大声喊道：
        “只要您给我饭吃，我就跟您走，让我干什么都行！我……我会洗衣做饭，天冷了还能……还能帮您暖床……只要……只要给我口饭吃就行！”
        她的话语在雨声中显得那么微弱又那么决绝。她紧紧攥着衣角，用一种混合着恐惧、羞耻和孤注一掷的眼神，死死地盯着你，等待着你的审判。
        '''
        logger.info(f"[自动输入] {AUTO_START_MESSAGE}")
        async for text_chunk in execute_model(model_name, AUTO_START_MESSAGE, system_instructions, current_personas):
            print_model_output_colored(text_chunk, color=Fore.LIGHTBLACK_EX)
        logger.info("\n[生成完成] 初始剧情输出完成")
    else:
        logger.info("[跳过] 历史记录非空，未填充初始剧情")


async def main_loop():
    current_personas = get_default_personas()           # 人物加载
    model_name = await select_model()                   # 模型选择
    system_instructions = get_system_prompt("安清雪")     # 获取默认配置文件
    logger.info(f"[默认出场人物] {current_personas}")

    # 只有历史记录为空才填充初始剧情
    await auto_fill_initial_story(model_name, system_instructions, current_personas)

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
            print_model_output_colored(text_chunk, color=Fore.LIGHTBLACK_EX)
        logger.info("\n[生成完成] 模型回复已输出完成 ")


if __name__ == "__main__":
    asyncio.run(main_loop())
