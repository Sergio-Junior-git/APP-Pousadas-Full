from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from schemas.common import Money
from schemas.enums import ReservationStatusEnum
from schemas.guest import GuestSummary
from schemas.room import RoomSummary


class ReservationBase(BaseModel):
    guest_id: int
    room_id: int
    check_in_date: date
    check_out_date: date
    adults: int = 1
    children: int = 0
    discount: Money = Decimal("0")
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_reservation(self):
        if self.check_out_date <= self.check_in_date:
            raise ValueError("A data de check-out deve ser posterior à data de check-in")
        if self.adults < 1:
            raise ValueError("A reserva deve ter pelo menos 1 adulto")
        if self.children < 0:
            raise ValueError("O número de crianças não pode ser negativo")
        if self.discount < 0:
            raise ValueError("O desconto não pode ser negativo")
        return self


class ReservationCreate(ReservationBase):
    daily_rate: Optional[Money] = None
    status: ReservationStatusEnum = ReservationStatusEnum.pendente


class ReservationUpdate(BaseModel):
    guest_id: Optional[int] = None
    room_id: Optional[int] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    adults: Optional[int] = None
    children: Optional[int] = None
    daily_rate: Optional[Money] = None
    discount: Optional[Money] = None
    notes: Optional[str] = None
    status: Optional[ReservationStatusEnum] = None

    @model_validator(mode="after")
    def validate_reservation(self):
        if (
            self.check_in_date is not None
            and self.check_out_date is not None
            and self.check_out_date <= self.check_in_date
        ):
            raise ValueError("A data de check-out deve ser posterior à data de check-in")
        if self.adults is not None and self.adults < 1:
            raise ValueError("A reserva deve ter pelo menos 1 adulto")
        if self.children is not None and self.children < 0:
            raise ValueError("O número de crianças não pode ser negativo")
        if self.discount is not None and self.discount < 0:
            raise ValueError("O desconto não pode ser negativo")
        return self


class ReservationCheckoutRequest(BaseModel):
    notes: Optional[str] = None
    force: bool = False


class ReservationCancelRequest(BaseModel):
    reason: Optional[str] = None


class ReservationResponse(BaseModel):
    id: int
    code: str
    guest_id: int
    room_id: int
    guest_name: Optional[str] = None
    room_number: Optional[str] = None
    check_in_date: date
    check_out_date: date
    adults: int
    children: int
    nights: int
    daily_rate: Money
    discount: Money
    total_consumptions: Money
    total_amount: Money
    total_paid: Money
    balance_due: Money
    status: ReservationStatusEnum
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    guest: Optional[GuestSummary] = None
    room: Optional[RoomSummary] = None

    model_config = ConfigDict(from_attributes=True)
