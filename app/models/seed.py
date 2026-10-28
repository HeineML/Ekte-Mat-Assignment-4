"""CLI commands `init-db` and `seed`. They only use the repository interface, so they work for any backend.

All data here is synthetic. The demo passwords are for local test accounts only.
"""
from datetime import date, timedelta

import click
from werkzeug.security import generate_password_hash

from app.models.entities import (
    EventCategory, FoodItem, GuestGroup, Order, OrderItem, OrderStatus, PaymentStatus, Question, Role, User,
)

DEMO_ACCOUNTS = [
    ("Ada Admin", "admin@example.test", "admin123", Role.ADMIN),
    ("Kari Kunde", "kari@example.test", "kunde123", Role.CUSTOMER),
    ("Ola Testesen", "ola@example.test", "kunde123", Role.CUSTOMER),
]

CATEGORIES = ["Birthday", "Confirmation", "Wedding", "Conference", "Christmas party"]

# name, description, price NOK, minimum quantity, published, allergens, dietary labels, categories
FOOD_ITEMS = [
    ("Open sandwiches", "Classic Norwegian open sandwiches with ham, egg and cheese.", 45, 20, True,
     ["gluten", "milk", "eggs"], [], ["Birthday", "Confirmation", "Conference"]),
    ("Cream cake", "Layered sponge cake with cream and fresh berries. Serves 12.", 650, 1, True,
     ["gluten", "milk", "eggs"], ["vegetarian"], ["Birthday", "Confirmation", "Wedding"]),
    ("Roast beef with potato salad", "Sliced roast beef, potato salad and pickled cucumber.", 189, 10, True,
     ["eggs", "mustard"], ["gluten-free"], ["Confirmation", "Wedding"]),
    ("Baked salmon with dill sauce", "Oven-baked salmon, dill sauce and new potatoes.", 229, 10, True,
     ["fish", "milk"], ["gluten-free"], ["Wedding", "Conference"]),
    ("Lentil curry", "Red lentil curry with rice and coriander.", 159, 10, True,
     [], ["vegan", "gluten-free"], ["Birthday", "Conference"]),
    ("Shrimp sandwich", "Open sandwich with shrimp, mayonnaise and lemon.", 89, 10, True,
     ["gluten", "crustaceans", "eggs", "milk"], [], ["Confirmation", "Wedding"]),
    ("Pork rib with sauerkraut", "Christmas pork rib with crackling, sauerkraut and potatoes.", 289, 10, True,
     ["gluten", "celery"], [], ["Christmas party"]),
    ("Pinnekjøtt", "Salted, dried lamb ribs with mashed swede and potatoes.", 329, 10, True,
     ["milk"], ["gluten-free"], ["Christmas party"]),
    ("Rice cream with red sauce", "Cold rice pudding with whipped cream and berry sauce.", 59, 10, True,
     ["milk"], ["vegetarian", "gluten-free"], ["Christmas party", "Confirmation"]),
    ("Fruit platter", "Seasonal fruit, cut and ready to serve.", 79, 10, True,
     [], ["vegan", "gluten-free"], ["Birthday", "Conference", "Wedding"]),
    ("Sushi platter", "Draft item, not yet on the menu.", 249, 5, False,
     ["fish", "soy", "sesame", "gluten"], [], ["Conference"]),
]


def reset_storage():
    from app.models import get_repos
    get_repos().reset()


def seed_data():
    """Fill empty storage with synthetic demo data. Returns a summary dict."""
    from app.models import get_repos
    repos = get_repos()

    users = {}
    for name, email, password, role in DEMO_ACCOUNTS:
        users[email] = repos.users.add(User(name=name, email=email,
                                            password_hash=generate_password_hash(password), role=role))

    categories = {name: repos.food.add_category(EventCategory(name=name)) for name in CATEGORIES}

    food = {}
    for name, description, price, minimum, published, allergens, labels, cats in FOOD_ITEMS:
        food[name] = repos.food.add(FoodItem(
            name=name, description=description, price_nok=price, minimum_quantity=minimum,
            published=published, allergens=allergens, dietary_labels=labels,
            event_categories=[categories[c] for c in cats],
        ))

    def line(food_name, quantity):
        item = food[food_name]
        return OrderItem(food_item_id=item.id, food_name=item.name, quantity=quantity,
                         unit_price_nok=item.price_nok)

    today = date.today()
    kari, ola = users["kari@example.test"], users["ola@example.test"]
    confirmation = repos.orders.add(Order(
        customer_id=kari.id, event_date=today + timedelta(days=30), number_of_guests=40,
        delivery_address="Testveien 1, 5000 Bergen",
        items=[line("Open sandwiches", 60), line("Cream cake", 4), line("Roast beef with potato salad", 40)],
        guest_groups=[
            GuestGroup("Adults", 30),
            GuestGroup("Children", 8, allergy_notes="Two children are allergic to milk."),
            GuestGroup("Vegetarians", 2, dietary_notes="Vegetarian."),
        ],
    ))
    repos.orders.add(Order(
        customer_id=kari.id, event_date=today + timedelta(days=7), number_of_guests=15,
        delivery_address="Testveien 1, 5000 Bergen",
        items=[line("Lentil curry", 15), line("Fruit platter", 15)],
        guest_groups=[GuestGroup("All guests", 15, dietary_notes="Several vegans.")],
        status=OrderStatus.APPROVED, payment_status=PaymentStatus.DEPOSIT_PAID,
    ))
    christmas = repos.orders.add(Order(
        customer_id=ola.id, event_date=today + timedelta(days=55), number_of_guests=25,
        delivery_address="Eksempelgata 12, 5003 Bergen",
        items=[line("Pork rib with sauerkraut", 15), line("Pinnekjøtt", 10), line("Rice cream with red sauce", 25)],
        guest_groups=[
            GuestGroup("Employees", 24),
            GuestGroup("Guest with celiac disease", 1, allergy_notes="Gluten (celiac disease)."),
        ],
        status=OrderStatus.IN_PREPARATION, payment_status=PaymentStatus.INVOICED,
    ))

    answered = repos.questions.add(Question(
        order_id=confirmation.id, customer_id=kari.id,
        question="Can the children's portions be marked so we know which ones are milk-free?",
    ))
    repos.questions.answer(answered.id, "Yes, milk-free portions are packed separately and labelled.")
    repos.questions.add(Question(
        order_id=christmas.id, customer_id=ola.id,
        question="Is it possible to move the delivery time to 17:00?",
    ))

    return {"users": len(users), "categories": len(categories), "food items": len(food),
            "orders": 3, "questions": 2}


def register_commands(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Delete all data and create empty storage."""
        reset_storage()
        click.echo("Initialised empty database.")

    @app.cli.command("seed")
    def seed_command():
        """Reset storage and load synthetic demo data."""
        reset_storage()
        summary = seed_data()
        click.echo("Seeded: " + ", ".join(f"{n} {k}" for k, n in summary.items()) + ".")
        click.echo("Demo logins (local test data only):")
        for _, email, password, role in DEMO_ACCOUNTS:
            click.echo(f"  {role.value:<8} {email} / {password}")
