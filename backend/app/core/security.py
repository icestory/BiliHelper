import base64
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# ============ JWT ============

def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode({"sub": str(subject), "exp": expire}, settings.APP_SECRET_KEY, algorithm="HS256")


def create_refresh_token(subject: str | int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": str(subject), "exp": expire, "type": "refresh"}, settings.APP_SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.APP_SECRET_KEY, algorithms=["HS256"])


# ============ 密码哈希 ============

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ============ API Key 加密 ============

def get_fernet() -> Fernet:
    key = settings.CREDENTIAL_ENCRYPTION_KEY
    if not key:
        raise RuntimeError("CREDENTIAL_ENCRYPTION_KEY 未配置，请生成: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        raise RuntimeError(
            "CREDENTIAL_ENCRYPTION_KEY 无效，不是合法的 Fernet key。"
            "请生成: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )


def encrypt_api_key(plain: str) -> str:
    f = get_fernet()
    return f.encrypt(plain.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    f = get_fernet()
    return f.decrypt(encrypted.encode()).decode()
