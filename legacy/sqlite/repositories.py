"""SQLite implementations of the repository interfaces.

Rows, SQL and JSON stay inside this module; every public method returns entities.
`with db:` wraps each write in a transaction (commit on success, rollback on error).
"""
import json
import sqlite3
from datetime import date, datetime

from app.models.entities import (
    EventCategory, FoodItem, GuestGroup, Order, OrderItem, OrderStatus,
    PaymentStatus, Question, Role, User,
)
from app.models.repositories import (
    EmailAlreadyRegistered, FoodItemRepository, OrderRepository, QuestionRepository, UserRepository,
)
from app.models.sqlite.db import get_db


def _now():
    return datetime.now().replace(microsecond=0)


def _parse_datetime(value):
    return datetime.fromisoformat(value) if value else None


class SqliteUserRepository(UserRepository):
    def add(self, user):
        db = get_db()
        try:
            with db:
                cur = db.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                    (user.name, user.email, user.password_hash, user.role.value),
                )
        except sqlite3.IntegrityError as e:
            raise EmailAlreadyRegistered(user.email) from e
        user.id = cur.lastrowid
        return user

    def get(self, user_id):
        row = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._to_user(row)

    def get_by_email(self, email):
        row = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return self._to_user(row)

    @staticmethod
    def _to_user(row):
        if row is None:
            return None
        return User(id=row["id"], name=row["name"], email=row["email"],
                    password_hash=row["password_hash"], role=Role(row["role"]))


class SqliteFoodItemRepository(FoodItemRepository):
    def list_categories(self):
        rows = get_db().execute("SELECT * FROM event_categories ORDER BY name").fetchall()
        return [EventCategory(id=r["id"], name=r["name"]) for r in rows]

    def get_category(self, category_id):
        row = get_db().execute("SELECT * FROM event_categories WHERE id = ?", (category_id,)).fetchone()
        return EventCategory(id=row["id"], name=row["name"]) if row else None

    def add_category(self, category):
        db = get_db()
        with db:
            cur = db.execute("INSERT INTO event_categories (name) VALUES (?)", (category.name,))
        category.id = cur.lastrowid
        return category

    def add(self, item):
        db = get_db()
        with db:
            cur = db.execute(
                "INSERT INTO food_items (name, description, price_nok, minimum_quantity, published,"
                " image, allergens, dietary_labels) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                self._columns(item),
            )
            item.id = cur.lastrowid
            self._save_categories(db, item)
        return item

    def update(self, item):
        db = get_db()
        with db:
            db.execute(
                "UPDATE food_items SET name = ?, description = ?, price_nok = ?, minimum_quantity = ?,"
                " published = ?, image = ?, allergens = ?, dietary_labels = ? WHERE id = ?",
                (*self._columns(item), item.id),
            )
            db.execute("DELETE FROM food_item_categories WHERE food_item_id = ?", (item.id,))
            self._save_categories(db, item)
        return item

    def delete(self, item_id):
        db = get_db()
        with db:
            db.execute("DELETE FROM food_items WHERE id = ?", (item_id,))

    def get(self, item_id):
        row = get_db().execute("SELECT * FROM food_items WHERE id = ?", (item_id,)).fetchone()
        return self._to_food_item(row) if row else None

    def list_all(self):
        rows = get_db().execute("SELECT * FROM food_items ORDER BY name").fetchall()
        return [self._to_food_item(r) for r in rows]

    def list_published(self, category_id=None):
        if category_id is None:
            rows = get_db().execute(
                "SELECT * FROM food_items WHERE published = 1 ORDER BY name").fetchall()
        else:
            rows = get_db().execute(
                "SELECT f.* FROM food_items f"
                " JOIN food_item_categories fc ON fc.food_item_id = f.id"
                " WHERE f.published = 1 AND fc.category_id = ? ORDER BY f.name",
                (category_id,),
            ).fetchall()
        return [self._to_food_item(r) for r in rows]

    @staticmethod
    def _columns(item):
        return (item.name, item.description, item.price_nok, item.minimum_quantity,
                int(item.published), item.image,
                json.dumps(item.allergens), json.dumps(item.dietary_labels))

    @staticmethod
    def _save_categories(db, item):
        db.executemany(
            "INSERT INTO food_item_categories (food_item_id, category_id) VALUES (?, ?)",
            [(item.id, c.id) for c in item.event_categories],
        )

    @staticmethod
    def _to_food_item(row):
        categories = get_db().execute(
            "SELECT c.* FROM event_categories c"
            " JOIN food_item_categories fc ON fc.category_id = c.id"
            " WHERE fc.food_item_id = ? ORDER BY c.name",
            (row["id"],),
        ).fetchall()
        return FoodItem(
            id=row["id"], name=row["name"], description=row["description"],
            price_nok=row["price_nok"], minimum_quantity=row["minimum_quantity"],
            published=bool(row["published"]), image=row["image"],
            allergens=json.loads(row["allergens"]), dietary_labels=json.loads(row["dietary_labels"]),
            event_categories=[EventCategory(id=c["id"], name=c["name"]) for c in categories],
        )


class SqliteOrderRepository(OrderRepository):
    def add(self, order):
        db = get_db()
        order.created_at = order.created_at or _now()
        with db:
            cur = db.execute(
                "INSERT INTO orders (customer_id, event_date, number_of_guests, delivery_address,"
                " status, payment_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (order.customer_id, order.event_date.isoformat(), order.number_of_guests,
                 order.delivery_address, order.status.value, order.payment_status.value,
                 order.created_at.isoformat()),
            )
            order.id = cur.lastrowid
            for item in order.items:
                cur = db.execute(
                    "INSERT INTO order_items (order_id, food_item_id, food_name, quantity, unit_price_nok)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (order.id, item.food_item_id, item.food_name, item.quantity, item.unit_price_nok),
                )
                item.id = cur.lastrowid
            db.executemany(
                "INSERT INTO guest_groups (order_id, description, size, allergy_notes, dietary_notes)"
                " VALUES (?, ?, ?, ?, ?)",
                [(order.id, g.description, g.size, g.allergy_notes, g.dietary_notes)
                 for g in order.guest_groups],
            )
        return order

    def get(self, order_id):
        row = get_db().execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return self._to_order(row) if row else None

    def get_for_customer(self, order_id, customer_id):
        row = get_db().execute(
            "SELECT * FROM orders WHERE id = ? AND customer_id = ?", (order_id, customer_id)).fetchone()
        return self._to_order(row) if row else None

    def list_for_customer(self, customer_id):
        rows = get_db().execute(
            "SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC, id DESC",
            (customer_id,),
        ).fetchall()
        return [self._to_order(r) for r in rows]

    def list_all(self, status=None, event_date=None):
        sql, params = "SELECT * FROM orders WHERE 1 = 1", []
        if status is not None:
            sql += " AND status = ?"
            params.append(OrderStatus(status).value)
        if event_date is not None:
            sql += " AND event_date = ?"
            params.append(event_date.isoformat())
        rows = get_db().execute(sql + " ORDER BY created_at DESC, id DESC", params).fetchall()
        return [self._to_order(r) for r in rows]

    def update_status(self, order_id, status):
        db = get_db()
        with db:
            db.execute("UPDATE orders SET status = ? WHERE id = ?", (OrderStatus(status).value, order_id))

    def update_payment_status(self, order_id, payment_status):
        db = get_db()
        with db:
            db.execute("UPDATE orders SET payment_status = ? WHERE id = ?",
                       (PaymentStatus(payment_status).value, order_id))

    @staticmethod
    def _to_order(row):
        db = get_db()
        items = db.execute("SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (row["id"],)).fetchall()
        groups = db.execute("SELECT * FROM guest_groups WHERE order_id = ? ORDER BY id", (row["id"],)).fetchall()
        return Order(
            id=row["id"], customer_id=row["customer_id"],
            event_date=date.fromisoformat(row["event_date"]),
            number_of_guests=row["number_of_guests"], delivery_address=row["delivery_address"],
            status=OrderStatus(row["status"]), payment_status=PaymentStatus(row["payment_status"]),
            created_at=_parse_datetime(row["created_at"]),
            items=[OrderItem(id=i["id"], food_item_id=i["food_item_id"], food_name=i["food_name"],
                             quantity=i["quantity"], unit_price_nok=i["unit_price_nok"]) for i in items],
            guest_groups=[GuestGroup(description=g["description"], size=g["size"],
                                     allergy_notes=g["allergy_notes"], dietary_notes=g["dietary_notes"])
                          for g in groups],
        )


class SqliteQuestionRepository(QuestionRepository):
    def add(self, question):
        db = get_db()
        question.created_at = question.created_at or _now()
        with db:
            cur = db.execute(
                "INSERT INTO questions (order_id, customer_id, question, answer, created_at, answered_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (question.order_id, question.customer_id, question.question, question.answer,
                 question.created_at.isoformat(),
                 question.answered_at.isoformat() if question.answered_at else None),
            )
        question.id = cur.lastrowid
        return question

    def get(self, question_id):
        row = get_db().execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        return self._to_question(row) if row else None

    def list_for_order(self, order_id):
        rows = get_db().execute(
            "SELECT * FROM questions WHERE order_id = ? ORDER BY created_at, id", (order_id,)).fetchall()
        return [self._to_question(r) for r in rows]

    def list_all(self, unanswered_only=False):
        sql = "SELECT * FROM questions"
        if unanswered_only:
            sql += " WHERE answer IS NULL"
        rows = get_db().execute(sql + " ORDER BY created_at DESC, id DESC").fetchall()
        return [self._to_question(r) for r in rows]

    def answer(self, question_id, text):
        db = get_db()
        with db:
            db.execute("UPDATE questions SET answer = ?, answered_at = ? WHERE id = ?",
                       (text, _now().isoformat(), question_id))

    @staticmethod
    def _to_question(row):
        return Question(
            id=row["id"], order_id=row["order_id"], customer_id=row["customer_id"],
            question=row["question"], answer=row["answer"],
            created_at=_parse_datetime(row["created_at"]),
            answered_at=_parse_datetime(row["answered_at"]),
        )
