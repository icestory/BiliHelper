from sqlalchemy.orm import Session

from app.models.user import ApiCredential, BilibiliCredential


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


# ============ B 站 Cookie 凭证 ============

def get_bilibili_credentials_by_user(db: Session, user_id: int) -> list[BilibiliCredential]:
    return db.query(BilibiliCredential).filter(BilibiliCredential.user_id == user_id).all()


def get_bilibili_credential_by_id(db: Session, credential_id: int) -> BilibiliCredential | None:
    return db.query(BilibiliCredential).filter(BilibiliCredential.id == credential_id).first()


def get_enabled_bilibili_credential(db: Session, user_id: int) -> BilibiliCredential | None:
    """获取用户启用的 B 站凭证（当前每个用户只应启用一个）"""
    return db.query(BilibiliCredential).filter(
        BilibiliCredential.user_id == user_id,
        BilibiliCredential.enabled == True,  # noqa: E712
    ).first()


def create_bilibili_credential(
    db: Session,
    user_id: int,
    sessdata_encrypted: str,
    bili_jct_encrypted: str,
    buvid3_encrypted: str | None,
    enabled: bool,
) -> BilibiliCredential:
    cred = BilibiliCredential(
        user_id=user_id,
        sessdata_encrypted=sessdata_encrypted,
        bili_jct_encrypted=bili_jct_encrypted,
        buvid3_encrypted=buvid3_encrypted,
        enabled=enabled,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


def update_bilibili_credential(db: Session, cred: BilibiliCredential, **kwargs) -> BilibiliCredential:
    for key, value in kwargs.items():
        setattr(cred, key, value)
    db.commit()
    db.refresh(cred)
    return cred


def delete_bilibili_credential(db: Session, cred: BilibiliCredential) -> None:
    db.delete(cred)
    db.commit()


def unset_enabled_bilibili_for_user(db: Session, user_id: int) -> None:
    """将用户所有 B 站凭证设为禁用"""
    db.query(BilibiliCredential).filter(
        BilibiliCredential.user_id == user_id,
        BilibiliCredential.enabled == True,  # noqa: E712
    ).update({"enabled": False})
