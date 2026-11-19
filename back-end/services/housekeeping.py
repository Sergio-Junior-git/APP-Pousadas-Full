from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from models.pousada_models import HousekeepingTask, Room, User
from pagination import paginate
from schemas.housekeeping import HousekeepingCreate, HousekeepingUpdate
from validators import enum_value


def get_tasks(
    db: Session,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    room_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
):
    query = db.query(HousekeepingTask).options(
        joinedload(HousekeepingTask.room),
        joinedload(HousekeepingTask.assigned_to),
    )

    if status:
        query = query.filter(HousekeepingTask.status == enum_value(status))
    if room_id is not None:
        query = query.filter(HousekeepingTask.room_id == room_id)
    if assigned_to_id is not None:
        query = query.filter(HousekeepingTask.assigned_to_id == assigned_to_id)

    query = query.order_by(
        HousekeepingTask.status.asc(),
        HousekeepingTask.created_at.desc(),
        HousekeepingTask.id.desc(),
    )
    return paginate(query, page, page_size)


def get_task(task_id: int, db: Session) -> HousekeepingTask:
    task = (
        db.query(HousekeepingTask)
        .options(
            joinedload(HousekeepingTask.room),
            joinedload(HousekeepingTask.assigned_to),
        )
        .filter(HousekeepingTask.id == task_id)
        .first()
    )
    if not task:
        raise ValueError("Tarefa de governança não encontrada")
    return task


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


def create_task(
    data: HousekeepingCreate,
    db: Session,
    created_by: Optional[str] = None,
) -> HousekeepingTask:
    _resolve_room(data.room_id, db)
    if data.assigned_to_id is not None:
        _resolve_user(data.assigned_to_id, db)

    task = HousekeepingTask(
        room_id=data.room_id,
        assigned_to_id=data.assigned_to_id,
        status="Pendente",
        priority=enum_value(data.priority),
        notes=data.notes,
        scheduled_for=data.scheduled_for,
        created_by=created_by,
    )
    db.add(task)

    try:
        db.commit()
        db.refresh(task)
        return get_task(task.id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao criar tarefa de governança: {exc.orig}")


def update_task(
    task_id: int,
    data: HousekeepingUpdate,
    db: Session,
) -> HousekeepingTask:
    task = get_task(task_id, db)

    if task.status == "Concluida":
        raise ValueError("Tarefa concluída não pode ser alterada")

    payload = data.model_dump(exclude_unset=True)

    if "room_id" in payload and payload["room_id"] is not None:
        _resolve_room(payload["room_id"], db)
        task.room_id = payload["room_id"]
    if "assigned_to_id" in payload:
        if payload["assigned_to_id"] is not None:
            _resolve_user(payload["assigned_to_id"], db)
        task.assigned_to_id = payload["assigned_to_id"]
    if "priority" in payload and payload["priority"] is not None:
        task.priority = enum_value(payload["priority"])
    if "notes" in payload:
        task.notes = payload["notes"]
    if "scheduled_for" in payload:
        task.scheduled_for = payload["scheduled_for"]

    try:
        db.commit()
        return get_task(task_id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao atualizar tarefa de governança: {exc.orig}")


def start_task(task_id: int, db: Session) -> HousekeepingTask:
    task = get_task(task_id, db)

    if task.status != "Pendente":
        raise ValueError("Somente tarefas pendentes podem ser iniciadas")

    task.status = "EmAndamento"
    if task.room and task.room.status not in ("Ocupado", "Manutencao"):
        task.room.status = "Limpeza"

    try:
        db.commit()
        return get_task(task_id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao iniciar tarefa de governança: {exc.orig}")


def complete_task(task_id: int, db: Session) -> HousekeepingTask:
    task = get_task(task_id, db)

    if task.status == "Concluida":
        raise ValueError("Tarefa já concluída")

    task.status = "Concluida"
    task.completed_at = datetime.now()

    if task.room and task.room.status == "Limpeza":
        task.room.status = "Disponivel"

    try:
        db.commit()
        return get_task(task_id, db)
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao concluir tarefa de governança: {exc.orig}")


def delete_task(task_id: int, db: Session) -> None:
    task = get_task(task_id, db)
    db.delete(task)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao excluir tarefa de governança: {exc.orig}")
