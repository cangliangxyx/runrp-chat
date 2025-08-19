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
    TIMESTAMP_PATTERN = re.compile(r"(##\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}##)([\s\S]+)")

    def __init__(self):
        self._entries = []

    def add(self, summary: str):
        self._entries.append(summary)

    def format(self) -> str:
        if not self._entries:
            return "无历史记录。"

        formatted = []
        for idx, entry in enumerate(self._entries, 1):
            match = self.TIMESTAMP_PATTERN.match(entry)
            if match:
                timestamp, content = match.groups()
                formatted.append(f"{idx}. {timestamp} {content.strip()}")
            else:
                formatted.append(f"{idx}. {entry}")
        return "\n".join(formatted)

history = ChatHistory()

async def run_model(model: str, user_prompt: str, system_prompt):
    """调用指定模型，流式返回生成内容"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    model_config = model_registry(model)
    client_key = model_config.get("client_name")
    client_config = CLIENT_CONFIGS[client_key]

    base_url = client_config["base_url"]
    api_key = client_config["api_key"]
    model_label = model_config.get("label")

    logger.info(f"[call] model: {model_label}, 请求目标: {base_url}")

    system_rules = f"""
        {system_prompt}
        对话结束后，请生成对话摘要，格式如下：
        ##{current_time}##
        <最近对话摘要>
        """
    user_prompt = f"历史记录:{history.format()}\n用户输入:{user_prompt}"
    payload = {
        "model": model_label,
        "stream": True,
        "messages": [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": user_prompt},
        ],
    }
    print(payload)
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

                payload = line[len("data: "):]
                if payload == "[DONE]":
                    break

                try:
                    chunk = json.loads(payload)
                    delta = chunk["choices"][0]["delta"].get("content")
                    if delta:
                        full_text += delta
                        yield delta  # 流式输出
                except json.JSONDecodeError:
                    logger.warning(f"无法解析: {payload}")

    match = ChatHistory.TIMESTAMP_PATTERN.search(full_text)
    if match:
        history.add(match.group(0).strip())

from prompt.get_system_prompt import get_system_prompt

async def main():
    model = "gpt-5-mini"
    system_prompt = get_system_prompt("prompt01")  # 默认使用 default
    while True:
        user_prompt = input("\n请输入内容: ")
        async for chunk in run_model(model, user_prompt, system_prompt):
            print(chunk, end="")
        print("\n")
        print("历史摘要：")
        print(history.format())

if __name__ == "__main__":
    asyncio.run(main())
