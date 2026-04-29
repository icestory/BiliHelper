from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.credential import (
    ApiCredentialCreate,
    ApiCredentialUpdate,
    ApiCredentialResponse,
)
from app.services.credential_service import CredentialService

router = APIRouter(prefix="/api/llm-configs", tags=["大模型配置"])


@router.get("", response_model=list[ApiCredentialResponse])
def list_configs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CredentialService(db).list(current_user.id)


@router.post("", response_model=ApiCredentialResponse, status_code=201)
def create_config(
    body: ApiCredentialCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CredentialService(db).create(current_user.id, body)


@router.patch("/{config_id}", response_model=ApiCredentialResponse)
def update_config(
    config_id: int,
    body: ApiCredentialUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CredentialService(db).update(current_user.id, config_id, body)


@router.delete("/{config_id}", status_code=204)
def delete_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    CredentialService(db).delete(current_user.id, config_id)


@router.post("/{config_id}/set-default", response_model=ApiCredentialResponse)
def set_default(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CredentialService(db).set_default(current_user.id, config_id)
