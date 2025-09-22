import os
import requests
import json
from config.models import model_registry
from config.config import CLIENT_CONFIGS
from prompt.get_system_prompt import get_system_prompt


model_details = model_registry("google-pro")
print("model_details =",model_details)
client_key = model_details["client_name"]
print("client_key =",client_key)
client_settings = CLIENT_CONFIGS[client_key]
model_id = f"{model_details['label']}"
print("model_id =",model_id)
api_url = "https://api.246520.xyz/v1beta/chat/completions"
print("api_url =",api_url)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {client_settings['api_key']}"
}
messages = [
    {"role": "user", "content": "你好"}
]
payload = {
    "model": model_id,  # 使用构造好的模型ID
    "stream": True,
    "messages": messages
}

# --- 4. 发送请求并检测 API 响应 ---

try:
    print("\n🚀 正在发送 API 请求...")
    response = requests.post(
        api_url,
        headers=headers,
        json=payload,
        stream=True  # 启用流式传输以接收数据块
    )

    # 关键检测点：检查 HTTP 状态码
    if response.status_code == 200:
        print(f"API 请求成功！状态码: {response.status_code} (OK)")
        print("开始接收流式响应:\n---")

        # 迭代处理每一行流式数据
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                # API 返回的流式数据以 "data: " 开头
                if line_str.startswith('data: '):
                    json_str = line_str[6:]
                    if json_str.strip() != '[DONE]':
                        try:
                            chunk = json.loads(json_str)
                            content = chunk['choices'][0]['delta'].get('content', '')
                            print(content, end='', flush=True)
                        except json.JSONDecodeError:
                            # 忽略无法解析的行
                            pass
        print("\n---\n✅ 流式响应接收完毕。")

    else:
        # 如果状态码不是 200，则请求失败
        print(f"❌ API 请求失败！状态码: {response.status_code}")
        # 打印服务器返回的错误信息，这对于调试至关重要
        print("错误详情:", response.text)

except requests.exceptions.RequestException as e:
    print(f"❌ 网络连接错误: {e}")