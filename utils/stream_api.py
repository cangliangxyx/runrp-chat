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
# SAVE_STORY_SUMMARY_ONLY = True              # 只保存摘要，避免文件太大
SAVE_STORY_SUMMARY_ONLY = False               # 保存所有内容


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
    stream: bool = False,  # 新增参数，默认流式
) -> AsyncGenerator[str, None]:
    model_details = model_registry(model_name)
    client_key = model_details["client_name"]
    client_settings = CLIENT_CONFIGS[client_key]

    logger.info(f"[调用模型] {model_details['label']} @ {client_settings['base_url']}")

    messages = [
        {"role": "system", "content": system_instructions},
        # {"role": "assistant", "content": f"以下是之前的故事进展：{summary_content}"},
        {"role": "user", "content": f"用户输入内容：{user_input}"},
    ]

    print_messages_colored(messages)

    payload = {"model": model_details["label"], "stream": stream, "messages": messages}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {client_settings['api_key']}"}

    full_response_text = ""
    got_done_flag = False

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            if stream:
                # 流式处理
                async with client.stream("POST", client_settings["base_url"], headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        logger.error(f"模型接口返回非200状态码: {response.status_code}")
                        return

                    async for line in response.aiter_lines():
                        if not (line and line.startswith("data: ")):
                            continue
                        data_str = line[len("data: "):].strip()

                        if data_str == "[DONE]":
                            got_done_flag = True
                            logger.debug(" 检测到 [DONE] 信号，流式传输结束")
                            break

                        delta_content = parse_stream_chunk(data_str)
                        if delta_content:
                            full_response_text += delta_content
                            yield delta_content

            else:
                # 非流式处理
                response = await client.post(client_settings["base_url"], headers=headers, json=payload)
                if response.status_code != 200:
                    logger.error(f"模型接口返回非200状态码: {response.status_code}")
                    return

                data = response.json()
                # 兼容 OpenAI 风格
                if "choices" in data and data["choices"]:
                    for choice in data["choices"]:
                        # 有些接口可能用 'message' 包含内容
                        text = choice.get("message", {}).get("content") or choice.get("text") or ""
                        full_response_text += text
                    yield full_response_text
                got_done_flag = True

    except httpx.RequestError as e:
        logger.error(f"请求模型接口异常: {e}")

    await asyncio.sleep(0.05)

    if not got_done_flag:
        logger.warning("流式传输未检测到 [DONE]，输出可能不完整")

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
async def auto_fill_initial_story(model_name, system_instructions):
    """仅在历史记录为空时填充初始剧情"""
    # if chat_history.is_empty():
    AUTO_START_MESSAGE = '''
**第2章 救赎与诱惑的开端**
*   **人物**：常亮（留校辅导员）、林洛萱（英语系校花）、吕昊（校内富二代混子）、刘老太（宿管）。
*   **起因**：常亮救下林洛萱后，帮助她清理身体和心理创伤，但视频的秘密让他内心挣扎，产生更深的占有欲。林洛萱对常亮的感激转为依赖。
*   **事件过程**：
    1.  常亮帮林洛萱清洗身体，过程中不经意触碰引发暧昧，她羞涩却未拒绝。
    2.  林洛萱倾诉被吕昊纠缠的往事，常亮安慰她，分享自己的孤独，情感拉近。
    3.  次日，常亮用视频威胁吕昊，让他远离林洛萱，但吕昊暗中调查常亮的秘密。
    4.  林洛萱主动找常亮报恩，邀请他共进晚餐，氛围温馨却暗藏情愫。
    5.  晚上，常亮独处时回放视频，自慰时幻想与林洛萱的亲密，内心冲突加剧。
    6.  刘老太察觉宿舍异常，质问常亮，他巧妙回避，但刘老太起疑。
    7.  林洛萱梦中惊醒，跑到常亮处寻求安慰，两人拥抱，关系升温至纯爱边缘。
*   **结果**：常亮与林洛萱的关系从救赎转为暧昧，他开始计划如何利用视频保护她，同时压制自己的欲望，但吕昊的反扑隐现，埋下冲突种子。
    '''
    logger.info(f"[自动输入] {AUTO_START_MESSAGE}")
    async for text_chunk in execute_model(model_name, AUTO_START_MESSAGE, system_instructions):
        print_model_output_colored(text_chunk, color=Fore.LIGHTBLACK_EX)
    logger.info("\n[生成完成] 初始剧情输出完成")
    # else:
    #     logger.info("[跳过] 历史记录非空，未填充初始剧情")


async def main_loop():
    current_personas = get_default_personas()           # 人物加载
    model_name = await select_model()                   # 模型选择
    system_instructions = get_system_prompt("book")     # 获取默认配置文件
    logger.info(f"[默认出场人物] {current_personas}")

    # 只有历史记录为空才填充初始剧情
    await auto_fill_initial_story(model_name, system_instructions)

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

        async for text_chunk in execute_model(model_name, user_input, system_instructions):
            print_model_output_colored(text_chunk, color=Fore.LIGHTBLACK_EX)
        logger.info("\n[生成完成] 模型回复已输出完成 ")

if __name__ == "__main__":
    asyncio.run(main_loop())
