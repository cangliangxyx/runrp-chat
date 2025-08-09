# 使用官方 Python 基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 将需求文件复制到镜像中
COPY backend/requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码到容器中
COPY backend/ ./backend/

# 暴露后端服务端口 (例如 FastAPI 默认 8000)
EXPOSE 8000

# 启动后端服务
CMD ["python", "backend/app/main.py"]
