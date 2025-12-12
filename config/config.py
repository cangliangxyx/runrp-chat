# prompt.py
from config.decrypt_message import decrypt_message

CLIENT_CONFIGS = {
    # deepseek
    "deepseek": {
        "base_url": "https://api.deepseek.com/chat/completions",
        "api_key": decrypt_message("gAAAAABoySFC3kuOW6knCccmuo4tEfridSxwGubYuzaqgYiPJ3Il1c4HH26N1GZT2CjbZR0F3weJjztTSW0lz8azQ4ioSaTRvnIqdMx_TYJTuPBZAV4iNL0ixY2nT1cE7Lfrbz-U45-0")
    },
    # 单独购买 claude_api
    "claude_api": {
        "base_url": "https://chat.cloudapi.vip/v1/chat/completions",
        "api_key": decrypt_message("gAAAAABow8ZKhmf8JW3S29GXjaJMqtnaHQglS8u7T8AMefKK4JoqfhV9y5J6vJIRBtRlmxf9Upb_XgUkRqqJLFgU_Inwrg2pGCktnUz5weLhB3RYjFif5lvtIAoCtMvit5rs2O_909i_ZwPkMKYEGRWOuhuKrwOgiA==")
    },
    # api_key: runrp_claude_cc
    "runrp_claude_cc": {
        "base_url": "https://api.linkapi.org/v1/chat/completions",
        "api_key": decrypt_message("gAAAAABo1fYbMfy_q-hpmcsMydhrpgwJbeW63XV1qRhv-WWFFZ_re0p9P-nVG7Jyfpbkpu-Eg1nQiQlh00IxUII4z5Fx1YzyYD0zxcyH_SlAUoQaO0WpLRJAJEFAxduaymEztSJUJli7hVsZRYWGC4rFcYbJiDgEFA==")
    },
    # api_key：chat_runrp
    "link_api": {
        "base_url": "https://api.linkapi.org/v1/chat/completions",
        "api_key": decrypt_message("gAAAAABow8ZswUlACpA9hOmG1AxERQC4EoFyPFDqlPZbAUC0g5K_cZ2jsA9j3tCg4nWy5oAgwDO2V25wciqij-qwaLQW-vLzI9joGVLNIhVBV98R902Kh0oAU_N0w3TXEmB9Klng87EIiSUO4FFYu0GSNN1vD56HXw==")
    },
    # api_key：chat_runrp
    "nano-banana": {
        "base_url": "https://api.linkapi.org/v1/chat/completions",
        "api_key": decrypt_message("gAAAAABow8ZswUlACpA9hOmG1AxERQC4EoFyPFDqlPZbAUC0g5K_cZ2jsA9j3tCg4nWy5oAgwDO2V25wciqij-qwaLQW-vLzI9joGVLNIhVBV98R902Kh0oAU_N0w3TXEmB9Klng87EIiSUO4FFYu0GSNN1vD56HXw==")
    },
    # api_key: chat_runrp_gemini
    "runrp_gemini": {
        "base_url": "https://api.linkapi.org/v1beta/models/gemini-2.5-pro:generateContent",
        "api_key": decrypt_message(
            "gAAAAABo50kq7Giw4Gr4cbcDJHRoaNZ5OealtpGHcrepgmbRkcsVjB1aPMhIToLXooMIVeBadYV8A33dspd2xDIUqcAOeEmQ7AXPyvKg_GJ1MvnPJo8rcvUWBVVxdQzCU56HeQfd6kyFIbI5bp1B01s4i9J9ddJTzw==")
    },
    # google_key：google_api_changxr
    "google_changxr_key": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": decrypt_message(
            "gAAAAABpO3MNDKf1O-dsNMBzvy7KUIxpV0FxC3iTzlD59FrS3inaLDL3JovrAN2F4JYLVUkHpT-qdMfUzD0Lv0YhvA_G8Srcwj1bBT7uxS8bcvFqPbR2srtuApsJzRk3f7H3RnaArKfu")
    },
}
