"""Domain rules that use the repositories. Controllers call these instead of repeating logic."""
from dataclasses import dataclass, field

from app.models import get_repos
from app.models.entities import FoodItem


def menu_by_event(category_id=None):
    """Published menu grouped by event category, as a list of (EventCategory, [FoodItem]).

    With category_id, only that category is returned. Empty categories are skipped.
    Returns None if category_id doesn't exist.
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
        items = food.list_published(category_id=category.id)
        if items:
            sections.append((category, items))
    return sections


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
