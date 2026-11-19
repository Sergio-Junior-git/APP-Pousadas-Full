from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from models.pousada_models import (
    Guest,
    HousekeepingTask,
    Reservation,
    Room,
)
from pagination import paginate
from schemas.reservation import ReservationCreate, ReservationUpdate
from validators import ensure_period, enum_value

ACTIVE_RESERVATION_STATUSES = ("Pendente", "Confirmada", "CheckIn")
LOCKED_STATUSES = ("CheckOut", "Cancelada", "NoShow")
CREATABLE_STATUSES = ("Pendente", "Confirmada")


def reservation_query(db: Session):
    return db.query(Reservation).options(
        joinedload(Reservation.guest),
        joinedload(Reservation.room),
        selectinload(Reservation.payments),
        selectinload(Reservation.consumptions),
    )


def get_reservations(
    db: Session,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    room_id: Optional[int] = None,
    guest_id: Optional[int] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    search: Optional[str] = None,
):
    query = reservation_query(db)

    if status:
        query = query.filter(Reservation.status == enum_value(status))
    if room_id is not None:
        query = query.filter(Reservation.room_id == room_id)
    if guest_id is not None:
        query = query.filter(Reservation.guest_id == guest_id)
    if start is not None:
        query = query.filter(Reservation.check_in_date >= start)
    if end is not None:
        query = query.filter(Reservation.check_in_date <= end)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Reservation.code.ilike(like),
                Reservation.guest.has(Guest.full_name.ilike(like)),
            )
        )

    query = query.order_by(
        Reservation.check_in_date.desc(),
        Reservation.id.desc(),
    )
    return paginate(query, page, page_size)


def get_reservation(reservation_id: int, db: Session) -> Reservation:
    reservation = (
        reservation_query(db).filter(Reservation.id == reservation_id).first()
    )
    if not reservation:
        raise ValueError("Reserva não encontrada")
    return reservation


def _resolve_guest(guest_id: int, db: Session) -> Guest:
    guest = (
        db.query(Guest)
        .filter(Guest.id == guest_id, Guest.active.is_(True))
        .first()
    )
    if not guest:
        raise ValueError("Hóspede não encontrado ou inativo")
    return guest


def _resolve_room(room_id: int, db: Session) -> Room:
    room = (
        db.query(Room)
        .options(joinedload(Room.room_type))
        .filter(Room.id == room_id, Room.active.is_(True))
        .first()
    )
    if not room:
        raise ValueError("Quarto não encontrado ou inativo")
    if room.status == "Manutencao":
        raise ValueError("Quarto está em manutenção")
    return room


def _validate_capacity(room: Room, adults: int, children: int) -> None:
    capacity = room.room_type.capacity if room.room_type else 0
    if adults + children > capacity:
        raise ValueError(
            f"Capacidade do quarto {room.number} é {capacity} hóspede(s); "
            f"informado(s): {adults + children}"
        )


def _find_overlap(
    db: Session,
    room_id: int,
    check_in: date,
    check_out: date,
    exclude_id: Optional[int] = None,
) -> Optional[Reservation]:
    query = db.query(Reservation).filter(
        Reservation.room_id == room_id,
        Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
        Reservation.check_in_date < check_out,
        Reservation.check_out_date > check_in,
    )
    if exclude_id is not None:
        query = query.filter(Reservation.id != exclude_id)
    return query.first()


def _generate_code() -> str:
    return f"RES-{date.today():%Y%m%d}-{uuid4().hex[:4].upper()}"


def _value_or_current(payload: dict, key: str, current):
    value = payload.get(key)
    return current if value is None else value


def create_reservation(
    data: ReservationCreate,
    db: Session,
    created_by: Optional[str] = None,
) -> Reservation:
    status = enum_value(data.status)
    if status not in CREATABLE_STATUSES:
        raise ValueError("Reserva deve ser criada como Pendente ou Confirmada")

    _resolve_guest(data.guest_id, db)
    room = _resolve_room(data.room_id, db)
    ensure_period(data.check_in_date, data.check_out_date)
    _validate_capacity(room, data.adults, data.children)

    if _find_overlap(db, room.id, data.check_in_date, data.check_out_date):
        raise ValueError(
            "Quarto indisponível para o período informado. "
            "Verifique as reservas existentes."
        )

    daily_rate = (
        Decimal(data.daily_rate)
        if data.daily_rate is not None
        else Decimal(room.room_type.base_price or 0)
    )
    if daily_rate <= 0:
        raise ValueError("Valor da diária deve ser maior que zero")

    discount = Decimal(data.discount or 0)
    nights = (data.check_out_date - data.check_in_date).days
    if discount > daily_rate * nights:
        raise ValueError("Desconto não pode ser maior que o subtotal da reserva")

    reservation = Reservation(
        code=_generate_code(),
        guest_id=data.guest_id,
        room_id=data.room_id,
        check_in_date=data.check_in_date,
        check_out_date=data.check_out_date,
        adults=data.adults,
        children=data.children,
        status=status,
        daily_rate=daily_rate,
        discount=discount,
        notes=data.notes,
        created_by=created_by,
    )
    db.add(reservation)

    try:
        db.commit()
        db.refresh(reservation)
        return get_reservation(reservation.id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao criar reserva: {exc.orig}")


def update_reservation(
    reservation_id: int,
    data: ReservationUpdate,
    db: Session,
) -> Reservation:
    reservation = get_reservation(reservation_id, db)

    if reservation.status in LOCKED_STATUSES:
        raise ValueError("Reserva não pode ser alterada neste status")

    payload = data.model_dump(exclude_unset=True)

    if reservation.status == "CheckIn" and set(payload) - {"notes"}:
        raise ValueError(
            "Reserva em check-in permite alterar apenas as observações"
        )

    new_room_id = _value_or_current(payload, "room_id", reservation.room_id)
    new_check_in = _value_or_current(
        payload, "check_in_date", reservation.check_in_date
    )
    new_check_out = _value_or_current(
        payload, "check_out_date", reservation.check_out_date
    )
    new_adults = _value_or_current(payload, "adults", reservation.adults)
    new_children = _value_or_current(payload, "children", reservation.children)

    ensure_period(new_check_in, new_check_out)

    room = _resolve_room(new_room_id, db)
    _validate_capacity(room, new_adults, new_children)

    if _find_overlap(
        db,
        new_room_id,
        new_check_in,
        new_check_out,
        exclude_id=reservation_id,
    ):
        raise ValueError("Quarto indisponível para o período informado")

    if "guest_id" in payload and payload["guest_id"] is not None:
        _resolve_guest(payload["guest_id"], db)
        reservation.guest_id = payload["guest_id"]

    if "status" in payload and payload["status"] is not None:
        new_status = enum_value(payload["status"])
        if new_status in ("CheckIn", "CheckOut"):
            raise ValueError(
                "Use os endpoints de check-in/check-out para alterar este status"
            )
        reservation.status = new_status

    reservation.room_id = new_room_id
    reservation.check_in_date = new_check_in
    reservation.check_out_date = new_check_out
    reservation.adults = new_adults
    reservation.children = new_children

    if "daily_rate" in payload and payload["daily_rate"] is not None:
        if payload["daily_rate"] <= 0:
            raise ValueError("Valor da diária deve ser maior que zero")
        reservation.daily_rate = Decimal(payload["daily_rate"])

    if "discount" in payload and payload["discount"] is not None:
        reservation.discount = Decimal(payload["discount"])

    if "notes" in payload:
        reservation.notes = payload["notes"]

    nights = (reservation.check_out_date - reservation.check_in_date).days
    if reservation.discount > reservation.daily_rate * nights:
        raise ValueError("Desconto não pode ser maior que o subtotal da reserva")

    try:
        db.commit()
        return get_reservation(reservation_id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao atualizar reserva: {exc.orig}")


def checkin_reservation(
    reservation_id: int,
    db: Session,
    updated_by: Optional[str] = None,
) -> Reservation:
    reservation = get_reservation(reservation_id, db)

    if reservation.status not in ("Pendente", "Confirmada"):
        raise ValueError("Somente reservas pendentes ou confirmadas podem fazer check-in")

    room = reservation.room
    if not room:
        raise ValueError("Quarto da reserva não encontrado")
    if room.status == "Manutencao":
        raise ValueError("Quarto está em manutenção")

    another_stay = (
        db.query(Reservation)
        .filter(
            Reservation.room_id == room.id,
            Reservation.status == "CheckIn",
            Reservation.id != reservation.id,
        )
        .first()
    )
    if another_stay:
        raise ValueError("Quarto já está ocupado por outra reserva")

    reservation.status = "CheckIn"
    room.status = "Ocupado"

    try:
        db.commit()
        return get_reservation(reservation_id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao realizar check-in: {exc.orig}")


def checkout_reservation(
    reservation_id: int,
    db: Session,
    force: bool = False,
    notes: Optional[str] = None,
    updated_by: Optional[str] = None,
) -> Reservation:
    reservation = get_reservation(reservation_id, db)

    if reservation.status != "CheckIn":
        raise ValueError("Somente reservas em check-in podem fazer check-out")

    if reservation.balance_due > 0 and not force:
        raise ValueError(
            f"Existe saldo pendente de R$ {reservation.balance_due:.2f}. "
            "Registre o pagamento ou use force=true para finalizar mesmo assim."
        )

    room = reservation.room
    reservation.status = "CheckOut"

    if notes:
        reservation.notes = (
            f"{reservation.notes}\n{notes}" if reservation.notes else notes
        )

    if room:
        room.status = "Limpeza"

        existing_task = (
            db.query(HousekeepingTask)
            .filter(
                HousekeepingTask.room_id == room.id,
                HousekeepingTask.status.in_(("Pendente", "EmAndamento")),
            )
            .first()
        )
        if not existing_task:
            db.add(
                HousekeepingTask(
                    room_id=room.id,
                    status="Pendente",
                    priority="Alta",
                    notes=f"Limpeza pós check-out da reserva {reservation.code}",
                    scheduled_for=date.today(),
                    created_by=updated_by,
                )
            )

    try:
        db.commit()
        return get_reservation(reservation_id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao realizar check-out: {exc.orig}")


def cancel_reservation(
    reservation_id: int,
    db: Session,
    reason: Optional[str] = None,
    updated_by: Optional[str] = None,
) -> Reservation:
    reservation = get_reservation(reservation_id, db)

    if reservation.status not in ("Pendente", "Confirmada"):
        raise ValueError("Somente reservas pendentes ou confirmadas podem ser canceladas")

    reservation.status = "Cancelada"
    if reason:
        reservation.notes = (
            f"{reservation.notes}\nCancelamento: {reason}"
            if reservation.notes
            else f"Cancelamento: {reason}"
        )

    try:
        db.commit()
        return get_reservation(reservation_id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao cancelar reserva: {exc.orig}")


def delete_reservation(reservation_id: int, db: Session) -> None:
    reservation = get_reservation(reservation_id, db)

    if reservation.status == "CheckIn":
        raise ValueError("Faça o check-out antes de excluir a reserva")
    if reservation.status == "CheckOut":
        raise ValueError("Reserva finalizada não pode ser excluída")

    reservation.status = "Cancelada"

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao excluir reserva: {exc.orig}")


def get_arrivals_by_date(db: Session, day: date):
    return (
        reservation_query(db)
        .filter(
            Reservation.check_in_date == day,
            Reservation.status.in_(("Pendente", "Confirmada")),
        )
        .order_by(Reservation.code.asc())
        .all()
    )


def get_departures_by_date(db: Session, day: date):
    return (
        reservation_query(db)
        .filter(
            Reservation.check_out_date == day,
            Reservation.status == "CheckIn",
        )
        .order_by(Reservation.code.asc())
        .all()
    )
