from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pagination import Pagination
from schemas.common import MessageResponse, Page
from schemas.consumption import (
    ConsumptionCreate,
    ConsumptionResponse,
    ConsumptionUpdate,
)
from services.auth import require_role
from services.consumption import (
    create_consumption,
    delete_consumption,
    get_consumption,
    get_consumptions,
    update_consumption,
)

router = APIRouter(prefix="/consumptions", tags=["Consumptions"])

ROLES = ("Admin", "Gerente", "Recepcionista")


@router.get("/get", response_model=Page[ConsumptionResponse])
def list_consumptions(
    reservation_id: Optional[int] = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*ROLES)),
):
    items, total = get_consumptions(
        db,
        pagination.page,
        pagination.page_size,
        reservation_id=reservation_id,
    )
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{consumption_id}", response_model=ConsumptionResponse)
def get_consumption_route(
    consumption_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*ROLES)),
):
    try:
        return get_consumption(consumption_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/create", response_model=ConsumptionResponse, status_code=201)
def create_consumption_route(
    data: ConsumptionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*ROLES)),
):
    try:
        return create_consumption(data, db, created_by=current_user["login"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/update/{consumption_id}", response_model=ConsumptionResponse)
def update_consumption_route(
    consumption_id: int,
    data: ConsumptionUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*ROLES)),
):
    try:
        return update_consumption(consumption_id, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/delete/{consumption_id}", response_model=MessageResponse)
def delete_consumption_route(
    consumption_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        delete_consumption(consumption_id, db)
        return MessageResponse(detail="Consumo excluído com sucesso")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
