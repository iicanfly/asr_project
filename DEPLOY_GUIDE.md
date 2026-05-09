# 内网语音识别及文档生成系统 - Linux 部署指南

## 1. 开发机打包

### 1.1 打包项目代码

在 Windows 开发机上，进入项目目录，打包需要的文件：

```powershell
cd E:\Trae_Learning\04_Project_video

# 打包项目代码（排除不需要的文件）
tar czf E:\voice-system-code.tar.gz ^
    main.py config.py generate_cert.py requirements.txt .env logo.jpeg ^
    templates/ static/
```

> 以下文件/目录**不需要打包**，部署后会自动生成：
> `cert/`、`exports/`、`temp_audio/`、`__pycache__/`、
> `backend_build/`、`backend_dist/`、`dist/`、`src/`、
> `node_modules/`、`*.docx`、`*.pcm`、`*.wav`、`*.mp3`

### 1.2 打包 Conda 环境（conda-pack）

conda-pack 可以将整个 conda 环境打包成一个压缩包，在目标机器上解压即可使用，**无需重新安装依赖**。

```powershell
# 先安装 conda-pack（只需一次）
conda install -c conda-forge conda-pack -y

# 激活要打包的环境
conda activate voice-system

# 打包环境
conda pack -n voice-system -o E:\voice-system-env.tar.gz
```

打包完成后会得到两个文件：
- `E:\voice-system-code.tar.gz` — 项目代码
- `E:\voice-system-env.tar.gz` — Conda 环境

> **注意**：conda-pack 打包的环境与操作系统绑定。Windows 打包的环境**不能**在 Linux 上使用。
> 如果开发机是 Windows、服务器是 Linux，请跳到 [2.3 节](#23-安装-conda-环境) 在服务器上重建环境。

---

## 2. 服务器环境搭建

### 2.1 安装 Miniconda

```bash
# 下载 Miniconda（x86_64）
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# ARM 架构（华为鲲鹏等）
# wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh

# 安装
bash Miniconda3-latest-Linux-x86_64.sh
# 按提示操作，安装路径默认 ~/miniconda3 即可

# 重新加载 shell
source ~/.bashrc

# 验证
conda --version
```

### 2.2 上传文件到服务器

在开发机上执行：

```powershell
# 上传代码和环境包
scp E:\voice-system-code.tar.gz user@服务器IP:~/
scp E:\voice-system-env.tar.gz user@服务器IP:~/
```

### 2.3 安装 Conda 环境

**方式 A：使用 conda-pack 解压（开发机与服务器同系统时）**

```bash
# 创建环境目录
mkdir -p ~/miniconda3/envs/voice-system

# 解压 conda-pack 打包的环境
tar -xzf ~/voice-system-env.tar.gz -C ~/miniconda3/envs/voice-system

# 激活环境
conda activate voice-system

# 验证
python --version
pip list | grep flask
```

**方式 B：从 requirements.txt 重建（开发机与服务器不同系统时）**

```bash
# 创建 conda 环境
conda create -n voice-system python=3.9 -y
conda activate voice-system

# 安装依赖
cd /opt/voice-system
pip install -r requirements.txt
```

**方式 C：服务器无法联网时，离线安装**

在开发机上下载离线包：

```powershell
pip download -r requirements.txt -d pip_packages/
tar czf pip_packages.tar.gz pip_packages/
scp E:\pip_packages.tar.gz user@服务器IP:~/
```

在服务器上离线安装：

```bash
conda create -n voice-system python=3.9 -y
conda activate voice-system

cd ~
tar xzf pip_packages.tar.gz
pip install --no-index --find-links=pip_packages/ -r /opt/voice-system/requirements.txt
```

---

## 3. 部署项目代码

```bash
# 创建项目目录
mkdir -p /opt/voice-system

# 解压代码
cd /opt/voice-system
tar xzf ~/voice-system-code.tar.gz

# 确认目录结构
ls -la
# 应该看到: main.py  config.py  generate_cert.py  requirements.txt  .env  templates/  static/
```

---

## 4. 修改配置

### 4.1 修改 .env

```bash
vim /opt/voice-system/.env
```

**必须修改的配置**：

```ini
# --- 服务器配置 ---
HOST=0.0.0.0
PORT=6543

# --- HTTPS 配置 ---
# 必须启用，否则浏览器无法使用麦克风
ENABLE_HTTPS=True
SSL_CERT=cert/cert.pem
SSL_KEY=cert/key.pem

# --- AI 服务配置 ---
# ⚠️ 部署到内网时改为 True
USE_INTRANET=True

# ⚠️ 替换为内网 AI 服务的实际地址和密钥
INTRANET_API_KEY=your-api-key
INTRANET_BASE_URL=http://内网AI服务IP:8000/v1
INTRANET_ASR_MODEL=qwen-asr
INTRANET_LLM_MODEL=qwen2.5-7b
```

### 4.2 生成 SSL 证书

```bash
cd /opt/voice-system
conda activate voice-system

# 替换为服务器的实际 IP 地址
python generate_cert.py 192.168.X.X
```

输出示例：
```
SSL 证书生成成功！
  证书文件: /opt/voice-system/cert/cert.pem
  私钥文件: /opt/voice-system/cert/key.pem
  服务器 IP: 192.168.X.X
```

---

## 5. 快速试用

### 5.1 前台启动

```bash
cd /opt/voice-system
conda activate voice-system
python main.py
```

看到以下输出表示启动成功：
```
启动服务器: 0.0.0.0:6543
运行模式: 内网
ASR 模型: qwen-asr, LLM 模型: qwen2.5-7b
HTTPS 已启用，证书: /opt/voice-system/cert/cert.pem
访问地址: https://localhost:6543
 * Running on https://192.168.X.X:6543
```

### 5.2 验证服务

另开一个终端：

```bash
# 检查 API
curl -k https://127.0.0.1:6543/api/v1/debug/status
# 预期返回: {"status":"online","mode":"intranet",...}

# 检查端口
ss -tlnp | grep 6543
```

### 5.3 浏览器访问

在另一台电脑的浏览器中打开：

```
https://192.168.X.X:6543
```

首次访问会提示证书不安全，点击 **「高级」→「继续前往」** 即可。

> 按 `Ctrl+C` 可停止前台服务。

---

## 6. 正式部署（systemd 服务）

试用没问题后，配置为系统服务，实现开机自启和自动重启。

### 6.1 创建服务文件

```bash
sudo vim /etc/systemd/system/voice-system.service
```

写入以下内容（**替换路径和用户名**）：

```ini
[Unit]
Description=Voice System - 语音识别及文档生成系统
After=network.target

[Service]
Type=simple
User=your_username
Group=your_username
WorkingDirectory=/opt/voice-system
Environment=PATH=/home/your_username/miniconda3/envs/voice-system/bin:/usr/bin
ExecStart=/home/your_username/miniconda3/envs/voice-system/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> **获取 Python 路径**：激活 conda 环境后执行 `which python`，将输出填入 `ExecStart` 和 `PATH`。

### 6.2 启动和管理

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start voice-system

# 设置开机自启
sudo systemctl enable voice-system

# 查看状态
sudo systemctl status voice-system

# 查看实时日志
sudo journalctl -u voice-system -f

# 停止服务
sudo systemctl stop voice-system

# 重启服务
sudo systemctl restart voice-system
```

---

## 7. 防火墙配置

```bash
# firewalld
sudo firewall-cmd --permanent --add-port=6543/tcp
sudo firewall-cmd --reload

# iptables
sudo iptables -A INPUT -p tcp --dport 6543 -j ACCEPT
sudo iptables-save
```

---

## 8. 客户端访问

访问地址：`https://192.168.X.X:6543`

### 自签名证书提示

| 浏览器 | 操作步骤 |
|--------|----------|
| Chrome | 「高级」→「继续前往（不安全）」 |
| Firefox | 「高级」→「接受风险并继续」 |
| Edge | 「高级」→「继续前往（不安全）」 |

### 使用正式 SSL 证书（可选）

```bash
cp your_cert.pem /opt/voice-system/cert/cert.pem
cp your_key.pem /opt/voice-system/cert/key.pem
sudo systemctl restart voice-system
```

---

## 9. 常见问题排查

### Q1: 浏览器提示「当前环境不支持 getUserMedia」

- 确认使用 `https://` 访问（不是 `http://`）
- 确认 SSL 证书包含服务器实际 IP（重新运行 `python generate_cert.py 服务器IP`）

### Q2: Socket.IO 连接失败

- 检查防火墙是否开放 6543 端口
- 确认 `static/js/socket.io.min.js` 文件存在

### Q3: ASR 语音识别不工作

- 检查 `.env` 中 `USE_INTRANET=True` 和 AI 服务地址
- 测试 AI 服务连通性：`curl http://内网AI服务IP:8000/v1/models`
- 查看日志：`sudo journalctl -u voice-system -f` 或前台运行查看输出

### Q4: conda-pack 解压后环境无法激活

```bash
# 手动激活
source ~/miniconda3/envs/voice-system/bin/activate

# 如果提示权限问题
chmod -R +w ~/miniconda3/envs/voice-system
```

### Q5: 端口被占用

```bash
# 查看占用进程
ss -tlnp | grep 6543
# 杀掉进程
kill <PID>
```

---

## 10. 部署后目录结构

```
/opt/voice-system/
├── main.py                  # 后端主程序
├── config.py                # 配置加载
├── generate_cert.py         # 证书生成脚本
├── requirements.txt         # Python 依赖
├── .env                     # 环境配置（部署时修改）
├── logo.jpeg                # Logo
├── cert/                    # SSL 证书（generate_cert.py 生成）
│   ├── cert.pem
│   └── key.pem
├── templates/
│   └── index.html           # 前端页面
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js
│       └── socket.io.min.js
├── exports/                 # 导出文档（自动创建）
└── temp_audio/              # 临时音频（自动创建）
```

---

## 11. 更新部署

```bash
cd /opt/voice-system

# 停止服务
sudo systemctl stop voice-system

# 备份配置
cp .env .env.bak

# 上传新代码并解压覆盖
# ...

# 恢复配置
cp .env.bak .env

# 如有新依赖
pip install -r requirements.txt

# 重启服务
sudo systemctl start voice-system
```
