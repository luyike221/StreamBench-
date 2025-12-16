# API配置示例

## OpenAI API
```json
{
  "url": "https://api.openai.com/v1/chat/completions",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer sk-xxxxxxxxxxxxxxxx"
  },
  "body": {
    "model": "gpt-4",
    "messages": [
      {
        "role": "user",
        "content": "请写一个关于人工智能的文章"
      }
    ],
    "stream": true,
    "max_tokens": 500,
    "temperature": 0.7
  },
  "timeout": 300,
  "concurrency": 10,
  "total_requests": 100
}
```

## Anthropic Claude API
```json
{
  "url": "https://api.anthropic.com/v1/messages",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "x-api-key": "sk-ant-xxxxx",
    "anthropic-version": "2023-06-01"
  },
  "body": {
    "model": "claude-3-opus-20240229",
    "max_tokens": 1024,
    "messages": [
      {
        "role": "user",
        "content": "Hello, Claude!"
      }
    ],
    "stream": true
  },
  "timeout": 300,
  "concurrency": 5,
  "total_requests": 50
}
```

## Azure OpenAI
```json
{
  "url": "https://your-resource.openai.azure.com/openai/deployments/your-deployment/chat/completions?api-version=2023-05-15",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "api-key": "your-azure-api-key"
  },
  "body": {
    "messages": [
      {
        "role": "user",
        "content": "测试消息"
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

## 自建LLM服务 (兼容OpenAI格式)
```json
{
  "url": "http://localhost:8000/v1/chat/completions",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "model": "your-model-name",
    "messages": [
      {
        "role": "user",
        "content": "你好"
      }
    ],
    "stream": true,
    "max_tokens": 200
  },
  "timeout": 120,
  "concurrency": 20,
  "total_requests": 200
}
```

## 文心一言 API
```json
{
  "url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token=your_access_token",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "messages": [
      {
        "role": "user",
        "content": "你好"
      }
    ],
    "stream": true
  },
  "timeout": 300,
  "concurrency": 10,
  "total_requests": 100
}
```

## 通义千问 API
```json
{
  "url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer your-api-key",
    "X-DashScope-SSE": "enable"
  },
  "body": {
    "model": "qwen-turbo",
    "input": {
      "messages": [
        {
          "role": "user",
          "content": "你好"
        }
      ]
    },
    "parameters": {
      "result_format": "message",
      "incremental_output": true
    }
  },
  "timeout": 300,
  "concurrency": 10,
  "total_requests": 100
}
```