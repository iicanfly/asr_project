# ASR Project

## 项目简介

这是一个“语音转文字 + 文档生成”的系统，当前已经具备三类基础能力：

- 实时录音转写
- 上传音频文件转写
- 基于转写结果生成多种文档，并支持后续修改

项目的真实落地环境是**内网**，但功能开发与调试主要先在**外网**完成，因此所有开发任务默认都按**双环境**思路处理。

---

## 当前重点

当前阶段最核心的目标是：**提升实时转写质量与稳定性**。

近期重点包括：

- 静音检测与静音片段抑制
- 弱语音 / 背景语音门控
- 语气词过滤
- 实时转写延迟优化
- 多层级回写与前端替换展示
- 长时间录音稳定性

上传音频转写与文档生成目前可用，但暂时不是近期主优化方向。

---

## v1.0 实时转写稳定里程碑

`v1.0` 是当前一个重要稳定节点，主要完成了以下能力收敛：

- **单段展示**
  - 同一次连续录音默认只显示一个转写段落
  - 只有点击停止录音后再次开始/继续录音，才会新开下一段

- **三级回写**
  - `partial`：约 1.5 秒级实时小步结果
  - `medium rewrite`：约 6 秒级中级回写
  - `high rewrite`：高级回写

- **静音 10 秒自动高级回写**
  - 用户说完后即使不点击停止录音
  - 静音约 10 秒也会自动触发最终高级回写收尾

- **修复前端假分段**
  - 修复同一个 `segment_id` 因前端替换逻辑失配而错误拆成多个 `Speaker_1` 气泡的问题

- **静音检测**
  - 对明显静音、弱背景音、低价值片段进行门控，减少无效上传和误触发转写

- **语气词过滤**
  - 对“嗯、啊、呃”等低信息量输出进行清洗与抑制，提升前端文本可读性

这个版本适合作为后续继续优化实时转写质量的**稳定基线版本**。

---

## 技术结构

- 后端：Python + Flask + Flask-SocketIO
- 前端：`templates/index.html` + `static/js/app.js`
- AI 服务：
  - LLM：内外网均走 OpenAI 兼容接口
  - ASR：
    - 外网：OpenAI 兼容音频接口 / 聊天音频输入链路
    - 内网：HTTP `POST` / `audio/transcriptions` 链路
- 桌面封装：Electron

关键入口：

- 后端入口：`main.py`
- 配置入口：`config.py`
- ASR 服务封装：`services/asr_service.py`
- 前端主逻辑：`static/js/app.js`

---

## 双环境说明

`.env` 中通过以下开关区分内外网：

```env
USE_INTRANET=False
```

约定如下：

- `False`：外网开发模式
- `True`：内网部署模式

当前发布前已确认：

- 内网 `ASR_MODE=transcriptions`
- 内网实时链路默认**不启用**外网那套 simplified realtime pipeline
- 当前实时改动没有改乱内网 ASR 调用分流逻辑

依赖迁移方式：

- 外网调试完成后，通过 `conda pack` 打包环境
- 将环境迁移到内网后解压使用

因此新增依赖与运行方式都需要考虑 `conda pack` 兼容性。

---

## Codex 在这个仓库里的协作方式

本仓库已经建立了项目级协作规则。对协作者来说，可以把 Codex 理解为一个：

> 会改代码、会维护项目文档、默认走本地 Git 版本管理、并且按双环境约束做开发的代理

默认原则：

- 任何有效修改都必须进入**本地 Git 历史**
- 未经用户明确要求，不主动 push 远程
- 涉及项目事实变化时，同步维护 `docs/PM/` 下的项目管理文档
- 所有实现默认同时考虑外网开发与内网部署

---

## 协作者建议先看哪些文档

### 先看协作规则

- [AGENTS.md](./AGENTS.md)：仓库级行为准则，约束 Git、双环境、文档维护、调试方式等默认行为。
- [docs/PM/CODEX_PLAYBOOK.md](./docs/PM/CODEX_PLAYBOOK.md)：Codex 在本项目中的长期协作手册，说明任务理解、插件/技能使用和文档维护总原则。
- [docs/PM/DOC_MAINTENANCE.md](./docs/PM/DOC_MAINTENANCE.md)：项目管理文档的维护规则，说明什么时候必须更新哪些文档。
- [docs/PM/DOC_ROUTING.md](./docs/PM/DOC_ROUTING.md)：文档路由总表，说明“当前是什么任务 -> 下一步该去读哪些专项文档”。

### 再看当前项目状态

- [docs/PM/BACKLOG.md](./docs/PM/BACKLOG.md)：当前待办事项与优先级。
- [docs/PM/ENV_MATRIX.md](./docs/PM/ENV_MATRIX.md)：内网 / 外网差异总表。
- [docs/PM/TEST_MATRIX.md](./docs/PM/TEST_MATRIX.md)：当前必须回归的测试重点。
- [docs/PM/SESSION_SUMMARY.md](./docs/PM/SESSION_SUMMARY.md)：当前阶段结论、临时决策、阻塞项和下一步方向。
- [docs/PM/CHANGE_JOURNAL.md](./docs/PM/CHANGE_JOURNAL.md)：按轮次记录改动、验证结果、用户反馈和后续动作。
- [docs/PM/REALTIME_DEBUG_PLAYBOOK.md](./docs/PM/REALTIME_DEBUG_PLAYBOOK.md)：实时转写专项调试手册，包含调试方法、清单、命令和故障字典。

### 最后看系统与代码结构

- [docs/PM/SYSTEM_OVERVIEW.md](./docs/PM/SYSTEM_OVERVIEW.md)：系统整体结构与主链路说明。
- [docs/PM/MODULE_INDEX.md](./docs/PM/MODULE_INDEX.md)：主要模块 / 文件索引，方便快速定位代码。
- [docs/PM/FUNCTION_CONTRACTS.md](./docs/PM/FUNCTION_CONTRACTS.md)：关键函数的输入、输出、副作用与上下游关系。
- [docs/PM/CONFIG_MAP.md](./docs/PM/CONFIG_MAP.md)：配置项含义、作用范围和代码落点。
- [docs/PM/API_FLOW.md](./docs/PM/API_FLOW.md)：实时转写、上传转写、文档生成等核心数据流。
- [docs/PM/KNOWN_ISSUES.md](./docs/PM/KNOWN_ISSUES.md)：当前已知问题、结构风险与限制。

如果接下来要继续做“实时转写联调 / 口测回归 / 时延排查 / 回写异常排查”，默认还应额外先看：

- [docs/PM/REALTIME_DEBUG_PLAYBOOK.md](./docs/PM/REALTIME_DEBUG_PLAYBOOK.md)

这份手册当前已经包含：

- 调试原则
- 标准调试清单
- 常用命令速查表
- 故障字典（症状 -> 排查路径 -> 命令 -> 常见修法）

---

## 常用 Markdown 文档导航（GitHub 可点击）

下面这部分专门给 GitHub 协作者快速跳转使用。

### 仓库根目录文档

- [README.md](./README.md)：仓库首页说明，介绍项目目标、双环境约束、版本里程碑和文档导航。
- [AGENTS.md](./AGENTS.md)：Codex 在本仓库中的默认行为规则，包括文档保护、版本管理和实时转写调试默认准则。
- [CODING_PROTOCOL.md](./CODING_PROTOCOL.md)：编码与版本管理约定（如果后续继续使用该文件，可作为补充准则）。
- [DEPLOY.md](./DEPLOY.md)：部署说明。
- [DEPLOY_GUIDE.md](./DEPLOY_GUIDE.md)：更完整的部署步骤参考。
- [Setup_Guide.md](./Setup_Guide.md)：环境准备与启动说明。
- [Development_Plan.md](./Development_Plan.md)：早期开发计划文档。
- [Technical_Design.md](./Technical_Design.md)：技术设计说明。
- [Test_Specification.md](./Test_Specification.md)：测试规范或历史测试说明。
- [LLM_Integration_Spec.md](./LLM_Integration_Spec.md)：LLM 接入相关说明。

### `docs/PM/` 项目管理文档

- [docs/PM/CODEX_PLAYBOOK.md](./docs/PM/CODEX_PLAYBOOK.md)：Codex 的长期协作手册。
- [docs/PM/DOC_MAINTENANCE.md](./docs/PM/DOC_MAINTENANCE.md)：项目管理文档维护规则。
- [docs/PM/BACKLOG.md](./docs/PM/BACKLOG.md)：待办清单与优先级。
- [docs/PM/CHANGE_JOURNAL.md](./docs/PM/CHANGE_JOURNAL.md)：按轮记录改动与反馈。
- [docs/PM/ENV_MATRIX.md](./docs/PM/ENV_MATRIX.md)：内外网差异总表。
- [docs/PM/TEST_MATRIX.md](./docs/PM/TEST_MATRIX.md)：测试矩阵与回归重点。
- [docs/PM/SESSION_SUMMARY.md](./docs/PM/SESSION_SUMMARY.md)：当前阶段总结与方向。
- [docs/PM/SYSTEM_OVERVIEW.md](./docs/PM/SYSTEM_OVERVIEW.md)：系统结构总览。
- [docs/PM/MODULE_INDEX.md](./docs/PM/MODULE_INDEX.md)：模块索引。
- [docs/PM/FUNCTION_CONTRACTS.md](./docs/PM/FUNCTION_CONTRACTS.md)：函数契约说明。
- [docs/PM/CONFIG_MAP.md](./docs/PM/CONFIG_MAP.md)：配置项地图。
- [docs/PM/API_FLOW.md](./docs/PM/API_FLOW.md)：核心数据流说明。
- [docs/PM/KNOWN_ISSUES.md](./docs/PM/KNOWN_ISSUES.md)：当前已知问题与风险。
- [docs/PM/REALTIME_DEBUG_PLAYBOOK.md](./docs/PM/REALTIME_DEBUG_PLAYBOOK.md)：实时转写专项调试手册。
- [docs/PM/DOC_ROUTING.md](./docs/PM/DOC_ROUTING.md)：任务类型到文档阅读顺序的总路由表。
- [docs/PM/REALTIME_ASR_CURRENT_IMPLEMENTATION.md](./docs/PM/REALTIME_ASR_CURRENT_IMPLEMENTATION.md)：实时转写当前实现说明。
- [docs/PM/REALTIME_ASR_SIMPLIFIED_REFACTOR_PLAN.md](./docs/PM/REALTIME_ASR_SIMPLIFIED_REFACTOR_PLAN.md)：实时转写简化重构方案。
- [docs/PM/REALTIME_ASR_SIMPLIFIED_REFACTOR_CHECKLIST.md](./docs/PM/REALTIME_ASR_SIMPLIFIED_REFACTOR_CHECKLIST.md)：实时转写简化重构实施清单。
- [docs/PM/REALTIME_AUDIO_SAMPLE_MANIFEST.md](./docs/PM/REALTIME_AUDIO_SAMPLE_MANIFEST.md)：真实音频样本与用途说明。

---

## 推荐提需求方式

为了提高协作效率，建议尽量明确以下四项：

1. 目标
2. 网络范围（外网 / 内网 / 双环境）
3. 验收标准
4. 是否允许远程 push

示例：

- 目标：优化实时转写的静音过滤
- 网络范围：双环境共享
- 验收标准：旁边人小声说话不再频繁触发转写，主说话人正常语音不明显漏识别
- 远程 push：否

---

## Git 与版本管理约定

- 默认每轮有效修改至少形成一次本地 commit
- 远程 push 只在用户明确要求时执行
- 项目管理文档与代码一样，属于正式版本管理内容
- 提交前可先运行 `python tools/codex_guard.py`
- 仓库级 `pre-commit` hook 会运行 `python tools/codex_guard.py --staged`
- 如果实现改动确认不需要更新 Markdown，需显式使用 `CODEX_ALLOW_NO_DOC_UPDATE=1`

---

## 文档保护

为避免中文文档被错误写坏，仓库提供了文档损坏检测脚本：

```bash
python tools/check_doc_corruption.py
```

建议在以下场景执行：

- 批量修改中文 Markdown 后
- 更新 `docs/PM/` 文档后
- 提交文档类修改前

---

## 当前提醒

- 当前仓库同时存在 Web 与 Electron 两套前端入口，修改前端时需要确认影响范围
- 内外网 ASR 调用方式不同，涉及 ASR 链路时必须特别谨慎
- 当前最核心的优化对象仍然是实时转写，不要让次要工作稀释主线
