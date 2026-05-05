#!/bin/bash
set -e

# 等待数据库就绪
echo "等待数据库连接..."
until python -c "from app.core.database import engine; engine.connect()" 2>/dev/null; do
  sleep 2
done

# 运行已提交的迁移。迁移文件必须在开发阶段生成并审查，容器启动时不自动 autogenerate。
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "运行数据库迁移..."
  alembic upgrade head
else
  echo "跳过数据库迁移..."
fi

# 启动应用
echo "启动 $@"
exec "$@"
