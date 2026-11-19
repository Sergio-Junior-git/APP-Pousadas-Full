from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.pousada_models import RoomType
from pagination import paginate
from schemas.room_type import RoomTypeCreate, RoomTypeUpdate
from validators import validate_name


def get_room_types(
    db: Session,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    active: Optional[bool] = None,
):
    query = db.query(RoomType)

    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            or_(RoomType.name.ilike(like), RoomType.description.ilike(like))
        )
    if active is not None:
        query = query.filter(RoomType.active == active)

    query = query.order_by(RoomType.name.asc())
    return paginate(query, page, page_size)


def get_room_type(room_type_id: int, db: Session) -> RoomType:
    room_type = db.query(RoomType).filter(RoomType.id == room_type_id).first()
    if not room_type:
        raise ValueError("Tipo de quarto não encontrado")
    return room_type


def _name_exists(db: Session, name: str, exclude_id: Optional[int] = None) -> bool:
    query = db.query(RoomType).filter(
        func.lower(RoomType.name) == name.strip().lower()
    )
    if exclude_id is not None:
        query = query.filter(RoomType.id != exclude_id)
    return query.first() is not None


def create_room_type(data: RoomTypeCreate, db: Session) -> RoomType:
    name = validate_name(data.name, field="Nome do tipo de quarto")
    if _name_exists(db, name):
        raise ValueError("Tipo de quarto já existe")

    room_type = RoomType(
        name=name,
        description=data.description,
        capacity=data.capacity,
        base_price=data.base_price,
        image_url=data.image_url,
        active=data.active,
    )
    db.add(room_type)

    try:
        db.commit()
        db.refresh(room_type)
        return room_type
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao criar tipo de quarto: {exc.orig}")


def update_room_type(room_type_id: int, data: RoomTypeUpdate, db: Session) -> RoomType:
    room_type = get_room_type(room_type_id, db)
    payload = data.model_dump(exclude_unset=True)

    if "name" in payload and payload["name"] is not None:
        name = validate_name(payload["name"], field="Nome do tipo de quarto")
        if _name_exists(db, name, exclude_id=room_type_id):
            raise ValueError("Tipo de quarto já existe")
        room_type.name = name

    if "description" in payload:
        room_type.description = payload["description"]
    if "capacity" in payload and payload["capacity"] is not None:
        room_type.capacity = payload["capacity"]
    if "base_price" in payload and payload["base_price"] is not None:
        room_type.base_price = payload["base_price"]
    if "image_url" in payload:
        room_type.image_url = payload["image_url"]
    if "active" in payload and payload["active"] is not None:
        room_type.active = payload["active"]

    try:
        db.commit()
        db.refresh(room_type)
        return room_type
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao atualizar tipo de quarto: {exc.orig}")


def deactivate_room_type(room_type_id: int, db: Session) -> None:
    room_type = get_room_type(room_type_id, db)
    room_type.active = False

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao desativar tipo de quarto: {exc.orig}")
