from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from schemas.common import Money
from schemas.enums import PaymentMethodEnum, PaymentStatusEnum


class PaymentBase(BaseModel):
    reservation_id: int
    amount: Money
    method: PaymentMethodEnum
    status: PaymentStatusEnum = PaymentStatusEnum.pago
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount_field(cls, value):
        if value <= 0:
            raise ValueError("Valor do pagamento deve ser maior que zero")
        return value


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    amount: Optional[Money] = None
    method: Optional[PaymentMethodEnum] = None
    status: Optional[PaymentStatusEnum] = None
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount_field(cls, value):
        if value is not None and value <= 0:
            raise ValueError("Valor do pagamento deve ser maior que zero")
        return value


class PaymentRefundRequest(BaseModel):
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    reservation_id: int
    amount: Money
    method: PaymentMethodEnum
    status: PaymentStatusEnum
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
