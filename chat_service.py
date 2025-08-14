# chat_service.py
import asyncio, json, logging, httpx
from fastapi import HTTPException
from config.config import CLIENT_CONFIGS
from config.models import model_registry

logger = logging.getLogger(__name__)


async def stream_chat(model: str, prompt: str):
    """
    流式聊天生成器，yield 每个内容片段供 FastAPI StreamingResponse 使用
    """
    model_config = model_registry(model)
    if not model_config:
        raise HTTPException(status_code=400, detail=f"模型 `{model}` 未注册")
    if not model_config.get("supports_streaming", False):
        raise HTTPException(status_code=400, detail=f"模型 `{model}` 不支持流式返回")
    client_key = model_config.get("client_key")
    client_config = CLIENT_CONFIGS.get(client_key)
    if not client_config:
        raise HTTPException(status_code=500, detail=f"未找到接口配置：{client_key}")

    base_url = client_config["base_url"]
    api_key = client_config["api_key"]
    temperature = model_config.get("default_temperature", 0.7)

    url = base_url
    logger.info(f"调用模型: {model} | URL: {url} | 温度: {temperature}")

    # 确保 Authorization 头格式正确
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # 打印请求头用于调试（注意：生产环境中应移除此日志）
    logger.info(f"请求头: {headers}")

    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "temperature": temperature,
    }

    # print(json.dumps(data, ensure_ascii=False, indent=2))

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=data, headers=headers) as resp:
                logger.info(f"响应状态码: {resp.status_code}")

                if resp.status_code != 200:
                    error_text = await resp.aread()
                    error_msg = error_text.decode('utf-8', errors='ignore')
                    logger.error(f"API 错误 {resp.status_code}: {error_msg}")
                    yield f"[API 错误 {resp.status_code}] {error_msg}"
                    return

                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk.strip() == "[DONE]":
                            break
                        try:
                            parsed = json.loads(chunk)
                            if "choices" in parsed and len(parsed["choices"]) > 0:
                                delta = parsed["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError as e:
                            # 跳过无效的 JSON，这在流式响应中很常见
                            continue
                        except (KeyError, IndexError) as e:
                            logger.warning(f"响应结构异常: {e}")
                            continue

    except Exception as e:
        logger.error(f"请求异常: {e}")
        yield f"[请求错误] {str(e)}"


if __name__ == "__main__":
    async def test():
        print("开始测试...")
        async for chunk in stream_chat("gpt-5-mini", "你好，请简单说一句话"):
            print(chunk, end="", flush=True)
        print("\n测试完成")
    asyncio.run(test())