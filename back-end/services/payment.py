from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.pousada_models import Payment, Reservation
from pagination import paginate
from schemas.payment import PaymentCreate, PaymentUpdate
from validators import enum_value


def get_payments(
    db: Session,
    page: int,
    page_size: int,
    reservation_id: Optional[int] = None,
    status: Optional[str] = None,
):
    query = db.query(Payment)

    if reservation_id is not None:
        query = query.filter(Payment.reservation_id == reservation_id)
    if status:
        query = query.filter(Payment.status == enum_value(status))

    query = query.order_by(Payment.created_at.desc(), Payment.id.desc())
    return paginate(query, page, page_size)


def get_payment(payment_id: int, db: Session) -> Payment:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise ValueError("Pagamento não encontrado")
    return payment


def _resolve_reservation(reservation_id: int, db: Session) -> Reservation:
    reservation = (
        db.query(Reservation).filter(Reservation.id == reservation_id).first()
    )
    if not reservation:
        raise ValueError("Reserva não encontrada")
    return reservation


def create_payment(
    data: PaymentCreate,
    db: Session,
    created_by: Optional[str] = None,
) -> Payment:
    reservation = _resolve_reservation(data.reservation_id, db)
    if reservation.status in ("Cancelada", "NoShow"):
        raise ValueError("Não é possível registrar pagamento em reserva cancelada")

    status_value = enum_value(data.status)
    paid_at = data.paid_at
    if status_value == "Pago" and paid_at is None:
        paid_at = datetime.now()

    payment = Payment(
        reservation_id=data.reservation_id,
        amount=Decimal(data.amount),
        method=enum_value(data.method),
        status=status_value,
        paid_at=paid_at,
        notes=data.notes,
        created_by=created_by,
    )
    db.add(payment)

    try:
        db.commit()
        db.refresh(payment)
        return payment
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao registrar pagamento: {exc.orig}")


def update_payment(
    payment_id: int,
    data: PaymentUpdate,
    db: Session,
) -> Payment:
    payment = get_payment(payment_id, db)
    payload = data.model_dump(exclude_unset=True)

    if "amount" in payload and payload["amount"] is not None:
        payment.amount = Decimal(payload["amount"])
    if "method" in payload and payload["method"] is not None:
        payment.method = enum_value(payload["method"])
    if "status" in payload and payload["status"] is not None:
        payment.status = enum_value(payload["status"])
        if payment.status == "Pago" and payment.paid_at is None:
            payment.paid_at = datetime.now()
    if "paid_at" in payload:
        payment.paid_at = payload["paid_at"]
    if "notes" in payload:
        payment.notes = payload["notes"]

    try:
        db.commit()
        db.refresh(payment)
        return payment
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao atualizar pagamento: {exc.orig}")


def refund_payment(
    payment_id: int,
    notes: Optional[str],
    db: Session,
) -> Payment:
    payment = get_payment(payment_id, db)

    if payment.status != "Pago":
        raise ValueError("Somente pagamentos com status Pago podem ser estornados")

    payment.status = "Estornado"
    if notes:
        payment.notes = f"{payment.notes}\nEstorno: {notes}" if payment.notes else f"Estorno: {notes}"

    try:
        db.commit()
        db.refresh(payment)
        return payment
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao estornar pagamento: {exc.orig}")


def delete_payment(payment_id: int, db: Session) -> None:
    payment = get_payment(payment_id, db)

    if payment.status == "Pago":
        raise ValueError("Estorne o pagamento antes de excluí-lo")

    db.delete(payment)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao excluir pagamento: {exc.orig}")
