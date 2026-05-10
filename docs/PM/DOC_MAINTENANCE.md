# DOC_MAINTENANCE

## 文档损坏保护补充
- 只要本轮修改涉及中文 Markdown 文档，提交前默认补一轮：
  - `python tools/check_doc_corruption.py`
- 如果检查脚本报出疑似损坏，先修复文档内容，再进入本地 Git 提交。

## 目的
- 本文件用于约束 `docs/PM/` 下项目管理文档的维护方式。
- 目标是让未来每一轮 Codex 会话都能默认维护这些文档，而不是只在需要时临时补写。

## 默认原则
- 项目管理文档是项目状态的一部分，不是可有可无的附属品。
- 只要代码、配置、架构理解、风险判断或任务优先级发生变化，就应考虑同步更新文档。
- 文档更新默认和对应代码改动一起提交到本地 Git 历史中。
- 不管改动大小，只要本轮变更准备提交，都必须检查两件事：
  1. 哪些 Markdown 内容需要同步更新
  2. 哪些 Markdown 之间的路由关系需要同步更新

## 什么时候必须更新文档
- 新增、删除或重排了任务优先级：
  - 更新 `BACKLOG.md`
- 本轮完成了有效修改，且需要保留“改了什么、反馈如何、效果如何”的演进记录：
  - 更新 `CHANGE_JOURNAL.md`
- 新增了内网 / 外网差异，或修正了原有差异判断：
  - 更新 `ENV_MATRIX.md`
- 新增了必须回归的测试项，或改变了测试重点：
  - 更新 `TEST_MATRIX.md`
- 本轮完成了一项阶段性工作、发现了新阻塞、形成了新决策：
  - 更新 `SESSION_SUMMARY.md`
- 对系统结构、模块职责、关键函数、配置含义、数据流理解发生了变化：
  - 更新 `SYSTEM_OVERVIEW.md`
  - `MODULE_INDEX.md`
  - `FUNCTION_CONTRACTS.md`
  - `CONFIG_MAP.md`
  - `API_FLOW.md`
- 发现了新的已知问题、结构风险、兼容性问题：
  - 更新 `KNOWN_ISSUES.md`

## 什么时候可以不更新文档
- 只修改了实现细节，但没有改变项目事实。
- 只做了格式化、注释、重命名等，不影响功能理解。
- 本轮只是短暂实验，且最终没有合入任何有效变更。

## 文档内容应该怎么写
- 优先写稳定事实，不写临时情绪化判断。
- 优先写“之后还能指导开发”的内容，不写一次性噪声信息。
- 结论必须尽量能从代码、配置或用户确认的信息中得到支撑。
- 未确认的信息要明确标记为“待确认”或“风险点”，不要伪装成事实。

## 默认维护顺序
每次任务结束后，按以下顺序检查是否要更新：
1. `SESSION_SUMMARY.md`
2. `CHANGE_JOURNAL.md`
3. `KNOWN_ISSUES.md`
4. `BACKLOG.md`
5. `TEST_MATRIX.md`
6. `ENV_MATRIX.md`
7. 认知文档：
   - `SYSTEM_OVERVIEW.md`
   - `MODULE_INDEX.md`
   - `FUNCTION_CONTRACTS.md`
   - `CONFIG_MAP.md`
   - `API_FLOW.md`
8. 文档路由与入口：
   - `DOC_ROUTING.md`
   - `AGENTS.md`
   - `CODEX_PLAYBOOK.md`
   - 必要时 `SESSION_SUMMARY.md`

## 与 Git 的关系
- 文档更新应与本轮代码改动一起进入同一轮本地 commit，除非文档整理本身就是独立任务。
- 如果只更新文档，也必须独立 commit，确保文档演进同样可回滚。
- 未经用户明确要求，不因文档更新而单独 push 远程。

## 对 Codex 的默认要求
- 未来进入本仓库后，默认先读取：
  - `AGENTS.md`
  - `docs/PM/CODEX_PLAYBOOK.md`
  - `docs/PM/DOC_MAINTENANCE.md`
- 如果需要先判断“当前任务接下来该去读哪份专项文档”，默认再读取：
  - `docs/PM/DOC_ROUTING.md`
- 如果当前任务属于“实时转写调试 / 联调 / 口测回归 / 回写异常 / 前后端时延排查”，还应默认先读取：
  - `docs/PM/REALTIME_DEBUG_PLAYBOOK.md`
- 完成任务前，默认做一次“文档是否需要同步更新”的检查。
- 如果需要更新文档，应把这件事视为任务的一部分，而不是额外可选步骤。

## 路由文档的维护要求
- 以后默认把“维护文档路由”视为和“维护文档内容”同等级的重要动作，不能因为本轮改动小就省略。
- 如果新增了一个未来会反复使用的专项文档，除了更新对应内容文档外，还应判断是否需要同步更新：
  - `docs/PM/DOC_ROUTING.md`
- 如果某份专项文档已经成为某类任务的默认下钻入口，也应把它挂到：
  - `AGENTS.md`
  - `docs/PM/CODEX_PLAYBOOK.md`
  - 必要时挂到 `docs/PM/SESSION_SUMMARY.md`
- 如果本轮只是小改动，但已经改变了某份文档“该由谁来读、什么时候读、从哪里跳过去读”，也必须在同一轮提交里把这些入口修正掉。
