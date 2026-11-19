from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pagination import Pagination
from schemas.common import MessageResponse, Page
from schemas.enums import PaymentStatusEnum
from schemas.payment import (
    PaymentCreate,
    PaymentRefundRequest,
    PaymentResponse,
    PaymentUpdate,
)
from services.auth import require_role
from services.payment import (
    create_payment,
    delete_payment,
    get_payment,
    get_payments,
    refund_payment,
    update_payment,
)

router = APIRouter(prefix="/payments", tags=["Payments"])

ROLES = ("Admin", "Gerente", "Recepcionista")


@router.get("/get", response_model=Page[PaymentResponse])
def list_payments(
    reservation_id: Optional[int] = None,
    status: Optional[PaymentStatusEnum] = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*ROLES)),
):
    items, total = get_payments(
        db,
        pagination.page,
        pagination.page_size,
        reservation_id=reservation_id,
        status=status,
    )
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment_route(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*ROLES)),
):
    try:
        return get_payment(payment_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/create", response_model=PaymentResponse, status_code=201)
def create_payment_route(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*ROLES)),
):
    try:
        return create_payment(data, db, created_by=current_user["login"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/update/{payment_id}", response_model=PaymentResponse)
def update_payment_route(
    payment_id: int,
    data: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*ROLES)),
):
    try:
        return update_payment(payment_id, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
def refund_payment_route(
    payment_id: int,
    data: PaymentRefundRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        return refund_payment(payment_id, data.notes, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/delete/{payment_id}", response_model=MessageResponse)
def delete_payment_route(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        delete_payment(payment_id, db)
        return MessageResponse(detail="Pagamento excluído com sucesso")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
