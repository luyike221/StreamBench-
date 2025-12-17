# 安装脚本使用说明

这些脚本用于在内网环境中从本地 wheel 文件安装 Python 包。

## 特性

- ✅ **智能检查**：自动检测包是否已安装
- ✅ **避免重复安装**：如果包已安装且满足版本要求，跳过安装
- ✅ **不升级**：已安装的包不会被升级
- ✅ **使用 pip**：使用 pip 进行安装（适用于 conda base 环境）
- ✅ **跨平台**：支持 Windows PowerShell 和 Linux/Mac Bash

## 前置要求

**重要**：使用前请先激活 conda base 环境

```powershell
# Windows PowerShell
conda activate base
```

```bash
# Linux/Mac
conda activate base
```

## Windows PowerShell 使用

### 基本用法

```powershell
# 1. 先激活 conda base 环境
conda activate base

# 2. 安装 aiohttp（默认参数）
.\scripts\install_wheels.ps1

# 3. 指定参数
.\scripts\install_wheels.ps1 -Package "aiohttp" -WheelsDir "wheels" -MinVersion "3.13.0"
```

### 参数说明

- `-Package`: 要安装的包名（默认: `aiohttp`）
- `-WheelsDir`: wheel 文件目录（默认: `wheels`）
- `-MinVersion`: 最低版本要求（默认: `3.13.0`）

### 执行策略问题

如果遇到执行策略错误，运行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Linux/Mac 使用

### 基本用法

```bash
# 添加执行权限
chmod +x scripts/install_wheels.sh

# 安装 aiohttp（默认参数）
./scripts/install_wheels.sh

# 指定参数
./scripts/install_wheels.sh aiohttp wheels 3.13.0
```

### 参数说明

```bash
./scripts/install_wheels.sh <包名> <wheel目录> <最低版本>
```

## 使用示例

### 示例1: 安装 aiohttp

```powershell
# Windows
.\scripts\install_wheels.ps1 -Package "aiohttp" -WheelsDir "wheels"
```

```bash
# Linux/Mac
./scripts/install_wheels.sh aiohttp wheels
```

### 示例2: 检查并安装（如果未安装）

脚本会自动检查：
- 如果包已安装且版本满足要求 → 跳过安装
- 如果包未安装或版本不满足 → 执行安装

## 工作流程

1. **检查 conda base 环境**
   - 检查 pip 是否可用
   - 如果不可用，提示激活 conda base 环境

2. **检查包是否已安装**
   - 使用 `pip show` 检查
   - 比较版本号

3. **如果已安装**
   - 显示已安装版本
   - 跳过安装（不升级）

4. **如果未安装**
   - 查找 wheel 文件
   - 使用 `pip install --find-links --no-index` 安装
   - 显示安装结果

## 注意事项

1. **conda 环境**：必须先激活 conda base 环境
2. **wheel 文件位置**：确保 wheel 文件在指定的目录中
3. **网络环境**：脚本使用 `--no-index` 参数，完全离线安装
4. **版本检查**：版本比较是简化版本，主要检查版本字符串
5. **不升级**：已安装的包不会被升级，只安装未安装的包

## 故障排除

### 问题1: 找不到 wheel 文件

```
错误: 在 wheels 目录中未找到 aiohttp 的 wheel 文件
```

**解决**：确保 wheel 文件已下载到指定目录

### 问题2: 找不到 pip 命令

```
错误: 未找到 pip 命令
请先激活 conda base 环境: conda activate base
```

**解决**：
```powershell
# Windows
conda activate base

# Linux/Mac
conda activate base
```

### 问题3: 安装失败

```
✗ 安装失败
```

**解决**：
- 检查是否已激活 conda base 环境
- 检查 wheel 文件是否完整
- 检查 Python 版本是否匹配
- 检查依赖是否都已下载

### 问题4: PowerShell 执行策略错误

```
无法加载文件，因为在此系统上禁止运行脚本
```

**解决**：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

