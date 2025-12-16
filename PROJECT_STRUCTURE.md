# 项目结构说明

## 目录结构

```
ai_benchmark/
├── src/                    # 代码部分
│   └── stream_test_enhanced.py    # 主程序文件
│
├── configs/                 # 配置部分
│   ├── config_dify.json           # Dify API配置
│   ├── config_dify_fixed.json     # Dify API配置（修复版）
│   ├── config_dify_with_csv.json  # Dify API配置（CSV数据源）
│   ├── config_csv_example.json   # CSV数据源示例配置
│   └── model_config.json          # 模型配置示例
│
├── data/                    # 数据备份
│   ├── test_data.csv              # 测试数据CSV文件
│   └── test_results.json          # 测试结果（自动生成）
│
├── docs/                    # 文档
│   ├── STREAM_DETECTION.md        # 流式检测机制说明
│   └── 测试命令.md                # 测试命令说明
│
├── .venv/                   # Python虚拟环境（uv自动创建）
├── pyproject.toml           # 项目配置
├── uv.lock                  # 依赖锁文件
└── README.md                # 项目说明
```

## 目录说明

### src/ - 代码部分
存放所有Python源代码文件。

**文件**:
- `stream_test_enhanced.py`: 流式接口并发测试主程序

### configs/ - 配置部分
存放所有JSON配置文件。

**文件**:
- `config_dify.json`: Dify API基础配置
- `config_dify_fixed.json`: Dify API配置（修复版，包含必填字段）
- `config_dify_with_csv.json`: Dify API配置（支持CSV数据源）
- `config_csv_example.json`: CSV数据源使用示例
- `model_config.json`: 模型配置示例

### data/ - 数据备份
存放测试数据和测试结果。

**文件**:
- `test_data.csv`: 测试数据CSV文件（用于CSV数据源）
- `test_results.json`: 测试结果文件（程序自动生成）

### docs/ - 文档
存放项目文档。

**文件**:
- `STREAM_DETECTION.md`: 流式响应检测机制详细说明
- `测试命令.md`: 测试命令使用说明

## 使用方式

### 运行测试

```bash
# 从项目根目录运行
uv run python src/stream_test_enhanced.py -c configs/config_dify.json
```

### 配置文件路径

配置文件中的相对路径是相对于配置文件所在目录（`configs/`）的：

```json
{
    "data_source": {
        "type": "csv",
        "file": "../data/test_data.csv"  // 相对于configs/目录
    }
}
```

### 测试结果

测试结果默认保存在 `data/test_results.json`。

## 注意事项

1. **路径引用**: 
   - 代码中引用配置文件：使用 `configs/xxx.json`
   - 配置文件中引用CSV：使用相对路径 `../data/xxx.csv`

2. **环境变量**: 
   - `.venv/` 目录由uv自动管理，不要手动修改
   - `uv.lock` 文件自动生成，建议提交到版本控制

3. **数据文件**:
   - `data/` 目录中的 `test_results.json` 会被程序覆盖
   - 如需备份，请手动复制到其他位置
