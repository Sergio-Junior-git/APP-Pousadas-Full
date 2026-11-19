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


def test_reservation_creation_and_business_rules(
    client,
    auth_headers,
    create_guest,
):
    guest = create_guest(full_name="Hospede Reserva")
    room_101 = room_id_by_number(client, auth_headers, "101")
    room_103 = room_id_by_number(client, auth_headers, "103")
    room_201 = room_id_by_number(client, auth_headers, "201")
    room_202 = room_id_by_number(client, auth_headers, "202")
    room_203 = room_id_by_number(client, auth_headers, "203")

    check_in = date.today() + timedelta(days=40)
    check_out = check_in + timedelta(days=2)

    reservation = client.post(
        "/reservations/create",
        headers=auth_headers,
        json={
            "guest_id": guest["id"],
            "room_id": room_202,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "adults": 2,
            "children": 0,
        },
    )
    assert reservation.status_code == 201, reservation.text
    data = reservation.json()
    assert data["status"] == "Pendente"
    assert data["nights"] == 2
    assert data["daily_rate"] == 220.0
    assert data["total_amount"] == 440.0
    assert data["guest_name"] == "Hospede Reserva"
    assert data["room_number"] == "202"

    overbooking = client.post(
        "/reservations/create",
        headers=auth_headers,
        json={
            "guest_id": guest["id"],
            "room_id": room_202,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "adults": 1,
        },
    )
    assert overbooking.status_code == 400
    assert "Quarto indisponível" in overbooking.json()["detail"]

    other_room = client.post(
        "/reservations/create",
        headers=auth_headers,
        json={
            "guest_id": guest["id"],
            "room_id": room_101,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "adults": 2,
        },
    )
    assert other_room.status_code == 201, other_room.text

    invalid_guest = client.post(
        "/reservations/create",
        headers=auth_headers,
        json={
            "guest_id": 99999,
            "room_id": room_202,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
        },
    )
    assert invalid_guest.status_code == 400
    assert "Hóspede não encontrado" in invalid_guest.json()["detail"]

    maintenance_room = client.post(
        "/reservations/create",
        headers=auth_headers,
        json={
            "guest_id": guest["id"],
            "room_id": room_203,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
        },
    )
    assert maintenance_room.status_code == 400
    assert "manutenção" in maintenance_room.json()["detail"]

    capacity = client.post(
        "/reservations/create",
        headers=auth_headers,
        json={
            "guest_id": guest["id"],
            "room_id": room_103,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "adults": 2,
        },
    )
    assert capacity.status_code == 400
    assert "Capacidade" in capacity.json()["detail"]

    invalid_period = client.post(
        "/reservations/create",
        headers=auth_headers,
        json={
            "guest_id": guest["id"],
            "room_id": room_202,
            "check_in_date": check_out.isoformat(),
            "check_out_date": check_in.isoformat(),
        },
    )
    assert invalid_period.status_code == 422

    discount_check_in = date.today() + timedelta(days=44)
    discount_check_out = discount_check_in + timedelta(days=2)
    excessive_discount = client.post(
        "/reservations/create",
        headers=auth_headers,
        json={
            "guest_id": guest["id"],
            "room_id": room_201,
            "check_in_date": discount_check_in.isoformat(),
            "check_out_date": discount_check_out.isoformat(),
            "adults": 2,
            "discount": 1000,
        },
    )
    assert excessive_discount.status_code == 400
    assert "Desconto" in excessive_discount.json()["detail"]

    custom_rate_check_in = date.today() + timedelta(days=50)
    custom_rate_check_out = custom_rate_check_in + timedelta(days=2)
    custom_rate = client.post(
        "/reservations/create",
        headers=auth_headers,
        json={
            "guest_id": guest["id"],
            "room_id": room_201,
            "check_in_date": custom_rate_check_in.isoformat(),
            "check_out_date": custom_rate_check_out.isoformat(),
            "adults": 2,
            "daily_rate": 100,
        },
    )
    assert custom_rate.status_code == 201, custom_rate.text
    assert custom_rate.json()["total_amount"] == 200.0

    status_check_in = date.today() + timedelta(days=60)
    status_check_out = status_check_in + timedelta(days=2)
    invalid_status = client.post(
        "/reservations/create",
        headers=auth_headers,
        json={
            "guest_id": guest["id"],
            "room_id": room_202,
            "check_in_date": status_check_in.isoformat(),
            "check_out_date": status_check_out.isoformat(),
            "status": "CheckIn",
        },
    )
    assert invalid_status.status_code == 400
    assert "Pendente ou Confirmada" in invalid_status.json()["detail"]

    zero_rate_check_in = date.today() + timedelta(days=70)
    zero_rate_check_out = zero_rate_check_in + timedelta(days=2)
    zero_rate = client.post(
        "/reservations/create",
        headers=auth_headers,
        json={
            "guest_id": guest["id"],
            "room_id": room_202,
            "check_in_date": zero_rate_check_in.isoformat(),
            "check_out_date": zero_rate_check_out.isoformat(),
            "daily_rate": 0,
        },
    )
    assert zero_rate.status_code == 400
    assert "diária" in zero_rate.json()["detail"]


def test_checkin_checkout_financial_flow(
    client,
    auth_headers,
    create_reservation,
):
    room_202 = room_id_by_number(client, auth_headers, "202")
    check_in = date.today() + timedelta(days=30)
    check_out = check_in + timedelta(days=2)

    reservation = create_reservation(
        room_id=room_202,
        check_in=check_in,
        check_out=check_out,
        adults=2,
    )
    reservation_id = reservation["id"]
    assert reservation["total_amount"] == 440.0

    checkin = client.post(
        f"/reservations/{reservation_id}/checkin",
        headers=auth_headers,
    )
    assert checkin.status_code == 200, checkin.text
    assert checkin.json()["status"] == "CheckIn"
    assert checkin.json()["room_number"] == "202"

    room_after_checkin = client.get(
        f"/rooms/{room_202}",
        headers=auth_headers,
    )
    assert room_after_checkin.status_code == 200
    assert room_after_checkin.json()["status"] == "Ocupado"

    payment = client.post(
        "/payments/create",
        headers=auth_headers,
        json={
            "reservation_id": reservation_id,
            "amount": reservation["total_amount"],
            "method": "Pix",
            "notes": "Pagamento integral",
        },
    )
    assert payment.status_code == 201, payment.text
    assert payment.json()["status"] == "Pago"
    assert payment.json()["amount"] == 440.0

    consumption = client.post(
        "/consumptions/create",
        headers=auth_headers,
        json={
            "reservation_id": reservation_id,
            "description": "Frigobar",
            "quantity": 2,
            "unit_price": 8,
        },
    )
    assert consumption.status_code == 201, consumption.text
    assert consumption.json()["total"] == 16.0

    updated = client.get(
        f"/reservations/{reservation_id}",
        headers=auth_headers,
    )
    assert updated.status_code == 200
    updated_data = updated.json()
    assert updated_data["total_consumptions"] == 16.0
    assert updated_data["total_amount"] == 456.0
    assert updated_data["total_paid"] == 440.0
    assert updated_data["balance_due"] == 16.0

    blocked_checkout = client.post(
        f"/reservations/{reservation_id}/checkout",
        headers=auth_headers,
        json={"force": False},
    )
    assert blocked_checkout.status_code == 400
    assert "saldo pendente" in blocked_checkout.json()["detail"]
    assert "16.00" in blocked_checkout.json()["detail"]

    checkout = client.post(
        f"/reservations/{reservation_id}/checkout",
        headers=auth_headers,
        json={"force": True, "notes": "Check-out de teste"},
    )
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["status"] == "CheckOut"
    assert checkout.json()["balance_due"] == 16.0

    room_after_checkout = client.get(
        f"/rooms/{room_202}",
        headers=auth_headers,
    )
    assert room_after_checkout.json()["status"] == "Limpeza"

    tasks = client.get(
        f"/housekeeping/get?room_id={room_202}",
        headers=auth_headers,
    )
    assert tasks.status_code == 200
    assert tasks.json()["total"] == 1
    task = tasks.json()["items"][0]
    assert task["status"] == "Pendente"
    assert task["priority"] == "Alta"

    assert (
        client.post(
            f"/reservations/{reservation_id}/checkout",
            headers=auth_headers,
            json={"force": True},
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/reservations/{reservation_id}/checkin",
            headers=auth_headers,
        ).status_code
        == 400
    )

    consumption_after_checkout = client.post(
        "/consumptions/create",
        headers=auth_headers,
        json={
            "reservation_id": reservation_id,
            "description": "Agua",
            "quantity": 1,
            "unit_price": 5,
        },
    )
    assert consumption_after_checkout.status_code == 400

    summary = client.get("/reports/summary", headers=auth_headers)
    assert summary.status_code == 200
    summary_data = summary.json()
    assert summary_data["total_rooms"] == 6
    assert summary_data["rooms_occupied"] == 1
    assert summary_data["rooms_cleaning"] == 2
    assert summary_data["rooms_available"] == 2
    assert summary_data["rooms_maintenance"] == 1
    assert summary_data["pending_housekeeping"] == 2
    assert summary_data["revenue_month"] == 1380.0

    revenue = client.get("/reports/revenue", headers=auth_headers)
    assert revenue.status_code == 200
    assert revenue.json()["total"] == 1380.0


def test_reservation_update_cancel_and_lock(
    client,
    auth_headers,
    create_reservation,
):
    room_202 = room_id_by_number(client, auth_headers, "202")
    room_203 = room_id_by_number(client, auth_headers, "203")

    check_in = date.today() + timedelta(days=50)
    check_out = check_in + timedelta(days=2)
    reservation = create_reservation(
        room_id=room_202,
        check_in=check_in,
        check_out=check_out,
        adults=2,
    )

    updated = client.put(
        f"/reservations/update/{reservation['id']}",
        headers=auth_headers,
        json={
            "check_out_date": (check_out + timedelta(days=1)).isoformat(),
            "notes": "Reserva estendida",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["nights"] == 3
    assert updated.json()["total_amount"] == 660.0

    maintenance_room = client.put(
        f"/reservations/update/{reservation['id']}",
        headers=auth_headers,
        json={"room_id": room_203},
    )
    assert maintenance_room.status_code == 400
    assert "manutenção" in maintenance_room.json()["detail"]

    cancelled = client.post(
        f"/reservations/{reservation['id']}/cancel",
        headers=auth_headers,
        json={"reason": "Teste de cancelamento"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "Cancelada"
    assert "Teste de cancelamento" in cancelled.json()["notes"]

    update_cancelled = client.put(
        f"/reservations/update/{reservation['id']}",
        headers=auth_headers,
        json={"notes": "Nao deve alterar"},
    )
    assert update_cancelled.status_code == 400
    assert "não pode ser alterada" in update_cancelled.json()["detail"]

    checkin_cancelled = client.post(
        f"/reservations/{reservation['id']}/checkin",
        headers=auth_headers,
    )
    assert checkin_cancelled.status_code == 400
    assert "pendentes ou confirmadas" in checkin_cancelled.json()["detail"]

    deleted_cancelled = client.delete(
        f"/reservations/delete/{reservation['id']}",
        headers=auth_headers,
    )
    assert deleted_cancelled.status_code == 200

    second_check_in = date.today() + timedelta(days=60)
    second_check_out = second_check_in + timedelta(days=2)
    second = create_reservation(
        room_id=room_202,
        check_in=second_check_in,
        check_out=second_check_out,
        adults=2,
    )

    checkin = client.post(
        f"/reservations/{second['id']}/checkin",
        headers=auth_headers,
    )
    assert checkin.status_code == 200

    notes_update = client.put(
        f"/reservations/update/{second['id']}",
        headers=auth_headers,
        json={"notes": "Observacao durante a estadia"},
    )
    assert notes_update.status_code == 200

    blocked_update = client.put(
        f"/reservations/update/{second['id']}",
        headers=auth_headers,
        json={"adults": 1},
    )
    assert blocked_update.status_code == 400
    assert "apenas as observações" in blocked_update.json()["detail"]

    delete_checked_in = client.delete(
        f"/reservations/delete/{second['id']}",
        headers=auth_headers,
    )
    assert delete_checked_in.status_code == 400
    assert "check-out" in delete_checked_in.json()["detail"]

    checkout = client.post(
        f"/reservations/{second['id']}/checkout",
        headers=auth_headers,
        json={"force": True},
    )
    assert checkout.status_code == 200
    assert checkout.json()["status"] == "CheckOut"

    delete_checked_out = client.delete(
        f"/reservations/delete/{second['id']}",
        headers=auth_headers,
    )
    assert delete_checked_out.status_code == 400
    assert "finalizada" in delete_checked_out.json()["detail"]


def test_payment_and_consumption_rules(
    client,
    auth_headers,
    create_reservation,
    make_session,
):
    room_202 = room_id_by_number(client, auth_headers, "202")
    reservation = create_reservation(
        room_id=room_202,
        check_in=date.today() + timedelta(days=70),
        check_out=date.today() + timedelta(days=72),
        adults=2,
    )
    reservation_id = reservation["id"]

    payment = client.post(
        "/payments/create",
        headers=auth_headers,
        json={
            "reservation_id": reservation_id,
            "amount": 100,
            "method": "Pix",
        },
    )
    assert payment.status_code == 201, payment.text
    payment_id = payment.json()["id"]

    delete_paid = client.delete(
        f"/payments/delete/{payment_id}",
        headers=auth_headers,
    )
    assert delete_paid.status_code == 400
    assert "Estorne" in delete_paid.json()["detail"]

    recepcionista = make_session("recep_pag", "Recepcionista")
    assert (
        client.post(
            f"/payments/{payment_id}/refund",
            headers=recepcionista["headers"],
            json={"notes": "Tentativa"},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/payments/delete/{payment_id}",
            headers=recepcionista["headers"],
        ).status_code
        == 403
    )

    refunded = client.post(
        f"/payments/{payment_id}/refund",
        headers=auth_headers,
        json={"notes": "Estorno solicitado"},
    )
    assert refunded.status_code == 200
    assert refunded.json()["status"] == "Estornado"
    assert "Estorno: Estorno solicitado" in refunded.json()["notes"]

    deleted = client.delete(
        f"/payments/delete/{payment_id}",
        headers=auth_headers,
    )
    assert deleted.status_code == 200

    zero_payment = client.post(
        "/payments/create",
        headers=auth_headers,
        json={
            "reservation_id": reservation_id,
            "amount": 0,
            "method": "Pix",
        },
    )
    assert zero_payment.status_code == 422

    pending_payment = client.post(
        "/payments/create",
        headers=auth_headers,
        json={
            "reservation_id": reservation_id,
            "amount": 50,
            "method": "Dinheiro",
            "status": "Pendente",
        },
    )
    assert pending_payment.status_code == 201, pending_payment.text
    pending_id = pending_payment.json()["id"]

    refund_pending = client.post(
        f"/payments/{pending_id}/refund",
        headers=auth_headers,
        json={},
    )
    assert refund_pending.status_code == 400
    assert "status Pago" in refund_pending.json()["detail"]

    assert (
        client.delete(
            f"/payments/delete/{pending_id}",
            headers=auth_headers,
        ).status_code
        == 200
    )

    missing_reservation = client.post(
        "/payments/create",
        headers=auth_headers,
        json={
            "reservation_id": 99999,
            "amount": 50,
            "method": "Pix",
        },
    )
    assert missing_reservation.status_code == 400
    assert "Reserva não encontrada" in missing_reservation.json()["detail"]

    cancelled_reservation = create_reservation(
        room_id=room_202,
        check_in=date.today() + timedelta(days=80),
        check_out=date.today() + timedelta(days=82),
        adults=2,
    )
    client.post(
        f"/reservations/{cancelled_reservation['id']}/cancel",
        headers=auth_headers,
        json={"reason": "Cancelada para teste"},
    )
    payment_cancelled = client.post(
        "/payments/create",
        headers=auth_headers,
        json={
            "reservation_id": cancelled_reservation["id"],
            "amount": 50,
            "method": "Pix",
        },
    )
    assert payment_cancelled.status_code == 400
    assert "cancelada" in payment_cancelled.json()["detail"]

    consumption = client.post(
        "/consumptions/create",
        headers=auth_headers,
        json={
            "reservation_id": reservation_id,
            "description": "Frigobar",
            "quantity": 2,
            "unit_price": 8,
        },
    )
    assert consumption.status_code == 201, consumption.text
    consumption_id = consumption.json()["id"]
    assert consumption.json()["total"] == 16.0

    updated = client.put(
        f"/consumptions/update/{consumption_id}",
        headers=auth_headers,
        json={"quantity": 3},
    )
    assert updated.status_code == 200
    assert updated.json()["total"] == 24.0

    listed = client.get(
        f"/consumptions/get?reservation_id={reservation_id}",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    fetched = client.get(
        f"/consumptions/{consumption_id}",
        headers=auth_headers,
    )
    assert fetched.status_code == 200

    assert (
        client.delete(
            f"/consumptions/delete/{consumption_id}",
            headers=recepcionista["headers"],
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/consumptions/delete/{consumption_id}",
            headers=auth_headers,
        ).status_code
        == 200
    )

    consumption_cancelled = client.post(
        "/consumptions/create",
        headers=auth_headers,
        json={
            "reservation_id": cancelled_reservation["id"],
            "description": "Agua",
            "quantity": 1,
            "unit_price": 5,
        },
    )
    assert consumption_cancelled.status_code == 400
    assert "não é possível" in consumption_cancelled.json()["detail"].lower()

    assert (
        client.post(
            "/consumptions/create",
            headers=auth_headers,
            json={
                "reservation_id": reservation_id,
                "description": "Agua",
                "quantity": 0,
                "unit_price": 5,
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/consumptions/create",
            headers=auth_headers,
            json={
                "reservation_id": reservation_id,
                "description": "Agua",
                "quantity": 1,
                "unit_price": -1,
            },
        ).status_code
        == 422
    )
