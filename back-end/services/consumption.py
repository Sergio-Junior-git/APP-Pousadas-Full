from decimal import Decimal
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.pousada_models import Consumption, Reservation
from pagination import paginate
from schemas.consumption import ConsumptionCreate, ConsumptionUpdate


def get_consumptions(
    db: Session,
    page: int,
    page_size: int,
    reservation_id: Optional[int] = None,
):
    query = db.query(Consumption)

    if reservation_id is not None:
        query = query.filter(Consumption.reservation_id == reservation_id)

    query = query.order_by(Consumption.created_at.desc(), Consumption.id.desc())
    return paginate(query, page, page_size)


def get_consumption(consumption_id: int, db: Session) -> Consumption:
    consumption = db.query(Consumption).filter(Consumption.id == consumption_id).first()
    if not consumption:
        raise ValueError("Consumo não encontrado")
    return consumption


def _resolve_reservation(reservation_id: int, db: Session) -> Reservation:
    reservation = (
        db.query(Reservation).filter(Reservation.id == reservation_id).first()
    )
    if not reservation:
        raise ValueError("Reserva não encontrada")
    return reservation


def create_consumption(
    data: ConsumptionCreate,
    db: Session,
    created_by: Optional[str] = None,
) -> Consumption:
    reservation = _resolve_reservation(data.reservation_id, db)
    if reservation.status in ("CheckOut", "Cancelada", "NoShow"):
        raise ValueError("Não é possível lançar consumo nesta reserva")

    total = Decimal(data.quantity) * Decimal(data.unit_price)

    consumption = Consumption(
        reservation_id=data.reservation_id,
        description=data.description,
        quantity=data.quantity,
        unit_price=Decimal(data.unit_price),
        total=total,
        created_by=created_by,
    )
    db.add(consumption)

    try:
        db.commit()
        db.refresh(consumption)
        return consumption
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao lançar consumo: {exc.orig}")


def update_consumption(
    consumption_id: int,
    data: ConsumptionUpdate,
    db: Session,
) -> Consumption:
    consumption = get_consumption(consumption_id, db)
    payload = data.model_dump(exclude_unset=True)

    if "description" in payload and payload["description"] is not None:
        consumption.description = payload["description"]
    if "quantity" in payload and payload["quantity"] is not None:
        consumption.quantity = payload["quantity"]
    if "unit_price" in payload and payload["unit_price"] is not None:
        consumption.unit_price = Decimal(payload["unit_price"])

    consumption.total = Decimal(consumption.quantity) * Decimal(consumption.unit_price)

    try:
        db.commit()
        db.refresh(consumption)
        return consumption
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao atualizar consumo: {exc.orig}")


def delete_consumption(consumption_id: int, db: Session) -> None:
    consumption = get_consumption(consumption_id, db)
    db.delete(consumption)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao excluir consumo: {exc.orig}")
