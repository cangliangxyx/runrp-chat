# prompt/get_system_prompt.py
from pathlib import Path

PROMPT_FILES = {
    "聊天": "system_prompt_def.md",
    "提示词助手": "system_prompt_assist.md",
    "book": "book.md",
    "恋爱模拟器": "system_prompt_01.md",
    "安清雪": "system_prompt_02.md",
    "女神反转系统": "system_prompt_03.md",
    "角色卡设定架构师": "user_card_prompt.md",
    "game": "game.md",
    "Python":"python.md",
    "nsfw": "nsfw.md",
    "temp": "temp.md",
}

PROMPT_CACHE = {}

def get_system_prompt(name: str) -> str:
    """根据名称获取系统 prompt，不存在则返回 default """
    filename = PROMPT_FILES.get(name, PROMPT_FILES["book"])
    file_path = Path(__file__).parent / filename
    try:
        return file_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"未找到系统提示文件: {file_path}")
if __name__ == "__main__":
    print(get_system_prompt("system_prompt_def.md"))
