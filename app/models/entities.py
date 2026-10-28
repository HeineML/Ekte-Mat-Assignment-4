"""Domain entities. Plain dataclasses with no storage code, so any storage backend can produce them.

`id` is None until an entity has been saved. IDs are opaque: don't rely on them being integers.
Prices are whole NOK.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class _LabelledEnum(str, Enum):
    @property
    def label(self):
        return self.value.replace("_", " ").capitalize()


class Role(_LabelledEnum):
    CUSTOMER = "customer"
    ADMIN = "admin"


class OrderStatus(_LabelledEnum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    IN_PREPARATION = "in_preparation"
    DELIVERED = "delivered"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PaymentStatus(_LabelledEnum):
    NOT_PAID = "not_paid"
    DEPOSIT_PAID = "deposit_paid"
    INVOICED = "invoiced"
    PAID = "paid"


@dataclass
class User:
    name: str
    email: str
    password_hash: str
    role: Role = Role.CUSTOMER
    id: object = None

    @property
    def is_admin(self):
        return self.role == Role.ADMIN


@dataclass
class EventCategory:
    name: str
    id: object = None


@dataclass
class FoodItem:
    name: str
    description: str
    price_nok: int
    minimum_quantity: int = 1
    published: bool = False
    image: str | None = None
    allergens: list[str] = field(default_factory=list)
    dietary_labels: list[str] = field(default_factory=list)
    event_categories: list[EventCategory] = field(default_factory=list)
    id: object = None


@dataclass
class GuestGroup:
    """Part of an order's guests who share the same allergy and dietary needs."""
    description: str
    size: int
    allergy_notes: str = ""
    dietary_notes: str = ""


@dataclass
class OrderItem:
    """One line of an order. Name and price are copied from the food item when the order is placed,
    so later edits (or deletion, which sets food_item_id to None) don't change old orders."""
    food_item_id: object
    food_name: str
    quantity: int
    unit_price_nok: int
    id: object = None

    @property
    def line_total(self):
        return self.quantity * self.unit_price_nok


@dataclass
class Order:
    customer_id: object
    event_date: date
    number_of_guests: int
    delivery_address: str
    items: list[OrderItem] = field(default_factory=list)
    guest_groups: list[GuestGroup] = field(default_factory=list)
    status: OrderStatus = OrderStatus.SUBMITTED
    payment_status: PaymentStatus = PaymentStatus.NOT_PAID
    created_at: datetime | None = None
    id: object = None

    @property
    def total(self):
        return sum(item.line_total for item in self.items)


@dataclass
class Question:
    order_id: object
    customer_id: object
    question: str
    answer: str | None = None
    created_at: datetime | None = None
    answered_at: datetime | None = None
    id: object = None

    @property
    def is_answered(self):
        return self.answer is not None
