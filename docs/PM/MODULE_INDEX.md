# MODULE_INDEX

## 说明
本文件记录当前项目中主要模块 / 文件的职责，帮助后续会话快速定位“改哪里”。

## Python 后端

### `main.py`
- 角色：后端总入口。
- 主要职责：
  - 初始化 Flask 与 Socket.IO。
  - 初始化 LLM / ASR 客户端。
  - 处理实时音频流。
  - 处理上传音频转写。
  - 处理文档生成、重生成、导出。
- 关键区域：
  - 工具函数：WAV 封装、Markdown 清洗、转写文本拼接、结果过滤。
  - 实时转写：`detect_silence`、`SessionManager`、`on_audio_stream`
  - 文档接口：`summarize_meeting`、`regenerate_document`
  - 导出接口：`export_word`、`download_file`
  - 文件转写接口：`upload_audio`

### `config.py`
- 角色：配置解析层。
- 主要职责：
  - 从 `.env` 读取环境变量。
  - 根据 `USE_INTRANET` 决定使用哪套 AI 服务配置。
  - 向其他模块暴露统一的配置常量。

### `generate_cert.py`
- 角色：开发 / 部署辅助工具。
- 主要职责：
  - 生成 HTTPS 本地证书。
- 使用场景：
  - 浏览器在非 `localhost` 环境下使用麦克风时，需要 HTTPS 支持。

## Web 前端

### `templates/index.html`
- 角色：Flask Web 入口页面。
- 主要职责：
  - 组织主界面结构。
  - 引入静态资源：
    - `/static/css/style.css`
    - `/static/js/socket.io.min.js`
    - `/static/js/app.js`

### `static/js/app.js`
- 角色：Web 前端主逻辑文件。
- 主要职责：
  - 建立 Socket.IO 连接。
  - 录音开始 / 停止控制。
  - 音频采集、PCM 转换、实时发送。
  - 展示转写结果。
  - 管理本地缓存与补偿上传。
  - 文档生成、历史记录、预览、导出、手动编辑。
- 当前与实时转写质量最相关的区域：
  - `startRecording`
  - `setupAudioProcessing`
  - `handleASRResult`
  - `addMessageUI`

### `static/js/audio-processor.js`
- 角色：音频工作线程处理器。
- 主要职责：
  - 从 `AudioWorkletProcessor` 中提取单声道浮点音频数据。
  - 将数据传回主线程。

### `static/css/style.css`
- 角色：Web 页面样式层。
- 主要职责：
  - 定义页面布局、状态标签、消息区、文档区、弹窗等样式。

## Electron 桌面封装

### `src/main/main.js`
- 角色：Electron 主进程入口。
- 主要职责：
  - 检查后端端口是否可用。
  - 按需启动 Python 后端。
  - 创建桌面窗口。
  - 在应用退出时清理后端进程。
- 当前关注点：
  - 后端等待端口与 Flask 实际端口可能不一致。
  - 桌面端加载的是根目录 `index.html`，不是 Flask 模板页面。

### `src/preload/preload.js`
- 角色：Electron 预加载桥接层。
- 主要职责：
  - 向渲染进程暴露安全的 IPC 通信接口。

### 根目录 `index.html`
- 角色：Electron 桌面端前端入口。
- 主要职责：
  - 为桌面端提供页面、样式与脚本。
- 风险说明：
  - 这套入口与 `templates/index.html + static/*` 并不是完全同一实现。
  - 修改前端时必须确认本次改动是否也需要同步到 Electron 入口。

## 项目文档与运行辅助

### `.env`
- 角色：运行配置源。
- 主要职责：
  - 存储环境切换开关、AI 服务地址、模型、HTTPS 证书路径、导出目录等。

### `requirements.txt`
- 角色：Python 依赖列表。
- 主要职责：
  - 记录后端运行依赖。

### `package.json`
- 角色：Node / Electron 依赖与打包脚本入口。
- 主要职责：
  - 定义 Electron 启动和打包命令。
  - 管理 Electron 相关依赖。

## 当前最值得优先阅读的文件
如果后续任务仍然聚焦“实时转写质量”，优先阅读顺序建议如下：
1. `main.py`
2. `static/js/app.js`
3. `config.py`
4. `templates/index.html`
5. `static/js/audio-processor.js`

如果任务聚焦“桌面端部署 / 打包”，优先阅读顺序建议如下：
1. `src/main/main.js`
2. 根目录 `index.html`
3. `package.json`
4. `config.py`
5. `main.py`

## 2026-05-10 ??????

### `services/asr_service.py`
- ??????????????? ASR ????
- ?????
  - ?????? / ?? ASR ?????
  - ?? `RealtimeChunkPolicy` ? `decide_chunk_processing()`??????????????
  - ?? `detect_silence()`?`add_wav_header()`?`should_filter_asr_result()` ?????????
  - ?????????????????????????????

### `tests/test_asr_service.py`
- ???Sprint 0 ?????????????
- ?????
  - ?????????
  - ???????????
  - ??????????
- ???
  - ???? `unittest`??????????????????????
