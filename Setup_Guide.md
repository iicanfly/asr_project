# 开发者安装与环境配置手册 (Setup Guide - E 盘定制版)

本手册旨在指导人类开发者 (你) 在本机 Win11 环境下，将所有开发环境及安装包统一配置在 **E 盘**，以方便后续迁移和管理。

---

## 0. 准备工作
请在 E 盘创建以下目录结构，用于存放安装包及安装程序：
*   `E:\Dev_Tools\Downloads` (存放所有下载的安装包)
*   `E:\Dev_Tools\Nodejs` (Node.js 安装目录)
*   `E:\Dev_Tools\Miniconda` (Miniconda 安装目录)
*   `E:\Dev_Tools\FFmpeg` (FFmpeg 解压目录)

---

## 1. 前端开发环境 (Node.js)

### 1.1 安装 Node.js
1.  **下载**：下载 **v18.x (LTS)** 版本的 Windows Installer (.msi)。
2.  **安装**：运行安装程序，在选择安装路径 (Destination Folder) 时，修改为：
    `E:\Dev_Tools\Nodejs\`
3.  **验证**：打开终端，输入 `node -v`。

### 1.2 配置全局模块路径 (防止占用 C 盘)
为了确保 npm 下载的全局包也存储在 E 盘，请执行：
```powershell
npm config set prefix "E:\Dev_Tools\Nodejs\node_global"
npm config set cache "E:\Dev_Tools\Nodejs\node_cache"
npm config set registry https://registry.npmmirror.com
```

---

## 2. 后端开发环境 (Miniconda)

### 2.1 安装 Miniconda
1.  **下载**：下载 Miniconda Windows 64-bit 安装包。
2.  **安装**：
    - 在 **"Installation Path"** 步骤，修改为：`E:\Dev_Tools\Miniconda\`。
    - 在 **"Advanced Options"** 步骤，建议勾选 "Add Miniconda3 to my PATH"。
3.  **配置环境存储路径 (关键)**：
    为了确保后续创建的虚拟环境都在 E 盘，请在终端执行：
    ```powershell
    conda config --add envs_dirs E:\Dev_Tools\Miniconda\envs
    conda config --add pkgs_dirs E:\Dev_Tools\Miniconda\pkgs
    ```

### 2.2 创建虚拟环境
```powershell
# 1. 创建环境 (路径将自动指向 E:\Dev_Tools\Miniconda\envs)
conda create -n voice-system python=3.9 -y

# 2. 激活环境
conda activate voice-system

# 3. 配置 pip 缓存路径
pip config set global.cache-dir "E:\Dev_Tools\Downloads\pip_cache"
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2.3 后端环境配置 (Python 3.9)
```bash
# 激活环境
conda activate voice-system

# 安装核心依赖
pip install fastapi uvicorn aiohttp python-docx python-multipart
```

---

## 3. 外部工具

### 3.1 FFmpeg
1.  **下载**：下载 `ffmpeg-git-full.7z`。
2.  **解压**：将解压后的内容移动到 `E:\Dev_Tools\FFmpeg\`。
3.  **环境变量**：将 `E:\Dev_Tools\FFmpeg\bin` 添加到系统的 **环境变量 PATH** 中。

---

## 4. 环境就绪确认清单

| 检查项 | 验证内容 | 期望路径/结果 |
| :--- | :--- | :--- |
| Node.js 路径 | `where node` | `E:\Dev_Tools\Nodejs\node.exe` |
| Conda 路径 | `where conda` | `E:\Dev_Tools\Miniconda\Scripts\conda.exe` |
| 虚拟环境路径 | `conda info --envs` | `voice-system` 位于 E 盘目录下 |
| 音频工具 | `ffmpeg -version` | 正常显示 |

---

## 5. 完成后的反馈
当你完成所有步骤并确认都在 E 盘正确安装后，请告诉 AI：
**“环境已就绪，所有路径已配置到 E 盘。”**
