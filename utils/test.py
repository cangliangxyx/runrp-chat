import httpx
import json
import datetime
import asyncio
import re
from config.config import CLIENT_CONFIGS
from config.models import model_registry
from utils.chat_utils import logger

class ChatHistory:
    """管理聊天历史摘要"""
    # 改成更宽松的正则，适应模型生成格式
    TIMESTAMP_PATTERN = re.compile(r"##[\d\- :]+##([\s\S]+)")

    def __init__(self, max_entries: int = 10):
        self._entries = []
        self.max_entries = max_entries

    def add(self, summary: str):
        self._entries.append(summary)
        # 限制历史长度
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]

    def format(self) -> str:
        if not self._entries:
            return "无历史记录。"
        formatted = []
        for idx, entry in enumerate(self._entries, 1):
            formatted.append(f"{idx}. {entry.strip()}")
        return "\n".join(formatted)


history = ChatHistory(max_entries=5)  # 保留最近 5 条摘要


async def run_model(model: str, user_prompt: str, system_prompt: str):
    """调用指定模型，流式返回生成内容，增加健壮性"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    model_config = model_registry(model)
    client_key = model_config.get("client_name")
    client_config = CLIENT_CONFIGS[client_key]

    base_url = client_config["base_url"]
    api_key = client_config["api_key"]
    model_label = model_config.get("label")

    logger.info(f"[call] model: {model_label}, 请求目标: {base_url}")

    # 系统提示中要求生成摘要
    system_rules = f"""
        {system_prompt}
        对话结束后，请生成对话摘要，格式如下：
        ##{current_time}##
        <最近对话摘要>
    """

    # 仅使用最近几条摘要，避免过长
    last_summaries = "\n".join(history._entries[-5:])
    user_prompt_full = f"历史记录:\n{last_summaries}\n用户输入:{user_prompt}"

    payload = {
        "model": model_label,
        "stream": True,
        "messages": [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": user_prompt_full},
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    full_text = ""

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", base_url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                payload_line = line[len("data: "):]
                if payload_line == "[DONE]":
                    break

                try:
                    chunk = json.loads(payload_line)
                    choices = chunk.get("choices", [])
                    if not choices or "delta" not in choices[0]:
                        continue  # 忽略空 chunk

                    delta_content = choices[0].get("delta", {}).get("content")
                    if delta_content:
                        full_text += delta_content
                        yield delta_content
                except json.JSONDecodeError:
                    logger.warning(f"无法解析: {payload_line}")
                except Exception as e:
                    logger.error(f"处理流 chunk 出错: {e}")

    # 提取并保存摘要
    match = ChatHistory.TIMESTAMP_PATTERN.search(full_text)
    if match:
        summary_text = match.group(0).strip()
        history.add(summary_text)
        logger.info(f"保存摘要: {summary_text}")

from prompt.get_system_prompt import get_system_prompt

async def main():
    model = "gpt-5-mini"
    system_prompt = get_system_prompt("prompt02")  # 默认使用 default
    while True:
        user_prompt = input("\n请输入内容: ")
        async for chunk in run_model(model, user_prompt, system_prompt):
            print(chunk, end="", flush=True)
        print("\n历史摘要：")
        print(history.format())

if __name__ == "__main__":
    asyncio.run(main())
