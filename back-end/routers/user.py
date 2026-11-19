from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pagination import Pagination
from schemas.common import MessageResponse, Page
from schemas.enums import RoleEnum
from schemas.user import UserCreate, UserResponse, UserUpdate
from services.auth import require_role
from services.user import (
    create_user,
    deactivate_user,
    get_user,
    get_users,
    toggle_user_active,
    update_user,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/get", response_model=Page[UserResponse])
def list_users(
    search: Optional[str] = None,
    role: Optional[RoleEnum] = None,
    active: Optional[bool] = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    items, total = get_users(
        db,
        pagination.page,
        pagination.page_size,
        search=search,
        role=role,
        active=active,
    )
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user_route(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        return get_user(user_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/create", response_model=UserResponse, status_code=201)
def create_user_route(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin")),
):
    try:
        return create_user(data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/update/{user_id}", response_model=UserResponse)
def update_user_route(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin")),
):
    try:
        return update_user(user_id, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{user_id}/toggle-active", response_model=UserResponse)
def toggle_user_active_route(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin")),
):
    try:
        return toggle_user_active(user_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/delete/{user_id}", response_model=MessageResponse)
def delete_user_route(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin")),
):
    try:
        deactivate_user(user_id, db)
        return MessageResponse(detail="Usuário desativado com sucesso")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
