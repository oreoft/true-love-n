# ============================================
# True Love Server - Multi-stage Dockerfile
# ============================================
# 使用 uv 进行依赖管理的高效容器化构建

# 基础镜像阶段 - 安装 uv
FROM python:3.12-slim AS builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 使用 uv 安装依赖（利用缓存）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 复制源代码
COPY src/ ./src/

# 安装项目本身
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================
# 运行阶段 - 最小化镜像
# ============================================
FROM python:3.12-slim AS runtime

# 安装 curl 用于健康检查
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    APP_ENV=prod

WORKDIR /app

# 从 builder 复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 复制源代码
COPY --from=builder /app/src /app/src

# 复制静态文件
COPY static/ /app/static/

# 设置 PATH 使用虚拟环境
ENV PATH="/app/.venv/bin:$PATH"

# 暴露端口
EXPOSE 8088

# 健康检查（使用 curl 更轻量）
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8088/health || exit 1

# 启动命令
CMD ["python", "-m", "true_love_server"]


