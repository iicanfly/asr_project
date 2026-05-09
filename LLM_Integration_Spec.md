# 内网大模型接口对接技术规范书 (LLM API Spec)

## 1. 概述
本规范定义了本语音识别系统与内网大模型（如 Qwen, Llama, ChatGLM 等）之间的交互标准，确保在隔离环境下的高可用性与数据安全性。

## 2. ASR 语音识别接口 (WebSocket)
### 2.1 接口地址
`ws://[ASR_SERVER_IP]:[PORT]/asr/v1/stream`

### 2.2 请求参数 (Binary)
- **格式**: PCM Raw, 16bit, 16000Hz, 单声道。
- **分片**: 建议每 100ms - 200ms 发送一次数据包。

### 2.3 返回参数 (JSON)
```json
{
    "text": "识别到的文本内容",
    "is_final": true,
    "speaker_id": "Speaker_1",
    "confidence": 0.98
}
```

## 3. LLM 会议纪要接口 (HTTP POST)
### 3.1 接口地址
`http://[LLM_SERVER_IP]:[PORT]/api/v1/generate`

### 3.2 请求体
```json
{
    "model": "qwen-14b",
    "prompt": "请根据以下内容生成纪要...",
    "stream": false,
    "temperature": 0.3
}
```

## 4. 容错与补偿规范
- **重试机制**: 当 HTTP 5xx 错误时，系统需自动重试 3 次，间隔 1s。
- **超时设置**: ASR 握手超时需控制在 3s 内，LLM 响应超时控制在 30s 内。
- **安全隔离**: 所有 API 调用必须在内网 VPC 内完成，禁止任何外网域名解析。
