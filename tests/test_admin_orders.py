from datetime import date, timedelta

import pytest

from app.models.entities import GuestGroup, Order, OrderItem, OrderStatus, PaymentStatus
from tests.conftest import login

IN_10_DAYS = date.today() + timedelta(days=10)
IN_20_DAYS = date.today() + timedelta(days=20)


@pytest.fixture
def orders(repos, users):
    def add(customer, event_date, status=OrderStatus.SUBMITTED):
        return repos.orders.add(Order(
            customer_id=customer.id, event_date=event_date, number_of_guests=10, delivery_address="Testveien 1",
            items=[OrderItem(None, "Cake", 2, 650)],
            guest_groups=[GuestGroup("Children", 4, allergy_notes="Nut allergy")], status=status))

    return {"kari_submitted": add(users["kari"], IN_10_DAYS),
            "kari_approved": add(users["kari"], IN_20_DAYS, OrderStatus.APPROVED),
            "ola_approved": add(users["ola"], IN_10_DAYS, OrderStatus.APPROVED)}


@pytest.fixture
def admin(client, users):
    login(client, "admin@test.test")


def order_ids_in(html, orders):
    return {name for name, order in orders.items() if f">#{order.id}<" in html}


@pytest.mark.parametrize("method, url", [("get", "/admin/orders"), ("get", "/admin/orders/1"),
                                         ("post", "/admin/orders/1/status"), ("post", "/admin/orders/1/payment")])
def test_routes_require_admin(client, orders, method, url):
    assert getattr(client, method)(url).status_code == 302
    login(client, "kari@test.test")
    assert getattr(client, method)(url).status_code == 403


def test_admin_lands_on_orders(client, users):
    assert login(client, "admin@test.test").headers["Location"] == "/admin/orders"


def test_list_shows_all_orders(client, admin, orders):
    html = client.get("/admin/orders").get_data(as_text=True)
    assert order_ids_in(html, orders) == set(orders)
    assert "Kari" in html and "Ola" in html


@pytest.mark.parametrize("query, expected", [
    ("?status=approved", {"kari_approved", "ola_approved"}),
    (f"?event_date={IN_10_DAYS.isoformat()}", {"kari_submitted", "ola_approved"}),
    (f"?status=approved&event_date={IN_10_DAYS.isoformat()}", {"ola_approved"}),
    ("?status=delivered", set()),
])
def test_filters(client, admin, orders, query, expected):
    html = client.get("/admin/orders" + query).get_data(as_text=True)
    assert order_ids_in(html, orders) == expected


@pytest.mark.parametrize("query", ["?status=bogus", "?event_date=31-12-2026"])
def test_invalid_filter_is_ignored(client, admin, orders, query):
    html = client.get("/admin/orders" + query).get_data(as_text=True)
    assert order_ids_in(html, orders) == set(orders)
    assert 'class="flash flash-error"' in html


def test_detail(client, admin, orders):
    html = client.get(f"/admin/orders/{orders['kari_submitted'].id}").get_data(as_text=True)
    for text in ["Kari", "kari@test.test", "Testveien 1", "Cake", "1 300 kr", "Children", "Nut allergy",
                 "Submitted", "Not paid"]:
        assert text in html


def test_change_status_and_payment(client, admin, orders, repos):
    order = orders["kari_submitted"]
    response = client.post(f"/admin/orders/{order.id}/status", data={"status": "in_preparation"})
    assert response.headers["Location"] == f"/admin/orders/{order.id}"
    client.post(f"/admin/orders/{order.id}/payment", data={"payment_status": "invoiced"})
    saved = repos.orders.get(order.id)
    assert (saved.status, saved.payment_status) == (OrderStatus.IN_PREPARATION, PaymentStatus.INVOICED)

    client.post("/logout")
    login(client, "kari@test.test")
    html = client.get(f"/orders/{order.id}").get_data(as_text=True)
    assert "In preparation" in html and "Invoiced" in html


def test_invalid_status_value_is_400(client, admin, orders, repos):
    order = orders["kari_submitted"]
    assert client.post(f"/admin/orders/{order.id}/status", data={"status": "done"}).status_code == 400
    assert client.post(f"/admin/orders/{order.id}/payment", data={"payment_status": "free"}).status_code == 400
    assert repos.orders.get(order.id).status == OrderStatus.SUBMITTED


def test_unknown_order_is_404(client, admin):
    assert client.get("/admin/orders/999").status_code == 404
    assert client.post("/admin/orders/999/status", data={"status": "approved"}).status_code == 404
