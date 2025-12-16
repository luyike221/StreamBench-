# 流式接口并发测试工具

专门用于测试流式API（如ChatGPT、Claude等）的并发性能，精确测量首token时间(TTFT)和总体性能。

## 核心特性

✅ **固定并发控制** - 保持恒定并发数，一个请求完成后立即开启下一个  
✅ **首Token时间测试** - 精确测量每个请求的TTFT (Time To First Token)  
✅ **完整性能指标** - 统计P50/P90/P95/P99等关键指标  
✅ **灵活配置** - 支持配置文件和命令行参数  
✅ **CSV数据源支持** - 从CSV文件读取测试数据，每次请求使用不同内容  
✅ **详细报告** - 实时进度显示和完整JSON结果导出  

## 安装依赖

```bash
pip install aiohttp
```

## 快速开始

### 方式1: 使用配置文件（推荐）

1. 编辑 `config.json` 配置你的接口信息：

```json
{
  "url": "https://api.openai.com/v1/chat/completions",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer sk-your-api-key"
  },
  "body": {
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "写一个关于AI的短文"}
    ],
    "stream": true,
    "max_tokens": 500
  },
  "timeout": 300,
  "concurrency": 10,
  "total_requests": 100
}
```

2. 运行测试：

```bash
python stream_test_enhanced.py -c config.json
```

### 方式2: 使用命令行参数

```bash
python stream_test_enhanced.py -u https://api.example.com/stream -n 50 -p 10
```

参数说明：
- `-c, --config`: 配置文件路径
- `-u, --url`: 接口URL
- `-n, --requests`: 总请求数（默认100）
- `-p, --concurrency`: 并发数（默认10）

### 方式3: 直接修改代码

编辑 `stream_concurrent_test.py` 中的配置区域：

```python
config = RequestConfig(
    url="https://your-api.com/v1/stream",
    method="POST",
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer your-token",
    },
    body={
        "prompt": "你的提示词",
        "stream": True,
        "max_tokens": 100
    }
)

CONCURRENCY = 10        # 并发数
TOTAL_REQUESTS = 50     # 总请求数
```

运行：

```bash
python stream_concurrent_test.py
```

## 配置说明

### RequestConfig 参数

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| url | string | 流式接口URL | `https://api.openai.com/v1/chat/completions` |
| method | string | HTTP方法 | `POST` (默认) |
| headers | dict | 请求头 | `{"Authorization": "Bearer xxx"}` |
| body | dict | 请求体 | `{"stream": true, "messages": [...]}` |
| timeout | int | 超时时间(秒) | `300` (默认) |

### 测试参数

- **concurrency**: 并发数（同时进行的请求数量）
- **total_requests**: 总请求数（测试的总请求次数）

### CSV数据源配置（新增功能）

支持从CSV文件读取测试数据，每次请求自动使用CSV中的一行内容。

#### 1. 创建CSV文件

创建 `test_data.csv` 文件，例如：

```csv
content,topic,category
写一个关于人工智能的短文,AI,科技
介绍Python编程语言的特点和应用,编程,技术
分析机器学习算法的优缺点,ML,科技
解释深度学习的原理,深度学习,科技
讨论自然语言处理的发展趋势,NLP,科技
```

#### 2. 配置数据源

在 `config.json` 中添加 `data_source` 配置：

```json
{
  "url": "https://api.example.com/v1/chat/completions",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer sk-xxxxxxxxxxxxxxxx"
  },
  "data_source": {
    "type": "csv",
    "file": "test_data.csv",
    "column": "content",
    "encoding": "utf-8"
  },
  "body": {
    "model": "gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "{{content}}"
      }
    ],
    "stream": true,
    "max_tokens": 500
  },
  "timeout": 300,
  "concurrency": 10,
  "total_requests": 100
}
```

#### 3. 占位符说明

- 使用 `{{column_name}}` 格式在 `body` 中指定占位符
- 占位符会被CSV对应列的值替换
- 支持多个占位符，例如：`"{{topic}} - {{content}}"`
- 如果请求数大于CSV行数，会自动循环使用数据

#### 4. 数据源配置参数

| 参数 | 类型 | 说明 | 必填 |
|------|------|------|------|
| type | string | 数据源类型，目前支持 `csv` | 是 |
| file | string | CSV文件路径（相对路径相对于配置文件所在目录） | 是 |
| column | string | 指定使用的列名（可选，默认使用所有列） | 否 |
| encoding | string | 文件编码（默认 `utf-8`） | 否 |

#### 5. 示例

查看 `config_csv_example.json` 和 `test_data.csv` 获取完整示例。

## 输出报告

### 实时输出

```
[001] 首token: 0.234s
[001] 完成: 2.456s | 45 chunks | 18.32 chunks/s | 12.34 KB
进度: 1/100 | 已用时: 2.5s
```

### 最终报告

```
============================================================
测试报告
============================================================

【总体统计】
  总请求数:    100
  成功:        98 (98.0%)
  失败:        2 (2.0%)
  总耗时:      25.67s
  吞吐量:      3.90 req/s

【首Token时间 (TTFT)】
  最小值:      0.123s
  最大值:      1.234s
  平均值:      0.456s
  中位数:      0.432s
  标准差:      0.089s
  P50:         0.432s
  P90:         0.678s
  P95:         0.789s
  P99:         1.012s

【总耗时】
  最小值:      1.234s
  最大值:      5.678s
  平均值:      2.345s
  中位数:      2.234s
  P95:         3.456s
  P99:         4.567s

【生成速率】
  平均值:      18.45 chunks/s
  中位数:      17.89 chunks/s
  最大值:      25.67 chunks/s
```

### JSON结果文件

测试完成后会生成 `test_results.json`，包含每个请求的详细指标：

```json
{
  "config": {
    "url": "https://api.example.com/stream",
    "concurrency": 10,
    "total_requests": 100,
    "timestamp": "2024-01-15T10:30:00"
  },
  "summary": {
    "success_count": 98,
    "failed_count": 2
  },
  "metrics": [
    {
      "request_id": 1,
      "ttft": 0.234,
      "total_time": 2.456,
      "total_tokens": 45,
      "tokens_per_second": 18.32,
      "error": null
    }
  ]
}
```

## 关键指标说明

### TTFT (Time To First Token)
- **定义**: 从请求发送到收到第一个响应数据块的时间
- **重要性**: 衡量API的响应速度，影响用户体验
- **优化目标**: 越低越好，通常应 < 1秒

### 总耗时
- **定义**: 请求从开始到完全结束的时间
- **包含**: 网络延迟 + 首token时间 + 流式生成时间

### 生成速率 (Tokens/Second)
- **定义**: 每秒生成的token数量
- **用途**: 评估流式输出的速度

### Percentile (百分位数)
- **P50**: 中位数，50%的请求优于此值
- **P95**: 95%的请求优于此值
- **P99**: 99%的请求优于此值
- **用途**: 识别异常值和性能瓶颈

## 并发控制原理

脚本使用**信号量(Semaphore)**实现固定并发：

```
并发数 = 10

[请求1] [请求2] [请求3] ... [请求10]  ← 同时进行
   ↓ 完成
[请求11] 开始                          ← 立即补充
```

特点：
- ✅ 始终保持10个并发
- ✅ 某个请求完全结束后才开启新请求
- ✅ 不会出现并发数波动

## 使用场景

### 1. 压力测试
评估API在高并发下的表现：
```bash
python stream_test_enhanced.py -c config.json
# 设置: concurrency=50, total_requests=500
```

### 2. 性能基准测试
对比不同模型或配置的性能：
```bash
# 测试模型A
python stream_test_enhanced.py -c config_model_a.json

# 测试模型B
python stream_test_enhanced.py -c config_model_b.json
```

### 3. 持续监控
定期测试API性能变化：
```bash
# 每小时执行一次
*/60 * * * * /usr/bin/python3 /path/to/stream_test_enhanced.py -c config.json
```

## 常见问题

### Q: 如何测试本地API？
A: 修改URL为本地地址：
```json
{
  "url": "http://localhost:8000/v1/stream",
  ...
}
```

### Q: 如何处理认证？
A: 在headers中添加认证信息：
```json
{
  "headers": {
    "Authorization": "Bearer your-token",
    "X-API-Key": "your-api-key"
  }
}
```

### Q: 超时如何处理？
A: 调整timeout参数（单位：秒）：
```json
{
  "timeout": 600  // 10分钟
}
```

### Q: 如何测试非流式接口？
A: 此工具专为流式接口设计，非流式接口建议使用其他工具（如Apache Bench、wrk）

### Q: Token计数不准确？
A: 脚本按chunk数量计数，如需精确token数，需根据具体API协议解析响应内容

## 文件说明

- `stream_concurrent_test.py` - 基础版本（直接修改代码配置）
- `stream_test_enhanced.py` - 增强版本（支持配置文件和命令行）
- `config.json` - 配置文件示例
- `test_results.json` - 测试结果输出（自动生成）

## 注意事项

1. ⚠️ **API限流**: 注意目标API的速率限制，避免被封禁
2. ⚠️ **成本控制**: 大量请求可能产生费用
3. ⚠️ **网络带宽**: 高并发测试需要足够的网络带宽
4. ⚠️ **资源限制**: 注意本地系统的文件描述符限制

## License

MIT License