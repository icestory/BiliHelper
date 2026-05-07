import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import encrypt_api_key, decrypt_api_key
from app.models.user import ApiCredential, BilibiliCredential
from app.repositories import credential_repository
from app.schemas.credential import (
    ApiCredentialCreate, ApiCredentialUpdate, ApiCredentialResponse,
    BilibiliCredentialCreate, BilibiliCredentialUpdate, BilibiliCredentialResponse,
)


def mask_api_key(key: str) -> str:
    """脱敏展示：保留前 3 位和后 4 位"""
    if len(key) <= 7:
        return "****"
    return f"{key[:3]}{'*' * 4}{key[-4:]}"


def mask_cookie(value: str) -> str:
    """脱敏展示 Cookie 值：保留前 4 位和后 4 位"""
    if len(value) <= 10:
        return "****"
    return f"{value[:4]}{'*' * 4}{value[-4:]}"


def _is_blocked_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def validate_api_base_url(raw: str | None) -> str | None:
    if raw is None:
        return None
    url = raw.strip().rstrip("/")
    if not url:
        return None

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Base URL 必须是合法的 http(s) 地址")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Base URL 不允许包含用户名或密码")

    if settings.APP_ENV == "production":
        if parsed.scheme != "https":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="生产环境 Base URL 必须使用 HTTPS")

        host = parsed.hostname.lower()
        if host in {"localhost"} or host.endswith(".local"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="生产环境不允许使用本机或内网 Base URL")

        try:
            if _is_blocked_ip(host):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="生产环境不允许使用内网 Base URL")
        except ValueError:
            try:
                infos = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
            except socket.gaierror:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Base URL 域名无法解析")
            for info in infos:
                resolved_ip = info[4][0]
                try:
                    if _is_blocked_ip(resolved_ip):
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="生产环境不允许使用内网 Base URL")
                except ValueError:
                    continue

    return url


def _to_response(cred: ApiCredential) -> ApiCredentialResponse:
    plain = decrypt_api_key(cred.api_key_encrypted)
    return ApiCredentialResponse(
        id=cred.id,
        provider=cred.provider,
        api_base_url=cred.api_base_url,
        api_key_masked=mask_api_key(plain),
        default_model=cred.default_model,
        default_asr_model=cred.default_asr_model,
        default_embedding_model=cred.default_embedding_model,
        is_default=cred.is_default,
        created_at=cred.created_at.isoformat() if cred.created_at else "",
        updated_at=cred.updated_at.isoformat() if cred.updated_at else "",
    )


class CredentialService:
    def __init__(self, db: Session):
        self.db = db

    def list(self, user_id: int) -> list[ApiCredentialResponse]:
        creds = credential_repository.get_credentials_by_user(self.db, user_id)
        return [_to_response(c) for c in creds]

    def create(self, user_id: int, data: ApiCredentialCreate) -> ApiCredentialResponse:
        if data.is_default:
            credential_repository.unset_default_for_user(self.db, user_id)

        encrypted = encrypt_api_key(data.api_key)
        api_base_url = validate_api_base_url(data.api_base_url)
        cred = credential_repository.create_credential(
            self.db,
            user_id=user_id,
            provider=data.provider,
            api_key_encrypted=encrypted,
            api_base_url=api_base_url,
            default_model=data.default_model,
            default_asr_model=data.default_asr_model,
            default_embedding_model=data.default_embedding_model,
            is_default=data.is_default,
        )
        return _to_response(cred)

    def update(self, user_id: int, credential_id: int, data: ApiCredentialUpdate) -> ApiCredentialResponse:
        cred = credential_repository.get_credential_by_id(self.db, credential_id)
        if not cred or cred.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")

        if data.is_default:
            credential_repository.unset_default_for_user(self.db, user_id)

        kwargs = data.model_dump(exclude_unset=True)
        if "api_base_url" in kwargs:
            kwargs["api_base_url"] = validate_api_base_url(kwargs["api_base_url"])

        if "api_key" in kwargs:
            api_key = kwargs.pop("api_key")
            if api_key is not None:
                kwargs["api_key_encrypted"] = encrypt_api_key(api_key)

        cred = credential_repository.update_credential(self.db, cred, **kwargs)
        return _to_response(cred)

    def delete(self, user_id: int, credential_id: int) -> None:
        cred = credential_repository.get_credential_by_id(self.db, credential_id)
        if not cred or cred.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
        credential_repository.delete_credential(self.db, cred)

    def set_default(self, user_id: int, credential_id: int) -> ApiCredentialResponse:
        cred = credential_repository.get_credential_by_id(self.db, credential_id)
        if not cred or cred.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
        credential_repository.unset_default_for_user(self.db, user_id)
        cred = credential_repository.update_credential(self.db, cred, is_default=True)
        return _to_response(cred)


# ============ B 站 Cookie 凭证 ============

def _bili_to_response(cred: BilibiliCredential) -> BilibiliCredentialResponse:
    sessdata = decrypt_api_key(cred.sessdata_encrypted) if cred.sessdata_encrypted else ""
    bili_jct = decrypt_api_key(cred.bili_jct_encrypted) if cred.bili_jct_encrypted else ""
    buvid3 = decrypt_api_key(cred.buvid3_encrypted) if cred.buvid3_encrypted else None
    return BilibiliCredentialResponse(
        id=cred.id,
        sessdata_masked=mask_cookie(sessdata),
        bili_jct_masked=mask_cookie(bili_jct),
        buvid3_masked=mask_cookie(buvid3) if buvid3 else None,
        enabled=cred.enabled,
        updated_at=cred.updated_at.isoformat() if cred.updated_at else "",
    )


class BilibiliCredentialService:
    def __init__(self, db: Session):
        self.db = db

    def list(self, user_id: int) -> list[BilibiliCredentialResponse]:
        creds = credential_repository.get_bilibili_credentials_by_user(self.db, user_id)
        return [_bili_to_response(c) for c in creds]

    def create(self, user_id: int, data: BilibiliCredentialCreate) -> BilibiliCredentialResponse:
        # 如果本次设为启用，先把旧的启用凭证禁用
        if data.enabled:
            credential_repository.unset_enabled_bilibili_for_user(self.db, user_id)

        cred = credential_repository.create_bilibili_credential(
            self.db,
            user_id=user_id,
            sessdata_encrypted=encrypt_api_key(data.sessdata),
            bili_jct_encrypted=encrypt_api_key(data.bili_jct),
            buvid3_encrypted=encrypt_api_key(data.buvid3) if data.buvid3 else None,
            enabled=data.enabled,
        )
        return _bili_to_response(cred)

    def update(self, user_id: int, credential_id: int, data: BilibiliCredentialUpdate) -> BilibiliCredentialResponse:
        cred = credential_repository.get_bilibili_credential_by_id(self.db, credential_id)
        if not cred or cred.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="凭证不存在")

        if data.enabled:
            credential_repository.unset_enabled_bilibili_for_user(self.db, user_id)

        kwargs: dict = {}
        if data.sessdata is not None:
            kwargs["sessdata_encrypted"] = encrypt_api_key(data.sessdata)
        if data.bili_jct is not None:
            kwargs["bili_jct_encrypted"] = encrypt_api_key(data.bili_jct)
        if data.buvid3 is not None:
            kwargs["buvid3_encrypted"] = encrypt_api_key(data.buvid3)
        if data.enabled is not None:
            kwargs["enabled"] = data.enabled

        cred = credential_repository.update_bilibili_credential(self.db, cred, **kwargs)
        return _bili_to_response(cred)

    def delete(self, user_id: int, credential_id: int) -> None:
        cred = credential_repository.get_bilibili_credential_by_id(self.db, credential_id)
        if not cred or cred.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="凭证不存在")
        credential_repository.delete_bilibili_credential(self.db, cred)

    def set_enabled(self, user_id: int, credential_id: int) -> BilibiliCredentialResponse:
        cred = credential_repository.get_bilibili_credential_by_id(self.db, credential_id)
        if not cred or cred.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="凭证不存在")
        credential_repository.unset_enabled_bilibili_for_user(self.db, user_id)
        cred = credential_repository.update_bilibili_credential(self.db, cred, enabled=True)
        return _bili_to_response(cred)

    def get_enabled_cookies(self, user_id: int) -> dict[str, str] | None:
        """获取用户当前启用的 B 站 Cookie，用于注入 HTTP 请求。返回 None 表示未配置。"""
        cred = credential_repository.get_enabled_bilibili_credential(self.db, user_id)
        if not cred:
            return None

        cookies = {}
        if cred.sessdata_encrypted:
            cookies["SESSDATA"] = decrypt_api_key(cred.sessdata_encrypted)
        if cred.bili_jct_encrypted:
            cookies["bili_jct"] = decrypt_api_key(cred.bili_jct_encrypted)
        if cred.buvid3_encrypted:
            cookies["buvid3"] = decrypt_api_key(cred.buvid3_encrypted)
        return cookies if cookies else None
