# 使用轻量级 Python 镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# Cloud Build/Docker 没有交互式 TTY，避免 apt/debconf 尝试打开交互前端。
ENV DEBIAN_FRONTEND=noninteractive

# 安装必要的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY services/backend_api/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY services/backend_api/ ./services/backend_api/
COPY internal/ ./internal/

# 复制前端静态文件到后端可以访问的目录
COPY services/web_ui/ ./services/web_ui/

# 设置环境变量
ENV PYTHONPATH=/app
ENV PORT=8080

# 暴露端口 (Cloud Run 默认使用 8080)
EXPOSE 8080

# 启动命令
CMD ["python", "services/backend_api/main.py"]
