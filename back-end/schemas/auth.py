from pydantic import BaseModel

from schemas.enums import RoleEnum


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    id: int
    name: str
    login: str
    role: RoleEnum
    token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
