# API_FLOW

## 说明
- 本文件记录当前项目的主要数据流与调用流。
- 重点覆盖实时转写主链路，因为这是当前最核心的优化对象。

## 流程总览
当前系统有四条主链路：
- 实时录音转写链路。
- 上传音频转写链路。
- 文档生成链路。
- 文档重生成与导出链路。

## 1. 实时录音转写链路

### 前端采集阶段
入口位置：
- `static/js/app.js`
- `static/js/audio-processor.js`

主要步骤：
1. `toggleRecording()` 根据状态决定启动或停止录音。
2. `startRecording()` 调用 `navigator.mediaDevices.getUserMedia()` 获取麦克风。
3. `setupAudioProcessing()` 创建 `AudioContext` 与 `MediaStreamSource`。
4. 优先尝试加载 `AudioWorklet`：
   - 模块路径：`/static/js/audio-processor.js`
   - 处理器：`AudioProcessor`
5. 如果 `AudioWorklet` 不可用，则回退到 `ScriptProcessorNode`。
6. 采集到的 `Float32Array` 音频片段先放入 `audioChunks`。
7. 每个片段都会调用 `convertFloat32To16BitPCM()` 转为 16-bit PCM。
8. 如果 Socket 已连接，则通过 `socket.emit('audio_stream', pcmData)` 推送给后端。

### 后端缓冲与切片阶段
入口位置：
- `main.py` 的 `on_audio_stream(data)`

主要步骤：
1. 通过 `request.sid` 找到当前客户端 session。
2. `SessionManager.get_or_create()` 为 session 创建或复用：
   - 内存缓冲区 `buffer`
   - 会话状态 `processing`
   - 临时 PCM 文件句柄
3. 当前 PCM 片段同时写入：
   - session 内存缓冲区
   - `TEMP_DIR` 下的原始 PCM 文件
4. 如果当前 session 正在处理上一段音频，则新到数据只继续缓存，不触发并发处理。

### 后端触发转写阶段
核心判断位置：
- `main.py` 中的 `on_audio_stream(data)`

当前触发规则：
1. 如果累计音频长度超过 `ASR_MAX_AUDIO_SECONDS`，强制触发。
2. 如果累计音频长度超过 `ASR_CHUNK_SECONDS`，触发。
3. 如果累计音频长度超过 `ASR_MIN_AUDIO_SECONDS`，则进一步根据静音检测决定是否触发。

当前静音检测逻辑：
1. 对缓冲区末尾一小段音频调用 `detect_silence()`
2. `detect_silence()` 会：
   - 将 PCM bytes 解码为整型样本
   - 分帧计算 RMS 和最大幅值
   - 统计静音帧比例
3. 静音帧比例大于阈值时，认为当前片段可结束并触发转写。

### 后端 ASR 调用阶段
主要分流依据：
- `config.ASR_MODE`

分流逻辑：
- 当 `ASR_MODE == 'transcriptions'`：
  - 使用 `httpx.post()` 请求 `ASR_BASE_URL + /audio/transcriptions`
  - 以 `multipart/form-data` 上传 WAV 文件
  - 这是当前内网路径
- 其他情况：
  - 将 WAV 数据转为 base64
  - 通过 OpenAI 兼容 `chat.completions.create()` 发送音频内容
  - 这是当前外网路径

### 后端结果过滤与回推阶段
主要位置：
- `main.py` 的 `should_filter_asr_result()`
- `main.py` 的 `emit("asr_result", ...)`

当前行为：
1. 如果识别结果为空，直接丢弃。
2. 如果命中过滤规则，也不回推到前端。
3. 其余结果统一以：
   - `speaker_id = "Speaker_1"`
   - `text = text_result`
   - `is_final = True`
   的形式推送给前端。

### 前端结果展示阶段
入口位置：
- `static/js/app.js` 的 `handleASRResult(data)`

主要步骤：
1. 清除空状态占位符。
2. 生成当前时间戳。
3. 根据以下条件决定是合并到上一条还是新建一条：
   - 同一个 `speaker_id`
   - 与上一条间隔小于 10 秒
4. 调用 `addMessageUI()` 渲染 UI。
5. 更新 `transcriptData`。
6. 调用 `saveCache()` 持久化到浏览器 `localStorage`。

### 当前链路特点
- 实时链路本质上是“前端连续送 PCM，后端按阈值切片后再做批量识别”。
- 当前并不是逐帧流式 ASR，而是“伪流式分段识别 + 前端增量展示”。
- 当前前端只有“追加 / 合并”逻辑，还没有“旧结果被新结果替换”的机制。

## 2. 上传音频转写链路

### 前端阶段
入口位置：
- `handleFileUpload(event)`

主要步骤：
1. 用户选择一个或多个音频文件。
2. 前端逐个构造 `FormData`。
3. 调用 `POST /api/v1/audio/upload`
4. 返回结果后调用 `handleASRResult()` 直接并入转写列表。

### 后端阶段
入口位置：
- `upload_audio()`

主要步骤：
1. 校验是否存在 `file`。
2. 将文件保存到 `TEMP_DIR`。
3. 根据 `ASR_MODE` 选择 ASR 路径。
4. 返回：
   - `status`
   - `filename`
   - `transcript`
   - `speaker_id`

## 3. 文档生成链路

### 前端阶段
入口位置：
- `generateDocument(docType)`

主要步骤：
1. 收集当前 `transcriptData`。
2. 调用 `POST /api/v1/llm/summarize`
3. 携带：
   - `transcript`
   - `doc_type`
4. 后端返回文档标题与正文后，前端进行展示、历史存储与后续导出。

### 后端阶段
入口位置：
- `summarize_meeting()`

主要步骤：
1. 校验 `transcript` 是否为空。
2. 调用 `build_transcript_text()` 拼接转写文本。
3. 按 `doc_type` 选择 Prompt 模板。
4. 调用 `client.chat.completions.create()`
5. 用 `parse_doc_response()` 从 LLM 输出中提取：
   - 文档标题
   - 正文内容
6. 返回 JSON 给前端。

## 4. 文档重生成链路

### 前端阶段
入口位置：
- `regenerateDocument()`

主要步骤：
1. 收集转写内容与用户反馈。
2. 调用 `POST /api/v1/llm/regenerate`

### 后端阶段
入口位置：
- `regenerate_document()`

主要步骤：
1. 校验 `transcript` 与 `feedback`。
2. 将用户反馈嵌入增强 Prompt。
3. 调用 LLM 重新生成文档。
4. 返回新标题与新正文。

## 5. Word 导出链路

### 前端阶段
入口位置：
- `downloadMinutes()`
- `downloadHistoryDoc()`

### 后端阶段
入口位置：
- `export_word()`
- `download_file(filename)`

主要步骤：
1. 前端把当前文档摘要和转写列表提交给 `/api/v1/export/word`
2. 后端用 `python-docx` 生成 `.docx`
3. 后端返回下载 URL
4. 前端再请求 `/api/v1/export/download/<filename>`

## 6. 本地缓存与离线补偿链路

### 本地缓存
主要位置：
- `saveCache()`
- `loadCache()`
- `updateCacheInfo()`

作用：
- 将 `transcriptData` 存入浏览器 `localStorage`
- 在刷新或返回页面后恢复会话

### 音频补偿
主要位置：
- `saveAudioToLocal()`
- `checkPendingAudio()`
- `uploadCachedAudio()`

作用：
- 在后端不在线或中断时，本地保存原始录音
- 当后端恢复可用时，再走上传识别作为补偿

## 当前最需要关注的数据流缺口
- 实时转写只有“切片后提交识别”的单层链路，没有“小段粗识别 + 大段精识别”的双层链路。
- 前端 `handleASRResult()` 只有追加和合并，没有替换已有片段的能力。
- `speaker_id` 当前基本固定为 `Speaker_1`，真实说话人区分能力尚未建立。

## 2026-05-10 / Sprint 0 ????

### ??????????
1. ?????????????? `emitStopRecording()`?????????????
2. ?? `on_stop_recording()` ?????????????????? session?
3. ?????????? `main.py` ?????????? `services/asr_service.py:decide_chunk_processing()` ???
4. ????????????????? `ASRAdapter.transcribe_audio_bytes()`?
5. ????? `asr_result` ???? `speaker_id / text / is_final` ????????
   - `result_id`
   - `segment_id`
   - `replace_target_id`
   - `result_type`
   - `processing_reason`
   - `chunk_duration_seconds`
6. ?? `handleASRResult()` ??????????????????????????????????????
