# ASR Project

## 项目简介
这是一个语音转文字与文档生成系统，当前已经具备三类基础能力：

- 实时录音转写
- 上传音频文件转写
- 基于转写结果生成多种文档，并支持进一步修改

项目的真实落地环境是`内网`，但功能开发和调试主要先在`外网`完成，因此所有开发任务都必须按`双环境`思路处理。

## 当前开发重点
当前阶段的核心目标是大幅提升`实时转写质量`，重点包括：

- 静音音频过滤
- 弱语音与背景语音处理
- 语气词过滤
- 更合理的分段策略
- 小段结果到大段结果的替换回写

上传音频转写和文档生成目前可用，但暂时不是近期主优化方向。

## 技术结构
- Python 后端：Flask + Flask-SocketIO
- AI 调用：
  - LLM：内外网均为 OpenAI 兼容接口
  - ASR：外网走 OpenAI 兼容格式，内网走 HTTP `POST`
- Web 前端：`templates/index.html` + `static/js/*`
- 桌面封装：Electron

关键文件入口：
- 后端入口：[main.py](main.py)
- 配置入口：[config.py](config.py)
- Web 前端入口：[templates/index.html](templates/index.html)
- 前端主逻辑：[static/js/app.js](static/js/app.js)
- Electron 主进程：[src/main/main.js](src/main/main.js)

## 环境说明
- `.env` 里的 `USE_INTRANET=False/True` 用于切换外网 / 内网模式
- 当前约定：
  - 外网：先完成开发和调试
  - 内网：最终部署与使用环境
- 任何改动都不能只考虑外网，必须同时确认不会破坏内网路径

依赖迁移方式：
- 外网调通后，通过 `conda pack` 打包虚拟环境
- 内网通过解压该环境直接使用

## Codex 是如何在这个仓库里工作的
本仓库已经为 Codex 建立了项目级协作规则。对协作者来说，可以把 Codex 理解为一个“会写代码、会维护项目文档、并且默认走 Git 版本管理”的开发代理。

默认工作原则：
- 任何代码、配置、文档修改都应进入本地 Git 历史
- 没有明确要求时，只做本地 commit，不主动 push 远程
- 进入仓库后会优先读取项目协作文档，而不是只依赖聊天上下文
- 如果某一轮工作改变了项目事实，会同步更新 `docs/PM/` 下的项目管理文档
- 所有与功能相关的实现，默认都按双环境任务处理

这意味着：
- Codex 不只是改代码，也会维护项目认知和协作文档
- 后续新会话即使上下文较短，也可以快速通过仓库文档恢复状态

## 协作者需要先看哪些文档
如果你是项目协作者，建议先看这些文件：

- [AGENTS.md](AGENTS.md)
- [docs/PM/CODEX_PLAYBOOK.md](docs/PM/CODEX_PLAYBOOK.md)
- [docs/PM/DOC_MAINTENANCE.md](docs/PM/DOC_MAINTENANCE.md)

如果你要快速理解项目状态，再看：

- [docs/PM/BACKLOG.md](docs/PM/BACKLOG.md)
- [docs/PM/ENV_MATRIX.md](docs/PM/ENV_MATRIX.md)
- [docs/PM/TEST_MATRIX.md](docs/PM/TEST_MATRIX.md)
- [docs/PM/SESSION_SUMMARY.md](docs/PM/SESSION_SUMMARY.md)

如果你要快速理解代码结构，再看：

- [docs/PM/SYSTEM_OVERVIEW.md](docs/PM/SYSTEM_OVERVIEW.md)
- [docs/PM/MODULE_INDEX.md](docs/PM/MODULE_INDEX.md)
- [docs/PM/FUNCTION_CONTRACTS.md](docs/PM/FUNCTION_CONTRACTS.md)
- [docs/PM/CONFIG_MAP.md](docs/PM/CONFIG_MAP.md)
- [docs/PM/API_FLOW.md](docs/PM/API_FLOW.md)
- [docs/PM/KNOWN_ISSUES.md](docs/PM/KNOWN_ISSUES.md)

## 推荐协作方式
给 Codex 提任务时，推荐尽量说明：

1. 目标
2. 网络范围
3. 验收标准
4. 是否允许远程 push

示例：
- 目标：优化实时转写的静音过滤
- 网络范围：双环境共享
- 验收标准：旁边人的小声说话不再频繁触发转写，正常语音不明显漏识别
- 远程 push：否

## Git 与版本管理约定
- 默认每轮有效改动至少形成一次本地 commit
- 需要推送远程时，由用户明确指令触发
- 项目管理文档与代码一样，属于需要被版本管理的正式资产

## 当前提醒
- 当前仓库同时存在 Web 与 Electron 两套前端入口，修改前端时要确认影响范围
- 内外网 ASR 调用方式不同，涉及实时转写链路时必须特别谨慎
- 当前最核心的优化对象是实时转写，不要轻易让次要工作稀释主线
