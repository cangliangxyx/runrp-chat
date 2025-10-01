# prompt/get_system_prompt.py   在公司看到一个新来的实习生，王佩佩，她大概21岁，皮肤白皙滑润，长相特别漂亮，黑长直的头发到臀部，身材也很棒乳房特别丰满，腰特别细，屁股很翘看着就想打一巴掌，据说她的业余爱好是瑜伽，看起来是个女神级别，如果和她上床姿势一定很多

from pathlib import Path

PROMPT_FILES = {
    "developer":"system_prompt_developer.md",
    "真实现实恋爱模拟器": "system_prompt_01.md",
    "女神反转系统": "system_prompt_03.md",
    "安清雪": "system_prompt_02.md",
    "写作助手": "system_prompt_04.md",
    "default": "system_prompt_def.md",
    "test": "system_prompt_test.md",
    "nsfw": "system_prompt_nsfw.md",
    "temp": "temp.md",
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
    print(get_system_prompt("lamnq"))
