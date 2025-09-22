# models.py
import logging

logger = logging.getLogger(__name__)

# 预置模型
DEFAULT_MODELS = {
    # deepseek-chat / deepseek-reasoner
    "google-flash": {
        "label": "gemini-2.5-flash",
        "supports_streaming": True,
        "default_temperature": 0.6,
        "client_name": "google",
    },
    "google-pro": {
        "label": "gemini-2.5-pro",
        "supports_streaming": True,
        "default_temperature": 0.6,
        "client_name": "google",
    },
    "claude-api": {
        "label": "claude-sonnet-4-20250514",
        "supports_streaming": True,
        "default_temperature": 0.6,
        "client_name": "claude_api",
    },
    # deepseek-chat / deepseek-reasoner
    "deepseek-chat": {
        "label": "deepseek-chat",
        "supports_streaming": True,
        "default_temperature": 0.6,
        "client_name": "deepseek",
    },
    "gpt-5": {
        "label": "gpt-5",
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    "grok-4": {
        "label": "grok-4",
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    "gemini-2.5-pro": {
        # "label": "gemini-2.5-pro-nothinking",
        "label": "gemini-2.5-pro",
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    },
    "claude-sonnet-4": {
        "label": "claude-sonnet-4-20250514",
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_name": "link_api",
    }
}

def model_registry(model_name: str = None):
    if model_name:
        return DEFAULT_MODELS.get(model_name)
    return DEFAULT_MODELS

def list_model_ids() -> list:
    """返回所有可用的模型ID列表"""
    return list(DEFAULT_MODELS.keys())

if __name__ == "__main__":
    data = model_registry('google')
    print(data)

    print(list_model_ids())

