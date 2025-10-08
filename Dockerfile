# Dockerfile

FROM python:3.12-slim

# 安装依赖，包括 libc6 兼容库
#RUN apt-get update
#RUN apt-get install -y libc6
#RUN apt-get clean
#RUN rm -rf /var/lib/apt/lists/*1


# 创建项目目录并设置为工作目录
RUN mkdir /opt/project
WORKDIR /opt/project
#
# 将本地代码复制到容器
COPY ./ /opt/project
# 设置环境变量，指定 oc 所在路径
ENV PATH="/opt/project/bin:${PATH}"
ENV KUBECONFIG=/opt/project/kube/config

# 安装依赖
RUN pip install -r requirements.txt

# 暴露 Flask 默认端口
EXPOSE 8080

# 指定容器启动时执行的命令
CMD ["/bin/sh", "/opt/project/run.sh"]