# 下载 Windows 版本的 aiohttp Wheel 文件

本文档介绍如何下载 Windows 版本的 aiohttp wheel 文件，用于离线安装。

## 方法1: 使用 uv + pip 组合（推荐，如果使用 uv）

### ⚠️ 注意：uv pip 不支持 download 命令

`uv pip` 不支持 `download` 子命令，需要使用以下方法：

### 方法1.1: 在 uv 虚拟环境中使用 pip（推荐）

```powershell
# Windows PowerShell
# 创建虚拟环境（如果还没有）
uv sync

# 在虚拟环境中运行 pip download
uv run pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/
```

```bash
# Linux/Mac
uv sync
uv run pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/
```

### 方法1.2: 激活虚拟环境后使用 pip

```powershell
# Windows PowerShell
uv sync
.venv\Scripts\Activate.ps1  # 注意：PowerShell 使用 Activate.ps1
pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/
```

```bash
# Linux/Mac
uv sync
source .venv/bin/activate
pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/
```

**注意**：在 Windows PowerShell 中：
- 使用 `.venv\Scripts\Activate.ps1` 而不是 `source .venv/bin/activate`
- 如果遇到执行策略错误，运行：`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 方法1.3: 使用系统 pip（如果已安装）

```bash
# 直接使用系统的 pip（不依赖 uv）
pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/
```

### 方法1.4: 使用 uv 安装 pip，然后使用 pip

```bash
# 使用 uv 安装 pip 到虚拟环境
uv pip install pip

# 然后使用 uv run 执行 pip download
uv run pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/
```

## 方法2: 使用 pip download（传统方式）

### 下载单个包

```bash
# 下载 aiohttp 及其所有依赖（Windows 版本）
pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/

# 或者指定 Python 版本
pip download aiohttp>=3.13.0 --platform win_amd64 --python-version 311 --only-binary=:all: -d wheels/
```

### 参数说明

- `--platform win_amd64`: 指定 Windows 64位平台
- `--only-binary=:all:`: 只下载二进制包（wheel），不下载源码包
- `-d wheels/`: 指定下载目录
- `--python-version 311`: 指定 Python 3.11（可选）

### 下载所有依赖

```bash
# 下载 aiohttp 及其所有依赖
pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/ --no-deps
pip download -r requirements.txt --platform win_amd64 --only-binary=:all: -d wheels/
```

## 方法3: 使用 pip wheel

```bash
# 构建 wheel 文件（需要先安装依赖）
pip wheel aiohttp>=3.13.0 --wheel-dir=wheels/
```

**注意**: 此方法需要在 Windows 系统上运行，或使用交叉编译。

## 方法4: 从 PyPI 直接下载

### 访问 PyPI 页面

1. 打开浏览器访问: https://pypi.org/project/aiohttp/#files
2. 找到对应的 wheel 文件（例如: `aiohttp-3.13.0-cp311-cp311-win_amd64.whl`）
3. 直接下载

### 使用 curl 或 wget 下载

```bash
# 下载特定版本的 wheel（需要知道确切的文件名）
curl -O https://files.pythonhosted.org/packages/XX/XX/XX/aiohttp-3.13.0-cp311-cp311-win_amd64.whl

# 或使用 wget
wget https://files.pythonhosted.org/packages/XX/XX/XX/aiohttp-3.13.0-cp311-cp311-win_amd64.whl
```

## 方法5: 批量下载所有依赖（推荐用于离线环境）

### 创建 requirements.txt

```bash
# 生成 requirements.txt
pip freeze > requirements.txt

# 或手动创建
echo "aiohttp>=3.13.0" > requirements.txt
```

### 下载所有依赖

```bash
# 下载所有依赖到 wheels 目录
pip download -r requirements.txt --platform win_amd64 --only-binary=:all: -d wheels/
```

## 方法6: 使用 pip download 下载依赖树

```bash
# 下载 aiohttp 及其所有依赖（包括间接依赖）
pip download aiohttp>=3.13.0 \
  --platform win_amd64 \
  --python-version 311 \
  --only-binary=:all: \
  -d wheels/ \
  --no-binary=:none:
```

## 在 Windows 上离线安装

下载完成后，在 Windows 系统上安装：

### 方法1: 使用安装脚本（推荐，智能检查）

```powershell
# Windows PowerShell
.\scripts\install_wheels.ps1

# 或指定参数
.\scripts\install_wheels.ps1 -Package "aiohttp" -WheelsDir "wheels" -MinVersion "3.13.0"
```

**特性**：
- ✅ 自动检测包是否已安装
- ✅ 如果已安装且满足版本要求，跳过安装（不升级）
- ✅ 自动检测 uv 或 pip
- ✅ 显示安装的版本信息

### 方法2: 手动使用 pip 安装

```powershell
# 在 uv 虚拟环境中
uv run pip install --find-links wheels/ --no-index aiohttp

# 或激活虚拟环境后
.venv\Scripts\activate
pip install --find-links wheels/ --no-index aiohttp
```

### 方法3: 使用 uv pip 安装

```powershell
# 使用 uv pip 安装
uv pip install --find-links wheels/ --no-index aiohttp

# 或安装特定文件
uv pip install wheels/aiohttp-3.13.0-cp311-cp311-win_amd64.whl
```

### Linux/Mac 安装

```bash
# 使用安装脚本
chmod +x scripts/install_wheels.sh
./scripts/install_wheels.sh aiohttp wheels 3.13.0

# 或手动安装
pip install --find-links wheels/ --no-index aiohttp
```

## 常见平台标识符

| 平台 | 标识符 |
|------|--------|
| Windows 64位 | `win_amd64` |
| Windows 32位 | `win32` |
| Linux 64位 | `manylinux1_x86_64`, `manylinux2014_x86_64` |
| macOS Intel | `macosx_10_9_x86_64` |
| macOS ARM | `macosx_11_0_arm64` |

## 完整示例脚本

### Windows 下载脚本（在 Windows 上运行）

```batch
@echo off
REM 创建下载目录
mkdir wheels 2>nul

REM 下载 aiohttp 及其依赖
pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/

echo 下载完成！文件保存在 wheels/ 目录
```

### Linux/Mac 下载脚本（为 Windows 下载）

```bash
#!/bin/bash
# 在 Linux/Mac 上为 Windows 下载 wheel 文件

mkdir -p wheels

# 下载 Windows 版本的 wheel
pip download aiohttp>=3.13.0 \
  --platform win_amd64 \
  --python-version 311 \
  --only-binary=:all: \
  -d wheels/

echo "下载完成！文件保存在 wheels/ 目录"
echo "将 wheels/ 目录复制到 Windows 系统后，运行："
echo "  pip install --find-links wheels/ --no-index aiohttp"
```

### 使用 uv 下载脚本

```powershell
# Windows PowerShell 脚本
# 创建目录
New-Item -ItemType Directory -Path wheels -Force | Out-Null

# 使用 uv 虚拟环境中的 pip
uv sync
uv run pip download aiohttp>=3.13.0 --platform win_amd64 --python-version 312 --only-binary=:all: -d wheels/

Write-Host "下载完成！文件保存在 wheels/ 目录" -ForegroundColor Green
Write-Host "在 Windows 上安装命令:" -ForegroundColor Cyan
Write-Host "  .\scripts\install_wheels.ps1" -ForegroundColor Yellow
```

```bash
#!/bin/bash
# Linux/Mac 脚本：使用 uv 下载 Windows 版本的 wheel 文件

mkdir -p wheels

# 使用 uv 虚拟环境中的 pip
uv sync
uv run pip download aiohttp>=3.13.0 \
  --platform win_amd64 \
  --python-version 312 \
  --only-binary=:all: \
  -d wheels/

echo "下载完成！文件保存在 wheels/ 目录"
echo "将 wheels/ 目录复制到 Windows 系统后，运行："
echo "  .\scripts\install_wheels.ps1"
```

## 验证下载的文件

```bash
# 查看下载的文件
ls wheels/

# 验证 wheel 文件
pip show aiohttp
```

## 注意事项

1. **Python 版本匹配**: 确保下载的 wheel 文件与目标 Python 版本匹配
   - Python 3.11: `cp311`
   - Python 3.12: `cp312`
   - 等等

2. **架构匹配**: 
   - 64位系统使用 `win_amd64`
   - 32位系统使用 `win32`

3. **依赖关系**: aiohttp 的依赖包括：
   - `attrs`
   - `multidict`
   - `yarl`
   - `frozenlist`
   - `aiosignal`
   - `async-timeout`
   - `aiohttp` 本身

4. **完整依赖下载**: 使用 `pip download` 时，会自动下载所有依赖

## 快速命令参考

### 使用 uv（推荐）

```bash
# 使用 uv pip download（最简单）
uv pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/

# 使用 uv 虚拟环境中的 pip
uv sync
uv run pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/
```

### 使用传统 pip

```bash
# 最简单的方式（在 Windows 上）
pip download aiohttp>=3.13.0 -d wheels/

# 在 Linux/Mac 上为 Windows 下载
pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/

# 下载并打包
pip download aiohttp>=3.13.0 --platform win_amd64 --only-binary=:all: -d wheels/
tar -czf aiohttp-wheels-windows.tar.gz wheels/
```

## 相关链接

- [PyPI aiohttp 页面](https://pypi.org/project/aiohttp/)
- [pip download 文档](https://pip.pypa.io/en/stable/cli/pip_download/)
- [Wheel 文件格式说明](https://www.python.org/dev/peps/pep-0427/)

