from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from schemas.enums import RoomStatusEnum
from schemas.room_type import RoomTypeResponse


class RoomBase(BaseModel):
    number: str
    room_type_id: int
    floor: int = 0
    status: RoomStatusEnum = RoomStatusEnum.disponivel
    notes: Optional[str] = None
    image_url: Optional[str] = None
    active: bool = True

    @field_validator("number")
    @classmethod
    def validate_number_field(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Número do quarto é obrigatório")
        return cleaned

    @field_validator("floor")
    @classmethod
    def validate_floor_field(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Andar não pode ser negativo")
        return value


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    number: Optional[str] = None
    room_type_id: Optional[int] = None
    floor: Optional[int] = None
    status: Optional[RoomStatusEnum] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    active: Optional[bool] = None

    @field_validator("number")
    @classmethod
    def validate_number_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Número do quarto é obrigatório")
        return cleaned

    @field_validator("floor")
    @classmethod
    def validate_floor_field(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("Andar não pode ser negativo")
        return value


class RoomStatusUpdate(BaseModel):
    status: RoomStatusEnum


class RoomSummary(BaseModel):
    id: int
    number: str
    floor: int
    status: RoomStatusEnum

    model_config = ConfigDict(from_attributes=True)


class RoomResponse(RoomBase):
    id: int
    room_type: Optional[RoomTypeResponse] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
