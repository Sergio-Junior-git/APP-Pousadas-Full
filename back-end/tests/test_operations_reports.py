from datetime import date, timedelta


def room_id_by_number(client, headers, number: str) -> int:
    response = client.get(
        f"/rooms/get?search={number}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert items, f"Quarto {number} nao encontrado"
    return items[0]["id"]


def test_housekeeping_flow(client, auth_headers, make_session):
    room_103 = room_id_by_number(client, auth_headers, "103")
    room_202 = room_id_by_number(client, auth_headers, "202")
    camareira = make_session("camareira1", "Camareira")

    seed_tasks = client.get("/housekeeping/get", headers=auth_headers)
    assert seed_tasks.status_code == 200
    assert seed_tasks.json()["total"] == 1

    seed_room_tasks = client.get(
        f"/housekeeping/get?room_id={room_103}",
        headers=auth_headers,
    )
    assert seed_room_tasks.status_code == 200
    assert seed_room_tasks.json()["total"] == 1

    created = client.post(
        "/housekeeping/create",
        headers=auth_headers,
        json={
            "room_id": room_202,
            "assigned_to_id": camareira["user"]["id"],
            "priority": "Alta",
            "notes": "Limpeza completa",
            "scheduled_for": date.today().isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["status"] == "Pendente"
    assert task["priority"] == "Alta"
    assert task["room_number"] == "202"
    assert task["assigned_to_name"] == camareira["user"]["name"]
    task_id = task["id"]

    fetched = client.get(f"/housekeeping/{task_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == task_id

    started = client.post(
        f"/housekeeping/{task_id}/start",
        headers=auth_headers,
    )
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "EmAndamento"

    room_cleaning = client.get(
        f"/rooms/{room_202}",
        headers=auth_headers,
    )
    assert room_cleaning.json()["status"] == "Limpeza"

    completed = client.post(
        f"/housekeeping/{task_id}/complete",
        headers=auth_headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "Concluida"
    assert completed.json()["completed_at"] is not None

    room_available = client.get(
        f"/rooms/{room_202}",
        headers=auth_headers,
    )
    assert room_available.json()["status"] == "Disponivel"

    update_completed = client.put(
        f"/housekeeping/update/{task_id}",
        headers=auth_headers,
        json={"notes": "Nao deve alterar"},
    )
    assert update_completed.status_code == 400
    assert "concluída" in update_completed.json()["detail"]

    invalid_room = client.post(
        "/housekeeping/create",
        headers=auth_headers,
        json={"room_id": 99999, "notes": "Quarto inexistente"},
    )
    assert invalid_room.status_code == 400
    assert "Quarto não encontrado" in invalid_room.json()["detail"]

    another = client.post(
        "/housekeeping/create",
        headers=auth_headers,
        json={"room_id": room_202, "notes": "Tarefa para excluir"},
    )
    assert another.status_code == 201
    another_id = another.json()["id"]

    assert (
        client.delete(
            f"/housekeeping/delete/{another_id}",
            headers=camareira["headers"],
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/housekeeping/delete/{another_id}",
            headers=auth_headers,
        ).status_code
        == 200
    )

    pending = client.get(
        "/housekeeping/get?status=Pendente",
        headers=auth_headers,
    )
    assert pending.status_code == 200
    assert pending.json()["total"] >= 1


def test_maintenance_flow(client, auth_headers, make_session):
    room_202 = room_id_by_number(client, auth_headers, "202")
    manutencao = make_session("manutencao1", "Manutencao")

    seed_tickets = client.get("/maintenance/get", headers=auth_headers)
    assert seed_tickets.status_code == 200
    assert seed_tickets.json()["total"] == 1

    created = client.post(
        "/maintenance/create",
        headers=auth_headers,
        json={
            "room_id": room_202,
            "assigned_to_id": manutencao["user"]["id"],
            "title": "Lâmpada queimada",
            "description": "Lâmpada do banheiro não acende",
            "priority": "Alta",
        },
    )
    assert created.status_code == 201, created.text
    ticket = created.json()
    assert ticket["status"] == "Aberta"
    assert ticket["room_number"] == "202"
    assert ticket["assigned_to_name"] == manutencao["user"]["name"]
    assert ticket["reported_by"] == "admin"
    ticket_id = ticket["id"]

    room_maintenance = client.get(
        f"/rooms/{room_202}",
        headers=auth_headers,
    )
    assert room_maintenance.json()["status"] == "Manutencao"

    fetched = client.get(f"/maintenance/{ticket_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == ticket_id

    resolved = client.post(
        f"/maintenance/{ticket_id}/resolve",
        headers=auth_headers,
        json={"notes": "Lâmpada substituída"},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "Resolvida"
    assert resolved.json()["resolved_at"] is not None
    assert "Resolução: Lâmpada substituída" in resolved.json()["description"]

    room_available = client.get(
        f"/rooms/{room_202}",
        headers=auth_headers,
    )
    assert room_available.json()["status"] == "Disponivel"

    update_resolved = client.put(
        f"/maintenance/update/{ticket_id}",
        headers=auth_headers,
        json={"title": "Nao deve alterar"},
    )
    assert update_resolved.status_code == 400
    assert "finalizado" in update_resolved.json()["detail"]

    second = client.post(
        "/maintenance/create",
        headers=auth_headers,
        json={
            "room_id": room_202,
            "title": "Torneira vazando",
            "description": "Torneira do lavatório",
        },
    )
    assert second.status_code == 201
    second_id = second.json()["id"]

    cancelled = client.post(
        f"/maintenance/{second_id}/cancel",
        headers=auth_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "Cancelada"

    room_available = client.get(
        f"/rooms/{room_202}",
        headers=auth_headers,
    )
    assert room_available.json()["status"] == "Disponivel"

    invalid_room = client.post(
        "/maintenance/create",
        headers=auth_headers,
        json={"room_id": 99999, "title": "Chamado invalido"},
    )
    assert invalid_room.status_code == 400
    assert "Quarto não encontrado" in invalid_room.json()["detail"]

    open_tickets = client.get(
        "/maintenance/get?status=Aberta",
        headers=auth_headers,
    )
    assert open_tickets.status_code == 200
    assert open_tickets.json()["total"] >= 1

    assert (
        client.delete(
            f"/maintenance/delete/{ticket_id}",
            headers=manutencao["headers"],
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/maintenance/delete/{ticket_id}",
            headers=auth_headers,
        ).status_code
        == 200
    )


def test_reports_and_mobile_bootstrap(client, auth_headers):
    today = date.today()

    summary = client.get("/reports/summary", headers=auth_headers)
    assert summary.status_code == 200
    summary_data = summary.json()
    assert summary_data == {
        "total_rooms": 6,
        "rooms_available": 3,
        "rooms_occupied": 1,
        "rooms_cleaning": 1,
        "rooms_maintenance": 1,
        "occupancy_rate": 16.7,
        "checkins_today": 2,
        "checkouts_today": 0,
        "pending_housekeeping": 1,
        "open_maintenance": 1,
        "revenue_month": 940.0,
        "reservations_today": 2,
    }

    bootstrap = client.get("/mobile/bootstrap", headers=auth_headers)
    assert bootstrap.status_code == 200
    bootstrap_data = bootstrap.json()
    assert bootstrap_data["summary"] == summary_data
    assert len(bootstrap_data["rooms"]) == 6
    assert len(bootstrap_data["arrivals"]) == 2
    assert bootstrap_data["departures"] == []
    assert len(bootstrap_data["pending_housekeeping"]) == 1
    assert len(bootstrap_data["open_maintenance"]) == 1

    occupancy = client.get(
        "/reports/occupancy",
        headers=auth_headers,
        params={
            "start": (today - timedelta(days=1)).isoformat(),
            "end": (today + timedelta(days=1)).isoformat(),
        },
    )
    assert occupancy.status_code == 200
    occupancy_data = occupancy.json()
    assert occupancy_data["start"] == (today - timedelta(days=1)).isoformat()
    assert occupancy_data["end"] == (today + timedelta(days=1)).isoformat()
    assert [item["occupied_rooms"] for item in occupancy_data["items"]] == [1, 3, 2]
    assert [item["total_rooms"] for item in occupancy_data["items"]] == [6, 6, 6]
    assert [item["occupancy_rate"] for item in occupancy_data["items"]] == [
        16.7,
        50.0,
        33.3,
    ]

    default_occupancy = client.get("/reports/occupancy", headers=auth_headers)
    assert default_occupancy.status_code == 200
    assert default_occupancy.json()["start"] == today.replace(day=1).isoformat()
    assert default_occupancy.json()["end"] == today.isoformat()

    month_start = today.replace(day=1)
    revenue = client.get(
        "/reports/revenue",
        headers=auth_headers,
        params={
            "start": month_start.isoformat(),
            "end": today.isoformat(),
        },
    )
    assert revenue.status_code == 200
    revenue_data = revenue.json()
    assert revenue_data["total"] == 940.0
    assert {item["method"] for item in revenue_data["by_method"]} == {
        "Pix",
        "CartaoCredito",
    }
    assert sum(item["count"] for item in revenue_data["by_method"]) == 2
    assert len(revenue_data["by_day"]) == 1
    assert revenue_data["by_day"][0]["date"] == today.isoformat()
    assert revenue_data["by_day"][0]["total"] == 940.0

    default_revenue = client.get("/reports/revenue", headers=auth_headers)
    assert default_revenue.status_code == 200
    assert default_revenue.json()["total"] == 940.0

    arrivals = client.get(
        "/reports/arrivals-departures",
        headers=auth_headers,
    )
    assert arrivals.status_code == 200
    arrivals_data = arrivals.json()
    assert arrivals_data["date"] == today.isoformat()
    assert len(arrivals_data["arrivals"]) == 2
    assert arrivals_data["departures"] == []

    future_departures = client.get(
        "/reports/arrivals-departures",
        headers=auth_headers,
        params={"day": (today + timedelta(days=2)).isoformat()},
    )
    assert future_departures.status_code == 200
    assert future_departures.json()["arrivals"] == []
    assert len(future_departures.json()["departures"]) == 1
    assert future_departures.json()["departures"][0]["room_number"] == "101"

    invalid_occupancy = client.get(
        "/reports/occupancy",
        headers=auth_headers,
        params={
            "start": today.isoformat(),
            "end": (today - timedelta(days=1)).isoformat(),
        },
    )
    assert invalid_occupancy.status_code == 400
    assert "data final" in invalid_occupancy.json()["detail"]

    long_occupancy = client.get(
        "/reports/occupancy",
        headers=auth_headers,
        params={
            "start": (today - timedelta(days=400)).isoformat(),
            "end": today.isoformat(),
        },
    )
    assert long_occupancy.status_code == 400
    assert "Período máximo" in long_occupancy.json()["detail"]

    invalid_revenue = client.get(
        "/reports/revenue",
        headers=auth_headers,
        params={
            "start": today.isoformat(),
            "end": (today - timedelta(days=1)).isoformat(),
        },
    )
    assert invalid_revenue.status_code == 400
