# 项目名称

这是一个使用Python实现的聊天应用程序，支持调用不同的语言模型并流式返回生成的内容。项目通过与后端API交互来获取模型响应，并管理聊天历史记录。

## 目录结构
```
project-root/ 
    .
    |-- Dockerfile
    |-- app.py
    |-- config
    |   |-- config.py
    |   |-- decrypt_message.py
    |   |-- models.py
    |   `-- persona.json
    |-- log
    |   `-- chat_history.json
    |-- prompt
    |   `-- get_system_prompt.py
    |-- readme.md
    |-- requirements.txt
    |-- run.sh
    |-- static
    |   |-- app.css
    |   |-- app.js
    |   |-- custom.css
    |   |-- custom.js
    |   |-- script.js
    |   `-- style.css
    |-- templates
    |   `-- index.html
    `-- utils
        |-- chat_history.py
        |-- message_builder.py
        |-- persona_loader.py
        |-- print_messages_colored.py
        |-- stream_chat.py
        `-- stream_chat_app.py
```



