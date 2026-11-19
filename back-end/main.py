from config import app
from database import Base, engine
import models.pousada_models  # noqa: F401
from routers import (
    auth,
    consumption,
    guest,
    housekeeping,
    maintenance,
    mobile,
    payment,
    reports,
    reservation,
    room,
    room_type,
    user,
)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(room_type.router)
app.include_router(room.router)
app.include_router(guest.router)
app.include_router(reservation.router)
app.include_router(payment.router)
app.include_router(consumption.router)
app.include_router(housekeeping.router)
app.include_router(maintenance.router)
app.include_router(reports.router)
app.include_router(mobile.router)


@app.get("/", tags=["Health"])
def home():
    return {"message": "Pousada API funcionando", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


Base.metadata.create_all(bind=engine)
