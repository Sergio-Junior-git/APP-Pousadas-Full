from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pagination import Pagination
from schemas.common import MessageResponse, Page
from schemas.room_type import RoomTypeCreate, RoomTypeResponse, RoomTypeUpdate
from services.auth import get_current_user, require_role
from services.room_type import (
    create_room_type,
    deactivate_room_type,
    get_room_type,
    get_room_types,
    update_room_type,
)

router = APIRouter(prefix="/room-types", tags=["Room Types"])


@router.get("/get", response_model=Page[RoomTypeResponse])
def list_room_types(
    search: Optional[str] = None,
    active: Optional[bool] = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    items, total = get_room_types(
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


@router.get("/{room_type_id}", response_model=RoomTypeResponse)
def get_room_type_route(
    room_type_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        return get_room_type(room_type_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/create", response_model=RoomTypeResponse, status_code=201)
def create_room_type_route(
    data: RoomTypeCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        return create_room_type(data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/update/{room_type_id}", response_model=RoomTypeResponse)
def update_room_type_route(
    room_type_id: int,
    data: RoomTypeUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        return update_room_type(room_type_id, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/delete/{room_type_id}", response_model=MessageResponse)
def delete_room_type_route(
    room_type_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin")),
):
    try:
        deactivate_room_type(room_type_id, db)
        return MessageResponse(detail="Tipo de quarto desativado com sucesso")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
