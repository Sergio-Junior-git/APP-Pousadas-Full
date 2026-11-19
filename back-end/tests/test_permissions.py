def test_role_permission_matrix(client, auth_headers, make_session):
    admin_user = client.get("/auth/me", headers=auth_headers).json()
    gerente = make_session("gerente1", "Gerente")
    recepcionista = make_session("recep1", "Recepcionista")
    camareira = make_session("camareira1", "Camareira")
    manutencao = make_session("manutencao1", "Manutencao")

    sessions = {
        "Admin": {"headers": auth_headers, "user": admin_user},
        "Gerente": gerente,
        "Recepcionista": recepcionista,
        "Camareira": camareira,
        "Manutencao": manutencao,
    }

    for role, session in sessions.items():
        me = client.get("/auth/me", headers=session["headers"])
        assert me.status_code == 200, role
        assert me.json()["role"] == role

    users_expected = {
        "Admin": 200,
        "Gerente": 200,
        "Recepcionista": 403,
        "Camareira": 403,
        "Manutencao": 403,
    }
    for role, expected in users_expected.items():
        response = client.get("/users/get", headers=sessions[role]["headers"])
        assert response.status_code == expected, role

    guests_expected = {
        "Admin": 200,
        "Gerente": 200,
        "Recepcionista": 200,
        "Camareira": 403,
        "Manutencao": 403,
    }
    for role, expected in guests_expected.items():
        response = client.get("/guests/get", headers=sessions[role]["headers"])
        assert response.status_code == expected, role

    payments_expected = {
        "Admin": 200,
        "Gerente": 200,
        "Recepcionista": 200,
        "Camareira": 403,
        "Manutencao": 403,
    }
    for role, expected in payments_expected.items():
        response = client.get("/payments/get", headers=sessions[role]["headers"])
        assert response.status_code == expected, role
        response = client.get("/consumptions/get", headers=sessions[role]["headers"])
        assert response.status_code == expected, role

    reports_summary_expected = {
        "Admin": 200,
        "Gerente": 200,
        "Recepcionista": 200,
        "Camareira": 403,
        "Manutencao": 403,
    }
    for role, expected in reports_summary_expected.items():
        response = client.get("/reports/summary", headers=sessions[role]["headers"])
        assert response.status_code == expected, role

    reports_occupancy_expected = {
        "Admin": 200,
        "Gerente": 200,
        "Recepcionista": 403,
        "Camareira": 403,
        "Manutencao": 403,
    }
    for role, expected in reports_occupancy_expected.items():
        response = client.get("/reports/occupancy", headers=sessions[role]["headers"])
        assert response.status_code == expected, role

    for role in sessions:
        assert (
            client.get("/housekeeping/get", headers=sessions[role]["headers"]).status_code
            == 200
        ), role
        assert (
            client.get("/maintenance/get", headers=sessions[role]["headers"]).status_code
            == 200
        ), role
        assert (
            client.get("/reservations/get", headers=sessions[role]["headers"]).status_code
            == 200
        ), role
        assert (
            client.get("/mobile/bootstrap", headers=sessions[role]["headers"]).status_code
            == 200
        ), role

    room_types = client.get(
        "/room-types/get?search=Casal",
        headers=auth_headers,
    ).json()
    room_type_id = room_types["items"][0]["id"]

    room_numbers = {
        "Admin": "900",
        "Gerente": "901",
        "Recepcionista": "902",
        "Camareira": "903",
        "Manutencao": "904",
    }
    for role, expected in {
        "Admin": 201,
        "Gerente": 201,
        "Recepcionista": 403,
        "Camareira": 403,
        "Manutencao": 403,
    }.items():
        response = client.post(
            "/rooms/create",
            headers=sessions[role]["headers"],
            json={
                "number": room_numbers[role],
                "room_type_id": room_type_id,
                "floor": 9,
            },
        )
        assert response.status_code == expected, (role, response.text)

    room_202 = client.get(
        "/rooms/get?search=202",
        headers=auth_headers,
    ).json()["items"][0]["id"]

    for role, expected in {
        "Admin": 201,
        "Gerente": 201,
        "Recepcionista": 403,
        "Camareira": 201,
        "Manutencao": 403,
    }.items():
        response = client.post(
            "/housekeeping/create",
            headers=sessions[role]["headers"],
            json={
                "room_id": room_202,
                "notes": f"Tarefa criada por {role}",
            },
        )
        assert response.status_code == expected, (role, response.text)

    for role, expected in {
        "Admin": 201,
        "Gerente": 201,
        "Recepcionista": 201,
        "Camareira": 403,
        "Manutencao": 201,
    }.items():
        response = client.post(
            "/maintenance/create",
            headers=sessions[role]["headers"],
            json={
                "room_id": room_202,
                "title": f"Chamado criado por {role}",
                "description": "Teste de permissao",
            },
        )
        assert response.status_code == expected, (role, response.text)

    new_user_payload = {
        "name": "Usuario Novo",
        "login": "novo_usuario",
        "email": "novo_usuario@example.com",
        "password": "secret123",
        "role": "Recepcionista",
    }
    created_user = client.post(
        "/users/create",
        headers=auth_headers,
        json=new_user_payload,
    )
    assert created_user.status_code == 201, created_user.text

    for role in ("Gerente", "Recepcionista", "Camareira", "Manutencao"):
        response = client.post(
            "/users/create",
            headers=sessions[role]["headers"],
            json={
                **new_user_payload,
                "login": f"novo_{role.lower()}",
                "email": f"novo_{role.lower()}@example.com",
            },
        )
        assert response.status_code == 403, role

    gerente_id = gerente["user"]["id"]
    assert (
        client.delete(
            f"/users/delete/{gerente_id}",
            headers=gerente["headers"],
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/users/delete/{gerente_id}",
            headers=auth_headers,
        ).status_code
        == 200
    )

    inactive_login = client.post(
        "/auth/login",
        json={"login": "gerente1", "password": "secret123"},
    )
    assert inactive_login.status_code == 401
    assert "Usuário inativo" in inactive_login.json()["detail"]
