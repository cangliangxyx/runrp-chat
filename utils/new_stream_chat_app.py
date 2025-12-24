# prompt/stream_chat_app.py

import asyncio
import json
import logging
from typing import AsyncGenerator

import httpx
import tiktoken
from colorama import init

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
MAX_HISTORY_ENTRIES = 1  # 最近几条对话传给模型
SAVE_STORY_SUMMARY_ONLY = True  # 只保存摘要，避免文件太大
# SAVE_STORY_SUMMARY_ONLY = False               # 保存所有内容
DEBUG_STREAM = False  # 是否打印原始流，调试用

# -----------------------------
# 全局 HTTP Client & 并发控制
# -----------------------------
_async_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()
_stream_semaphore = asyncio.Semaphore(2)  # 同时最多 2 个流式请求，防止资源耗尽


def _build_timeout() -> httpx.Timeout:
    return httpx.Timeout(
        connect=10.0,
        read=60.0,
        write=10.0,
        pool=5.0,
    )


async def get_async_client() -> httpx.AsyncClient:
    global _async_client
    async with _client_lock:
        if _async_client is None or _async_client.is_closed:
            _async_client = httpx.AsyncClient(timeout=_build_timeout())
        return _async_client


# -----------------------------
# 工具函数
# -----------------------------
# 使用 tiktoken 计算总 token 数
def total_tokens(messages, model_label: str):
    try:
        encoding = tiktoken.encoding_for_model(model_label)
    except KeyError:
        logger.warning(f"模型 {model_label} 无法自动映射 tokenizer，使用 cl100k_base 估算")
        encoding = tiktoken.get_encoding("cl100k_base")

    total = sum(len(encoding.encode(msg.get("content", ""))) for msg in messages)
    logger.info(f"[Token统计] messages 总 token 数(估算): {total}")
    return total

# -----------------------------
# 统一的流解析函数
# -----------------------------
def parse_stream_chunk(data_str: str) -> str | None:
    """
    兼容 OpenAI / Gemini / 其他流式返回格式，解析内容片段1
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
        stream: bool = False,
) -> AsyncGenerator[dict, None]:
    """
    高稳定性 / 高效率模型调用器
    - 支持流式 & 非流式
    - 全局 AsyncClient 复用
    - DONE / 非 DONE 双兜底
    - 并发流式限流
    - 不阻塞 event loop
    """

    logger.info(f"[执行模型] model={model_name} stream={stream} nsfw={nsfw}")
    # ---------- 构建 messages ----------
    messages = build_messages(
        system_instructions,
        personas,
        chat_history,
        user_input,
        web_input,
        nsfw=nsfw,
        max_history_entries=MAX_HISTORY_ENTRIES,
    )
    if DEBUG_STREAM:
        print_messages_colored(messages)
    model_details = model_registry(model_name)
    client_settings = CLIENT_CONFIGS[model_details["client_name"]]
    payload = {
        "model": model_details["label"],
        "stream": stream,
        "messages": messages,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {client_settings['api_key']}",
    }
    chunks: list[str] = []

    # total_tokens
    total_tokens(messages, model_details["label"])

    try:
        client = await get_async_client()
        # ---------- 流式模式 ----------
        if stream:
            async with _stream_semaphore:
                async with client.stream(
                        "POST",
                        client_settings["base_url"],
                        headers=headers,
                        json=payload,
                ) as response:
                    if response.status_code != 200:
                        yield {
                            "type": "error",
                            "error": f"模型接口返回状态码 {response.status_code}",
                        }
                        return
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        delta = parse_stream_chunk(data_str)
                        if not delta:
                            continue
                        chunks.append(delta)
                        yield {"type": "chunk", "content": delta}
            # 流自然结束（即使无 DONE）
            full_text = "".join(chunks)
        # ---------- 非流式模式 ----------
        else:
            response = await client.post(
                client_settings["base_url"],
                headers=headers,
                json=payload,
            )
            if response.status_code != 200:
                yield {
                    "type": "error",
                    "error": f"模型接口返回状态码 {response.status_code}",
                }
                return
            data = response.json()
            if "choices" in data:
                for choice in data["choices"]:
                    text = (
                            choice.get("message", {}).get("content")
                            or choice.get("text")
                            or ""
                    )
                    if text:
                        chunks.append(text)
                        yield {"type": "chunk", "content": text}
            full_text = "".join(chunks)
    except httpx.TimeoutException:
        yield {"type": "error", "error": "模型请求超时"}
        return
    except httpx.RequestError as e:
        yield {"type": "error", "error": f"模型请求异常: {e}"}
        return
    except Exception as e:
        logger.exception("模型调用异常")
        yield {"type": "error", "error": str(e)}
        return
    # ---------- 保存历史 ----------
    if full_text.strip():
        if SAVE_STORY_SUMMARY_ONLY:
            summary = chat_history._extract_summary_from_assistant(full_text)
            if summary:
                chat_history.add_entry(user_input, summary)
        else:
            chat_history.add_entry(user_input, full_text)
        chat_history.save_history()
    yield {"type": "end", "full": full_text}


async def test_stream():
    model_name = "gpt-5.2-thinking"
    user_input = "请用告诉我现在使用的模型版本、功能特色、发布日期等关键信息"
    system_instructions = "你是一个系统工程师"
    personas = [""]

    buffer = ""
    async for chunk in execute_model_for_app(
            model_name, user_input, system_instructions, personas, stream=True
    ):
        if chunk["type"] == "chunk":
            buffer += chunk["content"]
            for char in buffer:
                if char == "\n":
                    print()
                else:
                    print(char, end="", flush=True)
            buffer = ""
    # print()


if __name__ == "__main__":
    asyncio.run(test_stream())

    # messages = [{"content": "123123"}]
    # model_label = "gemini-3-pro-preview-thinking-*"
    # total_tokens(messages, model_label)
