from pydantic import BaseModel


class ApiCredentialCreate(BaseModel):
    provider: str
    api_base_url: str | None = None
    api_key: str
    default_model: str | None = None
    default_asr_model: str | None = None
    default_embedding_model: str | None = None
    is_default: bool = False


class ApiCredentialUpdate(BaseModel):
    provider: str | None = None
    api_base_url: str | None = None
    api_key: str | None = None
    default_model: str | None = None
    default_asr_model: str | None = None
    default_embedding_model: str | None = None
    is_default: bool | None = None


class ApiCredentialResponse(BaseModel):
    id: int
    provider: str
    api_base_url: str | None = None
    api_key_masked: str  # 脱敏展示，如 sk-****abcd
    default_model: str | None = None
    default_asr_model: str | None = None
    default_embedding_model: str | None = None
    is_default: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
