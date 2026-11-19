from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from pagination import Pagination
from schemas.common import MessageResponse, Page
from schemas.enums import RoomStatusEnum
from schemas.room import (
    RoomCreate,
    RoomResponse,
    RoomStatusUpdate,
    RoomUpdate,
)
from services.auth import get_current_user, require_role
from services.room import (
    create_room,
    deactivate_room,
    get_available_rooms,
    get_room,
    get_rooms,
    update_room,
    update_room_status,
)

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("/get", response_model=Page[RoomResponse])
def list_rooms(
    search: Optional[str] = None,
    status: Optional[RoomStatusEnum] = None,
    floor: Optional[int] = None,
    room_type_id: Optional[int] = None,
    active: Optional[bool] = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    items, total = get_rooms(
        db,
        pagination.page,
        pagination.page_size,
        search=search,
        status=status,
        floor=floor,
        room_type_id=room_type_id,
        active=active,
    )
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/available", response_model=list[RoomResponse])
def list_available_rooms(
    check_in: date = Query(...),
    check_out: date = Query(...),
    guests: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        return get_available_rooms(db, check_in, check_out, guests)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{room_id}", response_model=RoomResponse)
def get_room_route(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        return get_room(room_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/create", response_model=RoomResponse, status_code=201)
def create_room_route(
    data: RoomCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        return create_room(data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/update/{room_id}", response_model=RoomResponse)
def update_room_route(
    room_id: int,
    data: RoomUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        return update_room(room_id, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{room_id}/status", response_model=RoomResponse)
def update_room_status_route(
    room_id: int,
    data: RoomStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        return update_room_status(room_id, data.status, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/delete/{room_id}", response_model=MessageResponse)
def delete_room_route(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin")),
):
    try:
        deactivate_room(room_id, db)
        return MessageResponse(detail="Quarto desativado com sucesso")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
