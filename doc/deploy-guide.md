# BiliHelper 部署指南

本文档面向零基础用户，从零开始在 Ubuntu 24.04 服务器上部署 BiliHelper。

---

## 准备工作

### 你需要什么

- 一台 Ubuntu 24.04 服务器（AWS/阿里云/腾讯云等均可）
- 可以通过 SSH 登录服务器
- 一个域名（可选，直接用 IP 也行）

### 登录服务器

在你自己电脑的终端里输入：

```bash
ssh ubuntu@你的服务器IP
```

---

## 第一步：安装基础软件

```bash
# 更新软件包列表
sudo apt update

# 安装必要工具
sudo apt install -y python3 python3-pip python3-venv git curl

# 安装 FFmpeg（音频处理用）
sudo apt install -y ffmpeg

# 安装 Node.js（前端构建用）
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# 安装 PostgreSQL 数据库
sudo apt install -y postgresql postgresql-client

# 安装 Redis（任务队列用）
sudo apt install -y redis-server

# 安装 Nginx（Web 服务器）
sudo apt install -y nginx
```

验证安装：

```bash
python3 --version   # 应该显示 3.12+
node --version      # 应该显示 v22+
psql --version      # 应该显示 16+
redis-cli ping      # 应该返回 PONG
```

---

## 第二步：克隆代码

```bash
cd ~
git clone git@github.com:icestory/BiliHelper.git
cd BiliHelper
```

> 如果没有配置 GitHub SSH Key，先用 HTTPS 克隆：
> ```bash
> git clone https://github.com/icestory/BiliHelper.git
> ```

---

## 第三步：配置数据库

```bash
# 启动 PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql   # 开机自启

# 创建数据库和用户
sudo -u postgres psql -c "CREATE USER bilihelper WITH PASSWORD '你的数据库密码';"
sudo -u postgres psql -c "CREATE DATABASE bilihelper OWNER bilihelper;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE bilihelper TO bilihelper;"
```

> ⚠️ 把 `你的数据库密码` 换成你自己的密码，记下来后面要用。

---

## 第四步：安装后端依赖

```bash
cd ~/BiliHelper/backend

# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装 Python 依赖
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary \
    pydantic pydantic-settings python-jose passlib celery redis \
    cryptography httpx yt-dlp

# 验证安装
python -c "from app.main import app; print('OK')"
# 应该输出 OK
```

---

## 第五步：生成密钥并创建配置文件

```bash
cd ~/BiliHelper/backend

# 激活虚拟环境（如果还没激活）
source .venv/bin/activate

# 生成加密密钥
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

复制输出的密钥（例如 `WJrO34Pl2UdTvM-tWbe7QTmGMD0vYORpR-IQgEZIzcw=`）。

然后创建 `.env` 文件：

```bash
nano .env
```

填入以下内容（**把标注的部分换成你自己的值**）：

```ini
APP_ENV=production
# 随便打一串随机字符
APP_SECRET_KEY=换成你的随机密钥
# 数据库地址（格式：postgresql://用户名:密码@主机:端口/数据库名）
DATABASE_URL=postgresql://bilihelper:你的数据库密码@localhost:5432/bilihelper
# Redis 地址
REDIS_URL=redis://localhost:6379/0
# 服务器外网地址（有域名就写域名）
API_BASE_URL=http://你的服务器IP
WEB_BASE_URL=http://你的服务器IP
# 粘贴刚才生成的加密密钥
CREDENTIAL_ENCRYPTION_KEY=刚才生成的密钥
DEFAULT_LLM_PROVIDER=openai
TEMP_FILE_TTL_HOURS=24
MAX_VIDEO_DURATION_SECONDS=7200
MAX_PARTS_PER_TASK=20
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
```

按 `Ctrl+O` 保存，`Ctrl+X` 退出。

---

## 第六步：初始化数据库

```bash
cd ~/BiliHelper/backend
source .venv/bin/activate
export PYTHONPATH=$(pwd)

# 生成迁移文件
alembic revision --autogenerate -m "initial: all tables"

# 执行迁移
alembic upgrade head
```

看到 `Running upgrade ... -> ... initial: all tables` 表示成功。

---

## 第七步：启动后端服务

### 7.1 启动 FastAPI

```bash
cd ~/BiliHelper/backend
source .venv/bin/activate
export PYTHONPATH=$(pwd)

nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/api.log 2>&1 &
```

验证：

```bash
curl http://localhost:8000/api/health
# 应该返回 {"status":"ok","version":"0.1.0"}
```

### 7.2 启动 Celery Worker

```bash
cd ~/BiliHelper/backend
source .venv/bin/activate
export PYTHONPATH=$(pwd)

nohup celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 > /tmp/worker.log 2>&1 &
```

验证：

```bash
grep "ready" /tmp/worker.log
# 应该看到 celery@xxx ready
```

### 7.3 启动 Redis

```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 验证
redis-cli ping   # 返回 PONG
```

---

## 第八步：构建并部署前端

```bash
cd ~/BiliHelper/web

# 安装前端依赖
npm install

# 构建生产版本
npm run build
```

构建完成后，`dist/` 目录中就是前端文件。复制到 Nginx 目录：

```bash
sudo mkdir -p /var/www/bilihelper
sudo cp -r dist/* /var/www/bilihelper/
```

---

## 第九步：配置 Nginx

创建 Nginx 配置文件：

```bash
sudo nano /etc/nginx/sites-available/bilihelper
```

填入以下内容（**把 `你的服务器IP` 换成实际 IP 或域名**）：

```nginx
server {
    listen 80;
    server_name 你的服务器IP;

    gzip on;
    gzip_types application/javascript text/css application/json image/svg+xml;
    gzip_min_length 1024;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    root /var/www/bilihelper;
    index index.html;

    # API 反代
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 前端 SPA
    location / {
        try_files $uri /index.html;
    }
}
```

启用配置：

```bash
sudo ln -sf /etc/nginx/sites-available/bilihelper /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t              # 检查配置是否正确
sudo systemctl reload nginx
```

---

## 第十步：开放防火墙端口

### 如果使用云服务器

登录云服务商控制台，在**安全组/防火墙规则**中添加入站规则：

| 端口 | 协议 | 说明 |
|------|------|------|
| 80 | TCP | Web 访问 |

### 如果使用物理机/虚拟机

```bash
sudo ufw allow 80/tcp
sudo ufw enable
```

> ⚠️ 不要开放 8000 和 5432 端口！这些只在服务器内部使用，开放有安全风险。

---

## 第十一步：验证部署

在浏览器中打开：

```
http://你的服务器IP
```

应该看到 BiliHelper 的登录页面。

注册一个账号 → 配置 LLM API Key → 粘贴 B 站链接 → 开始使用！

---

## 设置开机自启（可选）

创建一个 systemd 服务让后端开机自启：

```bash
sudo nano /etc/systemd/system/bilihelper-api.service
```

```ini
[Unit]
Description=BiliHelper FastAPI
After=network.target postgresql.service redis-server.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/BiliHelper/backend
Environment="PYTHONPATH=/home/ubuntu/BiliHelper/backend"
ExecStart=/home/ubuntu/BiliHelper/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 同样创建 Worker 服务
sudo nano /etc/systemd/system/bilihelper-worker.service
```

```ini
[Unit]
Description=BiliHelper Celery Worker
After=network.target postgresql.service redis-server.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/BiliHelper/backend
Environment="PYTHONPATH=/home/ubuntu/BiliHelper/backend"
ExecStart=/home/ubuntu/BiliHelper/backend/.venv/bin/celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
Restart=always

[Install]
WantedBy=multi-user.target
```

启用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable bilihelper-api bilihelper-worker
sudo systemctl start bilihelper-api bilihelper-worker
```

---

## 更新代码

后续有新版本时，执行以下步骤：

```bash
cd ~/BiliHelper
git pull origin master

# 后端
cd backend
source .venv/bin/activate
export PYTHONPATH=$(pwd)
pip install -r requirements.txt   # 如果有新的依赖
alembic upgrade head               # 如果有新的迁移

# 重启服务
sudo systemctl restart bilihelper-api bilihelper-worker

# 前端
cd ~/BiliHelper/web
npm install
npm run build
sudo cp -r dist/* /var/www/bilihelper/
```

---

## 常见问题

### Q: 访问网页显示 502 错误？

先检查后端是否正常运行：

```bash
curl http://localhost:8000/api/health
```

如果后端挂了，重启 API 服务。

### Q: 创建了分析任务但一直不执行？

检查 Worker 是否正常运行：

```bash
grep "ready" /tmp/worker.log
```

检查 Redis 是否正常：`redis-cli ping`

### Q: 数据库连接失败？

确认 PostgreSQL 在运行：`sudo systemctl status postgresql`  
确认 `.env` 中密码和用户名正确。

### Q: B 站链接解析失败？

从海外服务器访问 B 站可能有部分限制。可以配置 B 站 Cookie 解决。后续版本会支持在界面中配置。
