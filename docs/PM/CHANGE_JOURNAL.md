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
  - 为静音场景补上低信息幻觉短句拦截。
- 修改内容：
  - 在 `services/asr_service.py` 中新增低信息片段识别与整句清洗逻辑。
  - 对 `嗯 / 啊 / yeah / yes / huh / thank you / 你好 / 谢谢 / what's that` 等中英混合幻觉短句做发送前拦截。
  - 调整短句白名单，降低“你好 / 谢谢”在静音阶段被误发到前端的概率。
  - 在 `tests/test_asr_service.py` 中新增“整句低信息幻觉串过滤”和“混合句保留有效内容”的回归用例。
- 目的：
  - 解决用户实测中“完全不说话也会刷出一串嗯 / Yeah / Thank you / 你好”的问题。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_asr_service.py"`
  - `python -m unittest discover -s .\tests -p "test_*.py"`
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py`
  - `python tools/check_doc_corruption.py`
- 当前结果：
  - 自动化层面已能识别并过滤典型静音幻觉词串，同时保留混合句中的有效中文内容。
- 用户反馈：
  - 用户已明确反馈当前版本“什么都没说也会输出一堆嗯”，本轮正是针对该问题修复。
- 后续动作：
  - 继续做真实麦克风回归，观察是否还存在未覆盖的英文碎词幻觉样式。

### 2026-05-10 / Commit 待填写
- 主题：
  - 为实时转写补“保守上传门控”，减少静音上传但保留短语音机会。
- 修改内容：
  - 在 `services/asr_service.py` 中新增 `has_potential_short_speech()` 与 `retain_realtime_buffer()`。
  - 对 chunk 边界和尾静音边界处的可疑短语音，不再立刻上传或直接清空，而是先保留一小段缓冲等待后续上下文确认。
  - 对停止录音时的短促有声尾巴，新增 `stop_flush_short_voiced_tail` 放行路径。
  - 在 `main.py` 中接入 retain 分支日志与缓冲裁剪逻辑。
  - 在 `tests/test_asr_service.py` 中补充对应回归测试。
- 目的：
  - 降低“说完一句话后，后续静音片段仍被上传到 ASR 并持续冒出嗯 / thank you”的概率。
  - 同时避免把很短但可能重要的真实语音粗暴丢掉。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"`
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py`
  - `python tools/check_doc_corruption.py`
- 当前结果：
  - 自动化层面已确认：系统会优先 retain 边界短语音，而不是立刻 process / drop。
  - `stop flush` 对短促有声尾巴已增加保护路径。
- 用户反馈：
  - 用户明确要求：“静音不上传，但短有声不能被误杀；且要兼容以后多层次回写替换。”
- 后续动作：
  - 继续用真实录音观察 retain / process / drop 三种路径的占比与实际体验是否一致。

### 2026-05-10 / Commit 待填写
- 主题：
  - 清理“说完后幻觉尾巴”的上下文型低信息短句。
- 修改内容：
  - 在 `services/asr_service.py` 中新增 `DEFAULT_CONTEXTUAL_LOW_INFORMATION_SEGMENTS`。
  - 只有当 `对 / 好的 / 是的 / 是的吧 / 好 / 那啥 / 那个 / okay` 这类片段出现在多片段低信息混合结果里时，才和 `嗯 / thank you / just / what` 一起被清除。
  - 在 `tests/test_asr_service.py` 中补充对 `Just.呃...语音转写...Thank you` 与 `Okay.对。是的吧。那啥。语音转写。嗯` 的回归测试。
- 目的：
  - 继续压制“说完一句真实内容后，后面还挂着一串低信息尾巴”的展示问题。
  - 避免为了压尾巴而把单独出现的正常短句（如“好的”）一起误删。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"`
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py`
  - `python tools/check_doc_corruption.py`
- 当前结果：
  - 自动化样本中，混合尾巴可被清理成“现在在测试的是语音转写”或“语音转写”。
- 用户反馈：
  - 用户明确反馈“还是有一堆语气词”，本轮正是针对这个场景加固。
- 后续动作：
  - 继续结合真实录音判断：主要矛盾到底还剩“上传门控不足”还是“文本尾巴清洗不足”。

### 2026-05-10 / Commit 待填写
- 主题：
  - 为正文后的长串语气词 / 噪声尾巴增加整段截断。
- 修改内容：
  - 在 `services/asr_service.py` 中把 `嘘` 纳入低信息片段。
  - 为 `_strip_low_information_segments()` 增加“尾部连续噪声段整段截断”逻辑。
  - 在多片段上下文中，把 `那 / 你好` 也纳入上下文型低信息短片段集合。
  - 在 `tests/test_asr_service.py` 中补充“正文后跟一长串 嗯 / 嘘 / 嗯”应被整体截尾的回归测试。
- 目的：
  - 解决“前面正文基本对了，但结尾挂着大量嗯 / 嘘 / thank you”的展示污染。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"`
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py`
  - `python tools/check_doc_corruption.py`
- 当前结果：
  - 自动化层面已能把“正文 + 长尾巴”清洗成只保留正文。
- 用户反馈：
  - 用户明确反馈“有输出了，但还是一堆嗯”，本轮正是针对这个现象继续加固。
- 后续动作：
  - 继续用真实录音判断：下一轮主要该继续压“尾静音上传”还是继续压“尾巴文本污染”。

### 2026-05-10 / Commit 72a5939
- 主题：
  - 为实时语音转写补齐“当前实现说明”专项文档。
- 修改内容：
  - 新增 `docs/PM/REALTIME_ASR_CURRENT_IMPLEMENTATION.md`。
  - 系统整理了当前实时转写的流程、判断层、阈值、延迟来源、漏输出来源、段级 rewrite 逻辑与主要问题。
- 目的：
  - 解决“当前实时转写已经改得较复杂，难以掌控”的问题，先把现状讲清楚，再决定如何重构。
- 验证方式：
  - 人工校对文档结构与内容完整性。
  - `python tools/check_doc_corruption.py`
- 当前结果：
  - 已形成一份可长期回看的实时转写现状说明文档。
- 用户反馈：
  - 用户明确要求总结当前实时语音转写的整个流程、处理、判断与阈值。
- 后续动作：
  - 基于现状说明继续产出简化版重构方案。

### 2026-05-10 / Commit 4a922b6
- 主题：
  - 为实时语音转写补齐“简化版重构方案”专项文档。
- 修改内容：
  - 新增 `docs/PM/REALTIME_ASR_SIMPLIFIED_REFACTOR_PLAN.md`。
  - 明确了为什么不应继续在当前复杂实现上补丁式迭代，并提出四层主路径的简化重构思路。
- 目的：
  - 把后续开发方向从“继续补规则”转向“先恢复实时性与可解释性，再由 rewrite 提升质量”。
- 验证方式：
  - 人工校对文档结构与内容完整性。
  - `python tools/check_doc_corruption.py`
- 当前结果：
  - 已形成一份可作为后续重构路线图的方案文档。
- 用户反馈：
  - 用户明确同意继续写《实时语音转写简化版重构方案》。
- 后续动作：
  - 继续补齐实施清单，把方案落到可执行步骤。

### 2026-05-10 / Commit 待填写
- 主题：
  - 为实时语音转写补齐“简化重构实施清单”，并强化长期记忆维护准则。
- 修改内容：
  - 新增 `docs/PM/REALTIME_ASR_SIMPLIFIED_REFACTOR_CHECKLIST.md`。
  - 在 `AGENTS.md`、`docs/PM/CODEX_PLAYBOOK.md` 中写入新的默认准则：
    - 主动判断哪些输出 / 方案 / 阈值 / 测试策略值得沉淀为长期记忆文件；
    - 在连续开发前默认快速回看这些长期记忆文件。
  - 在 `SESSION_SUMMARY.md` 中补充实时转写专项文档索引与该准则说明。
- 目的：
  - 让后续实时转写重构进入“按 Phase 施工、按文档复盘”的可控状态。
  - 减少再次陷入上下文过长、只靠聊天临时记忆推进开发的风险。
- 验证方式：
  - `python tools/check_doc_corruption.py`
- 当前结果：
  - 已形成一份可直接指导逐阶段重构的实施清单；
  - 长期记忆维护准则已正式固化进仓库指导文件。
- 用户反馈：
  - 用户明确要求写《实时语音转写简化重构实施清单》，并要求把“主动沉淀与回看记忆文件”的准则写入长期记忆文件。
- 后续动作：
  - 后续正式重构实时转写时，先按实施清单确定当前 Phase，再只做该阶段改动。

### 2026-05-10 / Commit 待填写
- 主题：
  - 启动 simplified realtime pipeline，进入简化重构 Phase 0 / Phase 1。
- 修改内容：
  - 在 `services/asr_service.py` 中新增：
    - `decide_chunk_processing_simple()`
    - `decide_stop_flush_simple()`
    - 简化版 trigger / upload gate 辅助逻辑
  - 在 `main.py` 中接入 `ENABLE_SIMPLIFIED_REALTIME_PIPELINE` 开关，并根据该开关选择 simplified 或 legacy 路径。
  - 外网开发模式下，simplified 路径默认使用更快的 partial 基线参数：
    - `min_audio_seconds=0.6`
    - `chunk_seconds=2.5`
    - `max_audio_seconds=12.0`
    - `stop_flush_min_seconds=0.25`
    - `min_speech_frames=60`
  - 在 `tests/test_asr_service.py` 中新增 simplified 路径测试。
- 目的：
  - 先恢复实时 partial 的及时性与可预测性，不再默认等到 10 秒才出字。
  - 保留 legacy 路径作为回滚基线，避免继续在原逻辑上补丁式叠加。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"`
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py`
  - `python tools/check_doc_corruption.py`
- 当前结果：
  - simplified 路径已接入主链路；
  - 自动化 53 项通过；
  - 当前已具备继续做下一轮 Phase 1/2 手工回归与调参的基础。
- 用户反馈：
  - 用户已明确同意开始实施简化重构。
- 后续动作：
  - 先用真实录音验证 simplified 路径的 partial 延迟是否明显下降，再决定是否继续收缩上传门控与文本层复杂 patch。

### 2026-05-10 / Commit 待填写
- 主题：
  - 将语气词清洗策略收敛为“只删除独立片段，不整句过滤”。
- 修改内容：
  - 在 `services/asr_service.py` 中收缩 `DEFAULT_LOW_INFORMATION_SEGMENTS`，移除较多容易误伤正常内容的复杂上下文词。
  - 简化 `_strip_low_information_segments()`，不再做复杂上下文型尾巴 patch，只删除独立片段中的语气词 / 幻觉词。
  - 调整 `refine_asr_result_text()` 与 `should_filter_asr_result()`：
    - 若删完独立片段后仍有正文，则保留正文；
    - 只有整句删空时，才整体不输出。
  - 在 `tests/test_asr_service.py` 中更新为新的预期行为。
- 目的：
  - 降低之前“整句低信息过滤”和复杂上下文 patch 带来的不可控误伤风险。
  - 更贴近用户要求的最小策略：只删除单个语气词片段，其他文字不动。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"`
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py`
  - `python tools/check_doc_corruption.py`
- 当前结果：
  - 自动化 54 项通过；
  - 当前文本层策略已明显简化，更适合继续在 simplified pipeline 基础上迭代。
- 用户反馈：
  - 用户明确要求“单个单个词语气词进行去除，别的字不变化，而不是整一句过滤掉”。
- 后续动作：
  - 继续基于真实录音观察：
    - 独立语气词是否明显减少；
    - partial 是否仍然足够快；
    - rewrite 是否仍然不够可见。

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

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第八轮：无效 partial / rewrite 去重。
- 修改内容：
  - 在 `services/asr_service.py` 中新增 `is_effective_text_update()`，用于判断新结果相对上一次展示文本是否真的带来了有效信息增量。
  - 在 `main.py` 中对 `segment_partial` 与 `segment_rewrite` 增加 no-op 抑制：如果清洗后文本实质未变化，就只记录日志，不再重复 emit。
  - 对 no-op rewrite 仍会更新段内回写进度，避免因为“结果没变化”而反复重复触发同一次重写。
  - 在 `tests/test_asr_service.py` 中新增 no-op 文本更新判断测试。
- 目的：
  - 减少前端被同一文本反复刷新、反复写缓存。
  - 让双层转写链路更聚焦“真正变好的结果”，降低无效 UI 抖动和日志噪声。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py` 通过。
- 当前结果：
  - 如果 chunk 识别结果或段级回写结果与当前展示文本实质相同，系统会直接跳过这次回推。
  - 对长时间录音和段级回写较频繁的场景，预计前端重复刷新会更少。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 继续结合真实录音观察“去重后是否会漏掉本该展示的细微改写”。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第九轮：前端重复 result_id 投递去重。
- 修改内容：
  - 在 `static/js/app.js` 中新增 `seenResultIds` 内存集合，以及 `rememberResultId()` / `rebuildSeenResultIds()` / `hasSeenResultId()`。
  - `handleASRResult()` 现在会在最前面跳过同一个 `result_id` 的重复投递。
  - 在合并、替换、缓存恢复、删除消息、清空会话等路径上同步维护 `seenResultIds`，避免集合漂移。
- 目的：
  - 进一步降低网络重投、前端重复处理同一条结果时造成的 UI 抖动与重复缓存写入。
  - 让前端即使在后端已做 no-op 去重后，仍保留一层 result_id 级别的兜底保护。
- 验证方式：
  - `node -e "new Function(require('fs').readFileSync('static/js/app.js','utf8')); console.log('app.js syntax OK')"` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 同一个 `result_id` 即使被前端重复收到，也只会处理一次。
  - 对网络抖动、重连边界或未来可能的重放场景更稳。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 继续观察是否还存在“不同 result_id 但语义重复”的边界抖动场景。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第十轮：缓存恢复后的消息 ID 计数器同步。
- 修改内容：
  - 在 `static/js/app.js` 中新增 `rememberMessageId()`，让前端在使用显式消息 ID 时同步推进 `messageIdCounter`。
  - `addMessageUI()` 与 `loadCache()` 现在都会确保恢复出来的历史消息 ID 被计数器感知，避免后续新消息复用旧 ID。
- 目的：
  - 修复“从本地缓存恢复后，新的实时消息可能和旧消息撞 ID”这一长期会话一致性风险。
  - 进一步稳住编辑、删除、替换等依赖消息 ID 的前端操作。
- 验证方式：
  - `node -e "new Function(require('fs').readFileSync('static/js/app.js','utf8')); console.log('app.js syntax OK')"` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 缓存恢复后，新增消息会继续使用更大的新 ID，而不是从 1 重新开始碰撞旧消息。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 继续观察长会话恢复、编辑和删除路径是否还有前端 ID 级别的一致性边界问题。
### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第十一轮：前端 localStorage 读取保护。
- 修改内容：
  - 在 `static/js/app.js` 中新增 `safeGetLocalStorage()`，统一封装浏览器 `localStorage.getItem()` 的异常兜底。
  - 将离线补偿音频、补偿状态、转写缓存、历史文档、缓存体积统计等读取路径全部改为安全读取。
  - 读取失败时改为记录错误并展示“缓存受限”告警，而不是让前端流程直接中断。
- 目的：
  - 补齐此前只保护“写入 / 删除”、未保护“读取”的缺口。
  - 降低浏览器禁用本地存储、隐私模式限制或缓存异常时，页面初始化 / 恢复阶段直接报错的风险。
- 验证方式：
  - `node -e "new Function(require('fs').readFileSync('static/js/app.js','utf8')); console.log('app.js syntax OK')"` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 即使 `localStorage.getItem()` 抛异常，前端也会优先降级运行，并给出缓存受限提示。
  - 长时间录音相关的缓存恢复、补偿音频检测、缓存体积显示路径都更稳。
- 用户反馈：
  - 待明早真实长录音与缓存恢复场景测试确认。
- 后续动作：
  - 继续关注 localStorage 受限场景下，是否还存在未覆盖的读取入口或提示不够清晰的问题。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第十二轮：静音过滤 / 弱语音第二轮门槛细化。
- 修改内容：
  - 在 `services/asr_service.py` 的 `RealtimeChunkPolicy` 中新增“最小活跃时长 / 最小有声时长 / 弱语音活跃阈值”相关参数。
  - 为 `AudioFeatures` 增加 `active_seconds` 与 `voiced_seconds` 派生信息，并新增 `_adaptive_presence_seconds()`。
  - `has_usable_speech()` 不再让 `active_ratio` 单独放行，而是改为“强信号”或“持续有声”或“持续弱语音但带一定有声占比”三段式判定。
  - 在 `tests/test_asr_service.py` 中补充“持续活跃但无有声的噪声应被丢弃”与“持续柔和语音仍应保留”的自动化测试。
- 目的：
  - 进一步压制“旁边人小声说话 / 活跃噪声”误进入实时转写的问题。
  - 同时保留对真实弱语音的容忍度，避免因为降噪过猛而误杀主说话人。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 单靠 `active_ratio` 升高、但几乎没有有声特征的缓冲，不会再被当成可转写语音直接放行。
  - 具有一定持续时长与少量有声支撑的柔和主语音，仍可通过新的弱语音兜底通道。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 继续结合真实录音日志，观察 `rms / peak / active / voiced` 与主观听感是否一致。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第十三轮：静音过滤日志可观测性增强。
- 修改内容：
  - 在 `main.py` 的实时 chunk 处理、实时缓冲丢弃、stop flush 丢弃日志中补充 `active_s / voiced_s / silence`。
  - 同步更新 `TEST_MATRIX.md` 与 `SESSION_SUMMARY.md`，明确明早真实录音需要重点对照的新指标。
- 目的：
  - 降低第二轮静音过滤门槛的后续调参成本，避免只看比例难以判断“真实持续时长”。
  - 让明早测试时可以更快分辨：是阈值过严漏掉了主语音，还是弱背景音确实应该被压下去。
- 验证方式：
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 后端日志现在能直接给出活跃秒数、有声秒数与静音占比，便于下一轮人工校准。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 继续把真实录音日志与前端转写文本对照，必要时再微调自适应时长门槛。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第十四轮：短促尾段弱语音抑制。
- 修改内容：
  - 在 `services/asr_service.py` 中新增 `tail_trigger_min_active_seconds` 与 `tail_trigger_min_voiced_seconds`。
  - 新增 `has_tail_triggerable_speech()`，让 `tail_silence_detected` 不再只看“是否存在可用语音”，还要看尾段是否具备最小持续活跃 / 有声时长。
  - 对“短促弱语音 + 尾部静音”新增 `drop_brief_tail_speech` 路径，避免这类片段继续等待或误进入转写。
  - 在 `tests/test_asr_service.py` 中补充“短促尾段弱语音应被丢弃”的测试。
- 目的：
  - 进一步压制旁边人轻声插一句、短促弱声触发尾静音切片的问题。
  - 让“尾静音触发转写”更偏向真正形成了一小段完整主语音的场景。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 只有极短一点点有声特征、随后立刻进入尾静音的片段，现在会直接被丢弃，而不是继续拖在缓冲中或误触发转写。
  - 持续柔和但确实形成一小段主语音的样本，仍可通过 `has_tail_triggerable_speech()` 保留。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 继续结合真实录音观察 `drop_brief_tail_speech` 是否过严，是否会误伤非常短但用户确实想保留的单词级表达。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第十五轮：语音门槛原因显式化。
- 修改内容：
  - 在 `services/asr_service.py` 中新增 `describe_usable_speech()` 与 `describe_tail_triggerable_speech()`，把“为什么通过 / 没通过门槛”从布尔值细化为原因标签。
  - `ChunkDecision` 新增 `speech_gate_reason` 与 `tail_gate_reason`，并在 chunk / stop flush 决策中写入。
  - `main.py` 的实时处理与丢弃日志新增 `speech_gate`、`tail_gate` 输出。
  - 在 `tests/test_asr_service.py` 中补充原因标签的断言，确保噪声与柔和语音样本的分类结果稳定。
- 目的：
  - 让明早真实录音调阈值时，不只知道“过了 / 没过”，还能直接知道是强信号、持续有声还是柔和语音兜底在生效。
  - 降低继续细调静音过滤时的理解成本，避免后续规则堆叠后变成黑盒。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 日志现在不仅能输出 `active_s / voiced_s / silence`，还会明确标记本段命中了哪一类语音门槛。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 继续把真实录音中的 gate reason 与前端文本效果对照，决定下一轮是否需要微调具体阈值。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第十六轮：柔和语音兜底的有声密度约束。
- 修改内容：
  - 在 `RealtimeChunkPolicy` 中新增 `min_voiced_density_for_soft_speech`。
  - 为 `AudioFeatures` 增加 `voiced_density` 派生指标，并把它纳入 `sustained_soft_speech` 的放行条件。
  - `main.py` 日志新增 `density` 输出，方便明早从日志直接观察“有声帧在活跃帧中的占比”。
  - 在 `tests/test_asr_service.py` 中新增“活跃很多但有声过稀”的样本，确保这类片段不会再触发柔和语音兜底。
- 目的：
  - 进一步压制“活跃度不低，但真正有声成分很稀薄”的背景噪声或远处插话。
  - 保住持续柔和主语音的同时，减少软语音兜底被稀疏噪声钻空子的概率。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 柔和语音兜底现在除了看 RMS / peak / active / voiced，还会看 voiced density；稀疏有声片段更难被误放行。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 继续结合真实录音观察 density 与误触发之间是否存在明显相关性。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第十七轮：离线 wav 门槛回放工具。
- 修改内容：
  - 新增 `tools/analyze_realtime_audio.py`，可按前端 512-sample 推流节奏离线回放 wav，并统计 `process/drop/waiting`、`speech_gate`、`tail_gate` 等命中情况。
  - 用本地 `41.wav / 70.wav / 97.wav` 跑了一轮分析，当前三份样本都属于 `strong_signal`，且都只在 `chunk_duration_reached` 时切出，没有触发弱语音/尾静音相关分支。
- 目的：
  - 给明早真实录音调参前，先补一个可复用的离线分析抓手，避免继续只靠合成样本盲调。
  - 让后续新增的真实弱背景样本可以快速回放，直接验证每轮静音过滤规则的效果。
- 验证方式：
  - `python tools/analyze_realtime_audio.py 41.wav 70.wav 97.wav` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tools\analyze_realtime_audio.py` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 现有 3 个本地 wav 样本暂时都更像“强主语音样本”，还不足以验证弱背景过滤是否真正到位。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 明早优先补采或筛出一批“旁边人小声插话 / 低音量背景说话”的真实样本，再用该工具回放校准门槛。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第十八轮：门槛环境变量覆盖。
- 修改内容：
  - 在 `services/asr_service.py` 中新增 `load_realtime_chunk_policy_overrides()`，支持从环境变量覆盖 `RealtimeChunkPolicy` 各项门槛。
  - 支持两级配置：通用 `REALTIME_*`，以及按环境区分的 `ONLINE_REALTIME_*` / `INTRANET_REALTIME_*`，其中环境专属优先级更高。
  - `main.py` 启动时会应用覆盖后的实时门槛，并在存在覆盖时输出日志。
  - 在 `tests/test_asr_service.py` 中新增环境覆盖的自动化测试，验证通用覆盖与环境专属覆盖优先级。
- 目的：
  - 让外网调试和内网部署可以分别校准实时转写门槛，而不必每次都改代码重新提交。
  - 降低明早根据真实录音反复微调阈值时的操作成本。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tools\analyze_realtime_audio.py` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 实时门槛现在既能全局覆盖，也能按内外网分别覆盖，双环境调参路径更清晰。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 明早如需试阈值，优先先改 `.env` 中对应 `ONLINE_REALTIME_*` 项，再结合离线回放与真实页面效果校准。

### 2026-05-10 / Commit 待填写
- 主题：
  - 实时转写第十九轮：离线分析 gain sweep。
- 修改内容：
  - 将 `tools/analyze_realtime_audio.py` 改为支持 `--gains`，可对同一 wav 做多档音量衰减回放。
  - 用 `41.wav` 做了衰减回放：`gain=1.0/0.5/0.25/0.125` 仍稳定属于 `strong_signal`；进一步衰减到 `0.06/0.03/0.015` 后，开始出现 `tail_silence_detected`、`drop_brief_tail_speech` 与 `drop_weak_background_after_tail_silence` 分支切换。
- 目的：
  - 在缺少真实弱背景样本时，先用真实主语音样本做音量衰减，粗看当前门槛在“强语音 -> 弱语音 -> 被抑制”之间的大致过渡区间。
  - 为明早真实样本回放提供一个更接近调参工作的分析模板。
- 验证方式：
  - `python tools/analyze_realtime_audio.py --gains 1.0 0.5 0.25 0.125 -- 41.wav` 通过。
  - `python tools/analyze_realtime_audio.py --gains 0.06 0.03 0.015 -- 41.wav` 通过。
  - `python -m py_compile .\tools\analyze_realtime_audio.py` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 当前门槛对 `41.wav` 的衰减样本，大致在 `gain≈0.06 ~ 0.03` 开始进入弱语音 / 丢弃边界区。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 明早优先拿真实“旁边人小声插话”样本做同样的 gain sweep，对比它和主语音样本的分界差异。

### 2026-05-10 / Commit 661cd1d
- 主题：
  - 实时转写第二十轮：离线事件级时间线分析。
- 修改内容：
  - `tools/analyze_realtime_audio.py` 新增事件级时间线输出，可展示每次 `process / drop / waiting / stop flush` 的时间窗口、buffer 时长、`speech_gate / tail_gate` 与音频特征。
  - 工具默认模拟停止录音后的 `stop flush`，并修正了小数增益显示精度。
  - 新增 `tests/test_analyze_realtime_audio.py`，覆盖 chunk 触发、强语音 stop flush、弱语音 stop flush 三类分析路径。
- 目的：
  - 减少明早拿真实录音调静音过滤时的盲调成本，先把“为什么被放行 / 为什么被丢弃”看清楚。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py` 通过。
  - `python tools/check_doc_corruption.py` 通过。
- 当前结果：
  - 现在已经能从离线回放中直接定位“第几秒开始从放行转向丢弃”，并看到对应 gate 标签与音频特征。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 继续补更接近真实“旁边人小声插话”的离线模拟方式，缩小真实样本缺口。

### 2026-05-10 / Commit ba7d742
- 主题：
  - 实时转写第二十一轮：前景/背景混音弱背景模拟。
- 修改内容：
  - `tools/analyze_realtime_audio.py` 新增前景/背景混音分析能力，支持：
    - `--mix-background`
    - `--mix-background-gains`
    - `--mix-background-offset-seconds`
    - `--mix-tail-silence-seconds`
  - 可将一条主语音 wav 与另一条低增益背景 wav 叠加后回放，并继续复用现有时间线与 stop flush 分析。
  - `tests/test_analyze_realtime_audio.py` 新增混音偏移、尾部静音与混音后 stop flush 分析的自动化测试。
- 目的：
  - 在缺少真实弱背景样本前，先补一个更接近“主讲人 + 旁边人小声插话”的离线验证手段。
  - 为后续静音过滤门槛继续迭代提供更贴近目标场景的分析输入。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py` 通过。
  - `python tools/analyze_realtime_audio.py --timeline --timeline-limit 10 --gains 1.0 --mix-background .\70.wav --mix-background-gains 0.06 0.03 --mix-background-offset-seconds 2.0 --mix-tail-silence-seconds 0.4 -- .\41.wav` 通过。
  - `python tools/check_doc_corruption.py` 待本轮提交前执行。
- 当前结果：
  - 现在已经可以离线观察“主语音 + 低增益背景语音 + 尾部静音”组合场景下，chunk 与 stop flush 的分流表现。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 明早优先把真实弱背景样本带入同样的分析命令，对比混音模拟与真实回放之间的差异。

### 2026-05-10 / Commit b0ca075
- 主题：
  - 实时转写第二十二轮：片段裁剪分析。
- 修改内容：
  - `tools/analyze_realtime_audio.py` 新增主音频与背景音频的片段裁剪支持，可指定裁剪起点与裁剪时长后再做单条回放或前景/背景混音分析。
  - 新增裁剪标签输出，便于把分析结果与具体片段配置对应起来。
  - `tests/test_analyze_realtime_audio.py` 新增裁剪相关自动化测试，覆盖起点、时长、越界空片段与标签格式。
- 目的：
  - 在现有样本偏强的情况下，尽量通过“只取局部短片段”的方式逼近用户最关心的“短促弱插话 / 尾段弱背景说话”场景。
  - 进一步减少明早静音过滤调参时对整条强主语音样本的依赖。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py` 通过。
  - `python tools/analyze_realtime_audio.py --timeline --timeline-limit 12 --clip-start-seconds 0.0 --clip-duration-seconds 2.2 --gains 1.0 --mix-background .\70.wav --mix-background-start-seconds 1.5 --mix-background-duration-seconds 1.0 --mix-background-gains 0.06 0.03 --mix-background-offset-seconds 0.8 --mix-tail-silence-seconds 0.5 -- .\41.wav` 通过。
  - `python tools/check_doc_corruption.py` 待本轮提交前执行。
- 当前结果：
  - 现在已经可以只观察几秒钟的局部主语音 + 局部背景语音 + 尾静音组合场景，离线验证粒度更细。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 明早优先用真实弱背景录音片段跑相同命令，对比局部分析结果与整段分析结果是否一致。

### 2026-05-10 / Commit ee347a7
- 主题：
  - 实时转写第二十三轮：多偏移扫描与 JSON 导出。
- 修改内容：
  - `tools/analyze_realtime_audio.py` 新增：
    - 多组 `--mix-background-offset-seconds` 批量扫描；
    - `--json-output` 结构化导出。
  - 结构化结果包含 `scenario`、统计计数、`stop_flush_event` 与全量 `timeline_events`。
  - `tests/test_analyze_realtime_audio.py` 新增 JSON 结果与结构化字段的自动化测试。
- 目的：
  - 让明早的弱背景插话实验可以一次跑多组 offset，并把结果直接落盘留档，减少手工整理成本。
  - 为后续对真实样本做批量分析和脚本化比对打基础。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py` 通过。
  - `python tools/analyze_realtime_audio.py --clip-start-seconds 0.0 --clip-duration-seconds 2.2 --mix-background 70.wav --mix-background-start-seconds 1.5 --mix-background-duration-seconds 1.0 --mix-background-gains 0.06 --mix-background-offset-seconds 0.2 0.8 1.4 --mix-tail-silence-seconds 0.5 --json-output temp_audio\\analysis_scene_matrix.json -- 41.wav` 通过。
  - `python tools/check_doc_corruption.py` 待本轮提交前执行。
- 当前结果：
  - 现在已经可以一次性得到多组弱背景插话时机的分析结果，并直接输出成 JSON 供后续比对。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 明早优先把真实弱背景样本按多 offset / 多增益方式导出成 JSON，再和今晚的合成场景结果对照。

### 2026-05-10 / Commit 5413a9e
- 主题：
  - 实时转写第二十四轮：连续有声时长约束。
- 修改内容：
  - `services/asr_service.py` 中为 `AudioFeatures` 新增 `max_active_run_seconds` 与 `max_voiced_run_seconds`。
  - `RealtimeChunkPolicy` 新增连续时长门槛，实时主路径与尾静音路径都开始检查“最长连续有声时长”。
  - 对“累计有声量够、但只是零散碎片”的场景，`describe_usable_speech()` 现在会明确落到碎片化路径，而不是继续当作持续语音放行。
  - `main.py` 日志新增 `active_run_s / voiced_run_s` 输出。
  - `tests/test_asr_service.py` 新增碎片化有声场景测试与尾静音碎片场景测试。
- 目的：
  - 直接压制“总量看起来够、但实际上只是零散弱插话”的误触发。
  - 把前几轮离线分析得到的结论落实到线上判定规则里。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py` 通过。
  - `python tools/check_doc_corruption.py` 待本轮提交前执行。
- 当前结果：
  - 现在系统已经不只看累计 `voiced_ratio / voiced_seconds`，还会看 `voiced_run_s`，更容易拦住碎片化弱插话。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 明早优先对照误触发片段的 `voiced_run_s`，判断这轮规则是否真正命中目标场景。

### 2026-05-10 / Commit 17b74a2
- 主题：
  - 实时转写第二十五轮：离线 run 指标口径对齐。
- 修改内容：
  - `tools/analyze_realtime_audio.py` 的时间线输出、终端格式化结果与 JSON 导出新增：
    - `max_active_run_seconds`
    - `max_voiced_run_seconds`
  - `tests/test_analyze_realtime_audio.py` 新增对这两个结构化字段的校验。
- 目的：
  - 让离线分析工具和线上实时日志使用同一套连续时长指标，避免明早调参时出现“线上看一套、离线看另一套”的口径偏差。
- 验证方式：
  - `python -m unittest discover -s .\tests -p "test_*.py"` 通过。
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py` 通过。
  - `python tools/analyze_realtime_audio.py --timeline --timeline-limit 2 --clip-start-seconds 0.0 --clip-duration-seconds 2.2 --gains 1.0 --mix-background .\70.wav --mix-background-start-seconds 1.5 --mix-background-duration-seconds 1.0 --mix-background-gains 0.06 --mix-background-offset-seconds 0.2 --mix-tail-silence-seconds 0.5 --json-output temp_audio\\analysis_scene_matrix_runs.json -- 41.wav` 通过。
  - `python tools/check_doc_corruption.py` 待本轮提交前执行。
- 当前结果：
  - 离线分析结果现在已经能直接输出 `active_run_s / voiced_run_s` 对应值，可和线上日志逐项对照。
- 用户反馈：
  - 待明早真实录音测试确认。
- 后续动作：
  - 明早优先对一段真实误触发片段同时看线上日志与离线 JSON，确认 run 指标是否同方向变化。

### 2026-05-10 / Commit 15c2fc6
- 主题：
  - Python 3.9 运行兼容性修复。
- 修改内容：
  - 在 `main.py` 顶部补充 `from __future__ import annotations`。
- 目的：
  - 修复 Python 3.9 下 `str | None` 注解在模块导入时被立即求值，导致 `TypeError: unsupported operand type(s) for |` 的启动报错。
- 验证方式：
  - `python -m py_compile .\main.py` 通过。
  - 当前 shell 直接 `import main` 时，已越过注解报错点；后续阻塞变为环境中缺少 `flask_socketio` 包，而不再是类型注解兼容性错误。
- 当前结果：
  - 这次报出的 `| None` 兼容性问题已修复。
- 用户反馈：
  - 用户已明确反馈当前版本启动时出现该报错。
- 后续动作：
  - 若用户的 asr 环境仍提示缺包，再继续处理依赖问题。
## 2026-05-10 / 本轮：接入真实 PCM 录音离线分析
- 改动：`tools/analyze_realtime_audio.py` 新增 `pcm` 输入支持，可直接分析 `temp_audio/` 下前端自动落盘的真实录音
- 改动：补充 `tests/test_analyze_realtime_audio.py`，覆盖 `pcm` 输入路径
- 新增：`docs/PM/REALTIME_AUDIO_SAMPLE_MANIFEST.md`，沉淀本地样本来源、估算时长和推荐命令
- 验证：`python -m unittest tests.test_analyze_realtime_audio` 通过；真实样本 `stream_recording_20260510_183243.pcm` 可直接跑出时间线

## 2026-05-10 / 本轮：固化 PowerShell 中文写入禁令
- 背景：此前已多次出现通过 PowerShell 命令链路写中文文档，导致内容变成 `?` 或乱码的问题。
- 改动：把这条教训正式写入长期记忆文件：
  - `AGENTS.md`
  - `docs/PM/CODEX_PLAYBOOK.md`
- 新默认规则：后续修改中文文档时，优先使用 `apply_patch`，避免再走 PowerShell 直接写中文的高风险路径。
- 验证：`python tools/check_doc_corruption.py` 通过。

## 2026-05-10 / 本轮：启动真实 PCM 的静音过滤 / 弱语音门控校准
- 已确认 `temp_audio/` 下的真实 PCM 录音可按前端实时流粒度回放，当前离线工具按 `packet_samples=512` 重放，适合做实时门控复盘。
- 改动：`tools/analyze_realtime_audio.py` 新增 `--pipeline simplified|legacy`，并默认按 `simplified` 分析，和当前外网开发链路对齐。
- 改动：`services/asr_service.py` 新增 `build_realtime_chunk_policy()`，把 main 与离线分析工具的默认门控参数收敛到同一处维护。
- 改动：收紧 simplified 上传门控：
  - `speech_gate_reason=no_usable_speech`
  - `speech_gate_reason=fragmented_voiced_presence`
  - 上述两类片段不再通过 `simplified_fallback_*` 放行，而是直接走 `simplified_drop_non_speech_after_*`
- 保留：`tail_short_speech_detected` 的极短短语音兜底，不直接一刀切删除。
- 验证：
  - `python -m unittest tests.test_asr_service tests.test_analyze_realtime_audio`
  - `python -m py_compile .\main.py .\services\asr_service.py .\tools\analyze_realtime_audio.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py`

## 2026-05-10 / 本轮：修复停止录音后仍继续写入 PCM 的风险链路
- 用户反馈：
  - 点击停止录音后，`stream_recording_20260510_204811.pcm` 仍继续增长
  - 整段朗读前端没有输出，但离线分析显示这条样本本身已被停止后的持续录音污染
- 结构性结论：
  - 这不是单纯的静音门槛问题，还涉及录音停止链路未收干净
- 改动：
  - 前端新增 `start_recording` 握手
  - 前端停止时显式失效旧 `recordingGeneration`
  - 前端停止时更彻底地断开 `processor`、`sourceNode`、`mediaStream`、`audioContext`
  - 后端忽略 `stop_requested` 之后继续到达的 `audio_stream`
  - 后端新增 stop 后短冷却窗口，忽略晚到音频包，避免 stop 后又偷偷创建/污染 session
- 直接证据：
  - `stream_recording_20260510_204811.pcm` 离线分析显示总时长约 75.87 秒，明显超过用户主观操作预期，属于已污染样本
- 验证：
  - `python -m py_compile .\main.py`
  - `node --check static\js\app.js`

## 2026-05-10 / 本轮：降低连续朗读场景的切段碎片与展示延迟
- 用户反馈：
  - `stream_recording_20260510_211035.pcm` 中，连续朗读时前端虽然有输出，但切得偏碎
  - 后半段“如果某类信息在……”出现得很晚，且展示不完整
- 离线结论：
  - 真实 ASR 抽样显示，后半段内容其实已经被识别到
  - 更像是“微小停连导致 chunk 过碎 + 运行时 backlog 排空不够积极”
- 改动：
  - `services/asr_service.py` 为 simplified 管线新增 `min_tail_chunk_seconds=1.4`
  - 过短尾静音不再立刻 `tail_silence_detected` 切段，而是先继续等待
  - `main.py` 新增 `drain_ready_realtime_buffer()`，每次处理完当前 chunk 后继续主动消化已积压的 buffer
- 离线结果：
  - `211035.pcm` 在 simplified 口径下的 `process_count` 从 18 降到 16
  - 首段切分从约 1 秒多提前切，改为更偏向先攒到 2.5 秒左右再发
- 验证：
  - `python -m unittest tests.test_asr_service tests.test_analyze_realtime_audio`
  - `python -m py_compile .\main.py .\services\asr_service.py .\tools\analyze_realtime_audio.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py`
