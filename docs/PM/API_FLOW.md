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
9. 当前前端只在后端离线 / Socket 断开时，才额外把原始音频片段保留到本地补偿缓存；在线正常转写时不再默认把整段原始音频一直留在内存中。
10. 本地缓存写入当前带有安全保护：如果浏览器本地存储空间不足，前端会降级成告警，而不是直接让缓存链路报错中断。

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
5. 如果用户在处理过程中点击停止录音，session 会先记录 `stop_requested`，等待当前 chunk 处理完成后再进入最终收尾。

### 后端触发转写阶段
核心判断位置：
- `main.py` 中的 `on_audio_stream(data)`

当前触发规则：
1. 统一调用 `services/asr_service.py:decide_chunk_processing()`。
2. 如果累计音频长度超过 `max_audio_seconds`，强制触发。
3. 如果累计音频长度超过 `chunk_seconds`，触发。
4. 如果累计音频长度超过 `min_audio_seconds`，则进一步根据尾部静音、整段 RMS / peak / active_ratio / voiced_ratio 等特征决定：
   - 是否立即送 ASR
   - 是否继续等待更多音频
   - 是否直接把弱背景音缓冲丢弃

当前静音检测逻辑：
1. 对缓冲区末尾一小段音频调用 `detect_silence()`
2. 同时对整段音频调用 `extract_audio_features()`
3. `detect_silence()` 会：
   - 将 PCM bytes 解码为整型样本
   - 分帧计算 RMS 和最大幅值
   - 统计静音帧比例
4. 静音帧比例大于阈值时，认为当前片段可结束并触发转写。
5. 如果整段音频被判定为弱背景音，则不会继续进入 ASR 主流程。

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
- `services/asr_service.py` 的 `refine_asr_result_text()` / `should_filter_asr_result()`
- `main.py` 的 `emit("asr_result", ...)`

当前行为：
1. 如果识别结果为空，直接丢弃。
2. 如果结果首尾存在明显语气词，先清洗再判断是否展示。
3. 如果命中过滤规则，也不回推到前端。
4. 其余结果统一以：
   - `speaker_id = "Speaker_1"`
   - `text = text_result`
   - `is_final = True`
   的形式推送给前端。
5. 当段内累计多个 chunk 后，后端还可能再次发出：
   - `result_type = "segment_rewrite"`
   - `replace_target_id = 上一次段内结果 id`
   用更长上下文的识别结果覆盖前面的粗糙文本。
6. 当后端判断“尾部静音 + 当前文本更像可收尾句子”或“文本已足够长”时，才更倾向于结束当前段并切到下一段。
7. 当收到 `stop_recording` 时，后端还会对剩余短缓冲单独做一次 `stop flush` 判断；如果像有效语音，会补做一次尾段转写和最终段级收尾。
8. 如果新的 partial / rewrite 与当前展示文本实质相同，后端会直接跳过这次回推，减少前端抖动和无效缓存写入。
9. 即使后端已经去重，前端仍会对重复到达的同一 `result_id` 再做一次入口去重，作为网络边界兜底。

### 前端结果展示阶段
入口位置：
- `static/js/app.js` 的 `handleASRResult(data)`

主要步骤：
1. 清除空状态占位符。
2. 生成当前时间戳。
3. 如果带有 `replace_target_id`，优先替换旧消息。
4. 如果后端显式给出相同 `segment_id`，则继续合并到同一条消息。
5. 如果后端显式切换了新的 `segment_id`，则强制新开一条消息。
6. 其余情况再回退到原有规则：
   - 同一个 `speaker_id`
   - 与上一条间隔小于 10 秒
7. 调用 `addMessageUI()` 渲染 UI。
8. 更新 `transcriptData`。
9. 调用 `saveCache()` 持久化到浏览器 `localStorage`。
10. 同段文本拼接时，前端会优先做“中文直接相连、英文 / 数字连续词保留空格”的智能合并，而不是无条件插入空格。
11. 转写缓存当前采用短延迟防抖写入；在停止录音或页面卸载前会再强制落盘一次。
12. 如果缓存读取到损坏数据，前端会自动忽略并清理坏缓存，避免恢复阶段直接失败。
13. 缓存恢复时，前端还会同步恢复消息 ID 计数器，避免后续新增消息与旧消息撞 ID。

### 当前链路特点
- 实时链路本质上是“前端连续送 PCM，后端按阈值切片后再做批量识别”。
- 当前并不是逐帧流式 ASR，而是“伪流式分段识别 + 前端增量展示”。
- 当前已进入“双层结果”形态：
  - 先用小 chunk 快速出结果
  - 再用更长段音频发起一次 `segment_rewrite` 覆盖旧结果

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

## 2026-05-10 / Sprint 0 链路补充

### 实时录音转写链路补充
1. 前端点击停止录音时，会先调用 `emitStopRecording()`，再关闭本地音频采集节点。
2. 后端 `on_stop_recording()` 会记录当前待处理缓冲时长并立即结束该 session。
3. 实时切片触发判断已从 `main.py` 内联逻辑抽出，统一由 `services/asr_service.py:decide_chunk_processing()` 决定。
4. 后端实时转写与上传转写现在统一复用 `ASRAdapter.transcribe_audio_bytes()`。
5. 后端回推的 `asr_result` 现在除了 `speaker_id / text / is_final` 之外，还会补充：
   - `result_id`
   - `segment_id`
   - `replace_target_id`
   - `result_type`
   - `processing_reason`
   - `chunk_duration_seconds`
6. 前端 `handleASRResult()` 已能消费这组扩展字段，但当前只有“兼容能力”，尚未真正启用双层替换回写策略。
