#!/bin/bash
# Linux/Mac 脚本：从本地 wheel 文件安装包（智能检查，避免重复安装）
# 使用方法: ./install_wheels.sh

PACKAGE="${1:-aiohttp}"
WHEELS_DIR="${2:-wheels}"
MIN_VERSION="${3:-3.13.0}"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# 检查 wheel 目录是否存在
if [ ! -d "$WHEELS_DIR" ]; then
    echo -e "${RED}错误: wheel 目录不存在: $WHEELS_DIR${NC}"
    echo -e "${YELLOW}请确保 wheel 文件已下载到 $WHEELS_DIR 目录${NC}"
    exit 1
fi

# 检查 pip 是否可用
if ! command -v pip &> /dev/null; then
    echo -e "${RED}错误: 未找到 pip 命令${NC}"
    echo -e "${YELLOW}请先激活 conda base 环境: conda activate base${NC}"
    exit 1
fi

# 检查包是否已安装
check_package_installed() {
    local pkg=$1
    local min_ver=$2
    
    # 使用 pip 检查
    if pip show "$pkg" > /dev/null 2>&1; then
        local installed_ver=$(pip show "$pkg" 2>/dev/null | grep "^Version:" | awk '{print $2}')
        if [ -n "$installed_ver" ]; then
            echo -e "${GREEN}已安装 $pkg 版本: $installed_ver${NC}"
            if [ -n "$min_ver" ]; then
                echo -e "${GRAY}要求最低版本: $min_ver${NC}"
                # 简单版本比较
                if [ "$installed_ver" = "$min_ver" ] || [ "$installed_ver" \> "$min_ver" ] 2>/dev/null; then
                    return 0
                fi
            else
                return 0
            fi
        fi
    fi
    return 1
}

# 检查包是否已安装
echo -e "\n${CYAN}检查 $PACKAGE 是否已安装...${NC}"
if check_package_installed "$PACKAGE" "$MIN_VERSION"; then
    echo -e "\n${GREEN}✓ $PACKAGE 已安装且满足版本要求，跳过安装${NC}"
    exit 0
fi

echo -e "${YELLOW}$PACKAGE 未安装或版本不满足要求，开始安装...${NC}"

# 查找 wheel 文件
WHEEL_FILES=$(find "$WHEELS_DIR" -name "${PACKAGE}*.whl" 2>/dev/null)

if [ -z "$WHEEL_FILES" ]; then
    echo -e "\n${RED}错误: 在 $WHEELS_DIR 目录中未找到 $PACKAGE 的 wheel 文件${NC}"
    echo -e "${YELLOW}请确保 wheel 文件已下载到 $WHEELS_DIR 目录${NC}"
    exit 1
fi

echo -e "\n${CYAN}找到以下 wheel 文件:${NC}"
echo "$WHEEL_FILES" | while read -r file; do
    echo -e "${GRAY}  - $(basename "$file")${NC}"
done

# 执行安装
echo -e "\n${CYAN}开始安装...${NC}"

# 使用 pip 安装
echo -e "${CYAN}使用 pip 安装...${NC}"
pip install --find-links "$WHEELS_DIR" --no-index "$PACKAGE"

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ 安装成功！${NC}"
    
    # 显示安装的版本
    INSTALLED_VER=$(pip show "$PACKAGE" 2>/dev/null | grep "^Version:" | awk '{print $2}')
    if [ -n "$INSTALLED_VER" ]; then
        echo -e "${GREEN}安装版本: $INSTALLED_VER${NC}"
    fi
else
    echo -e "\n${RED}✗ 安装失败${NC}"
    exit 1
fi

echo -e "\n${GREEN}安装完成！${NC}"

