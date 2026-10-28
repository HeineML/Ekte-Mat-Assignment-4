"""Repository interfaces: the contract between the rest of the app and the storage backend.

Controllers and views only use these methods. Each backend (SQLite now, maybe Neo4j later)
implements them and returns entities from app.models.entities, never rows or queries.
"""
from abc import ABC, abstractmethod


class EmailAlreadyRegistered(Exception):
    pass


class UserRepository(ABC):
    @abstractmethod
    def add(self, user):
        """Save a new user and return it with its id. Raises EmailAlreadyRegistered."""

    @abstractmethod
    def get(self, user_id):
        """Return the user or None."""

    @abstractmethod
    def get_by_email(self, email):
        """Return the user with this email (case-insensitive) or None."""


class FoodItemRepository(ABC):
    @abstractmethod
    def list_categories(self):
        """All event categories, ordered by name."""

    @abstractmethod
    def get_category(self, category_id):
        """Return the category or None."""

    @abstractmethod
    def add_category(self, category):
        """Save a new category and return it with its id."""

    @abstractmethod
    def add(self, item):
        """Save a new food item (with its categories) and return it with its id."""

    @abstractmethod
    def update(self, item):
        """Save changes to an existing food item, including its categories."""

    @abstractmethod
    def delete(self, item_id):
        """Delete a food item. Existing order items keep their name and price."""

    @abstractmethod
    def get(self, item_id):
        """Return the food item or None."""

    @abstractmethod
    def list_all(self):
        """All food items, published or not, ordered by name."""

    @abstractmethod
    def list_published(self, category_id=None):
        """Published food items, optionally only those in one event category."""


class OrderRepository(ABC):
    @abstractmethod
    def add(self, order):
        """Save a new order with its items and guest groups in one go; return it with ids."""

    @abstractmethod
    def get(self, order_id):
        """Return the order or None."""

    @abstractmethod
    def get_for_customer(self, order_id, customer_id):
        """Return the order only if it belongs to this customer, otherwise None."""

    @abstractmethod
    def list_for_customer(self, customer_id):
        """The customer's orders, newest first."""

    @abstractmethod
    def list_all(self, status=None, event_date=None):
        """All orders, newest first, optionally filtered by status and/or event date."""

    @abstractmethod
    def update_status(self, order_id, status):
        """Set the order status (an OrderStatus)."""

    @abstractmethod
    def update_payment_status(self, order_id, payment_status):
        """Set the payment status (a PaymentStatus)."""


class QuestionRepository(ABC):
    @abstractmethod
    def add(self, question):
        """Save a new question and return it with its id and created_at."""

    @abstractmethod
    def get(self, question_id):
        """Return the question or None."""

    @abstractmethod
    def list_for_order(self, order_id):
        """Questions about one order, oldest first."""

    @abstractmethod
    def list_all(self, unanswered_only=False):
        """All questions, newest first, optionally only unanswered ones."""

    @abstractmethod
    def answer(self, question_id, text):
        """Store the admin's answer and set answered_at."""


class Repositories(ABC):
    """Bundle of all repositories for one storage backend."""
    users: UserRepository
    food: FoodItemRepository
    orders: OrderRepository
    questions: QuestionRepository

    @abstractmethod
    def reset(self):
        """Delete all data and recreate empty storage."""
