import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from database import Base, Session, engine
from models.pousada_models import (
    Consumption,
    Guest,
    HousekeepingTask,
    MaintenanceTicket,
    Payment,
    Reservation,
    Room,
    RoomType,
    User,
)
from services.auth import hash_password

ROOM_TYPES = [
    {
        "name": "Solteiro",
        "description": "Quarto com uma cama de solteiro, ideal para viagens rápidas.",
        "capacity": 1,
        "base_price": Decimal("150.00"),
    },
    {
        "name": "Casal",
        "description": "Quarto com cama de casal e banheiro privativo.",
        "capacity": 2,
        "base_price": Decimal("220.00"),
    },
    {
        "name": "Suíte Master",
        "description": "Suíte ampla com varanda, ar-condicionado e frigobar.",
        "capacity": 4,
        "base_price": Decimal("380.00"),
    },
]

ROOMS = [
    ("101", "Casal", 1),
    ("102", "Casal", 1),
    ("103", "Solteiro", 1),
    ("201", "Suíte Master", 2),
    ("202", "Casal", 2),
    ("203", "Solteiro", 2),
]

GUESTS = [
    {
        "full_name": "Maria Silva",
        "cpf": "52998224725",
        "email": "maria.silva@example.com",
        "phone": "11999990001",
        "city": "São Paulo",
        "state": "SP",
    },
    {
        "full_name": "João Souza",
        "cpf": "11144477735",
        "email": "joao.souza@example.com",
        "phone": "11999990002",
        "city": "Campinas",
        "state": "SP",
    },
    {
        "full_name": "Ana Costa",
        "cpf": "12345678909",
        "email": "ana.costa@example.com",
        "phone": "11999990003",
        "city": "Rio de Janeiro",
        "state": "RJ",
    },
]

RESERVATIONS = [
    {
        "key": "maria",
        "guest": "Maria Silva",
        "room": "101",
        "check_in_offset": -1,
        "check_out_offset": 2,
        "status": "CheckIn",
        "daily_rate": Decimal("220.00"),
        "adults": 2,
        "children": 0,
    },
    {
        "key": "joao",
        "guest": "João Souza",
        "room": "201",
        "check_in_offset": 0,
        "check_out_offset": 3,
        "status": "Confirmada",
        "daily_rate": Decimal("380.00"),
        "adults": 2,
        "children": 0,
    },
    {
        "key": "ana",
        "guest": "Ana Costa",
        "room": "102",
        "check_in_offset": 0,
        "check_out_offset": 1,
        "status": "Pendente",
        "daily_rate": Decimal("220.00"),
        "adults": 1,
        "children": 0,
    },
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = Session()

    try:
        admin_login = os.getenv("ADMIN_LOGIN", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin_name = os.getenv("ADMIN_NAME", "Administrador")

        admin = db.query(User).filter(User.login == admin_login).first()
        if not admin:
            admin = User(
                name=admin_name,
                login=admin_login,
                email="admin@pousada.local",
                password=hash_password(admin_password),
                role="Admin",
                active=True,
            )
            db.add(admin)
            db.flush()
            print(f"Usuário admin criado: {admin_login} / {admin_password}")

        room_types = {}
        for data in ROOM_TYPES:
            room_type = (
                db.query(RoomType).filter(RoomType.name == data["name"]).first()
            )
            if not room_type:
                room_type = RoomType(**data)
                db.add(room_type)
                db.flush()
            room_types[data["name"]] = room_type

        rooms = {}
        for number, type_name, floor in ROOMS:
            room = db.query(Room).filter(Room.number == number).first()
            if not room:
                room = Room(
                    number=number,
                    room_type_id=room_types[type_name].id,
                    floor=floor,
                )
                db.add(room)
                db.flush()
            rooms[number] = room

        guests = {}
        for data in GUESTS:
            guest = db.query(Guest).filter(Guest.cpf == data["cpf"]).first()
            if not guest:
                guest = Guest(**data)
                db.add(guest)
                db.flush()
            guests[data["full_name"]] = guest

        today = date.today()
        reservations = {}

        for data in RESERVATIONS:
            guest = guests[data["guest"]]
            room = rooms[data["room"]]
            check_in = today + timedelta(days=data["check_in_offset"])
            check_out = today + timedelta(days=data["check_out_offset"])

            reservation = (
                db.query(Reservation)
                .filter(
                    Reservation.room_id == room.id,
                    Reservation.check_in_date == check_in,
                )
                .first()
            )
            if not reservation:
                reservation = Reservation(
                    code=f"RES-{check_in:%Y%m%d}-{uuid4().hex[:4].upper()}",
                    guest_id=guest.id,
                    room_id=room.id,
                    check_in_date=check_in,
                    check_out_date=check_out,
                    adults=data["adults"],
                    children=data["children"],
                    status=data["status"],
                    daily_rate=data["daily_rate"],
                    created_by=admin_login,
                )
                db.add(reservation)
                db.flush()

            reservations[data["key"]] = reservation
            if reservation.status == "CheckIn":
                room.status = "Ocupado"

        if "103" in rooms:
            rooms["103"].status = "Limpeza"
        if "203" in rooms:
            rooms["203"].status = "Manutencao"

        maria = reservations["maria"]
        if not db.query(Payment).filter(Payment.reservation_id == maria.id).first():
            db.add(
                Payment(
                    reservation_id=maria.id,
                    amount=Decimal("440.00"),
                    method="Pix",
                    status="Pago",
                    paid_at=datetime.now(),
                    notes="Sinal da reserva",
                    created_by=admin_login,
                )
            )

        joao = reservations["joao"]
        if not db.query(Payment).filter(Payment.reservation_id == joao.id).first():
            db.add(
                Payment(
                    reservation_id=joao.id,
                    amount=Decimal("500.00"),
                    method="CartaoCredito",
                    status="Pago",
                    paid_at=datetime.now(),
                    notes="Pagamento parcial",
                    created_by=admin_login,
                )
            )

        if not db.query(Consumption).filter(Consumption.reservation_id == maria.id).first():
            db.add(
                Consumption(
                    reservation_id=maria.id,
                    description="Frigobar - água e refrigerante",
                    quantity=2,
                    unit_price=Decimal("8.00"),
                    total=Decimal("16.00"),
                    created_by=admin_login,
                )
            )

        room_103 = rooms.get("103")
        if room_103 and not (
            db.query(HousekeepingTask)
            .filter(
                HousekeepingTask.room_id == room_103.id,
                HousekeepingTask.status.in_(("Pendente", "EmAndamento")),
            )
            .first()
        ):
            db.add(
                HousekeepingTask(
                    room_id=room_103.id,
                    status="Pendente",
                    priority="Alta",
                    notes="Limpeza de quarto de solteiro",
                    scheduled_for=today,
                    created_by=admin_login,
                )
            )

        room_203 = rooms.get("203")
        if room_203 and not (
            db.query(MaintenanceTicket)
            .filter(
                MaintenanceTicket.room_id == room_203.id,
                MaintenanceTicket.status.in_(("Aberta", "EmAndamento")),
            )
            .first()
        ):
            db.add(
                MaintenanceTicket(
                    room_id=room_203.id,
                    reported_by=admin_login,
                    title="Ar-condicionado com ruído",
                    description="Hóspede relatou ruído no ar-condicionado.",
                    status="Aberta",
                    priority="Media",
                )
            )

        db.commit()
        print("Seed concluído com sucesso.")
        print(f"Total de quartos: {db.query(Room).count()}")
        print(f"Total de hóspedes: {db.query(Guest).count()}")
        print(f"Total de reservas: {db.query(Reservation).count()}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
