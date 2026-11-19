from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.reports import (
    ArrivalsDeparturesResponse,
    OccupancyReportResponse,
    RevenueReportResponse,
    SummaryReportResponse,
)
from services.auth import require_role
from services.reports import (
    get_arrivals_departures,
    get_occupancy,
    get_revenue,
    get_summary,
)

router = APIRouter(prefix="/reports", tags=["Reports"])

READ_ROLES = ("Admin", "Gerente", "Recepcionista")


@router.get("/summary", response_model=SummaryReportResponse)
def summary_report(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*READ_ROLES)),
):
    return get_summary(db)


@router.get("/occupancy", response_model=OccupancyReportResponse)
def occupancy_report(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    today = date.today()
    start_date = start or today.replace(day=1)
    end_date = end or today
    try:
        return get_occupancy(db, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/revenue", response_model=RevenueReportResponse)
def revenue_report(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("Admin", "Gerente")),
):
    today = date.today()
    start_date = start or today.replace(day=1)
    end_date = end or today
    try:
        return get_revenue(db, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/arrivals-departures", response_model=ArrivalsDeparturesResponse)
def arrivals_departures_report(
    day: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*READ_ROLES)),
):
    return get_arrivals_departures(db, day)
