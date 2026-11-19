from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Pousada API",
    version="1.0.0",
    description=(
        "API para gestão de pousada com foco em aplicativos mobile: "
        "quartos, hóspedes, reservas, check-in/check-out, pagamentos, "
        "consumos, governança, manutenção e relatórios."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)
