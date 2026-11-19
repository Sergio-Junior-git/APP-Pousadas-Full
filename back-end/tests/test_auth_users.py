def test_health_and_root(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    root = client.get("/")
    assert root.status_code == 200
    assert "funcionando" in root.json()["message"]


def test_login_me_and_invalid_credentials(client):
    response = client.post(
        "/auth/login",
        json={"login": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["login"] == "admin"
    assert data["role"] == "Admin"
    assert data["token"]
    assert data["token_type"] == "bearer"

    headers = {"Authorization": f"Bearer {data['token']}"}
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["login"] == "admin"
    assert me.json()["role"] == "Admin"

    assert client.get("/auth/me").status_code == 401
    assert (
        client.get("/auth/me", headers={"Authorization": "Bearer invalido"}).status_code
        == 401
    )

    wrong_password = client.post(
        "/auth/login",
        json={"login": "admin", "password": "errada"},
    )
    assert wrong_password.status_code == 401
    assert "Senha incorreta" in wrong_password.json()["detail"]

    unknown_login = client.post(
        "/auth/login",
        json={"login": "nao_existe", "password": "admin123"},
    )
    assert unknown_login.status_code == 401
    assert "Login não encontrado" in unknown_login.json()["detail"]


def test_change_password(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    changed = client.post(
        "/auth/change-password",
        headers=headers,
        json={"current_password": "admin123", "new_password": "nova123"},
    )
    assert changed.status_code == 200

    old_login = client.post(
        "/auth/login",
        json={"login": "admin", "password": "admin123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login",
        json={"login": "admin", "password": "nova123"},
    )
    assert new_login.status_code == 200

    wrong_current = client.post(
        "/auth/change-password",
        headers=headers,
        json={"current_password": "errada", "new_password": "outra123"},
    )
    assert wrong_current.status_code == 400
    assert "Senha atual incorreta" in wrong_current.json()["detail"]

    short_password = client.post(
        "/auth/change-password",
        headers=headers,
        json={"current_password": "nova123", "new_password": "123"},
    )
    assert short_password.status_code == 400
    assert "mínimo 6" in short_password.json()["detail"]


def test_user_management_and_last_admin_guard(client, auth_headers, create_user):
    user = create_user("recepcao", "Recepcionista")
    assert user["login"] == "recepcao"
    assert user["role"] == "Recepcionista"
    assert "password" not in user

    duplicate_login = client.post(
        "/users/create",
        headers=auth_headers,
        json={
            "name": "Outra Pessoa",
            "login": "recepcao",
            "email": "outra@example.com",
            "password": "secret123",
            "role": "Recepcionista",
        },
    )
    assert duplicate_login.status_code == 400
    assert "Login já existe" in duplicate_login.json()["detail"]

    duplicate_email = client.post(
        "/users/create",
        headers=auth_headers,
        json={
            "name": "Outra Pessoa",
            "login": "outra_pessoa",
            "email": "recepcao@example.com",
            "password": "secret123",
            "role": "Recepcionista",
        },
    )
    assert duplicate_email.status_code == 400
    assert "E-mail já cadastrado" in duplicate_email.json()["detail"]

    updated = client.put(
        f"/users/update/{user['id']}",
        headers=auth_headers,
        json={"name": "Recepcao Nova", "role": "Gerente"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Recepcao Nova"
    assert updated.json()["role"] == "Gerente"

    toggled = client.patch(
        f"/users/{user['id']}/toggle-active",
        headers=auth_headers,
    )
    assert toggled.status_code == 200
    assert toggled.json()["active"] is False

    inactive_login = client.post(
        "/auth/login",
        json={"login": "recepcao", "password": "secret123"},
    )
    assert inactive_login.status_code == 401
    assert "Usuário inativo" in inactive_login.json()["detail"]

    me = client.get("/auth/me", headers=auth_headers).json()
    last_admin = client.delete(
        f"/users/delete/{me['id']}",
        headers=auth_headers,
    )
    assert last_admin.status_code == 400
    assert "último administrador" in last_admin.json()["detail"]


def test_user_role_permissions(client, auth_headers, make_session):
    gerente = make_session("gerente1", "Gerente")
    recepcionista = make_session("recep1", "Recepcionista")

    assert client.get("/users/get", headers=auth_headers).status_code == 200
    assert client.get("/users/get", headers=gerente["headers"]).status_code == 200
    assert client.get("/users/get", headers=recepcionista["headers"]).status_code == 403

    new_user_payload = {
        "name": "Novo Usuario",
        "login": "novo_usuario",
        "email": "novo_usuario@example.com",
        "password": "secret123",
        "role": "Recepcionista",
    }
    assert (
        client.post(
            "/users/create",
            headers=gerente["headers"],
            json=new_user_payload,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/users/create",
            headers=recepcionista["headers"],
            json=new_user_payload,
        ).status_code
        == 403
    )

    users = client.get("/users/get", headers=auth_headers).json()
    assert users["total"] >= 3
