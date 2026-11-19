import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from models.pousada_models import User

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token necessário",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_token(credentials.credentials)


def require_role(*allowed_roles):
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: perfil não autorizado",
            )
        return current_user

    return role_checker


def authenticate(login: str, password: str, db: Session) -> User:
    user = db.query(User).filter(User.login == login).first()
    if not user:
        raise ValueError("Login não encontrado")
    if not user.active:
        raise ValueError("Usuário inativo")
    if not verify_password(password, user.password):
        raise ValueError("Senha incorreta")
    return user


def login_user(login: str, password: str, db: Session) -> dict:
    user = authenticate(login, password, db)
    token = create_access_token(
        {
            "sub": str(user.id),
            "login": user.login,
            "role": user.role,
            "name": user.name,
        }
    )
    return {
        "id": user.id,
        "name": user.name,
        "login": user.login,
        "role": user.role,
        "token": token,
    }


def change_password(
    user_id: int,
    current_password: str,
    new_password: str,
    db: Session,
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("Usuário não encontrado")
    if not verify_password(current_password, user.password):
        raise ValueError("Senha atual incorreta")
    if len(new_password or "") < 6:
        raise ValueError("Nova senha deve conter no mínimo 6 caracteres")

    user.password = hash_password(new_password)

    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as exc:
        db.rollback()
        raise RuntimeError(f"Erro ao alterar senha: {exc}")
