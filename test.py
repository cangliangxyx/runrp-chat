from openai import OpenAI
from config.config import CLIENT_CONFIGS
from config.models import model_registry

model_details = model_registry("google_api")
client_key = model_details["client_name"]
client_settings = CLIENT_CONFIGS[client_key]

client = OpenAI(
    api_key=client_settings["api_key"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai",
)

response = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "你好"
        }
    ]
)

print(response.choices[0].message)
