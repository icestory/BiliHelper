from pydantic import BaseModel, field_validator


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


# ============ B 站 Cookie 凭证 ============

class BilibiliCredentialCreate(BaseModel):
    """B 站 Cookie 配置 — 三个关键值均从浏览器 Cookie 中获取"""
    sessdata: str  # SESSDATA，B 站登录会话令牌
    bili_jct: str   # bili_jct，CSRF Token
    buvid3: str | None = None  # buvid3，设备标识符（可选）
    enabled: bool = True

    @field_validator("sessdata")
    @classmethod
    def sessdata_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("SESSDATA 不能为空")
        return v.strip()

    @field_validator("bili_jct")
    @classmethod
    def bili_jct_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("bili_jct 不能为空")
        return v.strip()

    @field_validator("buvid3")
    @classmethod
    def buvid3_strip(cls, v: str | None) -> str | None:
        return v.strip() if v else None


class BilibiliCredentialUpdate(BaseModel):
    """部分更新 — 所有字段可选"""
    sessdata: str | None = None
    bili_jct: str | None = None
    buvid3: str | None = None
    enabled: bool | None = None

    @field_validator("sessdata")
    @classmethod
    def sessdata_not_empty(cls, v: str | None) -> str | None:
        return v.strip() if v else None

    @field_validator("bili_jct")
    @classmethod
    def bili_jct_not_empty(cls, v: str | None) -> str | None:
        return v.strip() if v else None

    @field_validator("buvid3")
    @classmethod
    def buvid3_strip(cls, v: str | None) -> str | None:
        return v.strip() if v else None


class BilibiliCredentialResponse(BaseModel):
    id: int
    sessdata_masked: str  # 脱敏展示，仅显示前后各 4 位
    bili_jct_masked: str
    buvid3_masked: str | None = None
    enabled: bool
    updated_at: str

    model_config = {"from_attributes": True}
