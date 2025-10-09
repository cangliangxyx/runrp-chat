# models.py
import logging

logger = logging.getLogger(__name__)

# 预置模型
DEFAULT_MODELS = {
    "gemini-2.5-pro": {
        "label": "gemini-2.5-pro",                  # $0.00125/K tokens（default）
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    "gemini-2.5-flash": {
        "label": "gemini-2.5-flash",                # $0.0003/K tokens（default）
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    "grok-4-fast-non-reasoning": {
        "label": "grok-4-fast-non-reasoning",       # $0.02/次（default）
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    "gpt-5-chat-latest": {
        "label": "gpt-5-chat-latest",               # $0.001/K tokens（vip）
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    "claude-sonnet-4-5": {
        "label": "claude-sonnet-4-5-20250929",      # $0.0024/K tokens（cc）
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    # deepseek-chat / deepseek-reasoner
    "deepseek-chat": {
        "label": "deepseek-chat",
        "supports_streaming": True,
        "default_temperature": 0.6,
        "client_name": "deepseek",
    },
    # google_api
    "google_api": {
        "label": "gemini-2.5-flash",
        "supports_streaming": True,
        "default_temperature": 0.6,
        "client_name": "google_api",
    },
}

def model_registry(model_name: str = None):
    if model_name:
        return DEFAULT_MODELS.get(model_name)
    return DEFAULT_MODELS

def list_model_ids() -> list:
    """返回所有可用的模型ID列表"""
    return list(DEFAULT_MODELS.keys())

if __name__ == "__main__":
    data = model_registry('google_api')
    print(data)

    print(list_model_ids())

