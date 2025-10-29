# Dockerfile

FROM python:3.13-slim

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends libc6 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /opt/project

# 先复制依赖文件（利用 Docker 缓存）
COPY requirements.txt /opt/project/

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置环境变量
ENV PATH="/opt/project/bin:${PATH}" \
    KUBECONFIG=/opt/project/kube/config

COPY . /opt/project
USER root

# 创建非 root 用户并切换
#RUN useradd -m -u 1000 appuser && \
#    chown -R appuser:appuser /opt/project
#COPY . /opt/project
#USER appuser

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["/bin/sh", "/opt/project/run.sh"]