from pydantic import BaseModel


class UserRegister(BaseModel):
    username: str
    email: str | None = None
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None = None
    status: str

    model_config = {"from_attributes": True}
