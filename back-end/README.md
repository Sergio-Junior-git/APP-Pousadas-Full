# Pousada API

API REST em **FastAPI** para gestão de pousada, pensada para consumo por aplicativos **mobile**. A estrutura segue o padrão do projeto `ci-api-fastapi-2`: `models` (SQLAlchemy), `schemas` (Pydantic v2), `services` (regras de negócio) e `routers` (endpoints), com JWT, Alembic e Docker.

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2
- MySQL 8 (PyMySQL) — SQLite é usado como fallback local
- Alembic
- Pydantic v2
- JWT (`python-jose`) + `passlib`/`bcrypt`

## Estrutura

```
pousada-api/
├── main.py
├── config.py
├── database.py
├── validators.py
├── pagination.py
├── models/pousada_models.py
├── schemas/           # um arquivo por entidade + enums + comum
├── services/          # regras de negócio
├── routers/           # endpoints
├── alembic/           # migration inicial
├── tests/             # suíte pytest (SQLite temporário)
├── scripts/           # teste de fumaça contra API em execução
├── seed_all.py
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
└── .env.example
```

## Como rodar

### 1. Com Docker (MySQL)

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

A API ficará em `http://localhost:8001` e o Swagger em `http://localhost:8001/docs`.

Depois que o banco estiver saudável, rode o seed dentro do container:

```bash
docker compose -f docker-compose.dev.yml exec api python seed_all.py
```

> A porta `8001` foi escolhida para não conflitar com a API atual na `8000`.

### 2. Local (SQLite)

Sem `DATABASE_URL`, a API usa `sqlite:///./pousada.db`.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python seed_all.py
uvicorn main:app --reload --port 8001
```

### 3. Migrations (MySQL)

```bash
alembic upgrade head
```

> O `main.py` também executa `create_all` como conveniência para desenvolvimento local/SQLite. Para MySQL em produção, rode `alembic upgrade head` antes de iniciar a API e o seed, mantendo o histórico de migrations.

### 4. Seed

```bash
python seed_all.py
```

Credenciais padrão do admin (configuráveis por env):

- **login:** `admin`
- **senha:** `admin123`

### 5. Testes automatizados

A suíte usa `TestClient` do FastAPI, cria um **SQLite temporário** e recria/seed o banco antes de cada teste. Não é necessário subir Docker ou MySQL.

```bash
source venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Para rodar um arquivo específico:

```bash
pytest tests/test_reservations_financial.py -q
```

Os testes cobrem autenticação, usuários/perfis, quartos, hóspedes, disponibilidade, reservas, overbooking, check-in/check-out, pagamentos, consumos, governança, manutenção, relatórios e o `/mobile/bootstrap`.

### 6. Teste de fumaça contra API em execução

Depois de subir a API com Docker/MySQL e rodar o seed, execute:

```bash
BASE_URL=http://127.0.0.1:8001 python scripts/smoke_test.py
```

> O teste de fumaça cria o hóspede `39053344705` e o usuário `recepcao`. Execute-o em um banco recém-semeado para evitar conflitos de unicidade.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./pousada.db` | URL do banco |
| `JWT_SECRET_KEY` | `dev-secret-change-me` | Chave do JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Expiração do token |
| `ADMIN_LOGIN` | `admin` | Login do admin no seed |
| `ADMIN_PASSWORD` | `admin123` | Senha do admin no seed |
| `ADMIN_NAME` | `Administrador` | Nome do admin no seed |
| `MYSQL_*` | — | Usadas pelo compose de dev |

## Perfis de acesso

| Perfil | Principais permissões |
|---|---|
| `Admin` | Tudo |
| `Gerente` | Quartos, tipos, hóspedes, reservas, relatórios |
| `Recepcionista` | Hóspedes, reservas, check-in/out, pagamentos, consumos |
| `Camareira` | Governança e status dos quartos |
| `Manutencao` | Chamados de manutenção e status dos quartos |

Todas as rotas (exceto `/` e `/health`) exigem `Authorization: Bearer <token>`.

## Endpoints

### Auth

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/login` | Login e geração do JWT |
| GET | `/auth/me` | Dados do usuário autenticado |
| POST | `/auth/change-password` | Troca de senha |

### Usuários (equipe)

| Método | Rota | Perfil |
|---|---|---|
| GET | `/users/get` | Admin, Gerente |
| GET | `/users/{id}` | Admin, Gerente |
| POST | `/users/create` | Admin |
| PUT | `/users/update/{id}` | Admin |
| PATCH | `/users/{id}/toggle-active` | Admin |
| DELETE | `/users/delete/{id}` | Admin |

### Tipos de quarto

| Método | Rota | Perfil |
|---|---|---|
| GET | `/room-types/get` | Autenticado |
| GET | `/room-types/{id}` | Autenticado |
| POST | `/room-types/create` | Admin, Gerente |
| PUT | `/room-types/update/{id}` | Admin, Gerente |
| DELETE | `/room-types/delete/{id}` | Admin |

### Quartos

| Método | Rota | Perfil |
|---|---|---|
| GET | `/rooms/get` | Autenticado |
| GET | `/rooms/available?check_in=&check_out=&guests=` | Autenticado |
| GET | `/rooms/{id}` | Autenticado |
| POST | `/rooms/create` | Admin, Gerente |
| PUT | `/rooms/update/{id}` | Admin, Gerente |
| PATCH | `/rooms/{id}/status` | Autenticado |
| DELETE | `/rooms/delete/{id}` | Admin |

### Hóspedes

| Método | Rota | Perfil |
|---|---|---|
| GET | `/guests/get?search=` | Admin, Gerente, Recepcionista |
| GET | `/guests/bycpf/{cpf}` | Admin, Gerente, Recepcionista |
| GET | `/guests/{id}` | Admin, Gerente, Recepcionista |
| POST | `/guests/create` | Admin, Gerente, Recepcionista |
| PUT | `/guests/update/{id}` | Admin, Gerente, Recepcionista |
| DELETE | `/guests/delete/{id}` | Admin, Gerente |

### Reservas

| Método | Rota | Perfil |
|---|---|---|
| GET | `/reservations/get` | Autenticado |
| GET | `/reservations/today/arrivals` | Autenticado |
| GET | `/reservations/today/departures` | Autenticado |
| GET | `/reservations/{id}` | Autenticado |
| POST | `/reservations/create` | Admin, Gerente, Recepcionista |
| PUT | `/reservations/update/{id}` | Admin, Gerente, Recepcionista |
| POST | `/reservations/{id}/checkin` | Admin, Gerente, Recepcionista |
| POST | `/reservations/{id}/checkout` | Admin, Gerente, Recepcionista |
| POST | `/reservations/{id}/cancel` | Admin, Gerente, Recepcionista |
| DELETE | `/reservations/delete/{id}` | Admin, Gerente |

### Pagamentos e consumos

| Método | Rota | Perfil |
|---|---|---|
| GET | `/payments/get?reservation_id=` | Admin, Gerente, Recepcionista |
| POST | `/payments/create` | Admin, Gerente, Recepcionista |
| PUT | `/payments/update/{id}` | Admin, Gerente, Recepcionista |
| POST | `/payments/{id}/refund` | Admin, Gerente |
| DELETE | `/payments/delete/{id}` | Admin, Gerente |
| GET | `/consumptions/get?reservation_id=` | Admin, Gerente, Recepcionista |
| POST | `/consumptions/create` | Admin, Gerente, Recepcionista |
| PUT | `/consumptions/update/{id}` | Admin, Gerente, Recepcionista |
| DELETE | `/consumptions/delete/{id}` | Admin, Gerente |

### Governança e manutenção

| Método | Rota | Perfil |
|---|---|---|
| GET | `/housekeeping/get` | Autenticado |
| POST | `/housekeeping/create` | Admin, Gerente, Camareira |
| PUT | `/housekeeping/update/{id}` | Admin, Gerente, Camareira |
| POST | `/housekeeping/{id}/start` | Admin, Gerente, Camareira |
| POST | `/housekeeping/{id}/complete` | Admin, Gerente, Camareira |
| GET | `/maintenance/get` | Autenticado |
| POST | `/maintenance/create` | Admin, Gerente, Manutencao, Recepcionista |
| PUT | `/maintenance/update/{id}` | Admin, Gerente, Manutencao |
| POST | `/maintenance/{id}/resolve` | Admin, Gerente, Manutencao |
| POST | `/maintenance/{id}/cancel` | Admin, Gerente |

### Relatórios e mobile

| Método | Rota | Descrição |
|---|---|---|
| GET | `/reports/summary` | Resumo operacional e financeiro |
| GET | `/reports/occupancy?start=&end=` | Ocupação por dia |
| GET | `/reports/revenue?start=&end=` | Receita por método e por dia |
| GET | `/reports/arrivals-departures?day=` | Chegadas e saídas |
| GET | `/mobile/bootstrap` | Home do app em uma única chamada |

## Exemplos rápidos

### Login

```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"admin123"}'
```

### Criar hóspede

```bash
curl -X POST http://localhost:8001/guests/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Carlos Pereira",
    "cpf": "39053344705",
    "email": "carlos@example.com",
    "phone": "11988887777"
  }'
```

### Consultar disponibilidade

```bash
curl "http://localhost:8001/rooms/available?check_in=2026-11-15&check_out=2026-11-18&guests=2" \
  -H "Authorization: Bearer $TOKEN"
```

### Criar reserva

```bash
curl -X POST http://localhost:8001/reservations/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "guest_id": 1,
    "room_id": 1,
    "check_in_date": "2026-11-15",
    "check_out_date": "2026-11-18",
    "adults": 2,
    "children": 0
  }'
```

### Check-in e check-out

```bash
curl -X POST http://localhost:8001/reservations/1/checkin \
  -H "Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8001/reservations/1/checkout \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force": true, "notes": "Check-out antecipado"}'
```

## Regras principais

- **Overbooking bloqueado:** a API verifica reservas ativas no intervalo de datas antes de criar/alterar.
- **Capacidade:** a soma de adultos e crianças não pode exceder a capacidade do tipo de quarto.
- **Check-in:** reserva precisa estar `Pendente` ou `Confirmada` e o quarto não pode ter outra estadia ativa.
- **Check-out:** exige status `CheckIn`; se houver saldo pendente, é necessário `force=true`. O quarto vai para `Limpeza` e uma tarefa de governança é criada automaticamente.
- **Pagamentos:** `Pago` alimenta o total pago; estorno muda para `Estornado`.
- **Consumos:** total calculado automaticamente (`quantidade × valor unitário`).
- **Exclusões:** usuários, tipos de quarto, quartos e hóspedes são **desativados** (`active=false`) para preservar histórico. Reservas são canceladas.
- **Manutenção:** abrir chamado coloca o quarto em `Manutencao` (quando não está ocupado); resolver/cancelar libera o quarto quando não há outros chamados abertos.

## Foco mobile

- JWT Bearer.
- Paginação padrão `page` / `page_size` em todas as listas.
- Filtros por status, período, quarto, hóspede e busca textual.
- `GET /mobile/bootstrap` entrega resumo, chegadas, saídas, quartos, governança pendente e manutenções abertas em uma chamada.
- Objetos aninhados resumidos (hóspede e quarto dentro da reserva).
- Datas em ISO 8601 e valores monetários em JSON numérico.
- Enums em PT-BR para facilitar a exibição direta no app.

## Documentação interativa

Com a API rodando, acesse:

- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
- OpenAPI JSON: `http://localhost:8001/openapi.json`
