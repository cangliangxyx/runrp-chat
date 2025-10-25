import os
import json
import requests
from datetime import datetime
from prompt.get_system_prompt import get_system_prompt
from engine.memory_manager import MemoryManager

# -----------------------------
# 模型配置
# -----------------------------
# MODEL_NAME = "gemma3:1b"
MODEL_NAME = "qwen3:4b"
# MODEL_NAME = "huihui_ai/deepseek-r1-abliterated:8b"
API_URL = "http://localhost:11434/v1/chat/completions"

# 初始化记忆系统
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(BASE_DIR, "game/data", "memory_db")
memory = MemoryManager(db_path=db_path, collection_name="story_memory")
# memory = MemoryManager(db_path="data/memory_db")

# -----------------------------
# 调用模型函数
# -----------------------------
def call_model(messages, stream=False):
    """
    调用本地模型，支持流式输出。
    stream=True 时使用生成器逐步返回。
    """
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 50000,
        "stream": stream
    }

    full_output = ""

    if stream:
        try:
            with requests.post(API_URL, json=payload, stream=True) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    decoded = line.decode("utf-8").strip()
                    if not decoded.startswith("data:"):
                        continue
                    data_str = decoded[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        j = json.loads(data_str)
                        content = ""
                        choice = j.get("choices", [{}])[0]
                        if "delta" in choice:
                            content = choice["delta"].get("content") or ""
                        elif "message" in choice:
                            content = choice["message"].get("content") or ""

                        # Gemini 风格兼容
                        if not content and "candidates" in j:
                            parts = j["candidates"][0].get("content", {}).get("parts", [])
                            content = "".join(p.get("text", "") for p in parts if "text" in p)

                        if content:
                            print(content, end="", flush=True)
                            full_output += content
                            yield content

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            print("[流式调用错误]", e)
        print("\n[流结束]")

    else:
        try:
            r = requests.post(API_URL, json=payload, timeout=30)
            r.raise_for_status()
            result = r.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"].get("content", "")
            return ""
        except Exception as e:
            print("[非流式调用错误]", e)
            return ""


# -----------------------------
# 主程序
# -----------------------------
def main():
    system_instructions = get_system_prompt("survival")
    # system_instructions = "你是一个具备记忆功能的对话助手，能够回忆之前的故事片段。"
    messages = [{"role": "system", "content": system_instructions}]

    print("=== 带记忆的模型调试工具 ===")
    print("输入 'exit' 退出\n")

    while True:
        user_input = input("用户: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            break

        related_context = memory.query_memory(user_input, top_k=3)
        if related_context:
            context_text = "\n".join(related_context)
            full_prompt = f"以下是你之前的记忆：\n{context_text}\n\n现在用户说：{user_input}"
        else:
            full_prompt = user_input

        # 构造消息序列
        messages.append({"role": "user", "content": full_prompt})

        try:
            full_output = ""
            for chunk in call_model(messages, stream=True):
                full_output += chunk
            print("\n[模型输出完毕]")

            messages.append({"role": "assistant", "content": full_output})
            memory.add_memory(f"用户：{user_input}\n模型：{full_output}")
            print("memory.add_memory = ", memory.add_memory(f"用户：{user_input}\n模型：{full_output}"))

        except Exception as e:
            print("[调用模型出错]", e)


if __name__ == "__main__":
    main()