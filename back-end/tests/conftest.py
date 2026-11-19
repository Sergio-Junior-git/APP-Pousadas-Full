import os
import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path

# A configuração de banco é lida no import de database.py. Por isso o ambiente
# precisa ser preparado antes de importar o app.
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["ADMIN_LOGIN"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin123"
os.environ["ADMIN_NAME"] = "Administrador"

TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="pousada-api-tests-"))
TEST_DB_PATH = TEST_DB_DIR / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from database import Base, engine  # noqa: E402
from main import app  # noqa: E402
from seed_all import seed  # noqa: E402

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin123"

_CPF_SEQUENCE = 100_000_000


def _cpf_check_digit(digits: list[int]) -> int:
    total = sum(
        (len(digits) + 1 - index) * digit
        for index, digit in enumerate(digits)
    )
    return (total * 10 % 11) % 10


def make_cpf() -> str:
    """Gera um CPF válido e único para cada chamada."""
    global _CPF_SEQUENCE
    _CPF_SEQUENCE += 1
    digits = [int(char) for char in f"{_CPF_SEQUENCE:09d}"[-9:]]
    digits.append(_cpf_check_digit(digits))
    digits.append(_cpf_check_digit(digits))
    return "".join(str(digit) for digit in digits)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_database():
    yield
    engine.dispose()
    shutil.rmtree(TEST_DB_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    seed()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(reset_database):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_token(client):
    response = client.post(
        "/auth/login",
        json={"login": ADMIN_LOGIN, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def create_user(client, auth_headers):
    def _create(
        login: str,
        role: str,
        password: str = "secret123",
        **overrides,
    ):
        payload = {
            "name": f"Usuario {login.title()}",
            "login": login,
            "email": f"{login}@example.com",
            "password": password,
            "role": role,
            "active": True,
        }
        payload.update(overrides)
        response = client.post("/users/create", headers=auth_headers, json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def make_session(client, create_user):
    def _make(
        login: str,
        role: str,
        password: str = "secret123",
        **overrides,
    ):
        user = create_user(login, role, password, **overrides)
        response = client.post(
            "/auth/login",
            json={"login": login, "password": password},
        )
        assert response.status_code == 200, response.text
        return {
            "user": user,
            "headers": {"Authorization": f"Bearer {response.json()['token']}"},
        }

    return _make


@pytest.fixture
def create_guest(client, auth_headers):
    def _create(**overrides):
        cpf = overrides.pop("cpf", None) or make_cpf()
        payload = {
            "full_name": "Hospede Teste",
            "cpf": cpf,
            "email": f"hospede{cpf}@example.com",
            "phone": "11999990000",
            "city": "Sao Paulo",
            "state": "SP",
        }
        payload.update(overrides)
        response = client.post("/guests/create", headers=auth_headers, json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def available_room(client, auth_headers):
    def _find(check_in: date, check_out: date, guests: int = 1):
        response = client.get(
            "/rooms/available",
            headers=auth_headers,
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "guests": guests,
            },
        )
        assert response.status_code == 200, response.text
        rooms = response.json()
        assert rooms, "Nenhum quarto disponivel para o periodo"
        return rooms[0]

    return _find


@pytest.fixture
def create_reservation(client, auth_headers, create_guest, available_room):
    def _create(
        *,
        room_id=None,
        guest_id=None,
        check_in=None,
        check_out=None,
        **overrides,
    ):
        check_in = check_in or (date.today() + timedelta(days=30))
        check_out = check_out or (check_in + timedelta(days=2))
        adults = overrides.get("adults", 2)
        children = overrides.get("children", 0)

        if guest_id is None:
            guest_id = create_guest()["id"]
        if room_id is None:
            room_id = available_room(check_in, check_out, adults + children)["id"]

        payload = {
            "guest_id": guest_id,
            "room_id": room_id,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "adults": adults,
            "children": children,
        }
        payload.update(overrides)
        response = client.post(
            "/reservations/create",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create
