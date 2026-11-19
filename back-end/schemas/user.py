from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from schemas.enums import RoleEnum
from validators import validate_email, validate_name


class UserBase(BaseModel):
    name: str
    login: str
    email: str
    phone: Optional[str] = None
    role: RoleEnum = RoleEnum.recepcionista
    active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name_field(cls, value: str) -> str:
        return validate_name(value)

    @field_validator("login")
    @classmethod
    def validate_login_field(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if len(cleaned) < 3:
            raise ValueError("Login deve conter no mínimo 3 caracteres")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str) -> str:
        return validate_email(value)


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, value: str) -> str:
        if len(value or "") < 6:
            raise ValueError("Senha deve conter no mínimo 6 caracteres")
        return value


class UserUpdate(BaseModel):
    name: Optional[str] = None
    login: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[RoleEnum] = None
    active: Optional[bool] = None
    password: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return validate_name(value)

    @field_validator("login")
    @classmethod
    def validate_login_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("Login deve conter no mínimo 3 caracteres")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return validate_email(value)

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if len(value) < 6:
            raise ValueError("Senha deve conter no mínimo 6 caracteres")
        return value


class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
