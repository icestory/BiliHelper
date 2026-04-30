# BiliHelper 部署指南

新手向，从零开始。推荐用 **Docker 方式**，只要 3 条命令。

---

## 方式一：Docker 部署（推荐）

### 1. 安装 Docker

```bash
curl -fsSL https://get.docker.com | sudo bash
sudo systemctl enable docker
```

### 2. 克隆代码

```bash
git clone https://github.com/icestory/BiliHelper.git
cd BiliHelper
```

### 3. 配置环境变量

```bash
cp .env.example .env
nano .env
```

只需要改 3 行：

| 变量 | 操作 |
|------|------|
| `APP_SECRET_KEY` | 运行 `openssl rand -hex 32`，复制结果填入 |
| `CREDENTIAL_ENCRYPTION_KEY` | 运行 `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`，复制结果填入（没有 cryptography 就先 `pip3 install cryptography`） |
| `API_BASE_URL` / `WEB_BASE_URL` | 换成 `http://你的服务器IP` |

### 4. 一键启动

```bash
docker compose up -d
```

首次启动会自动构建镜像、下载 PostgreSQL/Redis、运行数据库迁移。

```bash
# 查看运行状态（5 个服务都应该是 Up）
docker compose ps

# 查看日志
docker compose logs -f
```

### 5. 开放端口

登录云服务商控制台 → 安全组 / 防火墙 → 添加入站规则：

| 端口 | 协议 | 
|------|------|
| 80 | TCP |

### 6. 浏览器访问

```
http://你的服务器IP
```

注册 → 配置 API Key → 粘贴 B 站链接 → 开始使用。

### Docker 更新代码

```bash
docker compose down
git pull origin master
docker compose up -d --build
```

数据（数据库、Redis）存储在 Docker Volume 中，`down` 不会丢失。

---

## 方式二：手动部署

适合不想用 Docker 的情况。

### 1. 安装依赖

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl ffmpeg postgresql redis-server nginx

# Node.js（构建前端用）
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2. 克隆代码

```bash
cd ~
git clone https://github.com/icestory/BiliHelper.git
cd BiliHelper
```

### 3. 配置数据库

```bash
sudo systemctl start postgresql redis-server
sudo systemctl enable postgresql redis-server

sudo -u postgres psql -c "CREATE USER bilihelper WITH PASSWORD '你的数据库密码';"
sudo -u postgres psql -c "CREATE DATABASE bilihelper OWNER bilihelper;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE bilihelper TO bilihelper;"
```

### 4. 配置环境变量

```bash
cd backend
cp ../.env.example .env
```

编辑 `.env`，把 `DATABASE_URL` 和 `REDIS_URL` 换成：
```
DATABASE_URL=postgresql://bilihelper:你的数据库密码@localhost:5432/bilihelper
REDIS_URL=redis://localhost:6379/0
```
填好 `APP_SECRET_KEY` 和 `CREDENTIAL_ENCRYPTION_KEY`。

### 5. 安装 Python 依赖

```bash
cd ~/BiliHelper/backend
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary \
    pydantic pydantic-settings python-jose passlib celery redis \
    cryptography httpx yt-dlp
```

### 6. 初始化数据库

```bash
export PYTHONPATH=$(pwd)
alembic revision --autogenerate -m "initial: all tables"
alembic upgrade head
```

### 7. 启动后端

```bash
# 启动 FastAPI
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/api.log 2>&1 &

# 启动 Celery Worker
nohup celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 > /tmp/worker.log 2>&1 &
```

### 8. 构建并部署前端

```bash
cd ~/BiliHelper/web
npm install
npm run build
sudo mkdir -p /var/www/bilihelper
sudo cp -r dist/* /var/www/bilihelper/
```

### 9. 配置 Nginx

```bash
sudo nano /etc/nginx/sites-available/bilihelper
```

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

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        try_files $uri /index.html;
    }
}
```

启用并重载：

```bash
sudo ln -sf /etc/nginx/sites-available/bilihelper /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

### 10. 开放端口

云服务商安全组 → 添加 TCP 80 入站规则。

### 11. 访问

```
http://你的服务器IP
```

---

## 设置开机自启（手动部署用）

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

Worker 同理，把 ExecStart 换成 celery 命令即可。

---

## 常见问题

### 端口 80 已被占用？

```bash
sudo lsof -i :80
sudo systemctl stop 占用进程的服务
```

### 数据库连接失败？

确认 PostgreSQL 在运行：`sudo systemctl status postgresql`

### 分析任务一直等待？

确认 Celery Worker 在运行，Redis 正常（`redis-cli ping`）。

### B 站视频解析失败？

海外服务器访问 B 站可能部分受限。可以配置 B 站 Cookie 解决（后续版本支持 UI 配置）。
