"""Domain rules that use the repositories. Controllers call these instead of repeating logic."""
from app.models import get_repos


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
