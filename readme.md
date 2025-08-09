project-root/
│
├── backend/                              # 后端代码 (Python 实现) 
│   ├── app/                              # 核心后端应用代码
│   │   ├── main.py                       # 主入口文件 (启动后端服务)
│   │   ├── routes/                       # 所有路由定义
│   │   │   ├── chat_routes.py            # 聊天相关路由
│   │   │   └── health_check.py           # 健康检查路由
│   │   ├── services/                     # 业务逻辑
│   │   │   └── chat_service.py           # 聊天相关逻辑
│   │   ├── models/                       # 数据模型
│   │   │   └── message.py                # 消息数据模型定义
│   │   ├── utils/                        # 工具类
│   │   │   └── helper_functions.py       # 工具方法
│   │   └── config.py                     # 配置文件 (数据库、环境变量等)
│   ├── tests/                            # 后端测试
│   │   ├── test_routes.py                # 路由测试
│   │   └── test_services.py              # 服务测试
│   └── requirements.txt                  # Python 项目依赖
│
├── frontend/                             # 前端代码 (基于 chatbot-ui)
│   ├── public/                           # 静态文件
│   ├── src/                              # 源代码
│   │   ├── components/                   # 自定义组件
│   │   │   ├── ChatWindow.jsx            # 聊天窗口组件
│   │   │   └── ChatInput.jsx             # 聊天输入框
│   │   ├── pages/                        # 页面
│   │   │   └── ChatPage.jsx              # 主页面
│   │   ├── utils/                        # 公用函数
│   │   │   └── api.js                    # 前端调用后端 API 工具函数
│   │   ├── App.js                        # 主应用文件
│   │   └── index.js                    # 应用渲染起点
│   ├── package.json                      # 前端依赖管理
│   ├── vite.config.js                    # Vite 配置文件 (如果需要)
│   └── README.md                         # 前端开发文档
│
├── docs/                                 # 项目文档
│   ├── api.md                            # 后端 API 文档
│   ├── architecture.md                   # 项目架构说明
│   └── frontend.md                       # 前端开发指南
│
├── .env                                  # 环境变量配置
├── .gitignore                            # Git 忽略配置
├── README.md                             # 项目总说明文档
└── docker-compose.yml                    # Docker Compose 配置文件 (部署用)
