# prompt/stream_chat_app.py

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
MAX_HISTORY_ENTRIES = 1                     # 最近几条对话传给模型
SAVE_STORY_SUMMARY_ONLY = True              # 只保存摘要，避免文件太大
DEBUG_STREAM = False                        # 是否打印原始流，调试用


# -----------------------------
# 统一的流解析函数
# -----------------------------
def parse_stream_chunk(data_str: str) -> str | None:
    """
    兼容 OpenAI / Gemini / 其他流式返回格式，解析内容片段1
    """
    try:
        chunk = json.loads(data_str)

        # ✅ OpenAI 风格
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

        # ✅ Gemini 风格
        elif "candidates" in chunk:
            candidates = chunk.get("candidates", [])
            if not isinstance(candidates, list) or len(candidates) == 0:
                logger.debug(f"[空 candidates] {chunk}")
                return None

            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts if "text" in p)

        # 其他未知结构
        logger.debug(f"[未知结构] {chunk}")
        return None

    except json.JSONDecodeError:
        logger.warning(f"无效 JSON: {data_str}")
        return None
    except Exception as e:
        logger.warning(f"[parse_stream_chunk 异常] {e} - 原始数据: {data_str}")
        return None


# -----------------------------
# 流式调用模型（结构化输出 + 异常处理细分）
# -----------------------------
async def execute_model_for_app(
    model_name: str,
    user_input: str,
    system_instructions: str,
    personas: list[str],
    web_input: str = "",
    nsfw: bool = True,
) -> AsyncGenerator[dict, None]:
    """
    调用模型并流式返回
    每次 yield 一个 dict，包含：
    { "type": "chunk", "content": "文本片段" }
    { "type": "end", "full": "完整回复" }
    { "type": "error", "error": "错误描述" }
    """

    logger.info(f"[执行模型] nsfw={nsfw}")

    # 构建 messages
    messages = build_messages(
        system_instructions,
        personas,
        chat_history,
        user_input,
        web_input,
        nsfw=nsfw,
        max_history_entries=MAX_HISTORY_ENTRIES,
    )
    print_messages_colored(messages)

    # 模型配置
    model_details = model_registry(model_name)
    client_settings = CLIENT_CONFIGS[model_details["client_name"]]
    payload = {"model": model_details["label"], "stream": True, "messages": messages}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {client_settings['api_key']}"}

    chunks = []

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", client_settings["base_url"], headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_msg = f"模型接口返回非200状态码: {response.status_code}"
                    logger.error(error_msg)
                    yield {"type": "error", "error": error_msg}
                    return

                async for line in response.aiter_lines():
                    if not (line and line.startswith("data: ")):
                        continue
                    data_str = line[6:].strip()

                    if DEBUG_STREAM:
                        print(f"[DEBUG] 原始流: {data_str}")

                    # ✅ 结束标记
                    if data_str.strip() in ("[DONE]", ""):
                        break

                    # ✅ 调用统一解析器
                    delta_content = parse_stream_chunk(data_str)
                    if delta_content:
                        chunks.append(delta_content)
                        yield {"type": "chunk", "content": delta_content}

    except httpx.TimeoutException:
        error_msg = "[网络超时] 模型接口未响应"
        logger.error(error_msg)
        yield {"type": "error", "error": error_msg}
        return
    except httpx.ConnectError:
        error_msg = "[连接失败] 无法连接到模型接口"
        logger.error(error_msg)
        yield {"type": "error", "error": error_msg}
        return
    except httpx.RequestError as e:
        error_msg = f"[请求错误] {e}"
        logger.error(error_msg)
        yield {"type": "error", "error": error_msg}
        return
    except Exception as e:
        error_msg = f"[未知错误] {e}"
        logger.exception(error_msg)
        yield {"type": "error", "error": error_msg}
        return

    # 保存历史
    full_response_text = "".join(chunks)
    if full_response_text.strip():
        if SAVE_STORY_SUMMARY_ONLY:
            summary = chat_history._extract_summary_from_assistant(full_response_text)
            if summary:
                chat_history.add_entry(user_input, summary)
        else:
            chat_history.add_entry(user_input, full_response_text)
        chat_history.save_history()

    # ✅ 输出最终完整内容
    yield {"type": "end", "full": full_response_text}
