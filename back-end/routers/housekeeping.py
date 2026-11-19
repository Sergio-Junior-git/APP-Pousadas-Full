from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pagination import Pagination
from schemas.common import MessageResponse, Page
from schemas.enums import HousekeepingStatusEnum
from schemas.housekeeping import (
    HousekeepingCreate,
    HousekeepingResponse,
    HousekeepingUpdate,
)
from services.auth import get_current_user, require_role
from services.housekeeping import (
    complete_task,
    create_task,
    delete_task,
    get_task,
    get_tasks,
    start_task,
    update_task,
)

router = APIRouter(prefix="/housekeeping", tags=["Housekeeping"])

WRITE_ROLES = ("Admin", "Gerente", "Camareira")


@router.get("/get", response_model=Page[HousekeepingResponse])
def list_tasks(
    status: Optional[HousekeepingStatusEnum] = None,
    room_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    items, total = get_tasks(
        db,
        pagination.page,
        pagination.page_size,
        status=status,
        room_id=room_id,
        assigned_to_id=assigned_to_id,
    )
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{task_id}", response_model=HousekeepingResponse)
def get_task_route(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        return get_task(task_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/create", response_model=HousekeepingResponse, status_code=201)
def create_task_route(
    data: HousekeepingCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
):
    try:
        return create_task(data, db, created_by=current_user["login"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/update/{task_id}", response_model=HousekeepingResponse)
def update_task_route(
    task_id: int,
    data: HousekeepingUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
):
    try:
        return update_task(task_id, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{task_id}/start", response_model=HousekeepingResponse)
def start_task_route(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
):
    try:
        return start_task(task_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{task_id}/complete", response_model=HousekeepingResponse)
def complete_task_route(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
):
    try:
        return complete_task(task_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/delete/{task_id}", response_model=MessageResponse)
def delete_task_route(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        delete_task(task_id, db)
        return MessageResponse(detail="Tarefa de governança excluída com sucesso")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
