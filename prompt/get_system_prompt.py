from pathlib import Path

PROMPT_FILES = {
    "default": "system_prompt_def.md",
    "prompt01": "system_prompt_01.md",
    "prompt02": "system_prompt_02.md",
}

PROMPT_CACHE = {}

def load_prompt(name: str) -> str:
    """从文件加载指定的系统 prompt"""
    filename = PROMPT_FILES.get(name, PROMPT_FILES["default"])
    file_path = Path(__file__).parent / filename

    try:
        return file_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"未找到系统提示文件: {file_path}")

def get_system_prompt(name: str) -> str:
    """根据名称获取系统 prompt，不存在则返回 default"""
    if name not in PROMPT_CACHE:
        PROMPT_CACHE[name] = load_prompt(name)
    return PROMPT_CACHE[name]

if __name__ == "__main__":
    print(get_system_prompt("default"))
