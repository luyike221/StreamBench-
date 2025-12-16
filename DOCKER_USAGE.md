# Docker 使用说明

## 概述

本项目提供了 Docker 支持，可以在完全离线的环境中运行测试。代码采用外挂方式（volume mount），方便随时修改代码和配置。

## 特性

- ✅ **完全离线环境** - 使用 `network_mode: "none"`，确保测试环境无网络
- ✅ **依赖打包** - 所有 Python 依赖都打包到镜像中
- ✅ **代码外挂** - 源代码、配置、数据都通过 volume 挂载，方便修改
- ✅ **多阶段构建** - 优化镜像大小，只包含运行时需要的文件

## 快速开始

### 1. 构建镜像

> **注意**：`docker-compose.yml` 默认使用已构建好的镜像，适用于内网无网环境。如果需要构建镜像，请使用下面的方法。

#### 方式1: 使用 docker-compose.build.yml（推荐）

```bash
cd backend
docker-compose -f docker-compose.build.yml build
```

#### 方式2: 使用 Docker 直接构建

```bash
cd backend
docker build -t ai-benchmark:latest .
```

#### 内网环境：导入已构建的镜像

如果在内网无网环境下，需要先在有网络的环境构建镜像，然后导入：

**步骤1：在有网络的环境下构建镜像**

```bash
cd backend
docker-compose -f docker-compose.build.yml build
# 或
docker build -t ai-benchmark:latest .
```

**步骤2：导出镜像**

```bash
docker save ai-benchmark:latest | gzip > ai-benchmark.tar.gz
```

**步骤3：将镜像文件传输到内网环境**

使用 U盘、内网传输等方式将 `ai-benchmark.tar.gz` 复制到内网服务器。

**步骤4：在内网环境导入镜像**

```bash
docker load < ai-benchmark.tar.gz
```

**步骤5：验证镜像**

```bash
docker images | grep ai-benchmark
```

### 2. 运行测试

#### 方式1: 使用 docker-compose run（推荐）

```bash
# 运行测试（容器执行完后自动删除）
docker-compose run --rm ai-benchmark \
  python src/stream_test_enhanced.py -c configs/config_dify.json
```

#### 方式2: 进入容器交互式运行

```bash
# 启动容器（后台运行）
docker-compose up -d

# 进入容器
docker-compose exec ai-benchmark /bin/bash

# 在容器内运行测试
python src/stream_test_enhanced.py -c configs/config_dify.json

# 退出容器
exit

# 停止容器
docker-compose down
```

#### 方式3: 使用 docker run

```bash
docker run --rm \
  --network none \
  -v $(pwd)/src:/app/src:ro \
  -v $(pwd)/configs:/app/configs:rw \
  -v $(pwd)/data:/app/data:rw \
  -v $(pwd)/docs:/app/docs:ro \
  ai-benchmark:latest \
  python src/stream_test_enhanced.py -c configs/config_dify.json
```

### 3. 验证环境

```bash
# 检查 Python 版本和依赖
docker-compose run --rm ai-benchmark python --version
docker-compose run --rm ai-benchmark python -c "import aiohttp; print(aiohttp.__version__)"

# 查看容器内的文件结构
docker-compose run --rm ai-benchmark ls -la /app
```

## 目录挂载说明

| 本地目录 | 容器目录 | 权限 | 说明 |
|---------|---------|------|------|
| `./src` | `/app/src` | 只读 | 源代码目录 |
| `./configs` | `/app/configs` | 读写 | 配置文件目录 |
| `./data` | `/app/data` | 读写 | 测试数据和结果目录 |
| `./docs` | `/app/docs` | 只读 | 文档目录 |

## 修改代码和配置

由于代码采用外挂方式，你可以直接在本地修改：

1. **修改源代码**：直接编辑 `src/stream_test_enhanced.py`，下次运行时会自动使用新代码
2. **修改配置**：直接编辑 `configs/*.json`，立即生效
3. **查看结果**：测试结果会直接保存到 `data/test_results.json`

无需重新构建镜像！

## 网络隔离

容器使用 `network_mode: "none"`，确保：

- ✅ 完全无网络访问
- ✅ 无法访问外部 API
- ✅ 适合离线测试环境

如果需要网络访问（例如测试真实 API），可以修改 `docker-compose.yml`：

```yaml
# 注释掉或删除这一行
# network_mode: "none"
```

## 常见问题

### Q: 如何更新依赖？

如果修改了 `pyproject.toml` 或 `uv.lock`，需要重新构建镜像：

**在有网络的环境下：**

```bash
docker-compose -f docker-compose.build.yml build --no-cache
# 或
docker build --no-cache -t ai-benchmark:latest .
```

然后按照上面的步骤导出和导入镜像。

### Q: 如何查看容器日志？

```bash
docker-compose logs ai-benchmark
```

### Q: 如何清理所有容器和镜像？

```bash
# 停止并删除容器
docker-compose down

# 删除镜像
docker rmi ai-benchmark:latest
```

### Q: 如何在容器内安装额外的包？

由于是完全离线环境，无法在运行时安装包。如果需要新依赖：

1. 修改 `pyproject.toml`
2. 运行 `uv lock` 更新锁文件
3. 重新构建镜像

### Q: 测试结果保存在哪里？

测试结果保存在 `data/test_results.json`，这是通过 volume 挂载的，所以结果会直接保存到本地。

## 构建优化

镜像使用多阶段构建：

1. **构建阶段**：安装 uv 和所有依赖
2. **运行阶段**：只复制虚拟环境，最小化镜像大小

最终镜像只包含运行时需要的文件，大小约 200-300MB。

## 开发工作流

推荐的工作流程：

1. 在本地修改代码和配置
2. 使用 `docker-compose run` 快速测试
3. 查看 `data/test_results.json` 结果
4. 继续迭代，无需重新构建镜像

