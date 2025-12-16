# 多阶段构建 Dockerfile
# 阶段1: 构建阶段 - 安装依赖
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /build

# 安装系统依赖（构建 uv 和 Python 包所需）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# 复制项目依赖文件
COPY pyproject.toml uv.lock ./

# 使用 uv 同步依赖（创建虚拟环境并安装所有依赖）
# 使用 --frozen 确保使用锁文件中的精确版本
RUN uv sync --frozen --no-dev

# 阶段2: 运行阶段 - 最小化镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /build/.venv /app/.venv

# 设置环境变量，使用虚拟环境中的 Python
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 验证 Python 和依赖是否安装成功
RUN python --version && \
    python -c "import aiohttp; print(f'aiohttp version: {aiohttp.__version__}')" && \
    echo "Dependencies installed successfully"

# 创建必要的目录（代码将通过 volume 挂载）
RUN mkdir -p /app/src /app/configs /app/data /app/docs

# 设置默认命令（代码通过 volume 挂载，所以这里只是占位）
# 实际运行命令在 docker-compose.yml 中指定
CMD ["python", "--version"]

