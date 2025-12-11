# 项目名称
✅ 你现在是一个 “Flask 后端 + Vite React 前端” 的标准前后端分离结构
✅ 但你目前 还停留在「开发态」，还没有进入「生产部署态」
这是一个使用Python实现的聊天应用程序，支持调用不同的语言模型并流式返回生成的内容。项目通过与后端API交互来获取模型响应，并管理聊天历史记录。


npm run build
## 目录结构
```
./
├── Dockerfile
├── app.py
├── config
│   ├── config.py
│   ├── decrypt_message.py
│   └── models.py
├── create_requirements.py
├── frontend
│   ├── App.tsx
│   ├── README.md
│   ├── components
│   │   ├── Icons.tsx
│   │   └── Sidebar.tsx
│   ├── index.html
│   ├── index.tsx
│   ├── metadata.json
│   ├── package-lock.json
│   ├── package.json
│   ├── services
│   │   └── api.ts
│   ├── tsconfig.json
│   ├── types.ts
│   └── vite.config.ts
├── prompt
│   ├── book.md
│   ├── book_v6.md
│   ├── book_v7.md
│   ├── get_system_prompt.py
│   ├── persona.json
│   ├── prompt_demo.md
│   ├── system_prompt_01.md
│   ├── system_prompt_02.md
│   ├── system_prompt_03.md
│   ├── system_prompt_04.md
│   ├── system_prompt_def.md
│   ├── system_prompt_developer.md
│   ├── system_prompt_nsfw.md
│   ├── system_prompt_test.md
│   ├── temp.md
│   └── test.txt
├── readme.md
├── requirements.txt
├── run.sh
├── static
│   ├── app.core.js
│   ├── app.css
│   ├── app.js
│   ├── app.mobile.css
│   └── app.persona.js
├── templates
│   └── index.html
└── utils
    ├── chat_history.py
    ├── message_builder.py
    ├── persona_loader.py
    ├── print_messages_colored.py
    ├── stream_api.py
    ├── stream_chat.py
    └── stream_chat_app.py

```



