# chat_service.py
import json, datetime, requests
from config.config import CLIENT_CONFIGS
from config.models import model_registry

from utils.chat_utils import (
    logger
)

current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# chat_service.py
import json, datetime, requests
from config.config import CLIENT_CONFIGS
from config.models import model_registry
from utils.chat_utils import logger

current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def test(model, prompt):
    model_config = model_registry(model)
    client_key = model_config.get("client_name")
    client_config = CLIENT_CONFIGS.get(client_key)
    base_url = client_config["base_url"]
    api_key = client_config["api_key"]
    model_label = model_config.get("label")
    logger.info(f"[call] model: model_label={model_label}, 请求目标: URL={base_url}")

    system_rules = (
        f"""你是我的开发助手,输出语言:简体中文普通话
        对话结束生成简短对话摘要格式如下：
        ##{current_time}##
        对话摘要
        """
    )
    messages = [
        {"role": "system", "content": system_rules},
        {"role": "user", "content": prompt}
    ]
    data = {
        "model": model_label,
        "stream": True,
        "messages": messages
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    def event_stream():
        with requests.post(base_url, headers=headers, json=data, stream=True) as response:
            response.encoding = "utf-8"
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    if line.startswith("data: "):
                        payload = line[len("data: "):]
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                            delta = chunk["choices"][0]["delta"].get("content")
                            if delta:
                                # 不再 print，而是 yield 给 StreamingResponse
                                yield delta
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析: {payload}")
            # 结尾加一个换行，避免前端流式显示不完整
            yield "\n"

    return event_stream()

if __name__ == "__main__":
    test("gpt-5-mini","你好")