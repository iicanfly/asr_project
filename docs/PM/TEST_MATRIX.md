# TEST_MATRIX

## 当前测试重点
- 当前测试重点是`实时转写`。
- 音频上传与文档生成虽然可用，但暂不作为近期核心回归对象。

## 实时转写必测项
以下项目在每次修改实时转写逻辑后都必须回归：

| 测试项 | 目标 | 说明 |
| --- | --- | --- |
| 静音过滤 | 无效静音或低价值背景音不应触发转写 | 重点观察旁边人的小声说话、环境底噪 |
| 弱语音处理 | 真实有效的低音量说话不能被过度误杀 | 需要平衡“降噪”和“保留有效输入” |
| 语气词过滤 | “嗯”“啊”“呀”等语气词显著减少 | 不能明显误伤正常短句 |
| 转写延迟 | 输出速度保持可接受 | 不能为了质量显著拖慢实时反馈 |
| 替换回写 | 小段结果可被大段高质量结果替换 | 前端展示需要稳定、可理解 |
| 长时间录音稳定性 | 长时间运行不明显退化 | 关注堆积、卡顿、碎片化加重等现象 |

## 回归优先级
### P0：每次都测
- 静音过滤
- 弱语音处理
- 语气词过滤
- 转写延迟
- 替换回写
- 长时间录音稳定性

## 暂缓补充
- 上传音频转写的详细测试项：待后续补充。
- 文档生成与文档二次修改的详细测试项：待后续补充。
- 浏览器兼容性矩阵：待后续补充。

## 当前测试策略
- 近期所有与实时转写相关的改动，都应优先围绕“提高转写质量”进行验证。
- 验证时既要看单点效果，也要看多个优化叠加后是否互相冲突。

## 2026-05-10 新增回归项

### 自动化基础检查
- 每次改动 `services/asr_service.py` 或实时切片 / 过滤规则后，至少执行：
  - `python -m unittest discover -s .\tests -p "test_*.py"`
  - `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py`
- 每次批量修改中文文档后，至少执行：
  - `python tools/check_doc_corruption.py`

### 手工回归补充
- 停止录音闭环：
  - 点击“停止录音”后，前端不应继续推音频。
  - 后端日志中应看到 `stop_recording` 相关记录。
  - 如果停止时仍有一小段未切出的尾音，观察是否会触发一次补充转写，而不是直接丢掉。
  - 如果停止发生在某个 chunk 正在处理中，观察后端是否会在当前处理完成后再稳妥收尾。
- 前端数据一致性：
  - 当两条结果被合并为同一条消息时，UI 条数与 `transcriptData` 条数应保持一致。
  - 从缓存恢复后继续录音时，新消息不应复用旧消息 ID，编辑 / 删除 / 替换都应仍指向正确消息。
- 未来替换回写预演：
  - 当后端开始发送 `replace_target_id` 后，前端应替换旧消息而不是新增一条。
  - 重点确认：
    - 同一 `segment_id` 下的小段结果会继续合并到同一条消息中。
    - `segment_rewrite` 到达后，旧文本会被直接覆盖，而不是变成重复追加。
    - 新的 `segment_id` 到达后，应新开一条消息，不应继续粘到上一段里。
    - 当新结果与当前展示文本实质相同，前端不应再出现无意义的重复刷新。
    - 当同一个 `result_id` 被重复投递时，前端也不应重复渲染。
- 静音过滤 / 弱语音专项观察：
  - 后端日志里应重点看 `Dropping realtime buffer` 与 `Processing realtime chunk` 两类日志。
  - 观察 `rms / peak / active / voiced / active_s / voiced_s / silence` 指标与实际听感是否一致。
  - 如果旁边人的小声说话明显减少触发，同时主说话人的弱音没有被大量漏掉，说明第一轮阈值方向正确。
- 语气词过滤专项观察：
  - 后端日志里应同时观察“原始结果 / 清洗后结果”，确认是否把低价值语气词成功收敛。
  - 至少口测以下几类样本：
    - 纯语气词：如“嗯”“啊”
    - 首尾带语气词：如“嗯 今天开始”“你好啊”
    - 有效短句：如“好的”“可以”
  - 如果纯语气词显著减少，且“好的 / 可以 / 那个我们开始吧”没有被明显误杀，说明第二轮规则方向正确。
- 分段策略专项观察：
  - 对有短暂停顿但语义仍连续的一句话，观察是否仍被过早拆成两段。
  - 对明显一句话说完并停顿后进入下一点内容的场景，观察是否能稳定开启新段。
  - 检查同段中文拼接时是否还出现大量多余空格；英文连续词之间的空格是否仍正常。
- 长时间录音稳定性专项观察：
  - 连续录音较长时间后，浏览器页面不应明显越来越卡。
  - 在线录音时观察内存是否仍因 `audioChunks` 持续上涨。
  - 观察缓存大小增长速度是否明显放缓，停止录音或刷新页面后最近一批结果是否仍能恢复。
  - 如果本地缓存空间不足或缓存损坏，前端应给出“缓存受限”类提示，而不是直接出现恢复失败或页面异常。
### 2026-05-10 / localStorage 读取保护补充
- 手工补充检查：
  - 如果浏览器环境限制 `localStorage.getItem()`，页面初始化不应直接白屏或中断脚本。
  - 在缓存读取失败时，`cache-info` 应显示“缓存受限”类提示，而不是静默失败。
  - 离线补偿检测、缓存恢复、历史文档恢复在读取失败时都应允许页面继续使用其它核心功能。

### 2026-05-10 / 静音过滤第二轮自动化补充
- 自动化补充检查：
  - “持续活跃但无足够有声占比”的噪声样本，应被 `has_usable_speech()` 判为不可用，并在达到 chunk 时长后被丢弃。
  - “持续柔和但真实”的弱语音样本，即使 `voiced_ratio` 略低于常规阈值，也应能通过弱语音兜底路径保留。
- 本轮已新增：
  - `tests/test_asr_service.py::test_active_noise_without_voiced_presence_is_not_usable_speech`
  - `tests/test_asr_service.py::test_sustained_soft_speech_still_counts_as_usable`

### 2026-05-10 / 静音过滤日志校准补充
- 手工补充检查：
  - 明早真实录音时，优先记录被丢弃 chunk 的 `active_s / voiced_s / silence`，确认是否符合“旁边低声插话应被压制”的预期。
  - 对被保留但音量偏轻的主说话人样本，同样观察 `active_s / voiced_s` 是否稳定高于当前自适应门槛。

### 2026-05-10 / 尾静音短促弱语音补充
- 自动化补充检查：
  - 如果一小段短促弱语音后立刻进入尾静音，不应继续等待更长缓冲，也不应直接触发转写，而应走丢弃路径。
  - 如果同样是尾静音场景，但前面已经形成足够持续的柔和主语音，则仍应允许触发转写。
- 本轮已新增：
  - `tests/test_asr_service.py::test_brief_tail_speech_is_dropped_even_if_it_has_some_voiced_frames`

### 2026-05-10 / gate reason 观察补充
- 手工补充检查：
  - 明早真实录音时，除数值日志外，还要重点记录 `speech_gate` 与 `tail_gate` 标签，确认当前放行 / 拦截是否符合预期。
  - 如果误触发样本与漏识别样本长期集中在同一类 gate reason，下一轮阈值调整应优先围绕那条规则进行。
- 自动化补充检查：
  - 噪声样本应稳定输出 `no_usable_speech`。
  - 柔和但持续的人声样本应稳定输出 `sustained_soft_speech` 与 `tail_sustained_presence`。

### 2026-05-10 / voiced density 补充
- 自动化补充检查：
  - 如果活跃帧不少，但有声帧只占活跃帧中的很小一部分，则不应再走 `sustained_soft_speech` 兜底。
- 手工补充检查：
  - 明早真实录音时，结合 `density` 与 `speech_gate` 观察：误触发背景音是否集中出现在低 density 片段。

### 2026-05-10 / 离线 wav 回放补充
- 工具：
  - `python tools/analyze_realtime_audio.py <wav1> <wav2> ...`
- 用途：
  - 按前端真实推流节奏离线回放 wav，快速观察当前门槛下的 `process/drop/waiting` 与 gate reason 命中情况。
- 当前已知：
  - 本地 `41.wav / 70.wav / 97.wav` 当前都属于 `strong_signal` 样本，只能验证强主语音链路，暂时不能替代弱背景样本回归。

### 2026-05-10 / 离线时间线回放补充
- 工具：
  - `python tools/analyze_realtime_audio.py --timeline --timeline-limit 12 -- <wav>`
  - `python tools/analyze_realtime_audio.py --timeline --timeline-include-waiting --timeline-limit 0 -- <wav>`
- 用途：
  - 精确观察每次 `process / drop / waiting / stop flush` 发生在第几秒、对应 buffer 多长、命中了哪条 `speech_gate / tail_gate`。
  - 明早拿真实弱背景样本时，优先用这组输出定位“哪一段被误放行、哪一段被误丢弃”，减少盲调阈值。
- 自动化补充检查：
  - `tests/test_analyze_realtime_audio.py` 应覆盖：
    - chunk 到达阈值时的 `process` 事件记录；
    - 强语音尾段的 `stop_flush_pending_audio`；
    - 弱语音尾段的 `stop_flush_drop_weak_audio`。

### 2026-05-10 / gain sweep 补充
- 工具：
  - `python tools/analyze_realtime_audio.py --gains 1.0 0.5 0.25 0.125 -- <wav>`
  - `python tools/analyze_realtime_audio.py --gains 0.06 0.03 0.015 -- <wav>`
- 用途：
  - 对同一真实 wav 做音量衰减回放，粗看当前门槛在“强语音 / 弱语音 / 被抑制”之间的过渡区间。
- 当前已知：
  - `41.wav` 在高增益段仍稳定为 `strong_signal`；大致到 `gain≈0.06 ~ 0.03` 附近开始出现弱语音与丢弃分支。

### 2026-05-10 / 环境变量调参补充
- 手工补充检查：
  - 当通过 `.env` 设置 `ONLINE_REALTIME_*` 或 `INTRANET_REALTIME_*` 后，启动日志应能看到实际生效的覆盖项。
  - 调整某个实时门槛后，离线回放工具与页面真实录音日志应体现出一致的行为变化。
