# chat_service.py
import asyncio, json, logging, httpx, os, math
from fastapi import HTTPException
from config.config import CLIENT_CONFIGS
from config.models import model_registry

# --------- 可靠日志配置（模块级生效）---------
logger = logging.getLogger("chat_service")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False  # 避免重复打印

# --------- 可配置常量（支持环境变量覆盖）---------
def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default

def _env_float(name: str, default: float) -> float:
    v = os.environ.get(name)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError:
        return default

# 超过多少轮开始做“历史摘要”
SUMMARY_THRESHOLD = _env_int("SUMMARY_THRESHOLD", 12)

# 本次请求可用于上下文的粗略 token 预算（不含模型生成部分）
MESSAGE_BUDGET_TOKENS = _env_int("MESSAGE_BUDGET_TOKENS", 3000)

# 为本轮用户输入与余量预留的 token（固定余量，用于安全边界）
USER_RESERVE_TOKENS = _env_int("USER_RESERVE_TOKENS", 128)

# 历史窗口最小预算下限（防止历史完全装不进去）
MIN_HISTORY_BUDGET_TOKENS = _env_int("MIN_HISTORY_BUDGET_TOKENS", 512)

# 关键：中文保守估算，默认 1 char ≈ 1 token；可按实际模型调整（如 0.6/0.75）
APPROX_TOKENS_PER_CHAR = _env_float("APPROX_TOKENS_PER_CHAR", 1.0)

# 单条消息上限，避免一条撑爆预算
MAX_SINGLE_MESSAGE_TOKENS = _env_int("MAX_SINGLE_MESSAGE_TOKENS", 600)

# --------- 辅助预览 ---------
def _preview_text(text: str, limit: int = 200) -> str:
    if text is None:
        return "None"
    t = str(text)
    return t if len(t) <= limit else t[:limit] + "...(truncated)"

def _preview_list(items, limit_items: int = 3, limit_chars: int = 120):
    if not items:
        return "[]"
    sample = items[:limit_items]
    pretty = []
    for it in sample:
        s = str(it)
        pretty.append(s if len(s) <= limit_chars else s[:limit_chars] + "...(truncated)")
    more = "" if len(items) <= limit_items else f" +{len(items) - limit_items} more"
    return "[\n  " + ",\n  ".join(pretty) + f"\n]{more}"

# --------- 估算与裁剪 ---------
def approx_tokens(text: str) -> int:
    if not text:
        return 1
    # 保守估算：按 CJK 1char≈1token，避免低估导致超预算
    return max(1, math.ceil(len(text) * APPROX_TOKENS_PER_CHAR))

def prune_message_to_tokens(text: str, max_tokens: int) -> str:
    """将超长文本按 token 上限做安全截断：头尾保留，插入省略标记。"""
    if approx_tokens(text) <= max_tokens:
        return text
    # 粗略按字符截断（因 1char≈1token）
    max_chars = max_tokens
    if len(text) <= max_chars:
        return text
    head = text[: max(int(max_chars * 0.6), 1)]
    tail = text[-max(int(max_chars * 0.3), 1):]
    return head + "\n…(内容过长，已截断)…\n" + tail

# --------- 摘要与世界状态 ---------
def summarize_history_if_needed(turns: list[dict], summary: str | None, threshold: int | None = None) -> str | None:
    """
    当轮次超过阈值时，生成/更新一个简短摘要（示例用规则拼接要点；生产建议调用模型生成更优摘要）
    threshold: 允许临时覆盖，默认取 SUMMARY_THRESHOLD
    """
    th = threshold if isinstance(threshold, int) else SUMMARY_THRESHOLD
    total = len(turns) if turns else 0
    logger.info(f"[summary] turns_total={total}, threshold={th}")
    if not turns or total <= th:
        logger.info("[summary] 未超过阈值，沿用现有摘要")
        if summary:
            logger.info(f"[summary] 现有摘要预览: { _preview_text(summary, 160) }")
        return summary

    old_part = turns[:-th]
    logger.info(f"[summary] 需要压缩的早期轮次数量: {len(old_part)}")

    key_points = []
    for msg in old_part:
        role = "U" if msg.get("role") == "user" else "A"
        text = (msg.get("content") or "").replace("\n", " ").strip()
        if text:
            key_points.append(f"{role}: {text[:100]}")

    if not key_points:
        logger.info("[summary] 早期轮次无有效文本，保持原摘要")
        return summary

    logger.info(f"[summary] key_points 采样: { _preview_list(key_points, limit_items=3, limit_chars=100) }")
    condensed = "要点（历史摘要）:\n- " + "\n- ".join(key_points[:12])
    logger.info(f"[summary] 生成摘要长度: {len(condensed)}")
    logger.info(f"[summary] 摘要预览: { _preview_text(condensed, 200) }")
    return condensed

def slice_world_state(world_state: dict | None) -> str | None:
    """
    从 world_state 中提取与本轮相关的简短片段（示例：直接精简字段；可按需定制）
    """
    if not isinstance(world_state, dict):
        logger.info("[world] 无有效世界状态，跳过切片")
        return None
    keys = ["scene", "location", "time", "weather", "inventory", "quests", "flags"]
    data = {k: world_state.get(k) for k in keys if k in world_state}
    if not data:
        logger.info("[world] 世界状态为空或无关键字段，跳过切片")
        return None
    try:
        text = json.dumps(data, ensure_ascii=False)
    except Exception:
        text = str(data)
    sliced = f"[World State]\n{text}"
    logger.info(f"[world] 切片预览: { _preview_text(sliced, 200) }")
    return sliced

# --------- 预算判断与历史选择 ---------
def should_summarize_by_tokens(system_text: str, memory_text: str | None, world_text: str | None, turns: list[dict], user_text: str, budget_tokens: int) -> bool:
    """即使轮数未超，只要总预算超限也触发摘要。"""
    head = [t for t in [system_text, memory_text, world_text] if t]
    used = sum(approx_tokens(x) for x in head) + approx_tokens(user_text) + USER_RESERVE_TOKENS
    turns_tokens = sum(approx_tokens(m.get("content") or "") for m in (turns or []))
    total_est = used + turns_tokens
    logger.info(f"[budget] 总体估算: head+user={used}, turns={turns_tokens}, total={total_est}, budget={budget_tokens}")
    return total_est > budget_tokens

def select_recent_by_budget(turns: list[dict], budget_left: int) -> list[dict]:
    """
    从最近往前选入历史，若单条超过 MAX_SINGLE_MESSAGE_TOKENS 则先截断，再判断是否可纳入。
    """
    recent: list[dict] = []
    if not isinstance(turns, list):
        return recent
    for msg in reversed(turns):
        role = msg.get("role", "user")
        content = msg.get("content", "") or ""
        # 单条硬上限，避免撑爆
        content = prune_message_to_tokens(content, MAX_SINGLE_MESSAGE_TOKENS)
        t = approx_tokens(content)
        if t <= budget_left:
            recent.insert(0, {"role": role, "content": content})
            budget_left -= t
        else:
            # 如果还没选任何一条，尝试再缩一轮（更小阈值），确保至少能塞进一点
            if not recent and budget_left > 50:
                shrink = prune_message_to_tokens(content, max(budget_left, 50))
                if approx_tokens(shrink) <= budget_left:
                    recent.insert(0, {"role": role, "content": shrink})
                    budget_left = 0
            break
    return recent

# --------- 消息组装 ---------
def build_messages(
    system_text: str,
    memory_text: str | None,
    world_text: str | None,
    turns: list[dict],
    user_text: str,
    budget_tokens: int | None = None,
):
    """
    组装 messages：system -> memory -> world -> 最近若干轮 -> 当前用户
    严格控制预算，优先保留前置信息与最近轮次
    """
    budget = budget_tokens if isinstance(budget_tokens, int) else MESSAGE_BUDGET_TOKENS

    # 头部（system/memory/world）
    messages: list[dict] = []
    head_texts = []
    if system_text:
        messages.append({"role": "system", "content": system_text}); head_texts.append(system_text)
    if memory_text:
        messages.append({"role": "system", "content": f"{memory_text}"}); head_texts.append(memory_text)
    if world_text:
        messages.append({"role": "system", "content": f"{world_text}"}); head_texts.append(world_text)

    head_used = sum(approx_tokens(x) for x in head_texts)
    user_reserve = approx_tokens(user_text) + USER_RESERVE_TOKENS
    history_budget = max(MIN_HISTORY_BUDGET_TOKENS, budget - head_used - user_reserve)

    logger.info(f"[messages] 预算汇总: budget={budget}, head_used={head_used}, user_reserve={user_reserve}, history_budget={history_budget}")

    # 选择历史
    recent = select_recent_by_budget(turns or [], history_budget)
    messages.extend(recent)

    # 末尾追加当前用户
    messages.append({"role": "user", "content": user_text})

    # 统计估算
    total_est = sum(approx_tokens(m["content"]) for m in messages)
    logger.info(f"[messages] 装配完成: 总条数={len(messages)}, 估算total_tokens={total_est}")
    logger.info(f"[messages] recent 采样: { _preview_list([f'{m['role']}: {m['content']}' for m in recent], 3, 120) }")
    return messages

# --------- 核心流式聊天 ---------
async def stream_chat(
    model: str,
    prompt: str,
    history: list[dict] | None = None,
    memory: str | None = None,
    world_state: dict | None = None,
    conversation_id: str | None = None,
):
    logger.info(f"[call] stream_chat called | model={model} | prompt_preview={_preview_text(prompt, 80)} | conv={conversation_id or '-'}")
    print(f"[chat_service] stream_chat start, model={model}, conv={conversation_id or '-'}")

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
    logger.info(f"[call] 请求目标: URL={url}, 温度={temperature}")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
    }

    system_rules = (
        "你是对话式爱情故事的叙事引擎，以第三人称视角来叙述故事"
        "当用户或历史与世界状态冲突时，以世界状态为准并温和纠正"
        "输出语言中文普通话。"
        "男主:常亮"
        "女性角色:张静（常亮的女友）"
    )

    turns = history or []

    # 若总体预算超限，强制生成摘要（即使轮数不超）
    world_text_probe = slice_world_state(world_state)  # 先做一次探测，供预算判断与后续复用
    if should_summarize_by_tokens(system_rules, memory, world_text_probe, turns, prompt, MESSAGE_BUDGET_TOKENS):
        memory = summarize_history_if_needed(turns, memory, threshold=0)  # 强制把早期全部压到摘要
        logger.info("[budget] 因总预算超限，已强制摘要压缩早期历史")

    # 计算最终摘要与世界切片
    memory_text = summarize_history_if_needed(turns, memory, threshold=SUMMARY_THRESHOLD)
    if memory_text:
        logger.info(f"[call] 使用摘要: {_preview_text(memory_text, 200)}")
    else:
        logger.info("[call] 无摘要或未触发生成")

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
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": min(max(temperature, 0.0), 1.5),
        "max_tokens": 800,
        "top_p": 1.0,
    }

    # 请求体简要预览（头尾）
    try:
        preview = {
            "model": data["model"],
            "stream": data["stream"],
            "temperature": data["temperature"],
            "messages_head": messages[:2],
            "messages_tail": messages[-2:],
        }
        logger.info("请求体简要预览:\n" + json.dumps(preview, ensure_ascii=False, indent=2))
    except Exception:
        logger.info("请求体预览生成失败（可能含不可序列化对象）")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=data, headers=headers) as resp:
                logger.info(f"[http] 上游状态码: {resp.status_code}")
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
                            logger.info("[http] 收到 [DONE]")
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
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    async def test():
        print("开始测试...")
        demo_history = [
            {"role": "user", "content": "下班回家后看见女友梁红在厨房忙碌。"},
            {"role": "assistant", "content": "夜幕将至"}
        ]
        demo_world = {"scene": "forest_camp", "time": "dusk", "weather": "cloudy", "inventory": ["厨房"],
                      "quests": {"main": "下班回家"}, "flags": {"met_ranger": True}}
        async for chunk in stream_chat("deepseek-chat", "慢慢走过去从后面抱住梁红的腰", history=demo_history, world_state=demo_world, conversation_id="conv_demo"):
            print(chunk, end="", flush=True)
        print("\n测试完成")
    asyncio.run(test())
