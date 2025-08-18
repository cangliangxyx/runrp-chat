import httpx
import json, datetime, asyncio, re
from config.config import CLIENT_CONFIGS
from config.models import model_registry
from utils.chat_utils import logger

history = []  # 历史记录摘要

def format_history(history_list):
    """将历史摘要美化为编号 + 时间戳形式"""
    if not history_list:
        return "无历史记录。"
    formatted = []
    for idx, entry in enumerate(history_list, 1):
        # 提取时间戳和内容
        match = re.match(r"(##\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}##)([\s\S]+)", entry)
        if match:
            timestamp = match.group(1)
            content = match.group(2).strip()
            formatted.append(f"{idx}. {timestamp} {content}")
        else:
            formatted.append(f"{idx}. {entry}")
    return "\n".join(formatted)

async def test(model, prompt):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    model_config = model_registry(model)
    client_key = model_config.get("client_name")
    client_config = CLIENT_CONFIGS.get(client_key)
    base_url = client_config["base_url"]
    api_key = client_config["api_key"]
    model_label = model_config.get("label")

    logger.info(f"[call] model: {model_label}, 请求目标: {base_url}")

    # 把历史摘要拼接到系统规则里
    # history_text = "\n".join(history) if history else "无历史记录。"
    history_text = format_history(history)

    # system_rules = (
    #     f"""你是我的开发助手,输出语言:简体中文普通话
    #     对话结束后必须生成简短对话摘要格式如下：
    #     ##{current_time}##
    #     对话摘要
    #     """
    # )

    system_rules = (
        f"""你是都市爱情故事叙述者，以第一人称常亮的视角进行故事描写,输出语言:简体中文普通话，故事男主角:常亮，女主角:张静
        对话结束后必须生成简短对话摘要格式如下：
        ##{current_time}##
        <故事摘要>
        <女性角色姓名>:<身体状态>,<内心独白>
        """
    )

    messages = [
        {"role": "system", "content": system_rules},
        {"role": "user", "content": f"历史记录:{history_text}" + f"用户输入:{prompt}"}
    ]

    print(messages)

    data = {
        "model": model_label,
        "stream": True,
        "messages": messages
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    full_text = ""  # 收集完整输出

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", base_url, headers=headers, json=data) as response:
            async for line in response.aiter_lines():
                if line and line.startswith("data: "):
                    payload = line[len("data: "):]
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                        delta = chunk["choices"][0]["delta"].get("content")
                        if delta:
                            full_text += delta
                            # 只显示模型内容，不显示日志
                            print(delta, end="", flush=True)
                    except json.JSONDecodeError:
                        logger.warning(f"无法解析: {payload}")
    print()  # 流式输出完换行

    # 提取摘要
    match = re.search(r"(##\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}##[\s\S]+)", full_text)
    if match:
        summary = match.group(1).strip()
        history.append(summary)

    for h in format_history(history).split("\n"):
        print(h)

if __name__ == "__main__":
    async def main():
        model = "gpt-5-mini"
        while True:
            prompt = input("\ninput: ")
            await test(model, prompt)

    asyncio.run(main())
