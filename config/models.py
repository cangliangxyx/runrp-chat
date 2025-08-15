# models.py
import logging

logger = logging.getLogger(__name__)

# 预置模型
DEFAULT_MODELS = {
    "deepseek-chat": {
        "label": "deepseek-chat",
        "supports_streaming": True,
        "default_temperature": 0.6,
        "client_key": "deepseek",
    },
    "gpt-5-mini": {
        "label": "gpt-5-mini-2025-08-07",
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_key": "link_api",
    },
    "gpt-5": {
        "label": "gpt-5",
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_key": "link_api",
    },
    "grok-4": {
        "label": "grok-4",
        "supports_streaming": True,
        "default_temperature": 0.4,
        "client_key": "link_api",
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
    data = model_registry('gpt-3.5')
    print(data)

    print(list_model_ids())

