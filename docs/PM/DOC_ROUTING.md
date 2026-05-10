# DOC_ROUTING

## 目的

- 这份文档是本项目的**文档路由总表**。
- 它不负责记录实现细节，而是负责回答一个更上层的问题：

> 当前属于什么类型的任务？下一步应该先读哪些文档，再继续下钻到哪些专项文档？

- 目标是减少“知道文档很多，但不知道先看哪份、后看哪份”的情况。

---

## 使用原则

- 先用这份文档判断“当前任务属于哪一类”。
- 再按这里给出的顺序去读高层文档与下层专项文档。
- 如果一轮任务结束后新增了未来会反复使用的专项文档，也要考虑把它补进本路由表。

---

## 与其他上层文档的关系

### 1. 仓库级行为规则
- [../../AGENTS.md](../../AGENTS.md)
- 作用：约束 Git、本地提交、双环境、文档维护、调试默认动作。

### 2. Codex 长期协作手册
- [./CODEX_PLAYBOOK.md](./CODEX_PLAYBOOK.md)
- 作用：说明长期工作方式、技能/插件使用原则、项目协作约定。

### 3. 文档维护规则
- [./DOC_MAINTENANCE.md](./DOC_MAINTENANCE.md)
- 作用：说明什么时候必须更新哪些 PM 文档，以及如何避免记忆缺失。

### 4. 当前阶段摘要
- [./SESSION_SUMMARY.md](./SESSION_SUMMARY.md)
- 作用：快速了解当前做到哪里、下一轮默认先看什么、最近重点是什么。

### 5. GitHub 首页导航
- [../../README.md](../../README.md)
- 作用：给人和协作者一个总入口，快速跳转到各类文档。

---

## 高层文档与下层文档的分工

### 高层文档负责
- 当前阶段在做什么
- 当前最重要的问题是什么
- 当前任务应该继续下钻到哪些专项文档

典型高层文档：
- `AGENTS.md`
- `docs/PM/CODEX_PLAYBOOK.md`
- `docs/PM/SESSION_SUMMARY.md`
- `docs/PM/DOC_ROUTING.md`

### 下层文档负责
- 具体实现逻辑
- 具体调试方法
- 具体测试口径
- 具体环境差异
- 具体风险、回滚点与修改记录

典型下层文档：
- `docs/PM/REALTIME_ASR_CURRENT_IMPLEMENTATION.md`
- `docs/PM/REALTIME_DEBUG_PLAYBOOK.md`
- `docs/PM/TEST_MATRIX.md`
- `docs/PM/ENV_MATRIX.md`
- `docs/PM/CONFIG_MAP.md`
- `docs/PM/CHANGE_JOURNAL.md`

---

## 任务类型 -> 默认文档路径

### 1. 继续推进实时转写功能开发

#### 目标
- 继续优化实时转写质量、稳定性、回写效果、静音处理等。

#### 默认阅读顺序
1. [./SESSION_SUMMARY.md](./SESSION_SUMMARY.md)
2. [./BACKLOG.md](./BACKLOG.md)
3. [./REALTIME_ASR_CURRENT_IMPLEMENTATION.md](./REALTIME_ASR_CURRENT_IMPLEMENTATION.md)
4. [./REALTIME_DEBUG_PLAYBOOK.md](./REALTIME_DEBUG_PLAYBOOK.md)
5. [./TEST_MATRIX.md](./TEST_MATRIX.md)

#### 需要重构时继续下钻
- [./REALTIME_ASR_SIMPLIFIED_REFACTOR_PLAN.md](./REALTIME_ASR_SIMPLIFIED_REFACTOR_PLAN.md)
- [./REALTIME_ASR_SIMPLIFIED_REFACTOR_CHECKLIST.md](./REALTIME_ASR_SIMPLIFIED_REFACTOR_CHECKLIST.md)

---

### 2. 排查实时转写 bug / 联调 / 口测异常

#### 目标
- 解决“慢、碎、没回写、假分段、颜色不对、静音不收尾、说话不出字”等实时问题。

#### 默认阅读顺序
1. [./REALTIME_DEBUG_PLAYBOOK.md](./REALTIME_DEBUG_PLAYBOOK.md)
2. [./TEST_MATRIX.md](./TEST_MATRIX.md)
3. [./CHANGE_JOURNAL.md](./CHANGE_JOURNAL.md)
4. [./REALTIME_ASR_CURRENT_IMPLEMENTATION.md](./REALTIME_ASR_CURRENT_IMPLEMENTATION.md)

#### 必要时继续下钻
- 查看 `temp_audio/` 中的真实录音样本
- 查看 [./REALTIME_AUDIO_SAMPLE_MANIFEST.md](./REALTIME_AUDIO_SAMPLE_MANIFEST.md)

---

### 3. 发布前检查 / 内网风险核查 / 双环境确认

#### 目标
- 确认最近改动没有破坏内网逻辑，适合进入远程版本或发布节点。

#### 默认阅读顺序
1. [./SESSION_SUMMARY.md](./SESSION_SUMMARY.md)
2. [./ENV_MATRIX.md](./ENV_MATRIX.md)
3. [./CONFIG_MAP.md](./CONFIG_MAP.md)
4. [./KNOWN_ISSUES.md](./KNOWN_ISSUES.md)
5. [./TEST_MATRIX.md](./TEST_MATRIX.md)

#### 必要时继续下钻
- 查看 `config.py`
- 查看 `services/asr_service.py`
- 查看最近发布相关记录：[./CHANGE_JOURNAL.md](./CHANGE_JOURNAL.md)

---

### 4. 快速理解系统结构 / 定位该改哪个文件

#### 目标
- 搞清当前需求大概应该落在哪个模块、哪条链路、哪些函数。

#### 默认阅读顺序
1. [./SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)
2. [./MODULE_INDEX.md](./MODULE_INDEX.md)
3. [./FUNCTION_CONTRACTS.md](./FUNCTION_CONTRACTS.md)
4. [./API_FLOW.md](./API_FLOW.md)
5. [./CONFIG_MAP.md](./CONFIG_MAP.md)

---

### 5. 维护项目文档 / 沉淀长期记忆

#### 目标
- 把本轮已经形成稳定复用价值的知识沉淀成正式文档，而不是只留在聊天里。

#### 默认阅读顺序
1. [./DOC_MAINTENANCE.md](./DOC_MAINTENANCE.md)
2. [./CHANGE_JOURNAL.md](./CHANGE_JOURNAL.md)
3. [./SESSION_SUMMARY.md](./SESSION_SUMMARY.md)
4. [./BACKLOG.md](./BACKLOG.md)
5. 对应专项文档

#### 必须额外判断
- 这次新增内容是否值得写入：
  - `DOC_ROUTING.md`
  - `REALTIME_DEBUG_PLAYBOOK.md`
  - 其他专项说明 / 方案 / 清单

---

### 6. 回顾某次改动是否有效

#### 目标
- 判断某次修改做过没有、效果如何、用户是否满意、是否还要继续迭代。

#### 默认阅读顺序
1. [./CHANGE_JOURNAL.md](./CHANGE_JOURNAL.md)
2. [./TEST_MATRIX.md](./TEST_MATRIX.md)
3. [./SESSION_SUMMARY.md](./SESSION_SUMMARY.md)
4. 对应专项文档

---

### 7. 新协作者快速上手

#### 目标
- 在最短时间内理解仓库规则、项目状态与当前重点。

#### 默认阅读顺序
1. [../../README.md](../../README.md)
2. [../../AGENTS.md](../../AGENTS.md)
3. [./CODEX_PLAYBOOK.md](./CODEX_PLAYBOOK.md)
4. [./DOC_ROUTING.md](./DOC_ROUTING.md)
5. [./SESSION_SUMMARY.md](./SESSION_SUMMARY.md)
6. [./BACKLOG.md](./BACKLOG.md)

#### 按任务继续下钻
- 如果协作者接下来做实时转写，回到“任务类型 1 或 2”
- 如果协作者接下来做发布，回到“任务类型 3”

---

## 文档路由维护规则

- 如果新增了一份未来会反复使用的专项文档，要判断：
  1. 它服务于哪类任务？
  2. 应该挂到哪个任务类型的默认路径里？
  3. 它属于高层入口，还是下层专项文档？
- 如果某份旧文档已经不再起指导作用，也要考虑从本路由表中降级或移除。

---

## 相关文档

- [../../README.md](../../README.md)：GitHub 首页导航与文档总入口
- [../../AGENTS.md](../../AGENTS.md)：仓库级行为准则
- [./CODEX_PLAYBOOK.md](./CODEX_PLAYBOOK.md)：Codex 长期协作手册
- [./DOC_MAINTENANCE.md](./DOC_MAINTENANCE.md)：项目管理文档维护规则
- [./SESSION_SUMMARY.md](./SESSION_SUMMARY.md)：当前阶段状态总览
- [./REALTIME_DEBUG_PLAYBOOK.md](./REALTIME_DEBUG_PLAYBOOK.md)：实时转写专项调试手册
