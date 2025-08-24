# chat_utils.py
"""
对话上下文装配与开销控制工具集。

职责
- 读取环境配置（阈值/预算等），并暴露模块级常量
- 提供日志与调试预览工具
- 提供 token 估算、文本裁剪
- 提供历史摘要与世界状态切片
- 提供是否需要摘要的预算判断
- 提供消息装配（system/memory/world/recent/user）

注意
- 保持与 chat_service 的兼容：导出同名符号
"""

from __future__ import annotations

import json
import logging
import math
import os
from typing import List, Dict, Optional, TypedDict


# ============================== 日志与配置 ==============================

def _build_logger(name: str = "chat_service") -> logging.Logger:
    """构建模块级 logger，避免重复添加 handler。"""
    lg = logging.getLogger(name)
    if not lg.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        lg.addHandler(handler)
    # 通过环境变量控制日志级别（默认 INFO）
    level_name = os.getenv("CHAT_LOG_LEVEL", "INFO").upper()
    lg.setLevel(getattr(logging, level_name, logging.INFO))
    lg.propagate = False
    return lg



logger = _build_logger()


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    v = os.environ.get(name)
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ============================== 常量（可被环境变量覆盖） ==============================

# 超过多少轮开始做“历史摘要”
SUMMARY_THRESHOLD: int = _env_int("SUMMARY_THRESHOLD", 10)

# 本次请求可用于上下文的粗略 token 预算（不含模型生成部分）
MESSAGE_BUDGET_TOKENS: int = _env_int("MESSAGE_BUDGET_TOKENS", 3000)

# 为本轮用户输入与余量预留的 token（固定余量，用于安全边界）
USER_RESERVE_TOKENS: int = _env_int("USER_RESERVE_TOKENS", 128)

# 历史窗口最小预算下限（防止历史完全装不进去）
MIN_HISTORY_BUDGET_TOKENS: int = _env_int("MIN_HISTORY_BUDGET_TOKENS", 512)

# 关键：中文保守估算，默认 1 char ≈ 1 token；可按实际模型调整（如 0.6/0.75）
APPROX_TOKENS_PER_CHAR: float = _env_float("APPROX_TOKENS_PER_CHAR", 1.0)

# 单条消息上限，避免一条撑爆预算
MAX_SINGLE_MESSAGE_TOKENS: int = _env_int("MAX_SINGLE_MESSAGE_TOKENS", 600)


# ============================== 类型定义 ==============================

class Message(TypedDict):
    role: str
    content: str


# ============================== 调试预览工具 ==============================

def _preview_text(text: Optional[str], limit: int = 200) -> str:
    """返回截断后的文本预览，避免日志过长。"""
    if text is None:
        return "None"
    t = str(text)
    return t if len(t) <= limit else f"{t[:limit]}...(truncated)"


def _preview_list(items, limit_items: int = 3, limit_chars: int = 120) -> str:
    """列表预览：最多展示 limit_items 项，每项最多 limit_chars 字符。"""
    if not items:
        return "[]"
    sample = items[:limit_items]
    pretty = []
    for it in sample:
        s = str(it)
        pretty.append(s if len(s) <= limit_chars else f"{s[:limit_chars]}...(truncated)")
    more = "" if len(items) <= limit_items else f" +{len(items) - limit_items} more"
    return "[\n  " + ",\n  ".join(pretty) + f"\n]{more}"


def _safe_json(obj) -> str:
    """将对象转为 JSON 字符串用于日志预览，失败则回退为 str。"""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


# ============================== 估算与裁剪 ==============================

def approx_tokens(text: str) -> int:
    """粗略估算 token 数：默认 1 汉字≈1 token。"""
    if not text:
        return 1
    return max(1, math.ceil(len(text) * APPROX_TOKENS_PER_CHAR))


def prune_message_to_tokens(text: str, max_tokens: int) -> str:
    """
    将超长文本按 token 上限做安全截断：头部与尾部保留，中间以提示替代。
    近似按字符数处理（与 approx_tokens 假设一致）。
    """
    if approx_tokens(text) <= max_tokens:
        return text

    # 粗略按字符截断（因 1char≈1token）
    max_chars = max(1, max_tokens)
    if len(text) <= max_chars:
        return text

    head_len = max(1, int(max_chars * 0.6))
    tail_len = max(1, int(max_chars * 0.3))
    head = text[:head_len]
    tail = text[-tail_len:]
    return f"{head}\n…(内容过长，已截断)…\n{tail}"


# ============================== 摘要与世界状态 ==============================

def summarize_history_if_needed(
    turns: List[Dict],
    summary: Optional[str],
    threshold: Optional[int] = None
) -> Optional[str]:
    th = threshold if isinstance(threshold, int) else SUMMARY_THRESHOLD
    total = len(turns) if turns else 0
    logger.info(f"[summary] turns_total={total}, threshold={th}")

    if not turns or total <= th:
        logger.info("[summary] 未超过阈值，沿用现有摘要")
        if summary:
            logger.debug(f"[summary] 现有摘要预览: {_preview_text(summary, 160)}")
        return summary

    old_part = turns[:-th]
    logger.info(f"[summary] 需要压缩的早期轮次数量: {len(old_part)}")

    key_points: List[str] = []
    for msg in old_part:
        role = "U" if msg.get("role") == "user" else "A"
        text = (msg.get("content") or "").replace("\n", " ").strip()
        if text:
            key_points.append(f"{role}: {text[:100]}")

    if not key_points:
        logger.info("[summary] 早期轮次无有效文本，保持原摘要")
        return summary

    # 细节日志改为 DEBUG，调试时再开启
    logger.debug(f"[summary] key_points 采样: {_preview_list(key_points, limit_items=3, limit_chars=100)}")
    condensed = "要点（历史摘要）:\n- " + "\n- ".join(key_points[:12])
    logger.debug(f"[summary] 生成摘要长度: {len(condensed)}")
    logger.debug(f"[summary] 摘要预览: {_preview_text(condensed, 200)}")
    return condensed



def slice_world_state(world_state: Optional[dict]) -> Optional[str]:
    """
    从 world_state 中提取与本轮相关的简短片段（示例：精选字段并 JSON 化）。
    若无关键字段或 world_state 非 dict，返回 None。
    """
    if not isinstance(world_state, dict):
        logger.info("[world] 无有效世界状态，跳过切片")
        return None

    keys = ["scene", "location", "time", "weather", "inventory", "quests", "flags"]
    data = {k: world_state.get(k) for k in keys if k in world_state}
    if not data:
        logger.info("[world] 世界状态为空或无关键字段，跳过切片")
        return None

    text = _safe_json(data)
    sliced = f"[World State]\n{text}"
    logger.info(f"[world] 切片预览: {_preview_text(sliced, 200)}")
    return sliced


# ============================== 预算判断与历史选择 ==============================

def should_summarize_by_tokens(
    system_text: str,
    memory_text: Optional[str],
    world_text: Optional[str],
    turns: List[Dict],
    user_text: str,
    budget_tokens: int
) -> bool:
    """
    判断在整体预算下是否需要进行摘要：
    即使轮数不超，只要总预算估算超过限制即触发。
    """
    head = [t for t in (system_text, memory_text, world_text) if t]
    used_head_and_user = sum(approx_tokens(x) for x in head) + approx_tokens(user_text) + USER_RESERVE_TOKENS
    turns_tokens = sum(approx_tokens((m.get("content") or "")) for m in (turns or []))
    total_est = used_head_and_user + turns_tokens
    logger.info(f"[budget] 总体估算: head+user={used_head_and_user}, turns={turns_tokens}, total={total_est}, budget={budget_tokens}")
    return total_est > budget_tokens


def select_recent_by_budget(turns: List[Dict], budget_left: int) -> List[Message]:
    """
    从最近往前选入历史，若单条超过 MAX_SINGLE_MESSAGE_TOKENS 则先截断，再判断是否可纳入。
    - 以“最近优先”的方式回溯
    - 至少尝试纳入一小段，避免历史完全缺失
    """
    recent: List[Message] = []
    if not isinstance(turns, list) or budget_left <= 0:
        return recent

    for msg in reversed(turns):
        role = msg.get("role", "user")
        content = (msg.get("content") or "")

        # 单条硬上限，避免撑爆
        content = prune_message_to_tokens(content, MAX_SINGLE_MESSAGE_TOKENS)
        t = approx_tokens(content)

        if t <= budget_left:
            recent.insert(0, Message(role=role, content=content))
            budget_left -= t
        else:
            # 如果还没选任何一条，尝试再缩一轮（更小阈值），确保至少能塞进一点
            if not recent and budget_left > 50:
                shrink = prune_message_to_tokens(content, max(budget_left, 50))
                if approx_tokens(shrink) <= budget_left:
                    recent.insert(0, Message(role=role, content=shrink))
                    budget_left = 0
            break
    return recent


# ============================== 消息组装 ==============================

def build_messages(
    system_text: str,
    memory_text: Optional[str],
    world_text: Optional[str],
    turns: List[Dict],
    user_text: str,
    budget_tokens: Optional[int] = None,
) -> List[Message]:
    """
    组装 messages：system -> memory -> world -> 最近若干轮 -> 当前用户
    严格控制预算，优先保留前置信息与最近轮次。
    """
    budget = budget_tokens if isinstance(budget_tokens, int) else MESSAGE_BUDGET_TOKENS

    messages: List[Message] = []
    head_texts: List[str] = []

    # 头部（system/memory/world）
    if system_text:
        messages.append(Message(role="system", content=system_text))
        head_texts.append(system_text)
    if memory_text:
        messages.append(Message(role="system", content=f"{memory_text}"))
        head_texts.append(memory_text)
    if world_text:
        messages.append(Message(role="system", content=f"{world_text}"))
        head_texts.append(world_text)

    head_used = sum(approx_tokens(x) for x in head_texts)
    user_reserve = approx_tokens(user_text) + USER_RESERVE_TOKENS
    history_budget = max(MIN_HISTORY_BUDGET_TOKENS, budget - head_used - user_reserve)

    logger.info(
        "[messages] 预算汇总: "
        f"budget={budget}, head_used={head_used}, user_reserve={user_reserve}, history_budget={history_budget}"
    )

    # 选择历史
    recent = select_recent_by_budget(turns or [], history_budget)
    messages.extend(recent)

    # 末尾追加当前用户
    messages.append(Message(role="user", content=user_text))

    # 统计估算与采样
    total_est = sum(approx_tokens(m["content"]) for m in messages)
    logger.info(f"[messages] 装配完成: 总条数={len(messages)}, 估算total_tokens={total_est}")

    try:
        recent_samples = [f"{m['role']}: {m['content']}" for m in recent]
        # logger.info(f"[messages] recent 采样: {_preview_list(recent_samples, 5, 120)}")
    except Exception:
        # 防御性：日志预览失败不影响主流程
        pass

    return messages


__all__ = [
    # logger
    "logger",
    # 常量
    "SUMMARY_THRESHOLD",
    "MESSAGE_BUDGET_TOKENS",
    # 对外方法
    "summarize_history_if_needed",
    "slice_world_state",
    "should_summarize_by_tokens",
    "build_messages",
]
