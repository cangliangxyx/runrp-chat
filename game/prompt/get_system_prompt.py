import os
import json

# 系统提示配置文件路径（可选）
PROMPT_FILE_PATH = os.path.join("prompt", "system_prompts.json")

def load_prompts():
    """从 JSON 文件加载所有系统提示，如果不存在则返回默认配置"""
    if os.path.exists(PROMPT_FILE_PATH):
        try:
            with open(PROMPT_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            print("[警告] 加载 system_prompts.json 失败：", e)

    # 默认提示模板（内置）
    return {
        "default": """你是一个智能对话助手，负责与用户进行自然交流。你的回复应流畅、逻辑清晰、情感自然。""",

        "book": """你是一位叙事作家，负责创作文字冒险小说。你的风格应细腻、生动，包含人物外貌、心理描写和场景氛围。""",

        "adventure": """你是一名冒险故事叙事AI。请以紧张刺激的语气讲述事件，描述危险、未知与探索。""",

        "romance": """你是一位都市恋爱故事叙事AI。你的文字温柔细腻，注重人物情感、互动和内心活动。""",

        "survival": """你是一名末日求生叙事AI。请用沉重而真实的语气，描写寒冷、饥饿、恐惧与希望。""",

        "npc_dialogue": """你是游戏中的NPC对话生成AI。请根据人物性格、情绪和与玩家的关系生成自然对话。"""
    }


def get_system_prompt(mode: str = "default") -> str:
    """
    根据模式名返回对应的系统提示。
    mode: "book", "adventure", "romance", "survival", "npc_dialogue" 等。
    """
    prompts = load_prompts()
    return prompts.get(mode, prompts["default"])


def list_available_prompts():
    """列出可用模式"""
    prompts = load_prompts()
    return list(prompts.keys())


# 测试部分
if __name__ == "__main__":
    print("可用模式：", list_available_prompts())
    print("\n示例（romance 模式）:\n")
    print(get_system_prompt("romance"))