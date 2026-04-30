#!/bin/bash
set -e

# 等待数据库就绪
echo "等待数据库连接..."
until python -c "from app.core.database import engine; engine.connect()" 2>/dev/null; do
  sleep 2
done

# 运行迁移
echo "运行数据库迁移..."
alembic revision --autogenerate -m "docker-auto-migration" 2>/dev/null || true
alembic upgrade head

# 启动应用
echo "启动 $@"
exec "$@"
