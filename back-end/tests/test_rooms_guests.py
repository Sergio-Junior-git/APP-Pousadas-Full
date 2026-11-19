from datetime import date, timedelta


def test_room_type_and_room_crud(client, auth_headers):
    room_type = client.post(
        "/room-types/create",
        headers=auth_headers,
        json={
            "name": "Chalé",
            "description": "Chalé de teste",
            "capacity": 3,
            "base_price": 199.90,
            "image_url": "https://example.com/chale.jpg",
        },
    )
    assert room_type.status_code == 201, room_type.text
    room_type_data = room_type.json()
    assert room_type_data["name"] == "Chalé"
    assert room_type_data["capacity"] == 3
    assert room_type_data["base_price"] == 199.9

    duplicate_type = client.post(
        "/room-types/create",
        headers=auth_headers,
        json={
            "name": "Chalé",
            "capacity": 2,
            "base_price": 100,
        },
    )
    assert duplicate_type.status_code == 400
    assert "já existe" in duplicate_type.json()["detail"]

    room = client.post(
        "/rooms/create",
        headers=auth_headers,
        json={
            "number": "999",
            "room_type_id": room_type_data["id"],
            "floor": 3,
            "image_url": "https://example.com/quarto-999.jpg",
        },
    )
    assert room.status_code == 201, room.text
    room_data = room.json()
    assert room_data["number"] == "999"
    assert room_data["status"] == "Disponivel"
    assert room_data["room_type"]["name"] == "Chalé"

    duplicate_room = client.post(
        "/rooms/create",
        headers=auth_headers,
        json={"number": "999", "room_type_id": room_type_data["id"], "floor": 1},
    )
    assert duplicate_room.status_code == 400
    assert "já cadastrado" in duplicate_room.json()["detail"]

    updated = client.put(
        f"/rooms/update/{room_data['id']}",
        headers=auth_headers,
        json={"number": "998", "floor": 4, "status": "Limpeza"},
    )
    assert updated.status_code == 200
    assert updated.json()["number"] == "998"
    assert updated.json()["floor"] == 4
    assert updated.json()["status"] == "Limpeza"

    status_update = client.patch(
        f"/rooms/{room_data['id']}/status",
        headers=auth_headers,
        json={"status": "Disponivel"},
    )
    assert status_update.status_code == 200
    assert status_update.json()["status"] == "Disponivel"

    deleted = client.delete(
        f"/rooms/delete/{room_data['id']}",
        headers=auth_headers,
    )
    assert deleted.status_code == 200

    inactive_room = client.get(
        f"/rooms/{room_data['id']}",
        headers=auth_headers,
    )
    assert inactive_room.status_code == 200
    assert inactive_room.json()["active"] is False

    inactive_list = client.get(
        "/rooms/get?active=false",
        headers=auth_headers,
    )
    assert inactive_list.status_code == 200
    assert any(item["id"] == room_data["id"] for item in inactive_list.json()["items"])

    invalid_type = client.post(
        "/rooms/create",
        headers=auth_headers,
        json={"number": "997", "room_type_id": 99999, "floor": 1},
    )
    assert invalid_type.status_code == 400
    assert "Tipo de quarto" in invalid_type.json()["detail"]


def test_room_list_filters_and_pagination(client, auth_headers):
    listing = client.get("/rooms/get", headers=auth_headers)
    assert listing.status_code == 200
    data = listing.json()
    assert data["total"] == 6
    assert len(data["items"]) == 6
    assert data["page"] == 1
    assert data["page_size"] == 20

    paginated = client.get(
        "/rooms/get?page=1&page_size=2",
        headers=auth_headers,
    ).json()
    assert paginated["total"] == 6
    assert len(paginated["items"]) == 2

    search = client.get("/rooms/get?search=101", headers=auth_headers).json()
    assert search["total"] == 1
    assert search["items"][0]["number"] == "101"

    floor = client.get("/rooms/get?floor=2", headers=auth_headers).json()
    assert floor["total"] == 3
    assert {item["number"] for item in floor["items"]} == {"201", "202", "203"}

    available = client.get(
        "/rooms/get?status=Disponivel",
        headers=auth_headers,
    ).json()
    assert available["total"] == 3

    room_types = client.get(
        "/room-types/get?search=Casal",
        headers=auth_headers,
    ).json()
    casal_id = room_types["items"][0]["id"]
    by_type = client.get(
        f"/rooms/get?room_type_id={casal_id}",
        headers=auth_headers,
    ).json()
    assert by_type["total"] == 3
    assert {item["number"] for item in by_type["items"]} == {"101", "102", "202"}

    active = client.get("/rooms/get?active=true", headers=auth_headers).json()
    assert active["total"] == 6

    assert client.get("/rooms/get?page=0", headers=auth_headers).status_code == 422
    assert (
        client.get("/rooms/get?page_size=101", headers=auth_headers).status_code == 422
    )


def test_guest_crud_cpf_and_search(client, auth_headers):
    guest = client.post(
        "/guests/create",
        headers=auth_headers,
        json={
            "full_name": "Carlos Pereira",
            "cpf": "39053344705",
            "email": "CARLOS.PEREIRA@EXAMPLE.COM",
            "phone": "11988887777",
            "city": "Santos",
            "state": "sp",
        },
    )
    assert guest.status_code == 201, guest.text
    guest_data = guest.json()
    assert guest_data["cpf"] == "39053344705"
    assert guest_data["email"] == "carlos.pereira@example.com"
    assert guest_data["state"] == "SP"

    duplicate = client.post(
        "/guests/create",
        headers=auth_headers,
        json={
            "full_name": "Outro Carlos",
            "cpf": "39053344705",
        },
    )
    assert duplicate.status_code == 400
    assert "CPF já cadastrado" in duplicate.json()["detail"]

    invalid_cpf = client.post(
        "/guests/create",
        headers=auth_headers,
        json={"full_name": "Cpf Invalido", "cpf": "11111111111"},
    )
    assert invalid_cpf.status_code == 422

    by_name = client.get(
        "/guests/get?search=Carlos",
        headers=auth_headers,
    ).json()
    assert by_name["total"] == 1
    assert by_name["items"][0]["id"] == guest_data["id"]

    by_cpf = client.get(
        "/guests/get?search=39053344705",
        headers=auth_headers,
    ).json()
    assert by_cpf["total"] == 1

    by_cpf_route = client.get(
        "/guests/bycpf/39053344705",
        headers=auth_headers,
    )
    assert by_cpf_route.status_code == 200
    assert by_cpf_route.json()["full_name"] == "Carlos Pereira"

    updated = client.put(
        f"/guests/update/{guest_data['id']}",
        headers=auth_headers,
        json={"full_name": "Carlos Pereira Junior", "city": "São Vicente"},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Carlos Pereira Junior"
    assert updated.json()["city"] == "São Vicente"

    deleted = client.delete(
        f"/guests/delete/{guest_data['id']}",
        headers=auth_headers,
    )
    assert deleted.status_code == 200

    inactive = client.get(
        f"/guests/{guest_data['id']}",
        headers=auth_headers,
    )
    assert inactive.status_code == 200
    assert inactive.json()["active"] is False

    inactive_list = client.get(
        "/guests/get?active=false",
        headers=auth_headers,
    ).json()
    assert any(item["id"] == guest_data["id"] for item in inactive_list["items"])


def test_availability_filters_and_validation(client, auth_headers):
    check_in = date.today() + timedelta(days=30)
    check_out = check_in + timedelta(days=2)

    two_guests = client.get(
        "/rooms/available",
        headers=auth_headers,
        params={
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": 2,
        },
    )
    assert two_guests.status_code == 200
    assert {item["number"] for item in two_guests.json()} == {
        "101",
        "102",
        "201",
        "202",
    }

    one_guest = client.get(
        "/rooms/available",
        headers=auth_headers,
        params={
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": 1,
        },
    )
    assert one_guest.status_code == 200
    assert {item["number"] for item in one_guest.json()} == {
        "101",
        "102",
        "103",
        "201",
        "202",
    }

    five_guests = client.get(
        "/rooms/available",
        headers=auth_headers,
        params={
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": 5,
        },
    )
    assert five_guests.status_code == 200
    assert five_guests.json() == []

    invalid_period = client.get(
        "/rooms/available",
        headers=auth_headers,
        params={
            "check_in": check_out.isoformat(),
            "check_out": check_in.isoformat(),
            "guests": 2,
        },
    )
    assert invalid_period.status_code == 400
    assert "data final" in invalid_period.json()["detail"]

    missing_check_out = client.get(
        "/rooms/available",
        headers=auth_headers,
        params={"check_in": check_in.isoformat(), "guests": 2},
    )
    assert missing_check_out.status_code == 422
