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
