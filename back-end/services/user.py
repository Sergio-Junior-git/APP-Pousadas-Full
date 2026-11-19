from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.pousada_models import User
from pagination import paginate
from schemas.user import UserCreate, UserUpdate
from services.auth import hash_password
from validators import enum_value, validate_name


def get_users(
    db: Session,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    role: Optional[str] = None,
    active: Optional[bool] = None,
):
    query = db.query(User)

    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(like),
                User.login.ilike(like),
                User.email.ilike(like),
            )
        )
    if role:
        query = query.filter(User.role == enum_value(role))
    if active is not None:
        query = query.filter(User.active == active)

    query = query.order_by(User.name.asc())
    return paginate(query, page, page_size)


def get_user(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("Usuário não encontrado")
    return user


def _ensure_not_last_admin(db: Session, user: User, new_active: bool, new_role: str) -> None:
    if user.role != "Admin" or not user.active:
        return

    remains_admin = new_active and new_role == "Admin"
    if remains_admin:
        return

    active_admins = (
        db.query(User)
        .filter(User.role == "Admin", User.active.is_(True))
        .count()
    )
    if active_admins <= 1:
        raise ValueError("Não é possível desativar o último administrador ativo")


def create_user(data: UserCreate, db: Session) -> User:
    if db.query(User).filter(User.login == data.login).first():
        raise ValueError("Login já existe")
    if db.query(User).filter(User.email == data.email).first():
        raise ValueError("E-mail já cadastrado")

    user = User(
        name=validate_name(data.name),
        login=data.login,
        email=data.email,
        phone=data.phone,
        password=hash_password(data.password),
        role=enum_value(data.role),
        active=data.active,
    )
    db.add(user)

    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao criar usuário: {exc.orig}")


def update_user(user_id: int, data: UserUpdate, db: Session) -> User:
    user = get_user(user_id, db)
    payload = data.model_dump(exclude_unset=True)

    new_active = user.active if payload.get("active") is None else payload["active"]
    new_role = (
        user.role if payload.get("role") is None else enum_value(payload["role"])
    )
    _ensure_not_last_admin(db, user, new_active, new_role)

    if "login" in payload and payload["login"] != user.login:
        if db.query(User).filter(User.login == payload["login"], User.id != user_id).first():
            raise ValueError("Login já existe")
        user.login = payload["login"]

    if "email" in payload and payload["email"] != user.email:
        if db.query(User).filter(User.email == payload["email"], User.id != user_id).first():
            raise ValueError("E-mail já cadastrado")
        user.email = payload["email"]

    if "name" in payload and payload["name"] is not None:
        user.name = validate_name(payload["name"])
    if "phone" in payload:
        user.phone = payload["phone"]
    if "role" in payload and payload["role"] is not None:
        user.role = enum_value(payload["role"])
    if "active" in payload and payload["active"] is not None:
        user.active = payload["active"]
    if "password" in payload and payload["password"]:
        user.password = hash_password(payload["password"])

    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao atualizar usuário: {exc.orig}")


def toggle_user_active(user_id: int, db: Session) -> User:
    user = get_user(user_id, db)
    new_active = not user.active
    _ensure_not_last_admin(db, user, new_active, user.role)
    user.active = new_active

    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao alterar status do usuário: {exc.orig}")


def deactivate_user(user_id: int, db: Session) -> None:
    user = get_user(user_id, db)
    _ensure_not_last_admin(db, user, False, user.role)
    user.active = False

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao desativar usuário: {exc.orig}")
