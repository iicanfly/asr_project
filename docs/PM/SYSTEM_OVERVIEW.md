# SYSTEM_OVERVIEW

## 项目目标
- 当前项目是一个“语音转文字 + 文档生成”的系统。
- 已实现三条主要能力：
  - 实时录音转写。
  - 上传音频文件转写。
  - 基于转写结果生成多种文档，并支持二次修改。
- 当前阶段的核心优化目标是：在不破坏内外网兼容性的前提下，大幅提升实时转写质量。

## 总体架构
项目整体由四层组成：

### 1. 配置与环境层
- 入口文件：`config.py`、`.env`
- 作用：
  - 根据 `USE_INTRANET` 切换内网 / 外网模式。
  - 统一提供 LLM、ASR、HTTPS、导出目录、临时目录等配置。

### 2. Python 后端层
- 入口文件：`main.py`
- 技术栈：
  - Flask：HTTP 接口与页面服务。
  - Flask-SocketIO：实时音频流与识别结果推送。
  - OpenAI SDK / `httpx`：调用 LLM 与 ASR 服务。
  - `python-docx`：导出 Word 文档。
- 核心职责：
  - 提供页面与静态资源入口。
  - 接收前端实时音频流。
  - 根据环境选择不同 ASR 调用方式。
  - 调用 LLM 生成或重生成文档。
  - 导出 Word 文档。
  - 接收上传音频并做离线转写。

### 3. Web 前端层
- 主要文件：
  - `templates/index.html`
  - `static/js/app.js`
  - `static/js/audio-processor.js`
  - `static/css/style.css`
- 核心职责：
  - 建立 Socket.IO 连接。
  - 采集麦克风音频。
  - 将前端 PCM 数据片段发送给后端。
  - 展示实时转写结果。
  - 维护转写缓存、离线补偿上传、历史文档、文档预览与导出。

### 4. Electron 封装层
- 主要文件：
  - `src/main/main.js`
  - `src/preload/preload.js`
  - 根目录 `index.html`
- 核心职责：
  - 以桌面应用方式运行系统。
  - 尝试自动拉起后端。
  - 创建桌面窗口并加载前端页面。

## 当前两种运行形态

### 形态 A：Web 形态
- Flask 提供 `/` 页面。
- 页面模板为 `templates/index.html`。
- 前端逻辑来自 `static/js/app.js` 与 `static/js/audio-processor.js`。
- 这是当前浏览器调试与实时转写主链路的核心形态。

### 形态 B：Electron 形态
- Electron 主进程尝试启动 Python 后端。
- Electron 窗口加载仓库根目录 `index.html`。
- 该入口与 Flask 模板入口不是同一套文件，存在重复实现与同步风险。

## 核心业务链路

### 链路 1：实时录音转写
1. 前端调用 `getUserMedia` 获取麦克风。
2. 通过 `AudioWorklet` 或 `ScriptProcessorNode` 读取音频。
3. 前端将浮点音频转换为 16-bit PCM。
4. 通过 Socket.IO 事件 `audio_stream` 发给后端。
5. 后端按 session 将音频缓存在内存和临时文件中。
6. 后端根据音频时长、静音检测、最大分片阈值决定是否触发转写。
7. 后端将 PCM 封装为 WAV。
8. 后端根据环境走不同 ASR 路径：
   - 外网：OpenAI 兼容 Chat / Audio 接口。
   - 内网：HTTP `POST /audio/transcriptions` 风格接口。
9. 后端对识别结果做简单过滤。
10. 后端通过 `asr_result` 事件推回前端。
11. 前端将结果并入当前转写列表并展示。

### 链路 2：上传音频转写
1. 用户在前端选择音频文件。
2. 前端通过 `/api/v1/audio/upload` 上传。
3. 后端保存文件到临时目录。
4. 后端根据环境选择 ASR 调用方式。
5. 返回识别文本给前端。

### 链路 3：文档生成
1. 前端收集当前转写列表。
2. 调用 `/api/v1/llm/summarize`。
3. 后端拼接转写文本，套用文档类型 Prompt。
4. 调用 LLM 生成结构化结果。
5. 前端展示生成内容，并允许用户继续修改或反馈重生成。

### 链路 4：文档重生成与导出
1. 用户提供反馈。
2. 前端调用 `/api/v1/llm/regenerate`。
3. 后端在原始转写基础上结合反馈重新生成文本。
4. 用户可调用 `/api/v1/export/word` 导出 `.docx`。
5. 下载实际通过 `/api/v1/export/download/<filename>` 完成。

## 当前实时转写主问题位置
当前实时转写质量问题主要集中在两侧：

### 后端音频处理侧
- `main.py`
- 重点区域：
  - `detect_silence`
  - `should_filter_asr_result`
  - `on_audio_stream`
- 主要影响：
  - 静音判定是否误触发。
  - 音频切片大小是否过碎。
  - 小段实时结果是否质量不足。

### 前端展示侧
- `static/js/app.js`
- 重点区域：
  - `setupAudioProcessing`
  - `handleASRResult`
  - `addMessageUI`
  - 缓存与补偿上传相关逻辑
- 主要影响：
  - 转写展示是否过碎。
  - 是否具备合理分段。
  - 是否支持“小段结果 -> 大段结果”的替换回写。

## 当前需要特别记住的结构事实
- 内外网差异的核心不在 LLM，而在 ASR 调用方式。
- Web 形态和 Electron 形态不是同一套前端入口：
  - Web 使用 `templates/index.html + static/*`
  - Electron 使用根目录 `index.html`
- 这意味着前端修改时必须先确认改的是哪一套入口，避免“网页调通了但桌面端没同步”。

## 待确认 / 高风险结构点
- Electron 主进程当前等待的后端端口是 `8000`，而 Flask 默认运行端口来自 `.env`，当前值为 `6543`。
- 这意味着 Electron 自动拉起链路是否完全可用，需要后续专门核对。
- 根目录 `index.html` 与 `templates/index.html` 可能长期存在功能漂移风险，后续可考虑统一入口或明确主次关系。

## 2026-05-10 / Sprint 0 ????
- Python ????????????ASR ?????
  - `main.py` ???? HTTP / Socket.IO ???
  - `services/asr_service.py` ???
    - ASR ????
    - WAV ??
    - ????
    - ??????
    - ??????
- ????????????????????? `services/asr_service.py` ? `static/js/app.js`??????????? `main.py`?
- Web ?????????????????????
  - `handleASRResult()` ????????????????????????????
  - ????????????????????
