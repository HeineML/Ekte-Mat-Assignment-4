from datetime import date, timedelta

import pytest

from app.models.entities import EventCategory, FoodItem, Order, OrderItem
from app.models.services import parse_list
from tests.conftest import login


@pytest.fixture
def food(repos):
    birthday = repos.food.add_category(EventCategory("Birthday"))
    wedding = repos.food.add_category(EventCategory("Wedding"))
    cake = repos.food.add(FoodItem(name="Cake", description="Sponge cake", price_nok=650, published=True,
                                   allergens=["milk"], event_categories=[birthday]))
    draft = repos.food.add(FoodItem(name="Secret draft", description="Not ready", price_nok=100,
                                    published=False, event_categories=[birthday]))
    return {"birthday": birthday, "wedding": wedding, "cake": cake, "draft": draft}


@pytest.fixture
def admin(client, users):
    login(client, "admin@test.test")


def item_form(food, **overrides):
    """A valid form; an override of None leaves that field out (like an unticked checkbox)."""
    form = {"name": "Lasagne", "description": "Beef lasagne", "price_nok": "149", "minimum_quantity": "10",
            "category_ids": [food["birthday"].id, food["wedding"].id], "allergens": "gluten, milk, gluten",
            "dietary_labels": "", "published": "on", **overrides}
    return {key: value for key, value in form.items() if value is not None}


ROUTES = [("get", "/admin/food"), ("get", "/admin/food/new"), ("post", "/admin/food/new"),
          ("get", "/admin/food/1/edit"), ("post", "/admin/food/1/edit"),
          ("post", "/admin/food/1/delete"), ("post", "/admin/food/1/toggle-published")]


@pytest.mark.parametrize("method, url", ROUTES)
def test_routes_require_admin(client, users, food, method, url):
    assert getattr(client, method)(url).status_code == 302  # logged out → login
    login(client, "kari@test.test")
    assert getattr(client, method)(url).status_code == 403


def test_admin_login_lands_on_admin_page(client, users):
    assert login(client, "admin@test.test").headers["Location"].startswith("/admin/")


def test_parse_list():
    assert parse_list(" gluten, milk,, gluten ,") == ["gluten", "milk"]
    assert parse_list("") == []


def test_list_shows_published_and_unpublished(client, admin, food):
    html = client.get("/admin/food").get_data(as_text=True)
    assert "Cake" in html and "Secret draft" in html
    assert "Unpublished" in html


def test_create_item(client, admin, food, repos):
    response = client.post("/admin/food/new", data=item_form(food))
    assert response.headers["Location"] == "/admin/food"
    item = next(i for i in repos.food.list_all() if i.name == "Lasagne")
    assert (item.price_nok, item.minimum_quantity, item.published) == (149, 10, True)
    assert item.allergens == ["gluten", "milk"]
    assert {c.name for c in item.event_categories} == {"Birthday", "Wedding"}
    assert "Lasagne" in client.get("/menu").get_data(as_text=True)


@pytest.mark.parametrize("overrides, message", [
    ({"name": " "}, "Please enter a name."),
    ({"description": ""}, "Please enter a description."),
    ({"price_nok": "-1"}, "The price must be a whole number"),
    ({"price_nok": "12.50"}, "The price must be a whole number"),
    ({"minimum_quantity": "0"}, "The minimum order quantity must be"),
    ({"category_ids": []}, "Choose at least one event category"),
])
def test_create_validation(client, admin, food, repos, overrides, message):
    response = client.post("/admin/food/new", data=item_form(food, **overrides))
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    assert len(repos.food.list_all()) == 2


def test_edit_item(client, admin, food, repos):
    cake = food["cake"]
    form = client.get(f"/admin/food/{cake.id}/edit").get_data(as_text=True)
    assert 'value="Cake"' in form and 'value="milk"' in form

    client.post(f"/admin/food/{cake.id}/edit",
                data=item_form(food, name="Big cake", price_nok="700", category_ids=[food["wedding"].id],
                               published=None))
    cake = repos.food.get(cake.id)
    assert (cake.name, cake.price_nok, cake.published) == ("Big cake", 700, False)
    assert [c.name for c in cake.event_categories] == ["Wedding"]


def test_toggle_published(client, admin, food, repos):
    draft = food["draft"]
    client.post(f"/admin/food/{draft.id}/toggle-published")
    assert repos.food.get(draft.id).published is True
    client.post(f"/admin/food/{draft.id}/toggle-published")
    assert repos.food.get(draft.id).published is False


def test_delete_keeps_old_orders(client, admin, food, repos, users):
    cake = food["cake"]
    order = repos.orders.add(Order(customer_id=users["kari"].id, event_date=date.today() + timedelta(days=5),
                                   number_of_guests=10, delivery_address="Testveien 1",
                                   items=[OrderItem(cake.id, cake.name, 2, cake.price_nok)]))
    client.post(f"/admin/food/{cake.id}/delete")
    assert repos.food.get(cake.id) is None
    item = repos.orders.get(order.id).items[0]
    assert (item.food_item_id, item.food_name, item.unit_price_nok) == (None, "Cake", 650)


@pytest.mark.parametrize("method, url", [("get", "/admin/food/999/edit"), ("post", "/admin/food/999/delete"),
                                         ("post", "/admin/food/999/toggle-published")])
def test_unknown_item_is_404(client, admin, food, method, url):
    assert getattr(client, method)(url).status_code == 404


def test_admin_nav_only_for_admins(client, users, food):
    login(client, "kari@test.test")
    assert 'href="/admin/food"' not in client.get("/").get_data(as_text=True)
    client.post("/logout")
    login(client, "admin@test.test")
    assert 'href="/admin/food"' in client.get("/").get_data(as_text=True)
