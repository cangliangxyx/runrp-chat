# chat_service.py
import asyncio, json, httpx, datetime
from fastapi import HTTPException
from config.config import CLIENT_CONFIGS
from config.models import model_registry


# 导入拆分后的通用功能
from utils.chat_utils import (
    logger
)

# 获取当前时间并格式化为时分秒
current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# --------- 核心流式聊天（仅保留流输出与最小装配）---------
async def stream_chat(model: str,prompt: str):
    model_config = model_registry(model)
    client_key = model_config.get("client_name")
    client_config = CLIENT_CONFIGS.get(client_key)
    base_url = client_config["base_url"]
    api_key = client_config["api_key"]

    if not model_config:
        raise HTTPException(status_code=400, detail=f"模型 `{model}` 未注册")
    if not model_config.get("supports_streaming", False):
        raise HTTPException(status_code=400, detail=f"模型 `{model}` 不支持流式返回")
    model_label = model_config.get("label")
    temperature = model_config.get("default_temperature", 0.7)
    stream = model_config.get('supports_streaming')

    logger.info(f"[call] model: model_label={model_label}, 请求目标: URL={base_url}, 温度={temperature}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # 业务规则（仍保留在此处，便于按模型或业务定制）
    system_rules = (
        f"""
        你是我的开发助手
        输出语言:简体中文普通话
        对话结束生成简短对话摘要格式如下：
        ##{current_time}##
        对话摘要
        """
    )

    # 组装 messages
    messages = [
        {"role": "system", "content": system_rules},
        {"role": "user", "content": prompt}
    ]

    data = {
        "model": model_label,
        "messages": messages,
        "stream": stream,
        "temperature": temperature,
        "max_tokens": 800,
        "top_p": 1.0,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", base_url, json=data, headers=headers) as resp:
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    error_msg = error_text.decode('utf-8', errors='ignore')
                    logger.error(f"[http] 错误 {resp.status_code}: {error_msg}")
                    yield f"[API 错误 {resp.status_code}] {error_msg}"
                    return

                # 解析 SSE 流
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk.strip() == "[DONE]":
                            break
                        try:
                            parsed = json.loads(chunk)
                            if "choices" in parsed and parsed["choices"]:
                                delta = parsed["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            # 心跳或非 JSON 片段，忽略
                            continue

    except Exception as e:
        logger.error(f"[http] 请求异常: {e}")
        yield f"[请求错误] {str(e)}"

if __name__ == "__main__":
    async def test():
        async for chunk in stream_chat("claude-sonnet-4", "你好，我使用的模型版本是多少"):
            print(chunk, end="", flush=True)
    asyncio.run(test())
