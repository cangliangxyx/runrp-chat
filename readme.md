# Nebula Chat（FastAPI + Vite React 前后端分离版）

Nebula Chat 是一个 **多模型、多角色、流式输出** 的 AI 聊天应用。  
后端采用 **FastAPI**，前端使用 **Vite + React + TypeScript**，并支持调用本地或云端任意语言模型。

本项目已经实现稳定的前后端分离架构，并支持生产构建部署。

---

## 功能特性

### 后端（FastAPI）

- 支持调用任意大语言模型（本地/云端）
- 支持流式输出（SSE-like）
- 内置聊天历史管理（加载/清空/移除最后一条）
- 多角色（Personas）动态切换
- 自定义系统提示词（system rules）
- 支持 NSFW 控制
- 可选本地静态资源托管（React 打包后文件）

### 前端（Vite + React + TS）

- 响应式 UI
- 支持模型选择、角色选择、系统规则切换
- 聊天界面 + 流式效果
- 自动打包到 `frontend/dist`

---

## 项目目录结构

```
./
├── Dockerfile
├── app.py
├── config
│    ├── config.py
│    ├── decrypt_message.py
│    └── models.py
├── create_requirements.py
├── frontend
│    ├── App.tsx
│    ├── README.md
│    ├── components
│    │    ├── Icons.tsx
│    │    └── Sidebar.tsx
│    ├── dist
│    │    ├── assets
│    │    │    └── index-DdmxBqxE.js
│    │    └── index.html
│    ├── index.html
│    ├── index.tsx
│    ├── metadata.json
│    ├── package-lock.json
│    ├── package.json
│    ├── services
│    │    └── api.ts
│    ├── tsconfig.json
│    ├── types.ts
│    └── vite.config.ts
├── main.py
├── prompt
│    ├── book.md
│    ├── book_v6.md
│    ├── book_v7.md
│    ├── get_system_prompt.py
│    ├── nsfw.md
│    ├── persona.json
│    ├── prompt_demo.md
│    ├── python.md
│    ├── system_prompt_01.md
│    ├── system_prompt_02.md
│    ├── system_prompt_03.md
│    ├── system_prompt_assist.md
│    ├── temp.md
│    ├── test.md
│    └── test.txt
├── readme.md
├── requirements.txt
├── run.sh
├── static
│    ├── app.core.js
│    ├── app.css
│    ├── app.js
│    ├── app.mobile.css
│    └── app.persona.js
├── templates
│    └── index.html
└── utils
    ├── chat_history.py
    ├── message_builder.py
    ├── persona_loader.py
    ├── print_messages_colored.py
    ├── stream_api.py
    ├── stream_chat.py
    └── stream_chat_app.py
```

---

## 运行方式

### 安装依赖

```bash
pip install -r requirements.txt
```

### 进入前端目录安装依赖

```bash
cd frontend
npm install
```

### 开发调试（推荐分离启动）

#### 启动 Vite 前端（开发态）

```bash
npm run dev
```

#### 启动 FastAPI 后端

```bash
cd ..
python main.py
```

前端将自动通过 `/chat`、`/personas` 等 API 访问后端。

---

## 构建生产版本

前端：

```bash
cd frontend
npm run build
```

生成的文件将放在 `frontend/dist/`。

FastAPI 会自动托管该目录：

```
/assets
/index.html
```

无需 Nginx，直接运行 `main.py` 即可。

---

## API 说明

### `/chat`（POST）

发送聊天请求，可流式或一次性输出。

### `/personas`（GET/POST）

列出 / 更新当前角色列表。

### `/system_rules`

获取可用的系统提示词。

### `/clear_history`

清空服务器聊天历史。

其余接口可查看 `main.py`。

---

## 部署（Docker）

运行以下命令构建：

```bash
docker build -t nebula-chat .
docker run -p 8080:8080 nebula-chat
```

构建后的镜像包含前后端全部产物，可直接部署。

---

## 常见问题（FAQ）

### 为什么前端提示跨域？

请确保后端已启用 CORS（项目中已启用）。

### 为什么找不到 `frontend/dist`？

必须先：

```bash
cd frontend
npm install
npm run build
```
