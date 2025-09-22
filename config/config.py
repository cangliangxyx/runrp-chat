# config.py
from config.decrypt_message import decrypt_message

CLIENT_CONFIGS = {
    # deepseek
    "deepseek": {
        "base_url": "https://api.deepseek.com/chat/completions",
        "api_key": decrypt_message("gAAAAABoySFC3kuOW6knCccmuo4tEfridSxwGubYuzaqgYiPJ3Il1c4HH26N1GZT2CjbZR0F3weJjztTSW0lz8azQ4ioSaTRvnIqdMx_TYJTuPBZAV4iNL0ixY2nT1cE7Lfrbz-U45-0")
    },
    # chat_runrp
    "link_api": {
        "base_url": "https://api.linkapi.org/v1/chat/completions",
        "api_key": decrypt_message("gAAAAABow8ZswUlACpA9hOmG1AxERQC4EoFyPFDqlPZbAUC0g5K_cZ2jsA9j3tCg4nWy5oAgwDO2V25wciqij-qwaLQW-vLzI9joGVLNIhVBV98R902Kh0oAU_N0w3TXEmB9Klng87EIiSUO4FFYu0GSNN1vD56HXw==")
    },
    "claude_api": {
        "base_url": "https://chat.cloudapi.vip/v1/chat/completions",
        "api_key": decrypt_message("gAAAAABow8ZKhmf8JW3S29GXjaJMqtnaHQglS8u7T8AMefKK4JoqfhV9y5J6vJIRBtRlmxf9Upb_XgUkRqqJLFgU_Inwrg2pGCktnUz5weLhB3RYjFif5lvtIAoCtMvit5rs2O_909i_ZwPkMKYEGRWOuhuKrwOgiA==")
    },
    "google": {
        "base_url": "https://api.246520.xyz/v1beta/chat/completions",
        # "base_url": "https://generativelanguage.googleapis.com/v1beta/chat/completions",
        "api_key": decrypt_message("gAAAAABo0QSlhm1yMzos3vV5j0vlSYkc5isv9L6C-z-lGVoaiK33s5-ajcAs3L0TUVaHc2trYzVuCgWrvwuvCuAM_ONG5BlIqeA8hH6joBF_YyhUz9dzd4fIqxFjMxs0LNWZzdoQu6aB")
    }
}