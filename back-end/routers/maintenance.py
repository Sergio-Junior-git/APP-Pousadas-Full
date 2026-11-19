from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pagination import Pagination
from schemas.common import MessageResponse, Page
from schemas.enums import MaintenanceStatusEnum
from schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceResolveRequest,
    MaintenanceResponse,
    MaintenanceUpdate,
)
from services.auth import get_current_user, require_role
from services.maintenance import (
    cancel_ticket,
    create_ticket,
    delete_ticket,
    get_ticket,
    get_tickets,
    resolve_ticket,
    update_ticket,
)

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])

WRITE_ROLES = ("Admin", "Gerente", "Manutencao", "Recepcionista")


@router.get("/get", response_model=Page[MaintenanceResponse])
def list_tickets(
    status: Optional[MaintenanceStatusEnum] = None,
    room_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    items, total = get_tickets(
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


@router.get("/{ticket_id}", response_model=MaintenanceResponse)
def get_ticket_route(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        return get_ticket(ticket_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/create", response_model=MaintenanceResponse, status_code=201)
def create_ticket_route(
    data: MaintenanceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
):
    try:
        return create_ticket(data, db, reported_by=current_user["login"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/update/{ticket_id}", response_model=MaintenanceResponse)
def update_ticket_route(
    ticket_id: int,
    data: MaintenanceUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente", "Manutencao")),
):
    try:
        return update_ticket(ticket_id, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{ticket_id}/resolve", response_model=MaintenanceResponse)
def resolve_ticket_route(
    ticket_id: int,
    data: MaintenanceResolveRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente", "Manutencao")),
):
    try:
        return resolve_ticket(ticket_id, db, notes=data.notes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{ticket_id}/cancel", response_model=MaintenanceResponse)
def cancel_ticket_route(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        return cancel_ticket(ticket_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/delete/{ticket_id}", response_model=MessageResponse)
def delete_ticket_route(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        delete_ticket(ticket_id, db)
        return MessageResponse(detail="Chamado de manutenção excluído com sucesso")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
