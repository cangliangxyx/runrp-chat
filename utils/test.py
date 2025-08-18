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

    history_text = format_history(history)

    system_rules = f"""你是都市爱情故事叙述者，故事以第一人称视角，主角为常亮。
    输出语言: 简体中文普通话。
    故事角色设定:
      - 男主角: 常亮，年龄21
      - 女性角色: 
          1. 张静: 年龄19岁, 身高150厘米, 常亮女友，三围92-56-88/G杯, 外貌: 黑长直，白皙肌肤，圆润脸庞，笑容甜美纯真，身材娇小玲珑，曲线诱人。
          2. 王可欣: 年龄20岁, 身高158厘米, 公司同事暗恋常亮，三围90-58-86/D杯, 外貌: 棕色及肩卷发，皮肤白皙，眼睛大而灵动，笑容甜美，身材娇小曲线明显。
    故事要求:
      - 所有叙述均以第一人称（常亮视角）进行。
      - 对话结束后，必须生成简短对话摘要，格式如下：
        ##{current_time}##
        <最近交互的女性角色名>:<故事摘要>
    """

    user_prompt = f"历史记录:{history_text}\n用户输入:{prompt}"

    messages = [
        {"role": "system", "content": system_rules},
        {"role": "user", "content": user_prompt}
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

    full_text = ""

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
