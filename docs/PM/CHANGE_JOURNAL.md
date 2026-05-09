# CHANGE_JOURNAL

## 目的
- 记录每一轮关键修改的内容、目的、用户反馈、观察到的效果，以及下一步动作。
- 帮助后续会话快速判断：某个改动做过没有、用户是否满意、是否还要继续迭代。

## 记录规则
- 只记录有效进入本地 Git 历史的修改，不记录未合入的临时试验。
- 每条记录尽量回答五个问题：
  - 改了什么
  - 为什么改
  - 怎么验证
  - 用户反馈是什么
  - 下一步还要不要继续
- 如果某轮没有用户反馈，可以明确写“待用户反馈”。

## 建议格式
### YYYY-MM-DD / Commit <hash>
- 主题：
- 修改内容：
- 目的：
- 验证方式：
- 当前结果：
- 用户反馈：
- 后续动作：

## 变更记录

### 2026-05-10 / Commit c454127
- 主题：
  - 先整理实时转写主链路的结构与正确性，再进入质量优化。
- 修改内容：
  - 新增 `services/asr_service.py`，统一封装内外网 ASR 调用分流、实时切片规则、静音检测、WAV 封装与基础结果过滤。
  - `main.py` 改为复用统一 ASR 适配层，并为实时转写结果补充 `result_id / segment_id / replace_target_id / processing_reason` 等元数据。
  - `static/js/app.js` 中补齐 `stop_recording` 前后端闭环。
  - `static/js/app.js` 中修复实时消息合并时 `transcriptData` 与 UI 不一致的问题。
  - `static/js/app.js` 中为未来的结果替换回写加入兼容逻辑。
  - 新增 `tests/test_asr_service.py` 作为最小自动化测试抓手。
- 目的：
  - 降低后续实现静音过滤、双层转写、结果回写时的耦合风险。
  - 先修正明显的链路正确性问题，避免边开发边积累状态问题。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py` 通过。
  - `node -e "new Function(require('fs').readFileSync('static/js/app.js','utf8')); console.log('app.js syntax OK')"` 通过。
- 当前结果：
  - 实时链路结构比之前更清晰，后续可以在不直接碰内外网分流细节的前提下优化静音、切片和过滤规则。
  - 停止录音时的 session 清理链路已打通。
  - 前端已具备接受未来“替换回写”数据协议的能力，但替换策略本身尚未真正启用。
- 用户反馈：
  - 待本轮改动跑通后确认。
- 后续动作：
  - 进入实时转写质量优化第一轮：静音过滤、弱语音与语气词过滤。

### 2026-05-10 / Commit 待填写
- 主题：
  - 为中文文档写坏风险增加自动保护。
- 修改内容：
  - 新增 `tools/check_doc_corruption.py`，默认扫描 Markdown 文档中的异常密集 `?` 问号行。
  - 新增 `tests/test_doc_corruption_guard.py`，验证保护脚本的判断逻辑。
  - 在 `README.md`、`AGENTS.md`、`docs/PM/DOC_MAINTENANCE.md`、`docs/PM/TEST_MATRIX.md` 中写入该保护的默认使用方法。
- 目的：
  - 降低中文文档在 Windows / PowerShell 编码链路下被写坏后未及时发现的风险。
- 验证方式：
  - 运行 `python tools/check_doc_corruption.py`
  - 运行 `python -m unittest discover -s .\tests -p "test_*.py"`
- 当前结果：
  - 后续文档修改前可以快速自检，避免再次把大量 `?` 提交进仓库。
- 用户反馈：
  - 用户明确要求加上文档损坏保护。
- 后续动作：
  - 后续涉及中文文档批量修改时，默认先跑该检查脚本。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第一轮：静音过滤与弱语音拦截。
- 修改内容：
  - 在 `services/asr_service.py` 中新增整段音频特征提取：`AudioFeatures`、`extract_audio_features()`。
  - 新增 `has_usable_speech()` 与 `is_weak_background_audio()`，不再只靠尾部静音判断是否送 ASR。
  - 扩展 `ChunkDecision`，支持 `drop_buffer` 与音频特征透传。
  - 在 `main.py` 中接入“弱背景音直接丢弃缓冲”的分支，并把 `rms / peak / active_ratio / voiced_ratio` 打进实时日志。
  - 在 `tests/test_asr_service.py` 中补充弱背景音丢弃与音频特征判断测试。
- 目的：
  - 减少旁边人小声说话、低价值环境弱音、长时间弱噪声进入实时转写主流程。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py` 通过。
- 当前结果：
  - 实时切片判断从“只看尾部静音”升级成“整段特征 + 尾部静音 + 可用语音强度”。
  - 对明显弱背景音，系统会在后端直接丢弃缓冲，不再继续积累到一次无效 ASR 请求。
- 用户反馈：
  - 待明早实际测试确认。
- 后续动作：
  - 继续进入语气词过滤精细化，然后推进双层转写与替换回写。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第二轮：语气词过滤精细化与结果清洗。
- 修改内容：
  - 在 `services/asr_service.py` 中新增 `refine_asr_result_text()`，用于在发送前清洗实时结果两端的语气词与多余标点。
  - 收紧并细化 `should_filter_asr_result()` 规则：过滤纯语气词、重复低信息量短句，同时保留“好的”“可以”等有效短句。
  - 调整默认语气词集合，移除误伤风险较高的单字“那”，避免把正常短句误判成低价值内容。
  - 在 `main.py` 中改为优先发送清洗后的实时转写文本，并补充“原始结果 / 清洗结果”日志，便于明早对照观察。
  - 在 `tests/test_asr_service.py` 中新增边界清洗与短句保留测试样例。
- 目的：
  - 减少“嗯”“啊”等低信息量内容直接进入前端展示。
  - 在不过度误伤短句的前提下，提高实时转写文本的可读性。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py` 通过。
- 当前结果：
  - 纯语气词与两端挂着语气词的短结果，现在会先清洗再决定是否展示。
  - “嗯 今天开始”这类结果可直接收敛成“今天开始”，“啊好的”可收敛成“好的”。
- 用户反馈：
  - 待明早实际测试确认。
- 后续动作：
  - 继续推进“小段结果 -> 大段结果”替换回写与更合理的分段策略。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第三轮：小段结果到大段结果的替换回写最小闭环。
- 修改内容：
  - 在 `services/asr_service.py` 中新增 `SegmentRewritePolicy`、`SegmentRewriteDecision` 与 `decide_segment_rewrite()`，把段级回写触发条件抽成可测试规则。
  - 在 `main.py` 中为每个实时会话增加 `active_segment` 状态，累计多段音频后再发起一次更长片段的 ASR，并通过 `replace_target_id` 回写替换前面的粗结果。
  - `build_realtime_result_payload()` 现已支持显式传入 `segment_id / replace_target_id / result_type`，用于区分 `segment_partial` 与 `segment_rewrite`。
  - 在 `static/js/app.js` 中把 `segment_id` 纳入前端分段合并条件：同段强制合并、跨段强制分开，给后端主导段落边界留出空间。
  - 在 `tests/test_asr_service.py` 中新增段级回写决策测试。
- 目的：
  - 让前端先快速看到小段结果，再在更长上下文形成后收到一次更高质量的替换文本。
  - 顺带为后续“更合理的分段策略”准备后端主导的 `segment_id` 机制。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py` 通过。
  - `node -e "new Function(require('fs').readFileSync('static/js/app.js','utf8')); console.log('app.js syntax OK')"` 通过。
- 当前结果：
  - 后端已经可以在段内累计多个小 chunk，并在满足条件时发出 `segment_rewrite` 结果替换前面的段内粗结果。
  - 前端已经能根据 `segment_id` 区分“继续同一段”还是“开始新一段”，不再只靠 10 秒时间窗。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 继续校准段级回写阈值与段落边界，随后进入长时间录音稳定性回归。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第四轮：更稳的段落边界与更自然的文本拼接。
- 修改内容：
  - 在 `services/asr_service.py` 中新增 `collapse_transcript_text()` 与 `looks_like_sentence_boundary()`，用于判断段内文本是否更像一个可收尾的句子。
  - 扩展 `SegmentRewritePolicy` 与 `decide_segment_rewrite()`：尾部静音不再直接结束段，而是要求“句子边界成立”或“文本已足够长”，降低过碎分段风险。
  - 在 `main.py` 的 `active_segment` 中记录 `latest_display_text`，让段落收尾决策不仅看时长，也参考当前文本形态。
  - 在 `static/js/app.js` 中新增 `mergeTranscriptText()`，取消中文片段之间一律硬插空格的行为，只在英文 / 数字连续词之间保留空格。
  - 在 `tests/test_asr_service.py` 中新增文本边界与分段收尾判断测试。
- 目的：
  - 让段落边界更接近真实语义停顿，而不是一遇到短静音就过早切段。
  - 提升同段文本的阅读感，避免中文被拼成一串带空格的碎片。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py` 通过。
  - `node -e "new Function(require('fs').readFileSync('static/js/app.js','utf8')); console.log('app.js syntax OK')"` 通过。
- 当前结果：
  - 段落结束条件从“尾部静音 + 时长”升级为“尾部静音 + 文本完成度 / 足够长文本 + 时长”。
  - 中文实时结果在同段合并时不再默认插入空格，可读性更接近自然书写。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 继续做长时间录音稳定性回归，并视效果再微调段落边界阈值。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第五轮：长时间录音稳定性第一轮防护。
- 修改内容：
  - 在 `static/js/app.js` 中把离线补偿音频缓存改成“仅在后端离线 / socket 断开时才积累音频片段”，避免在线长时间录音时持续把整段原始音频堆在前端内存里。
  - `stopRecording()` 与 `beforeunload` 现在会强制刷新一次转写缓存，降低浏览器意外关闭时最近结果尚未落盘的概率。
  - `saveCache()` 改为防抖写入 localStorage，减少长时间录音过程中每条结果都全量序列化、全量写本地缓存的放大开销。
  - 离线补偿音频成功写入本地后，立即清空本轮离线音频缓存，避免停止录音后继续占用前端内存。
- 目的：
  - 降低长时间录音时浏览器内存持续增长与 localStorage 高频写入带来的卡顿风险。
  - 在不破坏双环境链路的前提下，优先做低风险的稳定性优化。
- 验证方式：
  - `node -e "new Function(require('fs').readFileSync('static/js/app.js','utf8')); console.log('app.js syntax OK')"` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 在线长时间录音时，前端不再默认把整段原始音频一直保存在 `audioChunks` 里。
  - 转写缓存写入从“每条结果立即全量写”变为“短延迟批量写 + 关键时刻强制落盘”。
- 用户反馈：
  - 待明早真实长录音测试确认。
- 后续动作：
  - 继续观察长时间录音下的浏览器内存、缓存大小与回写延迟是否稳定。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第六轮：停止录音时的尾段 flush 与最终收尾。
- 修改内容：
  - 在 `services/asr_service.py` 中新增 `decide_stop_flush()`，专门判断 `stop_recording` 时剩余短尾音频是否值得补做一次转写。
  - `RealtimeChunkPolicy` 新增 `stop_flush_min_seconds`，让“停止录音时的尾段补转写”与常规切片阈值解耦。
  - 在 `main.py` 中抽出实时 chunk 处理与段级回写逻辑，供常规切片和 `stop_recording` 尾段复用。
  - `stop_recording` 现在会优先尝试处理剩余缓冲；如果当前已有活动段，还会在结束前做一次强制段级收尾，尽量减少最后一句丢尾或来不及回写的问题。
  - 如果用户在某个 chunk 正在处理时点击停止录音，后端会延迟清理到当前处理完成之后，再做尾段 flush / 段落收尾。
  - 在 `tests/test_asr_service.py` 中新增 stop flush 规则测试。
- 目的：
  - 降低“刚说完一句就立刻点停止，最后一小段没被识别出来”的概率。
  - 让停止录音成为一个更完整的会话收尾动作，而不只是简单清理 session。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py` 通过。
- 当前结果：
  - 停止录音时，短但有效的尾音现在有机会被补做一次实时转写。
  - 结束前如果段内还有未被更长上下文覆盖的新内容，也会争取补一轮最终段级回写。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 继续结合真实口语录音观察 stop flush 阈值是否偏松或偏紧。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第七轮：本地缓存容量保护与损坏容错。
- 修改内容：
  - 在 `static/js/app.js` 中新增 `safeSetLocalStorage()` / `safeRemoveLocalStorage()` 与缓存告警状态，统一兜住本地缓存写入异常。
  - 转写缓存、离线补偿音频缓存、历史文档缓存现在都会在写入失败时给出告警，而不是直接让页面逻辑失稳。
  - `loadCache()` 与 `loadDocHistory()` 在遇到损坏 JSON 时会自动忽略并清理坏缓存。
  - `cache-info` 现在会同时展示“文本缓存 / 音频缓存”体积，并在缓存异常时显示“缓存受限”状态。
- 目的：
  - 降低长时间录音或历史堆积导致 localStorage 超限后，缓存逻辑直接报错或污染后续会话的风险。
  - 提前把“缓存满了 / 缓存坏了”的问题降级成可见警告，而不是隐性故障。
- 验证方式：
  - `node -e "new Function(require('fs').readFileSync('static/js/app.js','utf8')); console.log('app.js syntax OK')"` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 本地缓存写入现在有了统一保护层。
  - 即使缓存损坏或容量不足，前端也更有机会继续工作，而不是在恢复 / 落盘路径上直接失稳。
- 用户反馈：
  - 待明早真实长录音测试确认。
- 后续动作：
  - 继续观察超长会话下缓存体积、提示体验与恢复行为是否合理。
