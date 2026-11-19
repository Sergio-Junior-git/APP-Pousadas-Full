from datetime import date
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from models.pousada_models import Reservation, Room, RoomType
from pagination import paginate
from schemas.room import RoomCreate, RoomUpdate
from validators import ensure_period, enum_value

ACTIVE_RESERVATION_STATUSES = ("Pendente", "Confirmada", "CheckIn")


def get_rooms(
    db: Session,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    floor: Optional[int] = None,
    room_type_id: Optional[int] = None,
    active: Optional[bool] = None,
):
    query = db.query(Room).options(joinedload(Room.room_type))

    if search:
        like = f"%{search.strip()}%"
        query = query.join(Room.room_type).filter(
            or_(Room.number.ilike(like), RoomType.name.ilike(like))
        )
    if status:
        query = query.filter(Room.status == enum_value(status))
    if floor is not None:
        query = query.filter(Room.floor == floor)
    if room_type_id is not None:
        query = query.filter(Room.room_type_id == room_type_id)
    if active is not None:
        query = query.filter(Room.active == active)

    query = query.order_by(Room.number.asc())
    return paginate(query, page, page_size)


def get_room(room_id: int, db: Session) -> Room:
    room = (
        db.query(Room)
        .options(joinedload(Room.room_type))
        .filter(Room.id == room_id)
        .first()
    )
    if not room:
        raise ValueError("Quarto não encontrado")
    return room


def _resolve_room_type(room_type_id: int, db: Session) -> RoomType:
    room_type = (
        db.query(RoomType)
        .filter(RoomType.id == room_type_id, RoomType.active.is_(True))
        .first()
    )
    if not room_type:
        raise ValueError("Tipo de quarto não encontrado ou inativo")
    return room_type


def _number_exists(db: Session, number: str, exclude_id: Optional[int] = None) -> bool:
    query = db.query(Room).filter(func.lower(Room.number) == number.strip().lower())
    if exclude_id is not None:
        query = query.filter(Room.id != exclude_id)
    return query.first() is not None


def create_room(data: RoomCreate, db: Session) -> Room:
    number = (data.number or "").strip()
    if _number_exists(db, number):
        raise ValueError("Número de quarto já cadastrado")

    _resolve_room_type(data.room_type_id, db)

    room = Room(
        number=number,
        room_type_id=data.room_type_id,
        floor=data.floor,
        status=enum_value(data.status),
        notes=data.notes,
        image_url=data.image_url,
        active=data.active,
    )
    db.add(room)

    try:
        db.commit()
        db.refresh(room)
        return get_room(room.id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao criar quarto: {exc.orig}")


def update_room(room_id: int, data: RoomUpdate, db: Session) -> Room:
    room = get_room(room_id, db)
    payload = data.model_dump(exclude_unset=True)

    if "number" in payload and payload["number"] is not None:
        number = payload["number"].strip()
        if _number_exists(db, number, exclude_id=room_id):
            raise ValueError("Número de quarto já cadastrado")
        room.number = number

    if "room_type_id" in payload and payload["room_type_id"] is not None:
        _resolve_room_type(payload["room_type_id"], db)
        room.room_type_id = payload["room_type_id"]

    if "floor" in payload and payload["floor"] is not None:
        room.floor = payload["floor"]
    if "status" in payload and payload["status"] is not None:
        room.status = enum_value(payload["status"])
    if "notes" in payload:
        room.notes = payload["notes"]
    if "image_url" in payload:
        room.image_url = payload["image_url"]
    if "active" in payload and payload["active"] is not None:
        room.active = payload["active"]

    try:
        db.commit()
        db.refresh(room)
        return get_room(room_id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao atualizar quarto: {exc.orig}")


def update_room_status(room_id: int, status: str, db: Session) -> Room:
    room = get_room(room_id, db)
    new_status = enum_value(status)

    active_stay = (
        db.query(Reservation)
        .filter(
            Reservation.room_id == room_id,
            Reservation.status == "CheckIn",
        )
        .first()
    )

    if active_stay and new_status in ("Disponivel", "Manutencao"):
        raise ValueError("Quarto possui hóspede em estadia; faça o check-out antes")

    room.status = new_status

    try:
        db.commit()
        db.refresh(room)
        return get_room(room_id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao atualizar status do quarto: {exc.orig}")


def get_available_rooms(
    db: Session,
    check_in: date,
    check_out: date,
    guests: int = 1,
):
    ensure_period(check_in, check_out)
    if guests < 1:
        raise ValueError("Número de hóspedes deve ser no mínimo 1")

    overlapping = db.query(Reservation.room_id).filter(
        Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
        Reservation.check_in_date < check_out,
        Reservation.check_out_date > check_in,
    )

    query = (
        db.query(Room)
        .options(joinedload(Room.room_type))
        .join(RoomType)
        .filter(
            Room.active.is_(True),
            Room.status != "Manutencao",
            RoomType.capacity >= guests,
            ~Room.id.in_(overlapping),
        )
        .order_by(Room.number.asc())
    )
    return query.all()


def deactivate_room(room_id: int, db: Session) -> None:
    room = get_room(room_id, db)

    active_stay = (
        db.query(Reservation)
        .filter(
            Reservation.room_id == room_id,
            Reservation.status == "CheckIn",
        )
        .first()
    )
    if active_stay:
        raise ValueError("Quarto ocupado não pode ser desativado")

    room.active = False

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao desativar quarto: {exc.orig}")
