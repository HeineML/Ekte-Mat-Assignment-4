"""Domain rules that use the repositories. Controllers call these instead of repeating logic."""
from dataclasses import dataclass, field
from datetime import date

from werkzeug.security import check_password_hash, generate_password_hash

from app.models import get_repos, images
from app.models.entities import FoodItem, GuestGroup, Order, OrderItem, Question, Role, User
from app.models.repositories import EmailAlreadyRegistered

MIN_PASSWORD_LENGTH = 8


def menu_by_event(category_id=None, exclude_allergens=(), require_labels=()):
    """Published menu grouped by event category, as a list of (EventCategory, [FoodItem]).

    With category_id, only that category is returned. exclude_allergens and require_labels filter
    the dishes (C1): no dish contains any of the excluded allergens, and every dish has all the
    required dietary labels. Empty categories are skipped. Returns None if category_id doesn't exist.
    """
    food = get_repos().food
    if category_id is not None:
        category = food.get_category(category_id)
        if category is None:
            return None
        categories = [category]
    else:
        categories = food.list_categories()

    sections = []
    for category in categories:
        items = food.list_published(category_id=category.id, exclude_allergens=exclude_allergens,
                                    require_labels=require_labels)
        if items:
            sections.append((category, items))
    return sections


def menu_filters(without, diet):
    """The menu filter options and the valid selections among the raw values from the URL.

    Returns (allergens, labels, selected_without, selected_diet). Only allergens and dietary labels
    used by published dishes can be chosen; anything else in the URL is ignored.
    """
    food = get_repos().food
    allergens, labels = food.list_allergens(), food.list_dietary_labels()
    return (allergens, labels,
            [a for a in allergens if a in without], [l for l in labels if l in diet])


# Shopping cart (C2). The controller keeps the raw cart, {food_item_id: quantity}, in the session;
# these functions only apply the domain rules to it.

@dataclass
class CartLine:
    item: FoodItem
    quantity: int

    @property
    def line_total(self):
        return self.quantity * self.item.price_nok


@dataclass
class Cart:
    lines: list[CartLine] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)  # names of items no longer available

    @property
    def total(self):
        return sum(line.line_total for line in self.lines)


def check_quantity(item, quantity):
    """Return an error message if quantity is not allowed for this food item, otherwise None."""
    if quantity < item.minimum_quantity:
        return f"Minimum order for {item.name} is {item.minimum_quantity}."
    return None


def build_cart(raw):
    """Turn {food_item_id: quantity} into a Cart priced with current prices.

    Items that no longer exist or are unpublished are left out; the names of
    unpublished ones are listed in Cart.removed.
    """
    food = get_repos().food
    cart = Cart()
    for item_id, quantity in raw.items():
        item = food.get(item_id)
        if item is None or not item.published:
            if item is not None:
                cart.removed.append(item.name)
            continue
        cart.lines.append(CartLine(item, quantity))
    return cart


# Register and login (C3, §8). Passwords are only ever stored as werkzeug hashes.

def register_customer(name, email, password, password2):
    """Create a customer account. Returns (user, []) on success or (None, [error messages]).

    Public registration always creates customers; admin accounts come from the seed data.
    """
    name, email = name.strip(), email.strip().lower()
    errors = []
    if not name:
        errors.append("Please enter your name.")
    if "@" not in email:
        errors.append("Please enter a valid email address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"The password must be at least {MIN_PASSWORD_LENGTH} characters.")
    elif password != password2:
        errors.append("The passwords don't match.")
    if errors:
        return None, errors

    user = User(name=name, email=email, password_hash=generate_password_hash(password), role=Role.CUSTOMER)
    try:
        return get_repos().users.add(user), []
    except EmailAlreadyRegistered:
        return None, ["An account with this email already exists."]


def authenticate(email, password):
    """Return the user if the email and password match, otherwise None."""
    user = get_repos().users.get_by_email(email.strip())
    if user is None or not check_password_hash(user.password_hash, password):
        return None
    return user


# Checkout (C3). The controller parses the form; values it couldn't parse arrive as None.

def place_order(customer_id, cart, event_date, number_of_guests, delivery_address, guest_groups):
    """Validate the checkout and save the order. Returns (order, []) or (None, [error messages]).

    `cart` comes from build_cart(), so prices are current and only published items are left.
    Each OrderItem copies the dish's name and price, so later edits don't change the order.
    If guest_groups is empty, one "All guests" group is stored.
    """
    errors = []
    if not cart.lines:
        errors.append("Your cart is empty.")
    for line in cart.lines:
        if error := check_quantity(line.item, line.quantity):
            errors.append(error)

    if event_date is None:
        errors.append("Please enter a valid event date.")
    elif event_date <= date.today():
        errors.append("The event date must be after today.")
    if number_of_guests is None or number_of_guests < 1:
        errors.append("The number of guests must be at least 1.")
    delivery_address = delivery_address.strip()
    if not delivery_address:
        errors.append("Please enter a delivery address.")

    for number, group in enumerate(guest_groups, start=1):
        if not group.description or group.size is None or group.size < 1:
            errors.append(f"Guest group {number} needs a description and a size of at least 1.")
    sizes = [g.size for g in guest_groups if g.size is not None and g.size > 0]
    if number_of_guests and sum(sizes) > number_of_guests:
        errors.append(f"The guest groups add up to {sum(sizes)} people, "
                      f"which is more than the {number_of_guests} guests.")
    if errors:
        return None, errors

    order = Order(
        customer_id=customer_id, event_date=event_date, number_of_guests=number_of_guests,
        delivery_address=delivery_address,
        items=[OrderItem(food_item_id=line.item.id, food_name=line.item.name, quantity=line.quantity,
                         unit_price_nok=line.item.price_nok) for line in cart.lines],
        guest_groups=guest_groups or [GuestGroup("All guests", number_of_guests)],
    )
    return get_repos().orders.add(order), []


# Admin food items (A1).

def parse_list(text):
    """'gluten, milk,, gluten' -> ['gluten', 'milk']: comma-separated, trimmed, no blanks or duplicates."""
    values = []
    for part in text.split(","):
        part = part.strip()
        if part and part not in values:
            values.append(part)
    return values


def save_food_item(item, *, name, description, price_nok, minimum_quantity, category_ids,
                   allergens, dietary_labels, published, image_file=None, remove_image=False):
    """Create (item=None) or update a food item. Returns (item, []) or (None, [error messages]).

    price_nok and minimum_quantity are None if the input wasn't a whole number. allergens and
    dietary_labels are comma-separated text. image_file is an uploaded picture (A2) that replaces
    the current one; without it the item keeps its image unless remove_image is set. Files are only
    written once everything is valid, and a replaced picture's file is deleted.
    """
    food = get_repos().food
    name, description = name.strip(), description.strip()
    categories = [c for c in (food.get_category(i) for i in category_ids) if c is not None]

    errors = []
    if not name:
        errors.append("Please enter a name.")
    if not description:
        errors.append("Please enter a description.")
    if price_nok is None or price_nok < 0:
        errors.append("The price must be a whole number of NOK, 0 or more.")
    if minimum_quantity is None or minimum_quantity < 1:
        errors.append("The minimum order quantity must be a whole number, at least 1.")
    if not categories:
        errors.append("Choose at least one event category, otherwise the dish won't appear on the menu.")
    if image_file is not None and not images.is_allowed(image_file):
        errors.append("The picture must be a PNG, JPEG, GIF or WebP file.")
    if errors:
        return None, errors

    old_image = item.image if item else None
    image = old_image
    if image_file is not None:
        image = images.save_image(image_file)
    elif remove_image:
        image = None

    fields = dict(name=name, description=description, price_nok=price_nok, minimum_quantity=minimum_quantity,
                  published=published, image=image, allergens=parse_list(allergens),
                  dietary_labels=parse_list(dietary_labels), event_categories=categories)
    if item is None:
        saved = food.add(FoodItem(**fields))
    else:
        for key, value in fields.items():
            setattr(item, key, value)
        saved = food.update(item)
    if old_image and old_image != image:
        images.delete_image(old_image)
    return saved, []


def delete_food_item(item):
    """Delete the food item and its picture. Old orders keep the dish's name and price."""
    get_repos().food.delete(item.id)
    images.delete_image(item.image)


# Admin orders (A3).

def customers_by_id(records):
    """{customer_id: User} for the customers of these orders or questions, so lists can show names."""
    users = get_repos().users
    return {customer_id: users.get(customer_id) for customer_id in {r.customer_id for r in records}}


# Questions and answers (C5, A4).

MAX_QUESTION_LENGTH = 2000


def _check_text(text, what):
    if not text:
        return [f"Please write {what}."]
    if len(text) > MAX_QUESTION_LENGTH:
        return [f"The {what.split()[-1]} can be at most {MAX_QUESTION_LENGTH} characters."]
    return []


def ask_question(order, customer_id, text):
    """Save a customer's question about their order. Returns (question, []) or (None, [errors]).

    The caller must already have checked that the order belongs to the customer.
    """
    text = text.strip()
    if errors := _check_text(text, "a question"):
        return None, errors
    return get_repos().questions.add(Question(order_id=order.id, customer_id=customer_id, question=text)), []


def answer_question(question, text):
    """Store (or replace) the admin's answer. Returns a list of error messages, empty on success."""
    text = text.strip()
    if errors := _check_text(text, "an answer"):
        return errors
    get_repos().questions.answer(question.id, text)
    return []
