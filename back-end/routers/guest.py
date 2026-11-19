from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pagination import Pagination
from schemas.common import MessageResponse, Page
from schemas.guest import GuestCreate, GuestResponse, GuestUpdate
from services.auth import require_role
from services.guest import (
    create_guest,
    deactivate_guest,
    get_guest,
    get_guest_by_cpf,
    get_guests,
    update_guest,
)

router = APIRouter(prefix="/guests", tags=["Guests"])

READ_ROLES = ("Admin", "Gerente", "Recepcionista")
WRITE_ROLES = ("Admin", "Gerente", "Recepcionista")


@router.get("/get", response_model=Page[GuestResponse])
def list_guests(
    search: Optional[str] = None,
    active: Optional[bool] = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*READ_ROLES)),
):
    items, total = get_guests(
        db,
        pagination.page,
        pagination.page_size,
        search=search,
        active=active,
    )
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/bycpf/{cpf}", response_model=GuestResponse)
def get_guest_by_cpf_route(
    cpf: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*READ_ROLES)),
):
    try:
        return get_guest_by_cpf(cpf, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{guest_id}", response_model=GuestResponse)
def get_guest_route(
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*READ_ROLES)),
):
    try:
        return get_guest(guest_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/create", response_model=GuestResponse, status_code=201)
def create_guest_route(
    data: GuestCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
):
    try:
        return create_guest(data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/update/{guest_id}", response_model=GuestResponse)
def update_guest_route(
    guest_id: int,
    data: GuestUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
):
    try:
        return update_guest(guest_id, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/delete/{guest_id}", response_model=MessageResponse)
def delete_guest_route(
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        deactivate_guest(guest_id, db)
        return MessageResponse(detail="Hóspede desativado com sucesso")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
