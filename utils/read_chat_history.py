import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHAT_HISTORY_PATH = PROJECT_ROOT / "log" / "chat_history.json"


def extract_assistant_json(text: str) -> dict:
    """
    解析 ```json``` 代码块中的“伪 JSON”（含多段顶级对象、嵌套花括号、异常 key）
    返回标准 dict
    """
    if not isinstance(text, str):
        return {}

    block = re.search(r"```json\s*(.*?)\s*```", text, re.S)
    if not block:
        return {}

    content = block.group(1)
    content = content.replace("**", "")

    def fix_keys(s: str) -> str:
        # 修复 key 中多余的冒号，如 "障碍:"
        return re.sub(r'"([^"]+?):"\s*:', r'"\1":', s)

    def extract_object(s: str, start: int) -> tuple[str, int] | tuple[None, None]:
        # 从 start 处提取一个平衡的 {...}
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
        # 匹配 "标题":
        m = re.search(r'"([^"]+)"\s*:\s*', content[i:])
        if not m:
            break
        key = m.group(1).rstrip(":")
        key_start = i + m.start()
        val_start = i + m.end()

        # 跳过空白
        while val_start < n and content[val_start].isspace():
            val_start += 1

        # 仅处理对象值 {...}
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

        # 否则前进避免死循环
        i = val_start + 1

    return result


def main():
    if not CHAT_HISTORY_PATH.exists():
        print("{}")
        return
    with CHAT_HISTORY_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        print("{}")
        return
    assistant_text = data[-1].get("assistant", "")
    parsed = extract_assistant_json(assistant_text)
    return parsed


if __name__ == "__main__":
    print(main())
