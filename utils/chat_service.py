# chat_service.py
import asyncio, json, logging, httpx
from fastapi import HTTPException
from config.config import CLIENT_CONFIGS
from config.models import model_registry

# 导入拆分后的通用功能
from utils.chat_utils import (
    logger,
    SUMMARY_THRESHOLD,
    MESSAGE_BUDGET_TOKENS,
    summarize_history_if_needed,
    slice_world_state,
    should_summarize_by_tokens,
    build_messages,
)

# --------- 核心流式聊天（仅保留流输出与最小装配）---------
async def run_model(
    model: str,
    prompt: str,
    system_prompt: str,
    history: list[dict] | None = None,
    memory: str | None = None,
    world_state: dict | None = None
):

    model_config = model_registry(model)
    if not model_config:
        raise HTTPException(status_code=400, detail=f"模型 `{model}` 未注册")
    if not model_config.get("supports_streaming", False):
        raise HTTPException(status_code=400, detail=f"模型 `{model}` 不支持流式返回")
    model_label = model_config.get("label")
    client_key = model_config.get("client_name")
    client_config = CLIENT_CONFIGS.get(client_key)
    if not client_config:
        raise HTTPException(status_code=500, detail=f"未找到接口配置：{client_key}")

    base_url = client_config["base_url"]
    api_key = client_config["api_key"]
    temperature = model_config.get("default_temperature", 0.7)

    url = base_url
    logger.info(f"[call] model: model_label={model_label}, 请求目标: URL={url}, 温度={temperature}")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
    }

    # 业务规则（仍保留在此处，便于按模型或业务定制）
    system_rules = f"""
        {system_prompt}
    """

    turns = history or []

    # 若总体预算超限，强制生成摘要（即使轮数不超）
    world_text_probe = slice_world_state(world_state)  # 先做一次探测，供预算判断与后续复用
    if should_summarize_by_tokens(system_rules, memory, world_text_probe, turns, prompt, MESSAGE_BUDGET_TOKENS):
        memory = summarize_history_if_needed(turns, memory, threshold=0)  # 强制把早期全部压到摘要
        logger.info("[budget] 因总预算超限，已强制摘要压缩早期历史")

    # 计算最终摘要与世界切片
    memory_text = summarize_history_if_needed(turns, memory, threshold=SUMMARY_THRESHOLD)

    world_text = world_text_probe if world_text_probe else slice_world_state(world_state)

    # 组装 messages
    messages = build_messages(
        system_text=system_rules,
        memory_text=memory_text,
        world_text=world_text,
        turns=turns,
        user_text=prompt,
        budget_tokens=MESSAGE_BUDGET_TOKENS,
    )

    data = {
        "model": model_label,
        "messages": messages,
        "stream": True,
        "temperature": min(max(temperature, 0.0), 1.5),
        "max_tokens": 800,
        "top_p": 1.0,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=data, headers=headers) as resp:
                print(f"[chat_service] upstream status={resp.status_code}")

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


from prompt.get_system_prompt import get_system_prompt
from config.models import list_model_ids

async def main():
    models = list_model_ids()
    print("可用模型：")
    for idx, m in enumerate(models, 1):
        print(f"{idx}. {m}")
    while True:
        try:
            choice = int(input("请选择模型编号: "))
            if 1 <= choice <= len(models):
                model = models[choice - 1]
                break
            else:
                print("无效选择，请重新输入。")
        except ValueError:
            print("请输入数字。")
    system_prompt = get_system_prompt("prompt01")
    while True:
        user_prompt = input("\n请输入内容: ")
        async for chunk in run_model(model, user_prompt, system_prompt):
            print(chunk, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
