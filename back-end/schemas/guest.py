from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from validators import normalize_cpf, validate_email, validate_name


class GuestBase(BaseModel):
    full_name: str
    cpf: str
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    notes: Optional[str] = None
    active: bool = True

    @field_validator("full_name")
    @classmethod
    def validate_name_field(cls, value: str) -> str:
        return validate_name(value, field="Nome do hóspede")

    @field_validator("cpf")
    @classmethod
    def validate_cpf_field(cls, value: str) -> str:
        return normalize_cpf(value)

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        return validate_email(value)

    @field_validator("state")
    @classmethod
    def validate_state_field(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        cleaned = value.strip().upper()
        if len(cleaned) != 2:
            raise ValueError("UF deve conter 2 caracteres")
        return cleaned


class GuestCreate(GuestBase):
    pass


class GuestUpdate(BaseModel):
    full_name: Optional[str] = None
    cpf: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None

    @field_validator("full_name")
    @classmethod
    def validate_name_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return validate_name(value, field="Nome do hóspede")

    @field_validator("cpf")
    @classmethod
    def validate_cpf_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return normalize_cpf(value)

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        return validate_email(value)

    @field_validator("state")
    @classmethod
    def validate_state_field(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        cleaned = value.strip().upper()
        if len(cleaned) != 2:
            raise ValueError("UF deve conter 2 caracteres")
        return cleaned


class GuestSummary(BaseModel):
    id: int
    full_name: str
    cpf: str
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GuestResponse(GuestBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
