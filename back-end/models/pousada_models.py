from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from database import Base


class RoomType(Base):
    __tablename__ = "room_types"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(120), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    capacity = Column(Integer, nullable=False, default=1)
    base_price = Column(Numeric(10, 2), nullable=False, default=0)
    image_url = Column(String(500), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    rooms = relationship("Room", back_populates="room_type")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    login = Column(String(80), nullable=False, unique=True, index=True)
    email = Column(String(150), nullable=False, unique=True)
    phone = Column(String(30), nullable=True)
    password = Column(String(255), nullable=False)
    role = Column(
        Enum(
            "Admin",
            "Gerente",
            "Recepcionista",
            "Camareira",
            "Manutencao",
            name="user_role_enum",
        ),
        nullable=False,
        default="Recepcionista",
    )
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    housekeeping_tasks = relationship("HousekeepingTask", back_populates="assigned_to")
    maintenance_tickets = relationship("MaintenanceTicket", back_populates="assigned_to")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    number = Column(String(20), nullable=False, unique=True, index=True)
    room_type_id = Column(Integer, ForeignKey("room_types.id"), nullable=False)
    floor = Column(Integer, nullable=False, default=0)
    status = Column(
        Enum(
            "Disponivel",
            "Ocupado",
            "Limpeza",
            "Manutencao",
            "Reservado",
            name="room_status_enum",
        ),
        nullable=False,
        default="Disponivel",
    )
    notes = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    room_type = relationship("RoomType", back_populates="rooms")
    reservations = relationship("Reservation", back_populates="room")
    housekeeping_tasks = relationship("HousekeepingTask", back_populates="room")
    maintenance_tickets = relationship("MaintenanceTicket", back_populates="room")


class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(150), nullable=False)
    cpf = Column(String(14), nullable=False, unique=True, index=True)
    email = Column(String(150), nullable=True)
    phone = Column(String(30), nullable=True)
    birth_date = Column(Date, nullable=True)
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    zip_code = Column(String(10), nullable=True)
    notes = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    reservations = relationship("Reservation", back_populates="guest")


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(30), nullable=False, unique=True, index=True)
    guest_id = Column(Integer, ForeignKey("guests.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    adults = Column(Integer, nullable=False, default=1)
    children = Column(Integer, nullable=False, default=0)
    status = Column(
        Enum(
            "Pendente",
            "Confirmada",
            "CheckIn",
            "CheckOut",
            "Cancelada",
            "NoShow",
            name="reservation_status_enum",
        ),
        nullable=False,
        default="Pendente",
    )
    daily_rate = Column(Numeric(10, 2), nullable=False, default=0)
    discount = Column(Numeric(10, 2), nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_by = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    guest = relationship("Guest", back_populates="reservations")
    room = relationship("Room", back_populates="reservations")
    payments = relationship(
        "Payment", back_populates="reservation", cascade="all, delete-orphan"
    )
    consumptions = relationship(
        "Consumption", back_populates="reservation", cascade="all, delete-orphan"
    )

    @property
    def nights(self) -> int:
        if not self.check_in_date or not self.check_out_date:
            return 0
        return max((self.check_out_date - self.check_in_date).days, 0)

    @property
    def subtotal(self) -> Decimal:
        return (self.daily_rate or Decimal("0")) * self.nights

    @property
    def total_consumptions(self) -> Decimal:
        return sum((item.total or Decimal("0")) for item in self.consumptions)

    @property
    def total_paid(self) -> Decimal:
        return sum(
            (payment.amount or Decimal("0"))
            for payment in self.payments
            if payment.status == "Pago"
        )

    @property
    def total_amount(self) -> Decimal:
        value = self.subtotal + self.total_consumptions - (self.discount or Decimal("0"))
        return max(value, Decimal("0"))

    @property
    def balance_due(self) -> Decimal:
        return max(self.total_amount - self.total_paid, Decimal("0"))

    @property
    def guest_name(self) -> str | None:
        return self.guest.full_name if self.guest else None

    @property
    def room_number(self) -> str | None:
        return self.room.number if self.room else None


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False, default=0)
    method = Column(
        Enum(
            "Dinheiro",
            "Pix",
            "CartaoCredito",
            "CartaoDebito",
            "Transferencia",
            name="payment_method_enum",
        ),
        nullable=False,
    )
    status = Column(
        Enum("Pendente", "Pago", "Estornado", name="payment_status_enum"),
        nullable=False,
        default="Pago",
    )
    paid_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(String(255), nullable=True)
    created_by = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    reservation = relationship("Reservation", back_populates="payments")


class Consumption(Base):
    __tablename__ = "consumptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False)
    description = Column(String(150), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    total = Column(Numeric(10, 2), nullable=False, default=0)
    created_by = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    reservation = relationship("Reservation", back_populates="consumptions")


class HousekeepingTask(Base):
    __tablename__ = "housekeeping_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(
        Enum(
            "Pendente",
            "EmAndamento",
            "Concluida",
            name="housekeeping_status_enum",
        ),
        nullable=False,
        default="Pendente",
    )
    priority = Column(
        Enum("Baixa", "Media", "Alta", name="housekeeping_priority_enum"),
        nullable=False,
        default="Media",
    )
    notes = Column(Text, nullable=True)
    scheduled_for = Column(Date, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    room = relationship("Room", back_populates="housekeeping_tasks")
    assigned_to = relationship("User", back_populates="housekeeping_tasks")

    @property
    def room_number(self) -> str | None:
        return self.room.number if self.room else None

    @property
    def assigned_to_name(self) -> str | None:
        return self.assigned_to.name if self.assigned_to else None


class MaintenanceTicket(Base):
    __tablename__ = "maintenance_tickets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    reported_by = Column(String(120), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(
            "Aberta",
            "EmAndamento",
            "Resolvida",
            "Cancelada",
            name="maintenance_status_enum",
        ),
        nullable=False,
        default="Aberta",
    )
    priority = Column(
        Enum("Baixa", "Media", "Alta", name="maintenance_priority_enum"),
        nullable=False,
        default="Media",
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    room = relationship("Room", back_populates="maintenance_tickets")
    assigned_to = relationship("User", back_populates="maintenance_tickets")

    @property
    def room_number(self) -> str | None:
        return self.room.number if self.room else None

    @property
    def assigned_to_name(self) -> str | None:
        return self.assigned_to.name if self.assigned_to else None
