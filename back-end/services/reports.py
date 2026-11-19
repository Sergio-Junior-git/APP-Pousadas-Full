from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from models.pousada_models import (
    HousekeepingTask,
    MaintenanceTicket,
    Payment,
    Reservation,
    Room,
)
from schemas.reports import (
    ArrivalsDeparturesResponse,
    MobileBootstrapResponse,
    OccupancyReportItem,
    OccupancyReportResponse,
    RevenueByDayItem,
    RevenueByMethodItem,
    RevenueReportResponse,
    SummaryReportResponse,
)
from services.reservation import get_arrivals_by_date, get_departures_by_date
from validators import ensure_period

ACTIVE_STATUSES = ("Pendente", "Confirmada", "CheckIn")
OPEN_HOUSEKEEPING = ("Pendente", "EmAndamento")
OPEN_MAINTENANCE = ("Aberta", "EmAndamento")


def get_summary(db: Session) -> SummaryReportResponse:
    total_rooms = db.query(Room).filter(Room.active.is_(True)).count()

    counts = dict(
        db.query(Room.status, func.count(Room.id))
        .filter(Room.active.is_(True))
        .group_by(Room.status)
        .all()
    )

    available = counts.get("Disponivel", 0)
    occupied = counts.get("Ocupado", 0)
    cleaning = counts.get("Limpeza", 0)
    maintenance = counts.get("Manutencao", 0)
    occupancy_rate = round(occupied / total_rooms * 100, 1) if total_rooms else 0.0

    today = date.today()

    checkins_today = (
        db.query(Reservation)
        .filter(
            Reservation.check_in_date == today,
            Reservation.status.in_(("Pendente", "Confirmada")),
        )
        .count()
    )
    checkouts_today = (
        db.query(Reservation)
        .filter(
            Reservation.check_out_date == today,
            Reservation.status == "CheckIn",
        )
        .count()
    )
    pending_housekeeping = (
        db.query(HousekeepingTask)
        .filter(HousekeepingTask.status.in_(OPEN_HOUSEKEEPING))
        .count()
    )
    open_maintenance = (
        db.query(MaintenanceTicket)
        .filter(MaintenanceTicket.status.in_(OPEN_MAINTENANCE))
        .count()
    )
    reservations_today = (
        db.query(Reservation)
        .filter(
            Reservation.check_in_date == today,
            Reservation.status.in_(ACTIVE_STATUSES),
        )
        .count()
    )

    month_start = datetime.combine(today.replace(day=1), time.min)
    revenue_month = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.status == "Pago",
            Payment.paid_at.isnot(None),
            Payment.paid_at >= month_start,
        )
        .scalar()
        or Decimal("0")
    )

    return SummaryReportResponse(
        total_rooms=total_rooms,
        rooms_available=available,
        rooms_occupied=occupied,
        rooms_cleaning=cleaning,
        rooms_maintenance=maintenance,
        occupancy_rate=occupancy_rate,
        checkins_today=checkins_today,
        checkouts_today=checkouts_today,
        pending_housekeeping=pending_housekeeping,
        open_maintenance=open_maintenance,
        revenue_month=Decimal(revenue_month),
        reservations_today=reservations_today,
    )


def get_occupancy(db: Session, start: date, end: date) -> OccupancyReportResponse:
    ensure_period(start, end)
    if (end - start).days > 366:
        raise ValueError("Período máximo de 366 dias")

    total_rooms = db.query(Room).filter(Room.active.is_(True)).count()
    items: list[OccupancyReportItem] = []

    current = start
    while current <= end:
        occupied = (
            db.query(func.count(func.distinct(Reservation.room_id)))
            .join(Room, Room.id == Reservation.room_id)
            .filter(
                Room.active.is_(True),
                Reservation.status.in_(ACTIVE_STATUSES),
                Reservation.check_in_date <= current,
                Reservation.check_out_date > current,
            )
            .scalar()
            or 0
        )
        rate = round(occupied / total_rooms * 100, 1) if total_rooms else 0.0
        items.append(
            OccupancyReportItem(
                date=current,
                occupied_rooms=occupied,
                total_rooms=total_rooms,
                occupancy_rate=rate,
            )
        )
        current = date.fromordinal(current.toordinal() + 1)

    return OccupancyReportResponse(start=start, end=end, items=items)


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def get_revenue(
    db: Session,
    start: date,
    end: date,
) -> RevenueReportResponse:
    ensure_period(start, end)
    if (end - start).days > 366:
        raise ValueError("Período máximo de 366 dias")

    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)

    filters = (
        Payment.status == "Pago",
        Payment.paid_at.isnot(None),
        Payment.paid_at >= start_dt,
        Payment.paid_at <= end_dt,
    )

    total = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(*filters)
        .scalar()
        or Decimal("0")
    )

    method_rows = (
        db.query(
            Payment.method,
            func.coalesce(func.sum(Payment.amount), 0),
            func.count(Payment.id),
        )
        .filter(*filters)
        .group_by(Payment.method)
        .order_by(Payment.method.asc())
        .all()
    )

    day_rows = (
        db.query(
            func.date(Payment.paid_at),
            func.coalesce(func.sum(Payment.amount), 0),
        )
        .filter(*filters)
        .group_by(func.date(Payment.paid_at))
        .order_by(func.date(Payment.paid_at).asc())
        .all()
    )

    return RevenueReportResponse(
        start=start,
        end=end,
        total=Decimal(total),
        by_method=[
            RevenueByMethodItem(
                method=method,
                total=Decimal(amount),
                count=count,
            )
            for method, amount, count in method_rows
        ],
        by_day=[
            RevenueByDayItem(date=_as_date(day), total=Decimal(amount))
            for day, amount in day_rows
        ],
    )


def get_arrivals_departures(
    db: Session,
    day: Optional[date] = None,
) -> ArrivalsDeparturesResponse:
    target = day or date.today()
    return ArrivalsDeparturesResponse(
        date=target,
        arrivals=get_arrivals_by_date(db, target),
        departures=get_departures_by_date(db, target),
    )


def get_mobile_bootstrap(db: Session) -> MobileBootstrapResponse:
    today = date.today()

    rooms = (
        db.query(Room)
        .options(joinedload(Room.room_type))
        .filter(Room.active.is_(True))
        .order_by(Room.number.asc())
        .all()
    )

    pending_housekeeping = (
        db.query(HousekeepingTask)
        .options(
            joinedload(HousekeepingTask.room),
            joinedload(HousekeepingTask.assigned_to),
        )
        .filter(HousekeepingTask.status.in_(OPEN_HOUSEKEEPING))
        .order_by(HousekeepingTask.created_at.desc(), HousekeepingTask.id.desc())
        .limit(20)
        .all()
    )

    open_maintenance = (
        db.query(MaintenanceTicket)
        .options(
            joinedload(MaintenanceTicket.room),
            joinedload(MaintenanceTicket.assigned_to),
        )
        .filter(MaintenanceTicket.status.in_(OPEN_MAINTENANCE))
        .order_by(MaintenanceTicket.created_at.desc(), MaintenanceTicket.id.desc())
        .limit(20)
        .all()
    )

    return MobileBootstrapResponse(
        summary=get_summary(db),
        arrivals=get_arrivals_by_date(db, today),
        departures=get_departures_by_date(db, today),
        rooms=rooms,
        pending_housekeeping=pending_housekeeping,
        open_maintenance=open_maintenance,
    )
