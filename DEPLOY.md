# 内网语音识别系统 - Linux服务器部署指南

## 一、部署前准备

### 1.1 服务器环境要求
- **操作系统**: Linux (Ubuntu 20.04+ / CentOS 7+ / Debian 10+)
- **Python版本**: Python 3.9+
- **内存**: 建议4GB以上
- **网络**: 服务器需要能够访问大模型API地址

### 1.2 需要准备的文件
将以下文件从Windows复制到Linux服务器：
```
03_Project_video/
├── config.py          # 配置文件（需要修改大模型地址）
├── main.py            # 主程序
├── index.html         # 前端页面
├── requirements.txt   # Python依赖
├── logo.jpeg          # Logo图片
├── temp_audio/        # 音频临时目录（可空）
└── exports/           # 导出文件目录（可空）
```

---

## 二、部署步骤

### 步骤1: 上传项目文件到服务器

```bash
# 使用scp命令上传（在Windows PowerShell中执行）
scp -r C:\Users\Administrator\Desktop\123\03_Project_video user@your-server-ip:/home/user/

# 或者使用其他方式：FTP、WinSCP、rsync等
```

### 步骤2: 登录服务器并进入项目目录

```bash
ssh user@your-server-ip
cd /home/user/03_Project_video
```

### 步骤3: 安装Python环境（如未安装）

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.9 python3.9-pip python3.9-venv -y

# CentOS/RHEL
sudo yum install python39 python39-pip -y
```

### 步骤4: 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python3.9 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 步骤5: 修改配置文件（关键步骤）

编辑 `config.py` 文件，修改大模型地址：

```bash
# 使用vim或nano编辑
vim config.py
```

**需要修改的内容：**

```python
# 核心开关：切换外网开发模式 (False) 与 内网部署模式 (True)
USE_INTRANET = True  # 改为True，使用内网模式

if not USE_INTRANET:
    # --- 外网开发配置 (阿里云 DashScope) ---
    API_KEY = "sk-4016b26700e2419fb1fdedc04164dbf5"
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ASR_MODEL = "qwen3-asr-flash-2026-02-10"
    LLM_MODEL = "qwen-plus-2025-07-28"
else:
    # --- 内网部署配置 (私有化部署) ---
    API_KEY = ""  # 根据实际情况填写
    
    # 【重要】修改为您的内网AI服务器地址
    BASE_URL = "http://your-internal-ai-server:8000/v1"
    
    # 根据您部署的模型名称修改
    ASR_MODEL = "qwen-asr"      # 或您内网的ASR模型名称
    LLM_MODEL = "qwen2.5-7b"    # 或您内网的LLM模型名称
```

### 步骤6: 创建必要的目录

```bash
mkdir -p temp_audio exports
```

### 步骤7: 启动服务

```bash
# 确保在虚拟环境中
source venv/bin/activate

# 启动服务
python main.py
```

服务将在 `http://0.0.0.0:8000` 启动（需要修改main.py中的host）。

---

## 三、修改main.py以支持外部访问

默认情况下服务只在127.0.0.1上监听，需要修改为0.0.0.0以允许外部访问：

编辑 `main.py`，找到最后一行：

```python
# 原代码
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

# 修改为
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 四、使用systemd管理服务（推荐）

创建systemd服务文件，实现开机自启：

```bash
sudo vim /etc/systemd/system/voice-system.service
```

添加以下内容：

```ini
[Unit]
Description=Voice Recognition System
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/user/03_Project_video
Environment=PATH=/home/user/03_Project_video/venv/bin
ExecStart=/home/user/03_Project_video/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable voice-system
sudo systemctl start voice-system

# 查看状态
sudo systemctl status voice-system

# 查看日志
sudo journalctl -u voice-system -f
```

---

## 五、防火墙配置

如果服务器有防火墙，需要开放8000端口：

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 8000/tcp

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# 或者使用iptables
sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
```

---

## 六、客户端访问

部署完成后，其他电脑可以通过浏览器访问：

```
http://your-server-ip:8000
```

**注意：**
- 确保客户端电脑能够访问服务器的8000端口
- 确保服务器能够访问内网大模型API地址
- 如需HTTPS，建议使用Nginx反向代理

---

## 七、使用Nginx反向代理（可选，推荐用于生产环境）

安装Nginx：

```bash
# Ubuntu/Debian
sudo apt install nginx -y

# CentOS/RHEL
sudo yum install nginx -y
```

配置Nginx：

```bash
sudo vim /etc/nginx/sites-available/voice-system
```

添加配置：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 或服务器IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # WebSocket支持
        proxy_read_timeout 86400;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/voice-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 八、常见问题排查

### 8.1 服务启动失败

```bash
# 检查端口占用
sudo netstat -tlnp | grep 8000

# 查看Python错误
python main.py  # 直接运行查看错误信息
```

### 8.2 无法访问大模型API

```bash
# 测试API连通性
curl http://your-internal-ai-server:8000/v1/models

# 检查网络
ping your-internal-ai-server
```

### 8.3 客户端无法访问

```bash
# 在服务器上测试
 curl http://localhost:8000/api/v1/debug/status

# 检查防火墙
sudo iptables -L -n | grep 8000
```

---

## 九、目录结构说明

部署后的目录结构：

```
03_Project_video/
├── venv/                  # Python虚拟环境
├── config.py             # 配置文件
├── main.py               # 主程序
├── index.html            # 前端页面
├── requirements.txt      # 依赖列表
├── logo.jpeg             # Logo
├── temp_audio/           # 临时音频文件
├── exports/              # 导出的Word文档
├── DEPLOY.md             # 本部署文档
└── ports.txt             # 端口占用信息（参考）
```

---

## 十、更新部署

如需更新代码：

```bash
cd /home/user/03_Project_video

# 停止服务
sudo systemctl stop voice-system

# 更新代码（重新上传或git pull）

# 重启服务
sudo systemctl start voice-system
```

---

**部署完成！** 🎉

现在您可以通过浏览器访问 `http://your-server-ip:8000` 使用语音识别系统了。
