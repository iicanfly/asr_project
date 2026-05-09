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
    - `session_tag`
    - `chunk_seq`
    - `result_seq`
    - `segment_seq`
    - `active_segment`
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
  - `services/asr_service.py:decide_chunk_processing()`
  - `services/asr_service.py:refine_asr_result_text()`
  - `services/asr_service.py:should_filter_asr_result()`
  - `services/asr_service.py:decide_segment_rewrite()`
  - `ASRAdapter.transcribe_audio_bytes()`
- 当前限制：
  - 当前回推结果统一按 `Speaker_1`
  - 当前仍基于启发式规则做分段和回写，不是真正流式增量 ASR
  - 当用户在处理中的中途点击停止录音时，真正的 session 清理会延迟到当前 chunk 处理完成之后

### `main.py:get_or_create_active_segment(session)`
- 输入：
  - `session: dict`
- 输出：
  - 当前活动段对象，包含：
    - `segment_id`
    - `audio_buffer`
    - `chunk_count`
    - `duration_seconds`
    - `last_result_id`
    - `last_rewrite_chunk_count`
- 作用：
  - 为实时会话维护“当前段”的累计上下文，用于后续段级回写和分段边界控制。
- 副作用：
  - 当当前段不存在时，会原地修改 session，创建一个新的 `active_segment`。
- 主要调用方：
  - `on_audio_stream()`

### `main.py:on_stop_recording()`
- 输入：
  - 当前 Socket session
- 输出：
  - 无显式返回值
- 作用：
  - 结束实时录音会话，并尝试把剩余短尾音频做最后一次补充转写 / 段级收尾。
- 副作用：
  - 可能触发一次 `stop flush` 转写
  - 可能触发一次强制段级回写
  - 最终移除 session 并关闭 PCM 文件句柄
- 当前行为特点：
  - 如果当前已有 chunk 正在处理，会先标记 `stop_requested`，等当前处理结束后再做收尾和清理

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
    - 在后端离线 / socket 断开时，向 `audioChunks` 累积离线补偿数据
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
  - 强制刷新一次转写缓存
  - 更新 UI
- 上游调用方：
  - `toggleRecording()`

### `static/js/app.js:saveAudioToLocal()`
- 输入：
  - 使用外部状态 `audioChunks`
- 输出：
  - 无
- 副作用：
  - 把本地录音缓存保存到 `localStorage`
  - 把补偿标记设为未处理
  - 成功写入后清空本轮 `audioChunks` 内存缓存
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
  - 同一 `segment_id` 时优先继续合并
  - 新 `segment_id` 时优先新建一条
  - 其余情况再回退到“同说话人 + 10 秒时间窗”
  - 中文默认直接拼接，英文 / 数字连续词之间保留空格

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

### `static/js/app.js:saveCache(options = {})`
- 输入：
  - 可选参数 `immediate`
- 输出：
  - 无
- 副作用：
  - 将当前转写列表写入 `localStorage`
  - 更新缓存大小显示
  - 当前默认采用防抖写入，减少长时间录音中的高频全量缓存写入

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

## 2026-05-10 新增 / 修正契约

### `services/asr_service.py:decide_chunk_processing(audio_data, policy)`
- 输入：
  - 当前 session 累积的 PCM `bytes`
  - `RealtimeChunkPolicy`
- 输出：
  - `ChunkDecision`
  - 包含：`should_process`、`reason`、`audio_duration_seconds`、`trailing_silence_detected`
- 作用：
  - 统一管理实时转写的切片触发判断，避免阈值和静音逻辑散落在 `main.py` 中。

### `services/asr_service.py:refine_asr_result_text(text, filler_words=...)`
- 输入：
  - `text: str`
  - 可选语气词列表
- 输出：
  - 清洗后的文本 `str`
- 作用：
  - 在真正决定是否展示前，先去掉结果首尾的明显语气词和多余标点。
- 副作用：
  - 无
- 主要调用方：
  - `main.py:on_audio_stream()`

### `services/asr_service.py:collapse_transcript_text(text)`
- 输入：
  - `text: str`
- 输出：
  - 去掉空白与边界标点后的紧凑文本 `str`
- 作用：
  - 为语气词过滤、句子边界判断、分段收尾规则提供更稳定的文本长度与尾字符依据。
- 副作用：
  - 无
- 主要调用方：
  - `should_filter_asr_result()`
  - `looks_like_sentence_boundary()`

### `services/asr_service.py:looks_like_sentence_boundary(text, min_chars=6)`
- 输入：
  - `text: str`
  - 最小有效字符数阈值
- 输出：
  - `bool`
- 作用：
  - 判断当前文本是否更像一个可以自然收尾的句子，而不是仍处于口语续说中。
- 副作用：
  - 无
- 主要调用方：
  - `decide_segment_rewrite()`

### `services/asr_service.py:decide_segment_rewrite(...)`
- 输入：
  - 当前段累计时长
  - 当前段 chunk 数
  - 上次回写发生时的 chunk 数
  - 最新 chunk 的触发原因
  - 当前段最近一次可展示文本
  - `SegmentRewritePolicy`
- 输出：
  - `SegmentRewriteDecision`
  - 包含：
    - `should_emit_rewrite`
    - `should_finalize_segment`
    - `reason`
- 作用：
  - 决定当前段是否已经值得做一次“更长上下文回写”，以及是否该结束当前段、等待下一段开始。
  - 当前版本会把“尾部静音 + 文本完成度 / 足够长文本”一起纳入段落收尾判断。
- 副作用：
  - 无
- 主要调用方：
  - `main.py:on_audio_stream()`

### `services/asr_service.py:decide_stop_flush(audio_data, policy)`
- 输入：
  - 停止录音时剩余的 PCM `bytes`
  - `RealtimeChunkPolicy`
- 输出：
  - `ChunkDecision`
- 作用：
  - 判断停止录音时剩余的短尾音频是否值得再做一次补充转写，而不是直接清掉。
- 副作用：
  - 无
- 主要调用方：
  - `main.py:on_stop_recording()`

### `services/asr_service.py:ASRAdapter.transcribe_audio_bytes(audio_bytes, ...)`
- 输入：
  - 音频 `bytes`
  - 文件名、MIME 类型、语言等元数据
- 输出：
  - 识别后的文本 `str`
- 作用：
  - 对上层屏蔽“内网 HTTP transcriptions”与“外网 OpenAI 兼容 audio/chat”之间的差异。
- 当前约束：
  - 上层不应再直接在多个位置分别拼接两套 ASR 请求。

### `static/js/app.js:emitStopRecording()`
- 输入：
  - 无显式输入，使用全局 `socket`
- 输出：
  - 无
- 作用：
  - 在用户手动停止录音时，显式通知后端结束当前实时转写 session。

### `static/js/app.js:replaceTranscriptEntry(data, text, timeStr)`
- 输入：
  - 后端回推的实时结果对象
  - 规范化后的文本与时间
- 输出：
  - `bool`
  - `True` 表示已找到并替换既有消息
- 作用：
  - 为未来的“小段结果 -> 大段结果”回写替换提供前端兼容层。

### `static/js/app.js:handleASRResult(data)`（修正）
- 当前补充事实：
  - 当消息满足“同说话人 + 10 秒内”时，当前版本会只更新最后一条 `transcriptData`，不再额外重复 push。
  - 当 `replace_target_id` 存在时，当前版本会优先尝试替换已存在的消息。

### `static/js/app.js:loadCache()`（修正）
- 当前补充事实：
  - 从缓存恢复时，当前版本按缓存中的条目逐条恢复，不再在恢复阶段做额外合并，以避免缓存数据与界面展示再次发生偏移。
