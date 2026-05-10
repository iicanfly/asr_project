# 实时语音转写简化重构实施清单

## 1. 文档目的

本文档把《实时语音转写简化版重构方案》进一步落到执行层，回答：

- 下一步具体先改什么；
- 每一步改哪些文件；
- 每一步怎么验证；
- 每一步完成后建议形成什么本地版本；
- 失败时回滚到哪个 commit。

本文档默认建立在以下两份文档基础上：

- `C:\Users\16010\Desktop\asr_developing_project\asr_project\docs\PM\REALTIME_ASR_CURRENT_IMPLEMENTATION.md`
- `C:\Users\16010\Desktop\asr_developing_project\asr_project\docs\PM\REALTIME_ASR_SIMPLIFIED_REFACTOR_PLAN.md`

---

## 2. 当前建议的工作原则

在正式动手前，先固定这几条原则：

### 原则 A：先恢复“能稳定出字”，再继续追求极致过滤

当前最痛的问题已经从“嗯太多”变成了：

- 出字延迟大
- 有些话不出
- 行为不可预测

因此实施顺序必须是：

1. 先恢复实时性与可预测性
2. 再收敛静音噪声
3. 最后再精修尾巴文本质量

### 原则 B：每完成一个阶段，必须形成单独本地 commit

建议每个阶段至少一个 commit，确保可以按阶段回滚。

### 原则 C：不破坏双环境调用链路

本轮只允许改：

- 实时切片策略
- 实时 chunk 是否上传
- 文本基础清洗
- 段级 rewrite 节奏

本轮不要改：

- 内网 / 外网 ASR 协议
- 鉴权
- 证书
- LLM 接口

### 原则 D：不把文本过滤反向写进原始音频累计逻辑

也就是：

- partial 文本被清洗，不等于对应音频必须从 `active_segment.audio_buffer` 中删除
- rewrite 仍应尽量基于原始有效音频做后续修正

---

## 3. 当前回滚基线

建议把下面几个版本视为可回滚里程碑：

### 文档基线
- `72a5939` — `docs: add realtime asr implementation guide`
- `4a922b6` — `docs: add simplified realtime asr refactor plan`

### 当前代码基线
- `c8f2722` — `fix: trim long low-information transcript tails`

如果后续简化重构第一步做坏了，优先回滚到：

- `c8f2722`

---

## 4. 整体实施顺序

建议分 5 个执行阶段：

1. Phase 0：冻结复杂实现，建立重构工作面
2. Phase 1：恢复 partial 的实时性
3. Phase 2：简化上传门控
4. Phase 3：验证 rewrite 兼容性
5. Phase 4：视需要再决定是否加回高级尾巴策略

---

## 5. Phase 0：冻结复杂实现，建立重构工作面

## 5.1 目标

在真正改逻辑前，先把“复杂现状”与“简化版新实现”分开，避免在原函数上继续打补丁。

## 5.2 建议改动

### 文件
- `C:\Users\16010\Desktop\asr_developing_project\asr_project\services\asr_service.py`
- `C:\Users\16010\Desktop\asr_developing_project\asr_project\main.py`

### 动作

1. 不立即删除旧逻辑
2. 先明确新增“简化版”函数入口，例如：
   - `decide_chunk_trigger_simple()`
   - `decide_chunk_upload_simple()`
   - `refine_asr_result_text_basic()`
3. 旧逻辑继续保留作对照
4. 在 `main.py` 中通过一个明确开关切换：
   - 当前复杂版
   - 新的简化版

### 建议开关

优先使用环境变量，例如：

- `ENABLE_SIMPLIFIED_REALTIME_PIPELINE=True/False`

默认建议：

- 外网开发先开
- 内网默认先保持旧逻辑，等验证通过再切换

## 5.3 验证

### 必跑
- `python -m py_compile .\main.py .\services\asr_service.py`
- `python -m unittest discover -s .\tests -p "test_*.py"`

### 手工验证
- 启动服务，确保至少没有直接启动失败

## 5.4 建议 commit

建议形成：

- `refactor: scaffold simplified realtime pipeline switch`

---

## 6. Phase 1：恢复 partial 的实时性

## 6.1 目标

让用户恢复“正常说一句话，2~3 秒内能看到 partial”。

这是最优先目标。

## 6.2 建议改动

### 文件
- `services/asr_service.py`
- `main.py`
- `tests/test_asr_service.py`

### 重点动作

1. 将简化版路径里的：
   - `chunk_seconds`
   - `min_audio_seconds`
   - `max_audio_seconds`
   调回更适合实时系统的范围

### 建议起始值

- `chunk_seconds = 2.5`
- `min_audio_seconds = 0.6`
- `max_audio_seconds = 12.0`
- `stop_flush_min_seconds = 0.25 ~ 0.3`

2. 先不要动太多强弱语音阈值
3. 先观察仅仅缩短切片时长后，实时体验是否明显恢复

## 6.3 暂时不要做的事

此阶段先不要继续强化：

- 上下文型低信息短句过滤
- 长尾巴复杂截断
- retain 的复杂补丁

## 6.4 自动化验证

建议新增 / 调整测试：

1. chunk 达到 2.5 秒时可触发上传
2. 未到最小时长不触发
3. 停止录音时短尾音仍能走 stop flush

## 6.5 手工验证

至少口测：

1. 正常说一句话，2~3 秒内是否出 partial
2. 说完停顿，不点 stop 是否也能自然出字
3. 不说话时是否没有明显疯狂刷字

## 6.6 通过标准

只要满足以下两条，就可以进入下一阶段：

1. 延迟明显下降
2. 正常说话不再经常“说了但没字”

## 6.7 建议 commit

- `refactor: restore faster realtime partial chunking`

---

## 7. Phase 2：简化上传门控

## 7.1 目标

在恢复实时性的基础上，减少明显静音/弱噪声上传，但不要再次把系统改回“经常不出字”。

## 7.2 建议改动

### 文件
- `services/asr_service.py`
- `tests/test_asr_service.py`

### 动作

将当前复杂 chunk 决策拆成两个更清晰的函数：

#### A. `decide_chunk_trigger_simple()`
只判断：

- 是否达到最小时长
- 是否达到 chunk 时长
- 是否检测到尾静音

#### B. `decide_chunk_upload_simple()`
只判断：

- 这段候选 chunk 值不值得上传

这样可以把“触发”和“是否上传”从当前单个大函数中拆开。

## 7.3 建议保留的上传门控

第一版简化时，只建议保留这三类判断：

### 1）明显强语音 → 上传

### 2）持续有人声 → 上传

### 3）明显静音 / 明显弱背景 → 不上传

## 7.4 建议弱化的判断

暂时弱化：

- retain 的常规 chunk 路径
- 太多 “不够确认先等等” 的复杂分支

建议只保留一个相对收敛的保守点：

- stop 前极短尾音保护

## 7.5 自动化验证

重点增加：

1. 明显弱背景 chunk 不上传
2. 明显人声 chunk 上传
3. 短尾音 stop 时仍有补救机会

## 7.6 手工验证

重点观察日志：

- `Processing realtime chunk`
- `Dropping realtime buffer`

看是否能更容易解释：

- 为什么发了
- 为什么没发

## 7.7 通过标准

只要做到：

1. 行为比现在更可预测
2. 日志更容易解释
3. 不再严重依赖 retain 才能出字

就可以进入下一阶段。

## 7.8 建议 commit

- `refactor: simplify realtime upload gating`

---

## 8. Phase 3：把文本清洗降级为基础版

## 8.1 目标

让文本清洗重新承担“基础清理”职责，而不是继续承担“主路径补锅器”职责。

## 8.2 建议改动

### 文件
- `services/asr_service.py`
- `tests/test_asr_service.py`

### 本阶段建议保留

1. 边界语气词清洗
2. 明显低信息整句过滤
3. 少量稳定黑名单

### 本阶段建议降级 / 关停

1. `DEFAULT_CONTEXTUAL_LOW_INFORMATION_SEGMENTS`
2. 复杂“正文后长尾巴截断”
3. 针对个别样本补出来的 patch 型规则

建议方式：

- 不直接删
- 先收进可选开关

例如未来可加：

- `ENABLE_CONTEXTUAL_LOW_INFO_FILTER=False`
- `ENABLE_LONG_TAIL_TRIM=False`

## 8.3 自动化验证

应保留的测试：

1. 纯 `嗯 / 啊 / thank you` 仍被过滤
2. 正常句子不被误删
3. `好的 / 可以` 这类基础短句仍保留

应暂时弱化的测试：

1. 高度依赖上下文 patch 的复杂尾巴样本

## 8.4 手工验证

重点观察：

1. 说一句正常话，partial 是否更自然出现
2. 是否还在大范围刷 `嗯`
3. 是否因为文本层过强导致“本来识别到了但全被清掉”

## 8.5 通过标准

做到：

1. 文本层规则明显更简单
2. 误删感下降
3. 主问题仍受控

即可进入下一阶段。

## 8.6 建议 commit

- `refactor: reduce realtime transcript cleanup complexity`

---

## 9. Phase 4：验证 rewrite 兼容性

## 9.1 目标

确认简化主路径之后，段级 rewrite 仍正常工作。

## 9.2 建议改动

### 文件
- `services/asr_service.py`
- `main.py`
- `tests/test_asr_service.py`
- 如有必要：
  - `static/js/app.js`

### 动作

1. 检查 `active_segment.audio_buffer` 是否仍正常累计
2. 检查 `segment_partial` 是否仍绑定正确 `segment_id`
3. 检查 `segment_rewrite` 是否仍能覆盖前一个结果
4. 检查 finalize 段落条件是否仍合理

## 9.3 自动化验证

应至少覆盖：

1. enough chunks + enough duration → 触发 rewrite
2. rewrite 后仍能更新 `last_result_id`
3. 同段 rewrite 不会新增一条，而是替换旧条

## 9.4 手工验证

重点观察前端：

1. 小段是否先出来
2. 过几秒后是否出现更完整替换
3. 是否出现重复堆叠而不是替换

## 9.5 通过标准

做到：

1. partial 更快
2. rewrite 仍存在
3. 前端替换行为正常

即可认为简化重构主目标成立。

## 9.6 建议 commit

- `refactor: verify simplified pipeline rewrite compatibility`

---

## 10. Phase 5：决定是否加回高级尾巴策略

## 10.1 前提

只有在下面三件事都已经成立后，才考虑加回：

1. partial 已恢复实时性
2. 静音阶段已基本稳定
3. rewrite 已兼容正常

## 10.2 可选加回项

### 1）上下文型低信息短片段过滤

适用于：

- 说完后偶发少量 `对 / 好的 / 那啥 / okay`

### 2）长尾巴截断

适用于：

- 正文正确，但结尾经常挂一长串 `嗯`

## 10.3 加回方式

必须遵守：

1. 开关化
2. 可回退
3. 不与主路径强耦合

## 10.4 建议 commit

如果后续确实需要，建议单独一轮：

- `feat: re-enable optional contextual transcript tail cleanup`

---

## 11. 每个阶段都要执行的通用验证

## 11.1 自动化验证

每次改动实时转写逻辑后，至少执行：

- `python -m unittest discover -s .\tests -p "test_*.py"`
- `python -m py_compile .\main.py .\services\asr_service.py .\tests\test_asr_service.py .\tests\test_analyze_realtime_audio.py .\tools\analyze_realtime_audio.py`

如果修改了中文文档，还必须执行：

- `python tools/check_doc_corruption.py`

## 11.2 手工验证

每个阶段至少做这 5 类口测：

1. 正常说一句完整话
2. 轻声说一句短话
3. 说完后停顿
4. 完全不说话
5. 点击停止录音时是否补出尾段

---

## 12. 推荐的 commit 节奏

建议至少按下面节奏形成本地版本：

1. `refactor: scaffold simplified realtime pipeline switch`
2. `refactor: restore faster realtime partial chunking`
3. `refactor: simplify realtime upload gating`
4. `refactor: reduce realtime transcript cleanup complexity`
5. `refactor: verify simplified pipeline rewrite compatibility`

这样后续如果某一步做坏了，可以非常明确地回滚到前一个阶段。

---

## 13. 失败回滚策略

## 13.1 如果 Phase 1 做坏了

回滚到：

- Phase 0 完成后的 commit

## 13.2 如果 Phase 2 做坏了

回滚到：

- Phase 1 完成后的 commit

## 13.3 如果整个简化重构方向不成立

回滚到当前复杂版基线：

- `c8f2722`

---

## 14. 建议的第一轮实际执行顺序

如果现在立刻开始施工，我建议严格按下面顺序：

### 第一步
- 建立“简化版 pipeline 开关”

### 第二步
- 把 `chunk_seconds` 从 `10.0` 改到 `2.5`
- 把 `min_audio_seconds` 从 `1.0` 改到 `0.6`

### 第三步
- 把 retain 使用范围收窄

### 第四步
- 文本层回退到基础版

### 第五步
- 验证 rewrite 与前端替换

这 5 步都完成后，再决定要不要重新加回高级尾巴策略。

---

## 15. 本文档的使用方法

后续正式开工时，建议每一轮都按下面方式使用本文档：

1. 先确定当前处于哪个 Phase
2. 只执行该 Phase 对应的事项
3. 跑该 Phase 指定验证
4. 更新 `CHANGE_JOURNAL.md`
5. 形成一个本地 commit

这样可以避免重新滑回“同一轮里同时改 7 个逻辑点”的失控状态。

---

## 16. 最终结论

当前最稳妥的推进方式不是继续补丁式调参，而是：

> 按本文档，把实时转写拆成阶段化的简化重构任务。

只要坚持：

- 每阶段只解决一个核心问题
- 每阶段都有自动化和手工验证
- 每阶段都有独立本地 commit

那么这条链路就能重新回到可掌控状态。
