import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.models.user import RefreshTokenSession
from app.models.user import User
from app.repositories import user_repository


def _utcnow():
    return datetime.now(timezone.utc)


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


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
        refresh_token = self._create_refresh_session(user.id)
        self.db.commit()
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
        refresh_token = self._create_refresh_session(user.id)
        self.db.commit()
        return user, access_token, refresh_token

    def refresh_token(self, token_str: str) -> tuple[str, str]:
        try:
            payload = decode_token(token_str)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 无效或已过期")

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="仅支持 refresh token 刷新")

        sub = payload.get("sub")
        jti = payload.get("jti")
        if sub is None or not jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 无效")
        try:
            user_id = int(sub)
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 无效")

        user = user_repository.get_user_by_id(self.db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

        if user.status != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

        session = self.db.query(RefreshTokenSession).filter(RefreshTokenSession.jti == jti).first()
        token_hash = _hash_refresh_token(token_str)
        expires_at = session.expires_at if session else None
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if not session or session.user_id != user_id or session.token_hash != token_hash or not expires_at or expires_at <= _utcnow():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 无效或已过期")

        if session.revoked:
            self._revoke_all_refresh_sessions(user_id)
            self.db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 已失效，请重新登录")

        session.revoked = True
        session.last_used_at = _utcnow()
        session.revoked_at = _utcnow()
        access_token = create_access_token(user.id)
        new_refresh_token = self._create_refresh_session(user.id)
        self.db.commit()
        return access_token, new_refresh_token

    def revoke_refresh_token(self, token_str: str) -> None:
        try:
            payload = decode_token(token_str)
        except Exception:
            return
        sub = payload.get("sub")
        jti = payload.get("jti")
        if payload.get("type") != "refresh" or not jti or sub is None:
            return
        try:
            user_id = int(sub)
        except (TypeError, ValueError):
            return
        session = self.db.query(RefreshTokenSession).filter(RefreshTokenSession.jti == jti).first()
        if session and session.user_id == user_id and session.token_hash == _hash_refresh_token(token_str) and not session.revoked:
            session.revoked = True
            session.revoked_at = _utcnow()
            self.db.commit()

    def _create_refresh_session(self, user_id: int) -> str:
        jti = uuid.uuid4().hex
        token = create_refresh_token(user_id, jti)
        session = RefreshTokenSession(
            user_id=user_id,
            jti=jti,
            token_hash=_hash_refresh_token(token),
            expires_at=_utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(session)
        return token

    def _revoke_all_refresh_sessions(self, user_id: int) -> None:
        now = _utcnow()
        (
            self.db.query(RefreshTokenSession)
            .filter(RefreshTokenSession.user_id == user_id, RefreshTokenSession.revoked == False)  # noqa: E712
            .update({"revoked": True, "revoked_at": now})
        )
