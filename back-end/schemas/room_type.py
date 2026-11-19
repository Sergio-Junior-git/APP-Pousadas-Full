from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from schemas.common import Money
from validators import validate_name


class RoomTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    capacity: int
    base_price: Money
    image_url: Optional[str] = None
    active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name_field(cls, value: str) -> str:
        return validate_name(value, field="Nome do tipo de quarto")

    @field_validator("capacity")
    @classmethod
    def validate_capacity_field(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Capacidade deve ser no mínimo 1")
        return value

    @field_validator("base_price")
    @classmethod
    def validate_base_price_field(cls, value):
        if value <= 0:
            raise ValueError("Preço base deve ser maior que zero")
        return value


class RoomTypeCreate(RoomTypeBase):
    pass


class RoomTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    base_price: Optional[Money] = None
    image_url: Optional[str] = None
    active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return validate_name(value, field="Nome do tipo de quarto")

    @field_validator("capacity")
    @classmethod
    def validate_capacity_field(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 1:
            raise ValueError("Capacidade deve ser no mínimo 1")
        return value

    @field_validator("base_price")
    @classmethod
    def validate_base_price_field(cls, value):
        if value is not None and value <= 0:
            raise ValueError("Preço base deve ser maior que zero")
        return value


class RoomTypeResponse(RoomTypeBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
