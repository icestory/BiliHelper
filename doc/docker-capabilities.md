# BiliHelper Docker 能力文档

本文档介绍 Docker 对 BiliHelper 项目的全部价值和使用场景。

---

## 一、当前 Docker 能做什么

### 1. 一键部署 — 3 条命令上线

新服务器从零到运行只需要：

```bash
git clone https://github.com/icestory/BiliHelper.git && cd BiliHelper
cp .env.example .env && nano .env  # 改 3 行配置
docker compose up -d
```

30 秒后所有服务就绪，比手动安装节省 30+ 条命令、1 小时时间。

### 2. 环境一致性 — 杜绝"我这能跑你那不行"

`Dockerfile` 锁死了 Python 版本（3.12-slim）、npm 版本（22-alpine）、PostgreSQL 版本（16-alpine）、Redis 版本（7-alpine）。无论你部署到 AWS、阿里云还是自建服务器，运行环境完全相同。

### 3. 一键迁移服务器

把整个项目搬到新服务器：

```bash
# 老服务器：备份数据库
docker compose exec postgres pg_dump -U bilihelper bilihelper > backup.sql

# 新服务器：恢复
docker compose exec -T postgres psql -U bilihelper bilihelper < backup.sql
```

代码和数据各一条命令完成迁移。

### 4. 故障自愈 — 服务挂了自动重启

`docker-compose.yml` 中所有服务都配置了 `restart: unless-stopped`：
- Worker 崩溃 → 自动重启
- API 内存溢出 → 自动重启
- PostgreSQL 挂了 → 自动重启
- 服务器重启 → `systemctl enable docker` 后全部自动恢复

### 5. 健康检查 — 自动检测服务状态

```yaml
# PostgreSQL
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U bilihelper"]

# Redis
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
```

依赖服务就绪后才启动 API/Worker，避免冷启动竞态。

### 6. 数据持久化 — 删除容器不丢数据

```yaml
volumes:
  postgres_data:  # 数据库
  redis_data:     # Redis 持久化
  app_temp:       # 临时音频文件
```

`docker compose down` 不会删除 Volume。只有执行 `docker compose down -v` 才会清理。

### 7. 零残留卸载

```bash
docker compose down -v   # 彻底清除所有容器和数据
rm -rf ~/BiliHelper      # 删除代码
```

不污染系统环境，不留 `/etc/`、`/var/` 等残留文件。

### 8. 多实例共存

一台服务器同时跑多个 BiliHelper 实例（比如 dev + production）：

```bash
# 生产环境
docker compose -f docker-compose.yml -p bilihelper-prod up -d

# 开发环境（不同端口、不同 Volume）
docker compose -f docker-compose.yml -p bilihelper-dev up -d
```

---

## 二、Docker 的未来扩展方向

这些功能已经具备基础，进一步配置即可实现。

### 9. CI/CD 自动构建部署

配合 GitHub Actions，每次 `git push` 自动构建镜像并部署：

```yaml
# .github/workflows/deploy.yml (示例)
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose build
      - run: docker compose up -d
```

### 10. 镜像仓库分发

构建好的镜像推送到 Docker Hub / GitHub Container Registry，新服务器直接拉取，无需编译：

```bash
# 本地构建并推送
docker compose build
docker tag bilihelper-api icestory/bilihelper-api:latest
docker push icestory/bilihelper-api:latest

# 新服务器直接拉取运行（省掉 npm install + pip install）
docker pull icestory/bilihelper-api:latest
docker compose up -d
```

### 11. 资源限制

限制每个服务的 CPU 和内存，防止某个服务耗尽系统资源：

```yaml
services:
  worker:
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
```

### 12. ASR Worker 独立扩展

本地 faster-whisper 很吃 GPU/CPU，可以单独拆出一个服务限制资源：

```yaml
services:
  asr-worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker -Q asr --concurrency=1
    deploy:
      resources:
        limits:
          memory: 8G
```

### 13. 定时清理任务

用 Celery Beat（定时调度）自动清理过期临时文件：

```bash
celery -A app.workers.celery_app beat --loglevel=info
```

---

## 三、常用运维命令速查

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 重新构建（代码更新后）
docker compose up -d --build

# 查看运行状态
docker compose ps

# 查看实时日志
docker compose logs -f

# 只看某个服务的日志
docker compose logs -f api
docker compose logs -f worker

# 进入容器调试
docker compose exec api bash
docker compose exec postgres psql -U bilihelper

# 数据库备份
docker compose exec postgres pg_dump -U bilihelper bilihelper > backup.sql

# 数据库恢复
docker compose exec -T postgres psql -U bilihelper bilihelper < backup.sql

# 手动运行迁移
docker compose exec api alembic upgrade head

# 重启单个服务
docker compose restart worker

# 扩容 Worker（临时增加处理能力）
docker compose up -d --scale worker=3

# 彻底清理（包括数据）
docker compose down -v
```

---

## 四、对比总结

| 场景 | 手动部署 | Docker 部署 |
|------|---------|------------|
| 新服务器部署 | 30+ 条命令，1 小时 | 3 条命令，30 秒 |
| 迁移服务器 | 重做全套步骤 | 备份数据 → 新机恢复 |
| 代码更新 | 手动 git pull + 重启 | `docker compose up -d --build` |
| 故障恢复 | 手动排查重启 | 自动重启（restart: always） |
| 卸载清理 | 多处残留文件 | 一键彻底清理 |
| 环境一致性 | 依赖系统版本 | 镜像锁死版本 |
| 多实例 | 复杂端口/进程管理 | 不同 compose project | 
