from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from schemas.enums import HousekeepingStatusEnum, PriorityEnum


class HousekeepingBase(BaseModel):
    room_id: int
    assigned_to_id: Optional[int] = None
    priority: PriorityEnum = PriorityEnum.media
    notes: Optional[str] = None
    scheduled_for: Optional[date] = None


class HousekeepingCreate(HousekeepingBase):
    pass


class HousekeepingUpdate(BaseModel):
    room_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    priority: Optional[PriorityEnum] = None
    notes: Optional[str] = None
    scheduled_for: Optional[date] = None


class HousekeepingStatusUpdate(BaseModel):
    status: HousekeepingStatusEnum


class HousekeepingResponse(BaseModel):
    id: int
    room_id: int
    room_number: Optional[str] = None
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    status: HousekeepingStatusEnum
    priority: PriorityEnum
    notes: Optional[str] = None
    scheduled_for: Optional[date] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
