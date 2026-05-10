# AGENTS.md

## PowerShell 中文写入保护规则
- 不要通过 `functions.shell_command` 里的 PowerShell heredoc、`echo`、`Set-Content`、`Out-File` 等链路直接写入中文文档内容。
- 原因：这条链路已经在本项目里多次把中文写坏成 `?` 或乱码，属于已验证风险，不得再次使用同类方式试错。
- 只要要修改中文 `.md` / `.txt` / `.json` / 配置说明类文本，默认优先使用：
  - `apply_patch`
  - 或者明确以 UTF-8 安全方式写文件的程序化修改
- 如果只是读取中文文档，也要对终端显示乱码保持警惕：终端输出乱码不等于文件一定损坏，但只要发生过写入，就必须用 `python tools/check_doc_corruption.py` 复检。
- 以后凡是涉及“中文文档新增 / 追加 / 批量改写”，先检查自己是否正走在 PowerShell 中文写入链路上；如果是，立即切换到更安全的写法。

## 文档损坏保护规则
- 只要本轮任务修改了中文文档，默认在提交前运行：
  - `python tools/check_doc_corruption.py`
- 如果脚本报出“异常密集的 ? 问号行”，优先视为文档损坏风险，必须先修复再提交。
- 对文档内容的写入，优先使用不会经过终端编码链路的安全方式，避免再次把中文写坏。

## 版本管理规则（必须遵守）
- 任何项目修改都必须立即纳入 Git 版本管理。
- 只要某一轮对话引入了代码、配置或文档变更，该轮结束前至少要形成一次本地提交。
- 提交信息必须清晰描述本轮变更目的，确保项目在任意时点都可回滚。
- 未经用户在当轮明确要求，不得向远程仓库执行 push。

## 推荐的单轮工作流
1. 完成用户提出的修改。
2. 运行 `git status` 并检查差异。
3. 将本轮应提交的改动做成本地 commit。
4. 只有在用户明确要求远程更新时，才执行 push。

## 工具与技能路由规则
- 当任务涉及打开、测试、点击、输入或检查本地网页（如 `localhost`、`127.0.0.1`、本地前端页面）时，优先使用 `Browser Use` 插件。
- 当任务涉及仓库排查、Pull Request、Issue、代码评审或 CI 诊断时，优先使用 `GitHub` 插件。
- 只要任务场景与已安装技能明显匹配，即使用户没有显式点名，也应自动启用对应技能。
- `openai-docs`：用于查询最新的 OpenAI 产品与 API 官方文档。
- `transcribe`：用于音频或视频转写，尤其是批量转写与说话人分离。
- `speech`：用于文本转语音、配音、语音素材生成。
- `playwright`：用于终端驱动的浏览器自动化与可重复 UI 检查。
- `playwright-interactive`：用于多轮前端调试中的持久化浏览器会话。
- `jupyter-notebook`：用于实验型 Notebook、探索分析与可复现演示。
- `sentry`：用于在已配置 Sentry 时执行只读问题排查。
- `security-best-practices`：仅用于明确的安全编码指导或安全审查请求。
- `security-threat-model`：仅用于明确的威胁建模请求。

## 项目专属协作规范
- 本仓库同时支持外网和内网两种运行模式，未经明确批准，不得擅自合并或抹平环境差异。
- 涉及运行行为的改动，必须先判断影响范围属于 `外网专属`、`内网专属` 还是 `双环境共享`。
- 长期协作上下文应沉淀到 `docs/PM/` 目录下的项目管理文件中，避免后续会话因上下文过长而失效。
- 默认把 `docs/PM/CODEX_PLAYBOOK.md` 视为本仓库的协作说明主文件。

## 文档维护默认规则
- 这是一条非常重要的长期准则：**每次修改，不管改动大还是小，只要准备纳入版本管理，都必须顺手检查两件事：**
  1. 哪些 `.md` 文档内容已经因为本轮改动而过期
  2. 哪些 `.md` 文档之间的路由、入口、下钻关系需要同步调整
- 不允许因为“只是小改动”就跳过文档内容维护或文档路由维护。
- 只要某一轮工作改变了项目认知、任务优先级、环境差异、测试重点、已知问题或关键链路，就应同步更新 `docs/PM/` 下对应文档，而不是只修改代码。
- 默认优先维护以下文件：
  - `BACKLOG.md`
  - `CHANGE_JOURNAL.md`
  - `ENV_MATRIX.md`
  - `TEST_MATRIX.md`
  - `SESSION_SUMMARY.md`
  - `SYSTEM_OVERVIEW.md`
  - `MODULE_INDEX.md`
  - `FUNCTION_CONTRACTS.md`
  - `CONFIG_MAP.md`
  - `API_FLOW.md`
  - `KNOWN_ISSUES.md`
- 除了维护现有文档，还应主动判断：本轮新增的结论、流程、阈值、实施方案、回滚点、测试方法，是否已经值得沉淀为新的长期指导文件或补充到现有“记忆文件”中。
- 一旦判断“未来复用价值高、下轮会继续依赖、如果不记下来容易再次失控或重复扫描代码”，就默认应把它写入长期文件，而不是只留在对话输出里。
- 只要本轮新增、删除、重命名、降级或提升了某份文档的作用，就必须同步检查：
  - `docs/PM/DOC_ROUTING.md`
  - `AGENTS.md`
  - `docs/PM/CODEX_PLAYBOOK.md`
  - 必要时 `docs/PM/SESSION_SUMMARY.md`
  确保“上层入口 -> 下层专项文档”的指向仍然准确。
- 默认把以下文件视为需要经常回看的长期指导文件：
  - `AGENTS.md`
  - `docs/PM/CODEX_PLAYBOOK.md`
  - `docs/PM/DOC_ROUTING.md`（用于先判断“当前任务类型 -> 下一步该去读哪些下层文档”）
  - `docs/PM/SESSION_SUMMARY.md`
  - `docs/PM/REALTIME_DEBUG_PLAYBOOK.md`（只要任务涉及实时转写调试、联调、trace 排查、前后端时延分析，就默认优先回看）
  - 与当前主任务直接相关的专项说明 / 方案 / 实施清单文档
- 在进入连续多轮开发前，应先快速回看上述长期指导文件，再继续当前最高优先级任务。
- 如果某一轮改动不影响这些文档，可以不更新；但如果影响到了项目真实状态，必须把文档更新纳入同一轮本地提交。
- 默认把 `docs/PM/DOC_MAINTENANCE.md` 视为项目管理文档的维护准则。

## 实时转写调试默认规则
- 只要任务属于“实时转写质量问题 / 回写异常 / 假分段 / 颜色状态错误 / 静音不收尾 / 体感延迟过大”，默认不要先猜。
- 默认先执行：
  1. 看 `/api/v1/debug/status`
  2. 看 `/api/v1/debug/realtime_trace`
  3. 区分前端问题、后端状态机问题、门控问题、ASR API 耗时问题
- 默认优先使用真实 `temp_audio/` 录音样本做回放和对照，不只靠口述反馈。
- 如果前端看起来像“分段了”，先查 trace 里的 `segment_id`，先区分是后端真分段还是前端假分段。
- 如果用户反馈“很慢”，默认先拆解：
  - 前端送包
  - 后端缓冲与门控
  - ASR API
  - 回写触发
  - 前端渲染
  不要把所有慢都归因到 API。

## 文档路由规则（上层记忆 -> 下层文档）
- 以后进入仓库后，不只要“回看上层记忆文档”，还要根据任务类型，**继续下钻到对应的专项文档**，不能停在高层概述。
- 默认如果对“当前任务该往哪份专项文档下钻”还有疑问，先看：
  - `docs/PM/DOC_ROUTING.md`
- 默认按下面这张路由表执行：

### 1. 如果任务是“继续推进实时转写开发”
- 先看：
  - `docs/PM/SESSION_SUMMARY.md`
  - `docs/PM/BACKLOG.md`
- 再看：
  - `docs/PM/REALTIME_ASR_CURRENT_IMPLEMENTATION.md`
  - `docs/PM/REALTIME_DEBUG_PLAYBOOK.md`
  - `docs/PM/TEST_MATRIX.md`
- 如果涉及重构或结构调整，再看：
  - `docs/PM/REALTIME_ASR_SIMPLIFIED_REFACTOR_PLAN.md`
  - `docs/PM/REALTIME_ASR_SIMPLIFIED_REFACTOR_CHECKLIST.md`

### 2. 如果任务是“排查实时转写 bug / 联调 / 口测异常”
- 先看：
  - `docs/PM/REALTIME_DEBUG_PLAYBOOK.md`
- 再看：
  - `docs/PM/TEST_MATRIX.md`
  - `docs/PM/CHANGE_JOURNAL.md`
  - `docs/PM/REALTIME_ASR_CURRENT_IMPLEMENTATION.md`

### 3. 如果任务是“发布前检查 / 双环境确认 / 内网风险核查”
- 先看：
  - `docs/PM/ENV_MATRIX.md`
  - `docs/PM/SESSION_SUMMARY.md`
- 再看：
  - `docs/PM/CONFIG_MAP.md`
  - `docs/PM/KNOWN_ISSUES.md`
  - `docs/PM/TEST_MATRIX.md`

### 4. 如果任务是“理解代码结构 / 快速定位改哪个文件”
- 先看：
  - `docs/PM/SYSTEM_OVERVIEW.md`
  - `docs/PM/MODULE_INDEX.md`
- 再看：
  - `docs/PM/FUNCTION_CONTRACTS.md`
  - `docs/PM/API_FLOW.md`
  - `docs/PM/CONFIG_MAP.md`

### 5. 如果任务是“维护项目文档 / 更新长期记忆”
- 先看：
  - `docs/PM/DOC_MAINTENANCE.md`
  - `docs/PM/CHANGE_JOURNAL.md`
- 再判断是否要更新：
  - `docs/PM/BACKLOG.md`
  - `docs/PM/SESSION_SUMMARY.md`
  - `docs/PM/KNOWN_ISSUES.md`
  - 以及对应专项文档

### 6. 如果任务是“回顾某次修改有没有效果”
- 先看：
  - `docs/PM/CHANGE_JOURNAL.md`
- 再看：
  - `docs/PM/TEST_MATRIX.md`
  - `docs/PM/SESSION_SUMMARY.md`
  - 相关专项文档

- 默认原则：
  - 上层记忆文档负责“告诉自己现在该去读哪份下层文档”
  - 下层专项文档负责“给出具体实现、调试、测试或发布细节”
