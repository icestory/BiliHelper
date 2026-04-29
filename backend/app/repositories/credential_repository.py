from sqlalchemy.orm import Session

from app.models.user import ApiCredential


def get_credentials_by_user(db: Session, user_id: int) -> list[ApiCredential]:
    return db.query(ApiCredential).filter(ApiCredential.user_id == user_id).all()


def get_credential_by_id(db: Session, credential_id: int) -> ApiCredential | None:
    return db.query(ApiCredential).filter(ApiCredential.id == credential_id).first()


def get_default_credential(db: Session, user_id: int) -> ApiCredential | None:
    return db.query(ApiCredential).filter(
        ApiCredential.user_id == user_id,
        ApiCredential.is_default == True,  # noqa: E712
    ).first()


def create_credential(
    db: Session,
    user_id: int,
    provider: str,
    api_key_encrypted: str,
    api_base_url: str | None,
    default_model: str | None,
    default_asr_model: str | None,
    default_embedding_model: str | None,
    is_default: bool,
) -> ApiCredential:
    credential = ApiCredential(
        user_id=user_id,
        provider=provider,
        api_base_url=api_base_url,
        api_key_encrypted=api_key_encrypted,
        default_model=default_model,
        default_asr_model=default_asr_model,
        default_embedding_model=default_embedding_model,
        is_default=is_default,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


def update_credential(db: Session, credential: ApiCredential, **kwargs) -> ApiCredential:
    for key, value in kwargs.items():
        if value is not None:
            setattr(credential, key, value)
    db.commit()
    db.refresh(credential)
    return credential


def delete_credential(db: Session, credential: ApiCredential) -> None:
    db.delete(credential)
    db.commit()


def unset_default_for_user(db: Session, user_id: int) -> None:
    db.query(ApiCredential).filter(
        ApiCredential.user_id == user_id,
        ApiCredential.is_default == True,  # noqa: E712
    ).update({"is_default": False})
