# Windows PowerShell 脚本：从本地 wheel 文件安装包（智能检查，避免重复安装）
# 使用方法: .\install_wheels.ps1
# 注意: 请先激活 conda base 环境: conda activate base

param(
    [string]$Package = "aiohttp",
    [string]$WheelsDir = "wheels",
    [string]$MinVersion = "3.13.0"
)

# 检查 wheel 目录是否存在
if (-not (Test-Path $WheelsDir)) {
    Write-Host "错误: wheel 目录不存在: $WheelsDir" -ForegroundColor Red
    Write-Host "请确保 wheel 文件已下载到 $WheelsDir 目录" -ForegroundColor Yellow
    exit 1
}

# 检查 pip 是否可用
if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
    Write-Host "错误: 未找到 pip 命令" -ForegroundColor Red
    Write-Host "请先激活 conda base 环境: conda activate base" -ForegroundColor Yellow
    exit 1
}

# 检查包是否已安装
function Test-PackageInstalled {
    param([string]$packageName, [string]$minVersion)
    
    # 使用 pip 检查
    $result = pip show $packageName 2>&1
    if ($LASTEXITCODE -eq 0) {
        $versionLine = $result | Select-String "Version:"
        if ($versionLine) {
            $installedVersion = ($versionLine -split ":")[1].Trim()
            Write-Host "已安装 $packageName 版本: $installedVersion" -ForegroundColor Green
            
            if ($minVersion) {
                Write-Host "要求最低版本: $minVersion" -ForegroundColor Gray
                # 简单版本比较：如果已安装版本 >= 要求版本，或包含要求版本字符串
                if ($installedVersion -ge $minVersion -or $installedVersion -like "*$minVersion*") {
                    return $true
                }
            } else {
                return $true
            }
        }
    }
    return $false
}

# 检查包是否已安装
Write-Host "`n检查 $Package 是否已安装..." -ForegroundColor Cyan
if (Test-PackageInstalled -packageName $Package -minVersion $MinVersion) {
    Write-Host "`n✓ $Package 已安装且满足版本要求，跳过安装" -ForegroundColor Green
    exit 0
}

Write-Host "$Package 未安装或版本不满足要求，开始安装..." -ForegroundColor Yellow

# 查找 wheel 文件
$wheelFiles = Get-ChildItem -Path $WheelsDir -Filter "$Package*.whl" -ErrorAction SilentlyContinue

if ($wheelFiles.Count -eq 0) {
    Write-Host "`n错误: 在 $WheelsDir 目录中未找到 $Package 的 wheel 文件" -ForegroundColor Red
    Write-Host "请确保 wheel 文件已下载到 $WheelsDir 目录" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n找到 $($wheelFiles.Count) 个 wheel 文件:" -ForegroundColor Cyan
$wheelFiles | ForEach-Object {
    Write-Host "  - $($_.Name)" -ForegroundColor Gray
}

# 执行安装
Write-Host "`n开始安装..." -ForegroundColor Cyan

# 使用 pip 安装
Write-Host "使用 pip 安装..." -ForegroundColor Cyan
pip install --find-links $WheelsDir --no-index $Package

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ 安装成功！" -ForegroundColor Green
    
    # 显示安装的版本
    $result = pip show $Package 2>&1
    if ($LASTEXITCODE -eq 0) {
        $versionLine = $result | Select-String "Version:"
        if ($versionLine) {
            $version = ($versionLine -split ":")[1].Trim()
            Write-Host "安装版本: $version" -ForegroundColor Green
        }
    }
} else {
    Write-Host "`n✗ 安装失败" -ForegroundColor Red
    exit 1
}

Write-Host "`n安装完成！" -ForegroundColor Green

