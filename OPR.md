# 业务需求文档 (OPR - Operational Requirements Document)

## 1. 项目概览
**项目名称**：内网离线语音识别及会议纪要系统
**项目目标**：在完全断网的内网环境下，为 Win7 客户端提供高效、稳定的实时语音转写及会议纪要生成服务。

## 2. 目标运行环境 (Target Environment)
*   **操作系统**：Windows 7 (及以上)
*   **前端浏览器内核**：Chromium 86+ (建议使用 Electron 22 封装，内置 Chromium 108)
*   **网络环境**：完全断网 (Intranet Only)，所有依赖需离线打包。
*   **硬件支持**：服务器端具备 NVIDIA GPU 用于 ASR 及 LLM 推理。

## 3. 核心功能需求 (Functional Requirements)

### 3.1 音频采集模块
*   支持通过耳机/麦克风进行实时音频流采集。
*   采样率要求：16000Hz, 16bit, 单声道 (Mono)。
*   可视化反馈：界面需提供音量波动条。

### 3.2 语音转写模块 (ASR)
*   **实时转写**：支持流式音频传输，实时返回转写文本。
*   **说话人识别 (Diarization)**：必须能够区分不同的说话人（如：说话人1、说话人2）。
*   **交互方式**：WebSocket (用于实时流) 或 HTTP POST (用于文件转写)。

### 3.3 会议纪要生成模块 (LLM)
*   **模板提炼**：根据转写后的全量文本，调用大模型生成摘要、核心决议和待办事项。
*   **交互方式**：HTTP RESTful API。

### 3.4 预览与导出
*   **实时展示**：对话式展示转写内容，自动滚动。
*   **纪要预览**：支持富文本或 Markdown 预览。
*   **离线下载**：支持将生成的纪要导出为 Word (.docx) 或 PDF 格式。

### 3.5 音频上传调试模块 (Debug & Batch)
*   **文件支持**：支持上传已有的音频文件（WAV, MP3, M4A 等）。
*   **处理模式**：
    *   调试模式：模拟实时流输出，附带详细的时间戳和日志，便于排查 ASR 准确度。
    *   快速模式：全量异步处理，完成后直接展示结果。
*   **进度反馈**：大文件上传需提供进度条及预计剩余时间。

### 3.6 语音暂存与容灾机制
*   **本地暂存**：若实时转写过程中网络波动或服务中断，系统需自动将采集到的原始语音暂存在本地磁盘。
*   **事后补发**：用户可在网络恢复或服务正常后，从“暂存记录”中选择文件重新发起转写及纪要生成任务。

## 4. 技术规范与接口设计 (Technical Specifications)

### 4.1 接口 A：实时 ASR (WebSocket)
*   **Endpoint**: `ws://[server-ip]:[port]/api/v1/asr/stream`
*   **Payload**: 二进制 PCM 数据流。
*   **Response**: 
    ```json
    {
      "speaker_id": "string",
      "text": "string",
      "is_final": boolean
    }
    ```

### 4.2 接口 B：纪要生成 (HTTP POST)
*   **Endpoint**: `http://[server-ip]:[port]/api/v1/llm/summarize`
*   **Request**: 
    ```json
    {
      "transcript": [{"speaker": "id", "content": "text"}],
      "template": "default"
    }
    ```

## 5. 非功能性需求 (Non-functional Requirements)
*   **兼容性**：前端必须在 Win7 系统下的 Chrome 86+ 内核中无错运行。
*   **稳定性**：支持至少 2 小时的连续会议录制而不崩溃。
*   **安全性**：所有数据均在内网流转，严禁外传。
*   **部署性**：支持一键离线部署（前端 exe，后端基于 Conda/Miniconda 环境的离线包或全自动化安装脚本）。

## 6. 环境运维需求 (Maintenance Requirements)
*   **Conda 环境管理**：
    *   需提供离线版 Miniconda 安装包及自动安装脚本。
    *   需提供环境迁移方案（如 `conda-pack`），确保服务器端在无网情况下能快速复现 Python 开发环境。
*   **文档支持**：
    *   需提供《离线服务器 Conda 环境安装指南》。
    *   需提供《后端服务日常维护与日志查看手册》。

## 7. 开发计划阶段 (Roadmap)
1.  **Phase 1**: 环境搭建与 Electron 22 (Win7) 基础框架开发。
2.  **Phase 2**: 音频采集与 WebSocket 实时流对接。
3.  **Phase 3**: 说话人识别展示逻辑与 UI 优化。
4.  **Phase 4**: LLM 纪要生成接口集成与离线导出功能。
5.  **Phase 5**: 内网压力测试与离线打包交付。
