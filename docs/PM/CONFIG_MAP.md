# CONFIG_MAP

## 说明
- 本文件只记录配置项的含义、作用范围和使用位置。
- 不在本文档中记录任何真实密钥值。
- 所有环境切换都应优先通过 `.env` 完成，而不是在代码中硬编码。

## 核心环境开关

### `USE_INTRANET`
- 含义：是否启用内网模式。
- 取值：
  - `False`：外网开发模式。
  - `True`：内网部署模式。
- 影响范围：
  - LLM 与 ASR 的地址、模型、鉴权信息选择。
- 主要使用位置：
  - `config.py`
  - `main.py` 状态接口与启动日志

## 外网 AI 配置

### `ONLINE_API_KEY`
- 含义：外网 LLM 主密钥。
- 使用位置：
  - `config.API_KEY`
  - `main.py` 中主 LLM 客户端初始化

### `ONLINE_BASE_URL`
- 含义：外网 LLM 基础地址。
- 使用位置：
  - `config.BASE_URL`
  - `main.py` 中主 LLM 客户端初始化

### `ONLINE_LLM_MODEL`
- 含义：外网文档生成使用的 LLM 模型名。
- 使用位置：
  - `/api/v1/llm/summarize`
  - `/api/v1/llm/regenerate`

### `ONLINE_ASR_BASE_URL`
- 含义：外网 ASR 基础地址。
- 使用位置：
  - `config.ASR_BASE_URL`
  - `main.py` 实时 ASR 与上传音频 ASR

### `ONLINE_ASR_API_KEY`
- 含义：外网 ASR 密钥。
- 使用位置：
  - `config.ASR_API_KEY`
  - `main.py` 中 `asr_client`

### `ONLINE_ASR_MODEL`
- 含义：外网 ASR 模型名。
- 使用位置：
  - 实时转写
  - 上传音频转写

### `ONLINE_ASR_MODE`
- 含义：外网 ASR 调用模式。
- 默认值：`chat`
- 影响：
  - `chat`：使用 OpenAI 兼容聊天接口传音频。
  - 其他值若切换到 `transcriptions`，会进入 HTTP 转写路径。

## 内网 AI 配置

### `INTRANET_API_KEY`
- 含义：内网 LLM 密钥。
- 使用位置：
  - `config.API_KEY`
  - `main.py` 中主 LLM 客户端初始化

### `INTRANET_BASE_URL`
- 含义：内网 LLM 基础地址。
- 使用位置：
  - `config.BASE_URL`
  - `main.py` 中主 LLM 客户端初始化

### `INTRANET_LLM_MODEL`
- 含义：内网文档生成使用的 LLM 模型名。
- 使用位置：
  - `/api/v1/llm/summarize`
  - `/api/v1/llm/regenerate`

### `INTRANET_ASR_BASE_URL`
- 含义：内网 ASR 基础地址。
- 使用位置：
  - `config.ASR_BASE_URL`
  - `main.py` 中 HTTP 转写路径

### `INTRANET_ASR_API_KEY`
- 含义：内网 ASR 密钥。
- 使用位置：
  - `config.ASR_API_KEY`
  - 当前代码中主要保留为配置项，HTTP 转写路径本身未显式附带认证头

### `INTRANET_ASR_MODEL`
- 含义：内网 ASR 模型名。
- 使用位置：
  - 实时转写
  - 上传音频转写

### `INTRANET_ASR_MODE`
- 含义：内网 ASR 调用模式。
- 默认值：`transcriptions`
- 影响：
  - 进入 `httpx.post(.../audio/transcriptions)` 路径。

## 服务监听配置

### `HOST`
- 含义：Flask / Socket.IO 监听地址。
- 默认值：`0.0.0.0`
- 使用位置：
  - `main.py` 启动服务

### `PORT`
- 含义：Flask / Socket.IO 监听端口。
- 默认值：`6543`
- 使用位置：
  - `main.py` 启动服务
- 注意：
  - 当前 Electron 主进程等待的端口写死为 `8000`，与该默认值不一致，需要后续统一确认。

## HTTPS 配置

### `ENABLE_HTTPS`
- 含义：是否启用 HTTPS。
- 原因：
  - 浏览器在非 `localhost` 环境下访问麦克风时，通常需要 HTTPS。
- 使用位置：
  - `main.py` 启动阶段决定是否加载证书

### `SSL_CERT`
- 含义：证书文件路径。
- 使用位置：
  - `main.py`

### `SSL_KEY`
- 含义：私钥文件路径。
- 使用位置：
  - `main.py`

### `SECRET_KEY`
- 含义：Flask `SECRET_KEY`
- 使用位置：
  - `main.py` 中 `app.config['SECRET_KEY']`

## 目录配置

### `EXPORT_DIR`
- 含义：导出 Word 文件存放目录。
- 使用位置：
  - `main.py` 初始化目录
  - `/api/v1/export/word`
  - `/api/v1/export/download/<filename>`

### `TEMP_DIR`
- 含义：临时音频与流式录音原始数据存放目录。
- 使用位置：
  - `main.py` 初始化目录
  - 实时录音 session 文件
  - 上传音频文件落盘

## 运行时派生配置

### `config.API_KEY`
- 含义：当前环境实际生效的 LLM 密钥。
- 来源：
  - 外网时取 `ONLINE_API_KEY`
  - 内网时取 `INTRANET_API_KEY`

### `config.BASE_URL`
- 含义：当前环境实际生效的 LLM 基础地址。

### `config.ASR_API_KEY`
- 含义：当前环境实际生效的 ASR 密钥。

### `config.ASR_BASE_URL`
- 含义：当前环境实际生效的 ASR 基础地址。

### `config.ASR_MODEL`
- 含义：当前环境实际生效的 ASR 模型名。

### `config.LLM_MODEL`
- 含义：当前环境实际生效的 LLM 模型名。

### `config.ASR_MODE`
- 含义：当前环境实际生效的 ASR 调用模式。
- 当前设计意义：
  - 这是内外网 ASR 调用方式分流的关键配置。

## 当前配置上的重要结论
- LLM 路径基本通过一套 OpenAI 兼容客户端抽象完成。
- ASR 路径才是内外网差异最大的地方，后续修改时优先保护。
- 所有优化实时转写的改动，都应先检查是否会影响 `ASR_MODE` 分流逻辑。

## 2026-05-10 / 实时转写门槛覆盖补充
### 通用实时门槛覆盖
- 前缀：
  - `REALTIME_`
- 示例：
  - `REALTIME_CHUNK_SECONDS`
  - `REALTIME_MIN_ACTIVE_RATIO`
  - `REALTIME_MIN_VOICED_DENSITY_FOR_SOFT_SPEECH`
- 作用：
  - 覆盖 `RealtimeChunkPolicy` 的默认值，适合做全局调参。

### 环境专属实时门槛覆盖
- 外网前缀：
  - `ONLINE_REALTIME_`
- 内网前缀：
  - `INTRANET_REALTIME_`
- 优先级：
  - 环境专属覆盖优先于通用 `REALTIME_`。
- 作用：
  - 允许外网和内网在不改代码的前提下使用不同的实时转写门槛。

### 当前已落地的相关调参
- 外网 partial 触发门槛：
  - `ONLINE_REALTIME_MIN_AUDIO_SECONDS=1.5`
  - 含义：当前外网环境下，实时 partial 以约 1.5 秒最小时长作为基础触发门槛。
- 中级回写节奏：
  - `MEDIUM_REWRITE_SECONDS=6.0`
  - 含义：当前三级回写中的 `medium_rewrite` 以约 6 秒为一档滚动触发，而不是旧的 10 秒档。
- 空闲自动分段：
  - `IDLE_SEGMENT_SPLIT_SECONDS=3.0`
  - 含义：当前会话若连续约 3 秒没有明显有效活动，会先 flush 缓冲区，再对当前段做一次收尾并等待下一段。
