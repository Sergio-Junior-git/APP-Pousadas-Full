from datetime import date

from pydantic import BaseModel

from schemas.common import Money
from schemas.enums import PaymentMethodEnum
from schemas.housekeeping import HousekeepingResponse
from schemas.maintenance import MaintenanceResponse
from schemas.reservation import ReservationResponse
from schemas.room import RoomResponse


class SummaryReportResponse(BaseModel):
    total_rooms: int
    rooms_available: int
    rooms_occupied: int
    rooms_cleaning: int
    rooms_maintenance: int
    occupancy_rate: float
    checkins_today: int
    checkouts_today: int
    pending_housekeeping: int
    open_maintenance: int
    revenue_month: Money
    reservations_today: int


class OccupancyReportItem(BaseModel):
    date: date
    occupied_rooms: int
    total_rooms: int
    occupancy_rate: float


class OccupancyReportResponse(BaseModel):
    start: date
    end: date
    items: list[OccupancyReportItem]


class RevenueByMethodItem(BaseModel):
    method: PaymentMethodEnum
    total: Money
    count: int


class RevenueByDayItem(BaseModel):
    date: date
    total: Money


class RevenueReportResponse(BaseModel):
    start: date
    end: date
    total: Money
    by_method: list[RevenueByMethodItem]
    by_day: list[RevenueByDayItem]


class ArrivalsDeparturesResponse(BaseModel):
    date: date
    arrivals: list[ReservationResponse]
    departures: list[ReservationResponse]


class MobileBootstrapResponse(BaseModel):
    summary: SummaryReportResponse
    arrivals: list[ReservationResponse]
    departures: list[ReservationResponse]
    rooms: list[RoomResponse]
    pending_housekeeping: list[HousekeepingResponse]
    open_maintenance: list[MaintenanceResponse]
