# FUNCTION_CONTRACTS

## 说明
- 本文件聚焦当前最关键的函数契约，优先覆盖实时转写主链路。
- 每条记录只写“当前代码已经表现出来的输入 / 输出 / 副作用 / 上下游关系”。

## Python 后端关键函数

### `main.py:add_wav_header(pcm_data)`
- 输入：
  - `pcm_data: bytes`
- 输出：
  - 带标准 WAV 头的 `bytes`
- 作用：
  - 将前端上送的裸 PCM 包装成可供 ASR 服务识别的 WAV 数据
- 副作用：
  - 无
- 主要调用方：
  - `on_audio_stream()`

### `main.py:should_filter_asr_result(text)`
- 输入：
  - `text: str`
- 输出：
  - `bool`
  - `True` 表示结果应被过滤
- 当前过滤规则：
  - 空文本
  - 特定填充词占比过高
  - 重复字符过多
  - 文本长度过短
- 副作用：
  - 无
- 主要调用方：
  - `on_audio_stream()`

### `main.py:detect_silence(audio_data, sample_rate=16000, frame_size=256)`
- 输入：
  - 原始 PCM `bytes`
  - 采样率
  - 帧大小
- 输出：
  - `bool`
  - `True` 表示该片段整体更接近静音
- 当前判断依据：
  - 每帧 RMS
  - 每帧最大绝对幅值
  - 静音帧比例
- 副作用：
  - 无
- 主要调用方：
  - `on_audio_stream()`

### `main.py:SessionManager.get_or_create(sid)`
- 输入：
  - Socket session id
- 输出：
  - session 字典，当前包含：
    - `buffer`
    - `last_process_time`
    - `processing`
    - `file_path`
    - `file_handle`
- 副作用：
  - 当 session 不存在时，会创建临时 PCM 文件并打开文件句柄
- 主要调用方：
  - `on_audio_stream()`

### `main.py:SessionManager.remove(sid)`
- 输入：
  - Socket session id
- 输出：
  - 被移除 session 的文件路径；如果不存在则返回空字符串
- 副作用：
  - 关闭该 session 的文件句柄
  - 从 session 池中删除该会话
- 主要调用方：
  - `on_disconnect()`
  - `on_stop_recording()`

### `main.py:on_audio_stream(data)`
- 输入：
  - 前端通过 Socket.IO 发送的 PCM `bytes`
- 输出：
  - 无显式返回值
- 副作用：
  - 写入 session 临时文件
  - 更新 session 内存缓冲
  - 可能触发 ASR 请求
  - 可能向前端 `emit("asr_result", ...)`
- 上游调用方：
  - 前端 `socket.emit('audio_stream', pcmData)`
- 下游依赖：
  - `SessionManager.get_or_create()`
  - `detect_silence()`
  - `add_wav_header()`
  - `should_filter_asr_result()`
  - 内外网 ASR 调用分流
- 当前限制：
  - 只支持单层切片转写
  - 当前回推结果统一按 `Speaker_1`
  - 当前输出统一标记为 `is_final=True`

### `main.py:summarize_meeting()`
- 输入：
  - JSON body，至少包含 `transcript`
  - 可选 `doc_type`
- 输出：
  - 包含 `doc_title`、`summary_text`、`doc_type` 等字段的 JSON
- 副作用：
  - 调用 LLM 服务
- 上游调用方：
  - 前端 `generateDocument()`

### `main.py:regenerate_document()`
- 输入：
  - JSON body，包含：
    - `transcript`
    - `doc_type`
    - `feedback`
- 输出：
  - 新的文档标题与正文 JSON
- 副作用：
  - 调用 LLM 服务
- 上游调用方：
  - 前端 `regenerateDocument()`

### `main.py:export_word()`
- 输入：
  - JSON body，包含：
    - `summary`
    - `transcript`
    - `doc_type`
- 输出：
  - 下载 URL JSON
- 副作用：
  - 在 `EXPORT_DIR` 下写入 `.docx`
- 上游调用方：
  - 前端 `downloadMinutes()` / `downloadHistoryDoc()`

### `main.py:upload_audio()`
- 输入：
  - `multipart/form-data`
  - 字段名：`file`
- 输出：
  - 转写结果 JSON
- 副作用：
  - 将上传文件写入 `TEMP_DIR`
  - 调用 ASR 服务
- 上游调用方：
  - `handleFileUpload()`
  - `uploadCachedAudio()`

## 前端关键函数

### `static/js/audio-processor.js:AudioProcessor.process(inputs, outputs, parameters)`
- 输入：
  - 浏览器音频工作线程中的输入帧
- 输出：
  - 返回 `true` 以保持处理器持续工作
- 副作用：
  - 通过 `this.port.postMessage()` 向主线程发送 `Float32Array`
- 下游使用方：
  - `setupAudioProcessing()`

### `static/js/app.js:initSocketIO()`
- 输入：
  - 无
- 输出：
  - 无显式返回值
- 副作用：
  - 创建全局 `socket`
  - 注册 `connect` / `disconnect` / `asr_result` / `asr_error` / `connect_error` 事件
- 下游依赖：
  - `handleASRResult()`
  - `updateConnectionStatus()`

### `static/js/app.js:startRecording()`
- 输入：
  - 无
- 输出：
  - `Promise<void>`
- 副作用：
  - 请求麦克风权限
  - 初始化本地音频缓存
  - 调用 `setupAudioProcessing()`
  - 更新录音 UI 状态
  - 启动计时器
- 下游依赖：
  - `setupAudioProcessing()`
  - `startTimer()`

### `static/js/app.js:setupAudioProcessing()`
- 输入：
  - 使用外部状态 `mediaStream`
- 输出：
  - `Promise<void>`
- 副作用：
  - 创建 `AudioContext`
  - 创建 `AudioWorkletNode` 或 `ScriptProcessorNode`
  - 每次音频回调都可能：
    - 向 `audioChunks` 累积数据
    - 向后端发送 PCM
    - 更新可视化
- 上游调用方：
  - `startRecording()`
- 下游依赖：
  - `convertFloat32To16BitPCM()`
  - `socket.emit('audio_stream', ...)`
  - `updateVisualizer()`

### `static/js/app.js:stopRecording()`
- 输入：
  - 无
- 输出：
  - 无
- 副作用：
  - 停止音轨
  - 断开音频节点
  - 关闭 `AudioContext`
  - 把当前录音缓存到本地
  - 更新 UI
- 上游调用方：
  - `toggleRecording()`
- 当前限制：
  - 当前没有显式向后端发送 `stop_recording`

### `static/js/app.js:saveAudioToLocal()`
- 输入：
  - 使用外部状态 `audioChunks`
- 输出：
  - 无
- 副作用：
  - 把本地录音缓存保存到 `localStorage`
  - 把补偿标记设为未处理
- 上游调用方：
  - `stopRecording()`

### `static/js/app.js:uploadCachedAudio()`
- 输入：
  - 无显式参数，读取 `localStorage` 中缓存的音频 data URL
- 输出：
  - `Promise<void>`
- 副作用：
  - 调用 `/api/v1/audio/upload`
  - 将结果再次送入 `handleASRResult()`
- 上游调用方：
  - `showUploadPrompt()`

### `static/js/app.js:handleASRResult(data)`
- 输入：
  - `data`，当前至少包含：
    - `speaker_id`
    - `text`
    - `is_final`
- 输出：
  - 无
- 副作用：
  - 更新 DOM 中的转写列表
  - 更新内存中的 `transcriptData`
  - 更新 `lastSpeaker`、`lastMessageTime`
  - 持久化缓存
- 合并规则：
  - 同一说话人
  - 距离上一条小于 10 秒
- 当前限制：
  - 没有“替换已有消息”的能力
  - `is_final` 字段当前未真正驱动不同展示分支

### `static/js/app.js:addMessageUI(speaker, text, time, merge = false, messageId = null)`
- 输入：
  - 说话人
  - 文本
  - 时间
  - 是否与上一条合并
  - 消息 id
- 输出：
  - 无
- 副作用：
  - 直接修改消息列表 DOM
  - 在合并场景下同步修改 `transcriptData` 最后一项内容
- 上游调用方：
  - `handleASRResult()`
  - `loadCache()`

### `static/js/app.js:convertFloat32To16BitPCM(input)`
- 输入：
  - `Float32Array`
- 输出：
  - `ArrayBuffer`
- 作用：
  - 将浏览器浮点音频转为后端可接受的 16-bit PCM
- 上游调用方：
  - `setupAudioProcessing()`
  - `saveAudioToLocal()`

### `static/js/app.js:saveCache()`
- 输入：
  - 无显式参数，使用 `transcriptData`
- 输出：
  - 无
- 副作用：
  - 将当前转写列表写入 `localStorage`
  - 更新缓存大小显示

### `static/js/app.js:loadCache()`
- 输入：
  - 无
- 输出：
  - 无
- 副作用：
  - 从 `localStorage` 恢复转写记录
  - 重新渲染转写列表
- 当前限制：
  - 从缓存恢复时，合并判断只依赖说话人，不依赖真实时间间隔

## 当前最关键的上下游关系
- 实时转写质量的后端入口是 `on_audio_stream()`。
- 实时转写质量的前端入口是 `handleASRResult()`。
- 音频切片大小、静音过滤、结果过滤主要发生在后端。
- 展示碎片化、段落合并、结果回写替换主要发生在前端。

## 2026-05-10 ?? / ????

### `services/asr_service.py:decide_chunk_processing(audio_data, policy)`
- ???
  - ?? session ??? PCM `bytes`
  - `RealtimeChunkPolicy`
- ???
  - `ChunkDecision`
  - ???`should_process`?`reason`?`audio_duration_seconds`?`trailing_silence_detected`
- ???
  - ???????????????????????????? `main.py` ??

### `services/asr_service.py:ASRAdapter.transcribe_audio_bytes(audio_bytes, ...)`
- ???
  - ?? `bytes`
  - ????MIME ?????????
- ???
  - ?????? `str`
- ???
  - ???????? HTTP transcriptions????? OpenAI ?? audio/chat???????
- ?????
  - ?????????????????? ASR ???

### `static/js/app.js:emitStopRecording()`
- ???
  - ?????????? `socket`
- ???
  - ?
- ???
  - ????????????????????????? session?

### `static/js/app.js:replaceTranscriptEntry(data, text, timeStr)`
- ???
  - ???????????
  - ??????????
- ???
  - `bool`
  - `True` ????????????
- ???
  - ????????? -> ?????????????????

### `static/js/app.js:handleASRResult(data)`????
- ???????
  - ?????????? + 10 ????????????????? `transcriptData`??????? push?
  - ? `replace_target_id` ??????????????????????

### `static/js/app.js:loadCache()`????
- ???????
  - ???????????????????????????????????????????????????????
