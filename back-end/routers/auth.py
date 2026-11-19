from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse
from schemas.common import MessageResponse
from schemas.user import UserResponse
from services.auth import change_password, get_current_user, login_user
from services.user import get_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    try:
        return login_user(data.login, data.password, db)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@router.get("/me", response_model=UserResponse)
def me(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_user(int(current_user["sub"]), db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/change-password", response_model=MessageResponse)
def change_password_route(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        change_password(
            int(current_user["sub"]),
            data.current_password,
            data.new_password,
            db,
        )
        return MessageResponse(detail="Senha alterada com sucesso")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
