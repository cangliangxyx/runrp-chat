# models.py
import logging

logger = logging.getLogger(__name__)

# 预置模型
DEFAULT_MODELS = {
    # deepseek-reasoner
    "deepseek-reasoner": {
        "label": "deepseek-reasoner",
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "deepseek",
    },
    # deepseek-chat
    "deepseek-chat": {
        "label": "deepseek-chat",
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "deepseek",
    },
    # link_api for gemini
    "gemini-3-flash-preview": {
        "label": "gemini-3-flash-preview",  # $0.0005/K tokens（default）
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    "gemini-3-flash-preview-thinking": {
        "label": "gemini-3-flash-preview-thinking-*",  # $0.002/K tokens（default）
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    "gemini-3-pro-preview-thinking": {
        "label": "gemini-3-pro-preview-thinking-*",  # $0.002/K tokens（default）
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    # link_api for grok
    "grok-4.1": {
        "label": "grok-4.1",       # $0.02/次（default）
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    # link_api for chatgpt gpt-4o-mini
    "gpt-5-chat": {
        # "label": "gpt-5.2-thinking",  # $0.05/次（vip）
        # "label": "gpt-5.2-2025-12-11",    # $0.00175/K（vip）
        # "label": "gpt-5.2-chat-latest",    # $0.007/K（vip）
        # "label": "gpt-5.1-thinking",    # $0.001/K（vip）
        "label": "gpt-5-chat",  # $0.00125/K
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    # link_api for chatgpt gpt-4o-mini
    "gpt-4o-mini": {
        "label": "gpt-4o-mini",  # $0.01/次
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    # link_api for claude
    "claude-sonnet-4-5": {
        "label": "claude-opus-4-5-20251101-thinking",  # $0.0024/K tokens（cc）
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
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

