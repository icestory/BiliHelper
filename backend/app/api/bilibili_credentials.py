"""B 站 Cookie 凭证管理 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.credential import (
    BilibiliCredentialCreate,
    BilibiliCredentialUpdate,
    BilibiliCredentialResponse,
)
from app.services.credential_service import BilibiliCredentialService

router = APIRouter(prefix="/api/bilibili-credentials", tags=["B站Cookie凭证"])


@router.get("", response_model=list[BilibiliCredentialResponse])
def list_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出当前用户的所有 B 站 Cookie 凭证（脱敏）"""
    return BilibiliCredentialService(db).list(current_user.id)


@router.post("", response_model=BilibiliCredentialResponse, status_code=201)
def create_credential(
    body: BilibiliCredentialCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """添加 B 站 Cookie 凭证"""
    return BilibiliCredentialService(db).create(current_user.id, body)


@router.patch("/{credential_id}", response_model=BilibiliCredentialResponse)
def update_credential(
    credential_id: int,
    body: BilibiliCredentialUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """部分更新 Cookie 值或启用状态"""
    return BilibiliCredentialService(db).update(current_user.id, credential_id, body)


@router.delete("/{credential_id}", status_code=204)
def delete_credential(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除 Cookie 凭证"""
    BilibiliCredentialService(db).delete(current_user.id, credential_id)


@router.post("/{credential_id}/enable", response_model=BilibiliCredentialResponse)
def enable_credential(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """启用一个 Cookie 凭证（同时禁用其余凭证）"""
    return BilibiliCredentialService(db).set_enabled(current_user.id, credential_id)
