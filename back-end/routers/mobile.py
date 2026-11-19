from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas.reports import MobileBootstrapResponse
from services.auth import get_current_user
from services.reports import get_mobile_bootstrap

router = APIRouter(prefix="/mobile", tags=["Mobile"])


@router.get("/bootstrap", response_model=MobileBootstrapResponse)
def mobile_bootstrap(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retorna, em uma única chamada, os dados necessários para a home do app."""
    return get_mobile_bootstrap(db)
