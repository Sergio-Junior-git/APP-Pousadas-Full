from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from schemas.enums import MaintenanceStatusEnum, PriorityEnum
from validators import validate_name


class MaintenanceBase(BaseModel):
    room_id: int
    assigned_to_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    priority: PriorityEnum = PriorityEnum.media

    @field_validator("title")
    @classmethod
    def validate_title_field(cls, value: str) -> str:
        return validate_name(value, field="Título", min_length=3)


class MaintenanceCreate(MaintenanceBase):
    pass


class MaintenanceUpdate(BaseModel):
    room_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[PriorityEnum] = None

    @field_validator("title")
    @classmethod
    def validate_title_field(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return validate_name(value, field="Título", min_length=3)


class MaintenanceResolveRequest(BaseModel):
    notes: Optional[str] = None


class MaintenanceResponse(BaseModel):
    id: int
    room_id: int
    room_number: Optional[str] = None
    reported_by: Optional[str] = None
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: MaintenanceStatusEnum
    priority: PriorityEnum
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
