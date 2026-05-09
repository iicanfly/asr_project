(base) PS E:\Trae_Learning\03_Project_video> npm install
npm warn deprecated inflight@1.0.6: This module is not supported, and leaks memory. Do not use it. Check out lru-cache if you want a good and tested way to coalesce async requests by a key value, which is much more comprehensive and powerful.
npm warn deprecated glob@7.2.3: Glob versions prior to v9 are no longer supported
npm warn deprecated boolean@3.2.0: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.# 技术方案设计文档 (Technical Design Document)

## 1. 总体架构设计
系统采用前后端分离的架构，专门针对内网无网环境及 Windows 7 兼容性进行优化。

*   **前端客户端 (Win7 Client)**：基于 **Electron 22.x**。
    *   **Chromium 108 内核**：确保现代 Web API 支持及 Win7 兼容性。确保86以上谷歌浏览器内核可以使用
    *   **功能**：音频采集、实时 WebSocket 展示、文件上传、本地暂存、纪要预览及导出。
*   **后端服务层 (Server)**：基于 **Python 3.9+ (FastAPI)**。
    *   **部署环境**：Conda 虚拟环境。
    *   **功能**：业务逻辑处理、音频流转发、大模型接口对接、文件暂存管理。
*   **AI 服务层 (GPU Server)**：
    *   **ASR 服务**：Whisper (或内网自研 ASR)，负责语音转文字及说话人识别。
    *   **LLM 服务**：Qwen/Llama (或内网自研 LLM)，负责纪要提炼。

## 2. 前端技术方案 (Electron/Web)

### 2.1 音频采集与处理
*   **API**：`navigator.mediaDevices.getUserMedia` + `AudioContext`。
*   **采样**：通过 `ScriptProcessorNode` 或 `AudioWorklet` 获取原始 PCM 数据。
*   **转换**：在前端将 Float32 转换为 Int16 格式，采样率锁定 16000Hz 单声道。
*   **传输**：通过 WebSocket 将二进制数据流发送至后端。

### 2.2 本地暂存机制 (Resilience)
*   **存储**：使用 Electron 的 `app.getPath('userData')` 获取应用数据目录。
*   **实现**：实时采集时，同时将音频切片写入本地 `.tmp` 文件。
*   **管理**：维护一个简单的 SQLite 或 JSON 数据库，记录暂存文件的 ID、时间、转写状态。

### 2.3 兼容性处理
*   **浏览器内核适配**：
    *   **核心目标**：确保在内网主流的 **Chrome 86+** 内核中完美运行。
    *   **技术选型**：使用 **Electron 22.3.27** (内置 Chromium 108)，其内核特性向下兼容 Chrome 86。
    *   **API 降级策略**：在前端代码中避免使用只有 Chrome 90+ 才支持的极新特性（如某些新的 CSS 逻辑属性），确保 86 内核的渲染一致性。

## 3. 后端技术方案 (Python/FastAPI)

### 3.1 核心模块
*   **StreamHandler**：管理 WebSocket 连接，负责音频流的缓存与转发。
*   **AudioProcessor**：处理上传的 MP3/M4A 文件，使用 `pydub` 或 `ffmpeg` 进行转码。
*   **AIServiceClient**：封装对 ASR 和 LLM 服务的 HTTP/gRPC 调用。
*   **DocumentGenerator**：使用 `python-docx` 库根据 Markdown/文本生成 Word 文档。

### 3.2 并发模型
*   使用 `asyncio` 处理非阻塞 I/O，确保在高并发请求下保持响应。

## 4. 关键数据流设计

### 4.1 实时转写流 (Real-time Flow)
1. 前端采集 PCM 流 -> WebSocket -> 后端。
2. 后端 -> WebSocket -> 内网 ASR 服务。
3. ASR 服务返回 `speaker_id` + `text` -> 后端。
4. 后端 -> WebSocket -> 前端展示。

### 4.2 离线调试/文件转写流 (Batch Flow)
1. 前端上传文件 -> HTTP POST -> 后端。
2. 后端保存文件 -> 调用 ASR 异步接口。
3. 后端轮询/接收 ASR 回调 -> 获取全量文本。
4. 后端调用 LLM 接口 -> 生成纪要 -> 返回前端。

## 5. 部署与运维方案 (Conda-based)

### 5.1 后端部署
*   **环境迁移**：使用 `conda-pack` 将开发环境打包成 `env.tar.gz`。
*   **一键安装**：编写 `install.sh` / `install.bat`，逻辑如下：
    1. 解压 Miniconda 离线包。
    2. 解压 `env.tar.gz`。
    3. 注册系统服务或编写启动脚本。
*   **离线依赖**：所有 Python 包通过 `pip download` 预先下载并打包。

### 5.2 前端部署
*   **打包工具**：`electron-builder`。
*   **格式**：NSIS (.exe) 安装程序，包含所有依赖。

## 6. 开发环境部署教程 (Win11)

### 6.1 前端环境 (Node.js)
1.  **安装 Node.js**：建议安装 v16.x 或 v18.x (LTS 版本)。
2.  **初始化项目**：
    ```bash
    npm install electron@22.3.27 --save-dev
    npm install electron-builder --save-dev
    ```
3.  **启动开发模式**：`npm start`

### 6.2 后端环境 (Conda)
1.  **安装 Miniconda**：从官网下载并安装 Windows 版。
2.  **创建虚拟环境**：
    ```powershell
    # 创建环境
    conda create -n voice-system python=3.9
    # 激活环境
    conda activate voice-system
    ```
3.  **安装核心依赖**：
    ```bash
    pip install fastapi uvicorn pydub python-docx loguru
    ```
4.  **启动后端服务**：
    ```bash
    uvicorn main:app --reload --port 8000
    ```

### 6.3 联调准备
*   确保本机 Win11 的 8000 端口未被占用。
*   在前端代码中，将 API 基础路径配置为 `http://127.0.0.1:8000`。

## 7. 运维与监控
*   **日志管理**：使用 `loguru` 输出结构化日志，记录在 `logs/` 目录。
*   **进程守护**：考虑到内网服务器环境，**优先使用简单的 Python 监控脚本或 Windows 任务计划程序**，避免在服务器上额外安装 Node.js。若有 Node.js，亦可使用 PM2。
*   **调试支持**：后端保留 `/api/v1/debug/status` 接口，用于查看 ASR/LLM 服务连接状态。
