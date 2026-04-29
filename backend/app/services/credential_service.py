from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import encrypt_api_key, decrypt_api_key
from app.models.user import ApiCredential
from app.repositories import credential_repository
from app.schemas.credential import ApiCredentialCreate, ApiCredentialUpdate, ApiCredentialResponse


def mask_api_key(key: str) -> str:
    """脱敏展示：保留前 3 位和后 4 位"""
    if len(key) <= 7:
        return "****"
    return f"{key[:3]}{'*' * 4}{key[-4:]}"


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
        cred = credential_repository.create_credential(
            self.db,
            user_id=user_id,
            provider=data.provider,
            api_key_encrypted=encrypted,
            api_base_url=data.api_base_url,
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

        if "api_key" in kwargs and kwargs["api_key"] is not None:
            kwargs["api_key_encrypted"] = encrypt_api_key(kwargs.pop("api_key"))

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
