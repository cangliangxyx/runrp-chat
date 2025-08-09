# 使用官方 NodeJS 镜像
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 package-lock.json 文件
COPY frontend/package*.json ./

# 安装前端依赖
RUN npm install

# 复制前端代码到容器
COPY frontend/ ./frontend/

# 构建前端
RUN npm run build

# 使用静态文件服务器提供前端页面
RUN npm install -g serve
CMD ["serve", "-s", "frontend/dist", "-l", "3000"]

# 暴露前端端口
EXPOSE 3000
