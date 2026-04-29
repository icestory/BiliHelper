from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.repositories import user_repository


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, username: str, password: str, email: str | None = None) -> tuple[User, str, str]:
        # 检查用户名是否已存在
        if user_repository.get_user_by_username(self.db, username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

        # 检查邮箱是否已存在
        if email and user_repository.get_user_by_email(self.db, email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被注册")

        hashed = hash_password(password)
        user = user_repository.create_user(self.db, username=username, email=email, password_hash=hashed)
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)
        return user, access_token, refresh_token

    def login(self, username: str, password: str) -> tuple[User, str, str]:
        user = user_repository.get_user_by_username(self.db, username)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

        if user.status != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)
        return user, access_token, refresh_token

    def refresh_token(self, token_str: str) -> tuple[str, str]:
        try:
            payload = decode_token(token_str)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 无效或已过期")

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="仅支持 refresh token 刷新")

        user_id = int(payload["sub"])
        user = user_repository.get_user_by_id(self.db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

        if user.status != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

        access_token = create_access_token(user.id)
        new_refresh_token = create_refresh_token(user.id)
        return access_token, new_refresh_token
