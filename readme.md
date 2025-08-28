# 项目名称

这是一个使用Python实现的聊天应用程序，支持调用不同的语言模型并流式返回生成的内容。项目通过与后端API交互来获取模型响应，并管理聊天历史记录。

## 目录结构
project-root/ 
    ├── bak/ 
    │ ├── chat_service.py 
    │ ├── chat_utils.py 
    │ └── test.py 
    │
    ├── config/ 
    │ ├── config.py 
    │ └── models.py 
    │
    ├── prompt/ 
    │ ├── get_system_prompt.py
    │ ├── system_prompot_01.py
    │ ├── system_prompot_02.py
    │ └── system_prompot_def.py 
    │
    ├── static/ 
    │ ├── script.js
    │ └── style.css 
    │
    ├── templates/ 
    │ └── index.html 
    │
    ├── utils/ 
    │ ├── chat_histoory.py
    │ └── stream_chat.py 
    │
    ├── app.py
    ├── app_bak.py
    ├── dockerfile
    └── README.md



