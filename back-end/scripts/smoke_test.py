"""Teste de fumaça contra uma API em execução.

Execute contra um banco recém-semeado (SQLite local ou MySQL via Docker):

    BASE_URL=http://127.0.0.1:8001 python scripts/smoke_test.py

O script cria um hóspede com CPF 39053344705 e um usuário ``recepcao``.
Por isso ele deve ser executado em um banco limpo/recém-semeado.
"""

import json
import os
import time
import urllib.error
import urllib.request
from datetime import date, timedelta

BASE = os.getenv("BASE_URL", "http://127.0.0.1:8001")


def call(method, path, data=None, token=None, expect=None):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = None
    if data is not None:
        body = json.dumps(data).encode()

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            status = response.status
            payload = json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = raw

    if expect is not None and status != expect:
        raise AssertionError(f"{method} {path} -> {status}, esperado {expect}: {payload}")

    return status, payload


# Espera o servidor subir
for attempt in range(40):
    try:
        status, _ = call("GET", "/health")
        if status == 200:
            break
    except Exception:
        time.sleep(0.25)
else:
    raise SystemExit("Servidor não respondeu")

print("health:", call("GET", "/health"))

status, login = call(
    "POST",
    "/auth/login",
    {"login": "admin", "password": "admin123"},
    expect=200,
)
token = login["token"]
print("login:", status, login["name"], login["role"])

status, me = call("GET", "/auth/me", token=token, expect=200)
print("me:", me["login"], me["role"])

status, bootstrap = call("GET", "/mobile/bootstrap", token=token, expect=200)
print(
    "bootstrap:",
    status,
    "quartos=", len(bootstrap["rooms"]),
    "chegadas=", len(bootstrap["arrivals"]),
    "saidas=", len(bootstrap["departures"]),
    "resumo_disponiveis=", bootstrap["summary"]["rooms_available"],
)

status, rooms = call("GET", "/rooms/get?page=1&page_size=10", token=token, expect=200)
print("rooms:", status, "total=", rooms["total"])
assert rooms["total"] >= 6

check_in = date.today().isoformat()
check_out = (date.today() + timedelta(days=2)).isoformat()
status, available = call(
    "GET",
    f"/rooms/available?check_in={check_in}&check_out={check_out}&guests=2",
    token=token,
    expect=200,
)
print("available:", status, [room["number"] for room in available])
assert available, "Nenhum quarto disponível para o período"

status, guest = call(
    "POST",
    "/guests/create",
    {
        "full_name": "Carlos Pereira",
        "cpf": "39053344705",
        "email": "carlos.pereira@example.com",
        "phone": "11988887777",
        "city": "Santos",
        "state": "SP",
    },
    token=token,
    expect=201,
)
print("guest:", status, guest["id"], guest["full_name"], guest["cpf"])

room = available[0]
status, reservation = call(
    "POST",
    "/reservations/create",
    {
        "guest_id": guest["id"],
        "room_id": room["id"],
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": 2,
        "children": 0,
        "notes": "Reserva criada pelo teste automatizado",
    },
    token=token,
    expect=201,
)
print(
    "reservation:",
    status,
    reservation["code"],
    reservation["status"],
    "noites=", reservation["nights"],
    "total=", reservation["total_amount"],
)
assert reservation["status"] == "Pendente"
assert reservation["total_amount"] > 0

# Overbooking deve ser bloqueado
status, conflict = call(
    "POST",
    "/reservations/create",
    {
        "guest_id": guest["id"],
        "room_id": room["id"],
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": 1,
    },
    token=token,
)
print("overbooking bloqueado:", status, conflict.get("detail"))
assert status == 400

status, checked = call(
    "POST",
    f"/reservations/{reservation['id']}/checkin",
    token=token,
    expect=200,
)
print("checkin:", status, checked["status"], checked["room_number"])
assert checked["status"] == "CheckIn"

status, payment = call(
    "POST",
    "/payments/create",
    {
        "reservation_id": reservation["id"],
        "amount": reservation["total_amount"],
        "method": "Pix",
        "notes": "Pagamento integral",
    },
    token=token,
    expect=201,
)
print("payment:", status, payment["amount"], payment["status"])

status, consumption = call(
    "POST",
    "/consumptions/create",
    {
        "reservation_id": reservation["id"],
        "description": "Frigobar",
        "quantity": 2,
        "unit_price": 8,
    },
    token=token,
    expect=201,
)
print("consumption:", status, consumption["total"])

status, blocked_checkout = call(
    "POST",
    f"/reservations/{reservation['id']}/checkout",
    {"force": False},
    token=token,
)
print("checkout sem quitar:", status, blocked_checkout.get("detail"))
assert status == 400

status, checkout = call(
    "POST",
    f"/reservations/{reservation['id']}/checkout",
    {"force": True, "notes": "Check-out de teste"},
    token=token,
    expect=200,
)
print(
    "checkout:",
    status,
    checkout["status"],
    "saldo=", checkout["balance_due"],
)
assert checkout["status"] == "CheckOut"

status, summary = call("GET", "/reports/summary", token=token, expect=200)
print(
    "summary:",
    status,
    "quartos=", summary["total_rooms"],
    "ocupados=", summary["rooms_occupied"],
    "limpezas=", summary["pending_housekeeping"],
    "manutencoes=", summary["open_maintenance"],
    "receita_mes=", summary["revenue_month"],
)

status, tasks = call(
    "GET",
    f"/housekeeping/get?room_id={room['id']}",
    token=token,
    expect=200,
)
print("housekeeping:", status, "total=", tasks["total"])
assert tasks["total"] >= 1

status, occupancy = call("GET", "/reports/occupancy", token=token, expect=200)
print("occupancy:", status, "dias=", len(occupancy["items"]))

status, revenue = call("GET", "/reports/revenue", token=token, expect=200)
print("revenue:", status, "total=", revenue["total"], "metodos=", len(revenue["by_method"]))

status, arrivals = call("GET", "/reports/arrivals-departures", token=token, expect=200)
print("arrivals-departures:", status, arrivals["date"])

# Cria uma recepcionista e valida restrição de perfil
status, user = call(
    "POST",
    "/users/create",
    {
        "name": "Recepcionista Teste",
        "login": "recepcao",
        "email": "recepcao@pousada.local",
        "password": "recepcao123",
        "role": "Recepcionista",
    },
    token=token,
    expect=201,
)
print("user:", status, user["login"], user["role"])

status, receptionist = call(
    "POST",
    "/auth/login",
    {"login": "recepcao", "password": "recepcao123"},
    expect=200,
)
recep_token = receptionist["token"]

status, forbidden = call(
    "POST",
    "/rooms/create",
    {"number": "999", "room_type_id": 1, "floor": 9},
    token=recep_token,
)
print("perfil recepcionista bloqueado em /rooms/create:", status, forbidden.get("detail"))
assert status == 403

# Cleanup: desativa o usuário de teste
call("DELETE", f"/users/delete/{user['id']}", token=token)

print("\nTODOS OS TESTES PASSARAM")
