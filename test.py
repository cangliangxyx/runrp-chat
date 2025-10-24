import os
import json
import requests
from datetime import datetime
from prompt.get_system_prompt import get_system_prompt

# -----------------------------
# 配置部分
# -----------------------------
# MODEL_NAME = "huihui_ai/deepseek-r1-abliterated:8b" qwen3:4b
MODEL_NAME = "gemma3:1b"
# MODEL_NAME = "qwen3:4b"
API_URL = "http://localhost:11434/v1/chat/completions"

# -----------------------------
# 调用本地模型函数
# -----------------------------

def call_model(messages, stream=False):
    """
    调用本地模型，支持流式输出。
    stream=True 时，使用生成器 yield 实时返回 chunk。
    """
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500,
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
                    data_str = decoded[len("data:"):].strip()  # 去掉前缀
                    if data_str == "[DONE]":
                        break
                    try:
                        j = json.loads(data_str)
                        content = ""

                        # OpenAI 风格
                        choice = j.get("choices", [{}])[0]
                        if "delta" in choice:
                            content = choice["delta"].get("content") or ""
                        elif "message" in choice:
                            content = choice["message"].get("content") or ""

                        # Gemini 风格
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


def main():
    # system_instructions = get_system_prompt("book")  # 获取默认系统 prompt
    system_instructions = "你是一个对话助手"
    messages = [{"role": "system", "content": system_instructions}]

    print("=== 本地模型调试工具 ===")
    print("输入 'exit' 或 'quit' 退出\n")

    while True:
        user_input = input("用户: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            break
        messages.append({"role": "user", "content": user_input})
        try:
            full_output = ""
            # 使用生成器逐块处理流式输出
            for chunk in call_model(messages, stream=True):
                full_output += chunk  # 拼接完整文本
            print("\n[模型输出完毕]")
            # 保存模型输出到消息历史
            messages.append({"role": "assistant", "content": full_output})
        except Exception as e:
            print("[调用模型出错]", e)


if __name__ == "__main__":
    main()

