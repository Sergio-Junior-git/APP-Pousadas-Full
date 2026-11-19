from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from schemas.common import Money
from validators import validate_name


class ConsumptionBase(BaseModel):
    reservation_id: int
    description: str
    quantity: int = 1
    unit_price: Money

    @field_validator("description")
    @classmethod
    def validate_description_field(cls, value: str) -> str:
        return validate_name(value, field="Descrição", min_length=2)

    @field_validator("quantity")
    @classmethod
    def validate_quantity_field(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Quantidade deve ser no mínimo 1")
        return value

    @field_validator("unit_price")
    @classmethod
    def validate_unit_price_field(cls, value):
        if value < 0:
            raise ValueError("Valor unitário não pode ser negativo")
        return value


class ConsumptionCreate(ConsumptionBase):
    pass


class ConsumptionUpdate(BaseModel):
    description: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[Money] = None

    @field_validator("description")
    @classmethod
    def validate_description_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return validate_name(value, field="Descrição", min_length=2)

    @field_validator("quantity")
    @classmethod
    def validate_quantity_field(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 1:
            raise ValueError("Quantidade deve ser no mínimo 1")
        return value

    @field_validator("unit_price")
    @classmethod
    def validate_unit_price_field(cls, value):
        if value is not None and value < 0:
            raise ValueError("Valor unitário não pode ser negativo")
        return value


class ConsumptionResponse(BaseModel):
    id: int
    reservation_id: int
    description: str
    quantity: int
    unit_price: Money
    total: Money
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
