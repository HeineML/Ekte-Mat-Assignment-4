import pytest

from app import format_nok
from app.models.entities import EventCategory, FoodItem
from app.models.services import menu_by_event


@pytest.fixture
def menu(repos):
    """Two categories with a shared item, a single-category item and an unpublished item."""
    wedding = repos.food.add_category(EventCategory("Wedding"))
    christmas = repos.food.add_category(EventCategory("Christmas party"))
    repos.food.add_category(EventCategory("Conference"))  # stays empty

    def add(name, categories, published=True, price=650):
        return repos.food.add(FoodItem(
            name=name, description=f"{name} description", price_nok=price, minimum_quantity=10,
            published=published, allergens=["milk", "gluten"], dietary_labels=["vegetarian"],
            event_categories=categories,
        ))

    add("Cream cake", [wedding, christmas])
    add("Pinnekjøtt", [christmas], price=1250)
    add("Secret draft", [wedding], published=False)
    return {"wedding": wedding, "christmas": christmas}


def names(items):
    return [i.name for i in items]


def test_menu_by_event_groups_and_skips_empty_and_unpublished(menu):
    sections = menu_by_event()
    assert [(c.name, names(items)) for c, items in sections] == [
        ("Christmas party", ["Cream cake", "Pinnekjøtt"]),
        ("Wedding", ["Cream cake"]),
    ]


def test_menu_by_event_single_category(menu):
    sections = menu_by_event(menu["wedding"].id)
    assert [(c.name, names(items)) for c, items in sections] == [("Wedding", ["Cream cake"])]


def test_menu_by_event_unknown_category(menu):
    assert menu_by_event(999) is None


@pytest.mark.parametrize("url", ["/", "/menu"])
def test_menu_page_shows_published_items_grouped(client, menu, url):
    response = client.get(url)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "<h2>Christmas party</h2>" in html
    assert "<h2>Wedding</h2>" in html
    assert "<h2>Conference</h2>" not in html
    assert "Pinnekjøtt" in html
    assert "Secret draft" not in html


def test_menu_page_filtered_by_event(client, menu):
    html = client.get(f"/menu?event={menu['wedding'].id}").get_data(as_text=True)
    assert "<h2>Wedding</h2>" in html
    assert "<h2>Christmas party</h2>" not in html
    assert "Cream cake" in html
    assert "Pinnekjøtt" not in html


@pytest.mark.parametrize("event", ["999", "abc"])
def test_unknown_event_is_404(client, menu, event):
    assert client.get(f"/menu?event={event}").status_code == 404


def test_food_card_shows_required_fields(client, menu):
    html = client.get("/").get_data(as_text=True)
    assert "Cream cake description" in html
    assert "650 kr" in html
    assert "1 250 kr" in html
    assert "Minimum order: 10" in html
    assert "Allergens: milk, gluten" in html
    assert '<li class="badge">vegetarian</li>' in html
    assert "img/placeholder.svg" in html


def test_empty_menu_message(client):
    html = client.get("/").get_data(as_text=True)
    assert "There are no dishes on the menu yet." in html


def test_nok_format():
    assert format_nok(650) == "650 kr"
    assert format_nok(1250) == "1 250 kr"
    assert format_nok(1250000) == "1 250 000 kr"
