"""LLM Provider 工厂 — 从用户凭据创建 provider 实例"""
from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key
from app.models.user import ApiCredential
from app.integrations.llm import OpenAICompatibleProvider


def create_llm_provider(db: Session, user_id: int) -> tuple[OpenAICompatibleProvider, str, str]:
    """获取用户的默认 LLM provider，返回 (provider, provider_name, model_name)"""
    cred = (
        db.query(ApiCredential)
        .filter(ApiCredential.user_id == user_id, ApiCredential.is_default == True)  # noqa: E712
        .first()
    )
    if not cred:
        cred = db.query(ApiCredential).filter(ApiCredential.user_id == user_id).first()
    if not cred:
        raise ValueError("未配置大模型 API Key，请先在设置中配置")

    api_key = decrypt_api_key(cred.api_key_encrypted)
    provider = OpenAICompatibleProvider(
        api_key=api_key,
        base_url=cred.api_base_url,
        default_model=cred.default_model,
    )
    return provider, cred.provider, cred.default_model or "unknown"
