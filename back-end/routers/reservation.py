from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pagination import Pagination
from schemas.common import MessageResponse, Page
from schemas.enums import ReservationStatusEnum
from schemas.reservation import (
    ReservationCancelRequest,
    ReservationCheckoutRequest,
    ReservationCreate,
    ReservationResponse,
    ReservationUpdate,
)
from services.auth import get_current_user, require_role
from services.reservation import (
    cancel_reservation,
    checkin_reservation,
    checkout_reservation,
    create_reservation,
    delete_reservation,
    get_arrivals_by_date,
    get_departures_by_date,
    get_reservation,
    get_reservations,
    update_reservation,
)

router = APIRouter(prefix="/reservations", tags=["Reservations"])

WRITE_ROLES = ("Admin", "Gerente", "Recepcionista")


@router.get("/get", response_model=Page[ReservationResponse])
def list_reservations(
    status: Optional[ReservationStatusEnum] = None,
    room_id: Optional[int] = None,
    guest_id: Optional[int] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    search: Optional[str] = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    items, total = get_reservations(
        db,
        pagination.page,
        pagination.page_size,
        status=status,
        room_id=room_id,
        guest_id=guest_id,
        start=start,
        end=end,
        search=search,
    )
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/today/arrivals", response_model=list[ReservationResponse])
def list_arrivals_today(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return get_arrivals_by_date(db, date.today())


@router.get("/today/departures", response_model=list[ReservationResponse])
def list_departures_today(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return get_departures_by_date(db, date.today())


@router.get("/{reservation_id}", response_model=ReservationResponse)
def get_reservation_route(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        return get_reservation(reservation_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/create", response_model=ReservationResponse, status_code=201)
def create_reservation_route(
    data: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
):
    try:
        return create_reservation(data, db, created_by=current_user["login"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/update/{reservation_id}", response_model=ReservationResponse)
def update_reservation_route(
    reservation_id: int,
    data: ReservationUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
):
    try:
        return update_reservation(reservation_id, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{reservation_id}/checkin", response_model=ReservationResponse)
def checkin_route(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
):
    try:
        return checkin_reservation(
            reservation_id,
            db,
            updated_by=current_user["login"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{reservation_id}/checkout", response_model=ReservationResponse)
def checkout_route(
    reservation_id: int,
    data: ReservationCheckoutRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
):
    try:
        return checkout_reservation(
            reservation_id,
            db,
            force=data.force,
            notes=data.notes,
            updated_by=current_user["login"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
def cancel_route(
    reservation_id: int,
    data: ReservationCancelRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
):
    try:
        return cancel_reservation(
            reservation_id,
            db,
            reason=data.reason,
            updated_by=current_user["login"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/delete/{reservation_id}", response_model=MessageResponse)
def delete_reservation_route(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    try:
        delete_reservation(reservation_id, db)
        return MessageResponse(detail="Reserva cancelada com sucesso")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
