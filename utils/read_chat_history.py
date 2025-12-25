import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHAT_HISTORY_PATH = PROJECT_ROOT / "log" / "chat_history.json"


def extract_assistant_json(text: str) -> dict:
    """
    解析 ```json``` / ```JSON``` 代码块
    1. 优先整体解析完整 JSON
    2. 失败时再进行伪 JSON 修复
    """
    if not isinstance(text, str):
        return {}

    block = re.search(
        r"```json\s*(.*?)\s*```",
        text,
        re.S | re.I  # 关键：忽略大小写
    )
    if not block:
        return {}

    content = block.group(1).strip()
    content = content.replace("**", "")

    # ---------- 第一优先：整体解析 ----------
    try:
        return json.loads(content)
    except Exception:
        pass

    # ---------- fallback：伪 JSON 修复 ----------
    def fix_keys(s: str) -> str:
        # 修复 key 中多余的冒号，如 "障碍:"
        return re.sub(r'"([^"]+?):"\s*:', r'"\1":', s)

    def extract_object(s: str, start: int):
        if start >= len(s) or s[start] != "{":
            return None, None
        depth = 0
        for i in range(start, len(s)):
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    return s[start:i + 1], i + 1
        return None, None

    result = {}
    i = 0
    n = len(content)

    while i < n:
        m = re.search(r'"([^"]+)"\s*:\s*', content[i:])
        if not m:
            break

        key = m.group(1).rstrip(":")
        val_start = i + m.end()

        while val_start < n and content[val_start].isspace():
            val_start += 1

        if val_start < n and content[val_start] == "{":
            obj_text, next_pos = extract_object(content, val_start)
            if obj_text:
                obj_text = fix_keys(obj_text)
                try:
                    result[key] = json.loads(obj_text)
                except Exception:
                    result[key] = obj_text
                i = next_pos
                continue

        i = val_start + 1

    return result


def main():
    if not CHAT_HISTORY_PATH.exists():
        return {"message": "暂无历史记录"}

    try:
        with CHAT_HISTORY_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"message": "暂无历史记录"}

    if not isinstance(data, list) or not data:
        return {"message": "暂无历史记录"}

    assistant_text = data[-1].get("assistant", "")
    parsed = extract_assistant_json(assistant_text)

    if not parsed:
        return {"message": "暂无历史记录"}

    return parsed


if __name__ == "__main__":
    print(main())