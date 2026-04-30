import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 环境
    APP_ENV: str = "development"

    # 安全
    APP_SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # 数据库
    DATABASE_URL: str = "postgresql://bilihelper:bilihelper@localhost:5432/bilihelper"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str | None = None  # 默认使用 REDIS_URL
    CELERY_RESULT_BACKEND: str | None = None

    # API Key 加密主密钥 (32 字节 base64)
    CREDENTIAL_ENCRYPTION_KEY: str = ""

    # LLM 默认配置
    DEFAULT_LLM_PROVIDER: str = "openai"

    # 限额
    MAX_VIDEO_DURATION_SECONDS: int = 7200
    MAX_PARTS_PER_TASK: int = 20
    TEMP_FILE_TTL_HOURS: int = 24

    # 服务地址
    API_BASE_URL: str = "http://localhost:8000"
    WEB_BASE_URL: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
