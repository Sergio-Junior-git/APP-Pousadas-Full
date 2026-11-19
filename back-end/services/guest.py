from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.pousada_models import Guest
from pagination import paginate
from schemas.guest import GuestCreate, GuestUpdate
from validators import validate_name


def get_guests(
    db: Session,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    active: Optional[bool] = None,
):
    query = db.query(Guest)

    if search:
        cleaned = search.strip()
        like = f"%{cleaned}%"
        digits = "".join(char for char in cleaned if char.isdigit())
        filters = [Guest.full_name.ilike(like), Guest.email.ilike(like)]
        if digits:
            filters.append(Guest.cpf.ilike(f"%{digits}%"))
        query = query.filter(or_(*filters))
    if active is not None:
        query = query.filter(Guest.active == active)

    query = query.order_by(Guest.full_name.asc())
    return paginate(query, page, page_size)


def get_guest(guest_id: int, db: Session) -> Guest:
    guest = db.query(Guest).filter(Guest.id == guest_id).first()
    if not guest:
        raise ValueError("Hóspede não encontrado")
    return guest


def get_guest_by_cpf(cpf: str, db: Session) -> Guest:
    guest = db.query(Guest).filter(Guest.cpf == cpf).first()
    if not guest:
        raise ValueError("Hóspede não encontrado")
    return guest


def _cpf_exists(db: Session, cpf: str, exclude_id: Optional[int] = None) -> bool:
    query = db.query(Guest).filter(Guest.cpf == cpf)
    if exclude_id is not None:
        query = query.filter(Guest.id != exclude_id)
    return query.first() is not None


def create_guest(data: GuestCreate, db: Session) -> Guest:
    if _cpf_exists(db, data.cpf):
        raise ValueError("CPF já cadastrado")

    guest = Guest(
        full_name=validate_name(data.full_name, field="Nome do hóspede"),
        cpf=data.cpf,
        email=data.email,
        phone=data.phone,
        birth_date=data.birth_date,
        address=data.address,
        city=data.city,
        state=data.state,
        zip_code=data.zip_code,
        notes=data.notes,
        active=data.active,
    )
    db.add(guest)

    try:
        db.commit()
        db.refresh(guest)
        return guest
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao criar hóspede: {exc.orig}")


def update_guest(guest_id: int, data: GuestUpdate, db: Session) -> Guest:
    guest = get_guest(guest_id, db)
    payload = data.model_dump(exclude_unset=True)

    if "cpf" in payload and payload["cpf"] is not None:
        if _cpf_exists(db, payload["cpf"], exclude_id=guest_id):
            raise ValueError("CPF já cadastrado")
        guest.cpf = payload["cpf"]

    if "full_name" in payload and payload["full_name"] is not None:
        guest.full_name = validate_name(payload["full_name"], field="Nome do hóspede")

    for field in (
        "email",
        "phone",
        "birth_date",
        "address",
        "city",
        "state",
        "zip_code",
        "notes",
        "active",
    ):
        if field in payload:
            setattr(guest, field, payload[field])

    try:
        db.commit()
        db.refresh(guest)
        return guest
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao atualizar hóspede: {exc.orig}")


def deactivate_guest(guest_id: int, db: Session) -> None:
    guest = get_guest(guest_id, db)
    guest.active = False

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao desativar hóspede: {exc.orig}")
