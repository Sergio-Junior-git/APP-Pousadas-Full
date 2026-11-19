from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from models.pousada_models import MaintenanceTicket, Room, User
from pagination import paginate
from schemas.maintenance import MaintenanceCreate, MaintenanceUpdate
from validators import enum_value


def get_tickets(
    db: Session,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    room_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
):
    query = db.query(MaintenanceTicket).options(
        joinedload(MaintenanceTicket.room),
        joinedload(MaintenanceTicket.assigned_to),
    )

    if status:
        query = query.filter(MaintenanceTicket.status == enum_value(status))
    if room_id is not None:
        query = query.filter(MaintenanceTicket.room_id == room_id)
    if assigned_to_id is not None:
        query = query.filter(MaintenanceTicket.assigned_to_id == assigned_to_id)

    query = query.order_by(
        MaintenanceTicket.status.asc(),
        MaintenanceTicket.created_at.desc(),
        MaintenanceTicket.id.desc(),
    )
    return paginate(query, page, page_size)


def get_ticket(ticket_id: int, db: Session) -> MaintenanceTicket:
    ticket = (
        db.query(MaintenanceTicket)
        .options(
            joinedload(MaintenanceTicket.room),
            joinedload(MaintenanceTicket.assigned_to),
        )
        .filter(MaintenanceTicket.id == ticket_id)
        .first()
    )
    if not ticket:
        raise ValueError("Chamado de manutenção não encontrado")
    return ticket


def _resolve_room(room_id: int, db: Session) -> Room:
    room = (
        db.query(Room)
        .filter(Room.id == room_id, Room.active.is_(True))
        .first()
    )
    if not room:
        raise ValueError("Quarto não encontrado ou inativo")
    return room


def _resolve_user(user_id: int, db: Session) -> User:
    user = (
        db.query(User)
        .filter(User.id == user_id, User.active.is_(True))
        .first()
    )
    if not user:
        raise ValueError("Responsável não encontrado ou inativo")
    return user


def _has_other_open_ticket(db: Session, room_id: int, exclude_id: Optional[int] = None) -> bool:
    query = db.query(MaintenanceTicket).filter(
        MaintenanceTicket.room_id == room_id,
        MaintenanceTicket.status.in_(("Aberta", "EmAndamento")),
    )
    if exclude_id is not None:
        query = query.filter(MaintenanceTicket.id != exclude_id)
    return query.first() is not None


def create_ticket(
    data: MaintenanceCreate,
    db: Session,
    reported_by: Optional[str] = None,
) -> MaintenanceTicket:
    room = _resolve_room(data.room_id, db)
    if data.assigned_to_id is not None:
        _resolve_user(data.assigned_to_id, db)

    ticket = MaintenanceTicket(
        room_id=data.room_id,
        reported_by=reported_by,
        assigned_to_id=data.assigned_to_id,
        title=data.title,
        description=data.description,
        status="Aberta",
        priority=enum_value(data.priority),
    )
    db.add(ticket)

    if room.status != "Ocupado":
        room.status = "Manutencao"

    try:
        db.commit()
        db.refresh(ticket)
        return get_ticket(ticket.id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao abrir chamado de manutenção: {exc.orig}")


def update_ticket(
    ticket_id: int,
    data: MaintenanceUpdate,
    db: Session,
) -> MaintenanceTicket:
    ticket = get_ticket(ticket_id, db)

    if ticket.status in ("Resolvida", "Cancelada"):
        raise ValueError("Chamado finalizado não pode ser alterado")

    payload = data.model_dump(exclude_unset=True)

    if "room_id" in payload and payload["room_id"] is not None:
        room = _resolve_room(payload["room_id"], db)
        ticket.room_id = payload["room_id"]
        if room.status != "Ocupado":
            room.status = "Manutencao"

    if "assigned_to_id" in payload:
        if payload["assigned_to_id"] is not None:
            _resolve_user(payload["assigned_to_id"], db)
        ticket.assigned_to_id = payload["assigned_to_id"]

    if "title" in payload and payload["title"] is not None:
        ticket.title = payload["title"]
    if "description" in payload:
        ticket.description = payload["description"]
    if "priority" in payload and payload["priority"] is not None:
        ticket.priority = enum_value(payload["priority"])

    try:
        db.commit()
        return get_ticket(ticket_id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao atualizar chamado de manutenção: {exc.orig}")


def resolve_ticket(
    ticket_id: int,
    db: Session,
    notes: Optional[str] = None,
) -> MaintenanceTicket:
    ticket = get_ticket(ticket_id, db)

    if ticket.status in ("Resolvida", "Cancelada"):
        raise ValueError("Chamado já finalizado")

    ticket.status = "Resolvida"
    ticket.resolved_at = datetime.now()
    if notes:
        ticket.description = (
            f"{ticket.description}\nResolução: {notes}"
            if ticket.description
            else f"Resolução: {notes}"
        )

    room = ticket.room
    if (
        room
        and room.status == "Manutencao"
        and not _has_other_open_ticket(db, room.id, exclude_id=ticket_id)
    ):
        room.status = "Disponivel"

    try:
        db.commit()
        return get_ticket(ticket_id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao resolver chamado de manutenção: {exc.orig}")


def cancel_ticket(ticket_id: int, db: Session) -> MaintenanceTicket:
    ticket = get_ticket(ticket_id, db)

    if ticket.status in ("Resolvida", "Cancelada"):
        raise ValueError("Chamado já finalizado")

    ticket.status = "Cancelada"

    room = ticket.room
    if (
        room
        and room.status == "Manutencao"
        and not _has_other_open_ticket(db, room.id, exclude_id=ticket_id)
    ):
        room.status = "Disponivel"

    try:
        db.commit()
        return get_ticket(ticket_id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao cancelar chamado de manutenção: {exc.orig}")


def delete_ticket(ticket_id: int, db: Session) -> None:
    ticket = get_ticket(ticket_id, db)
    db.delete(ticket)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao excluir chamado de manutenção: {exc.orig}")
