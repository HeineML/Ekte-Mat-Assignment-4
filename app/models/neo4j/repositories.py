"""Neo4j implementations of the repository interfaces.

Cypher stays inside this module and every public method returns entities. All values are passed
as query parameters, never formatted into the query text. Each method is one transaction (see
db.py), so a food item with its relationships, or an order with its lines and guest groups, is
saved completely or not at all.

Graph model (see docs/report.md):

    (:User)-[:PLACED]->(:Order)-[:HAS_LINE]->(:OrderLine)-[:OF_ITEM]->(:FoodItem)
    (:Order)-[:HAS_GUEST_GROUP]->(:GuestGroup)
    (:User)-[:ASKED]->(:Question)-[:ABOUT]->(:Order)
    (:FoodItem)-[:IN_CATEGORY]->(:EventCategory)
    (:FoodItem)-[:CONTAINS]->(:Allergen)
    (:FoodItem)-[:HAS_LABEL]->(:DietaryLabel)

Ids are whole numbers from a (:Counter {name}) node per label, increased in the same transaction
that creates the node, so URLs and the cart keep using integer ids.
"""
from datetime import datetime

from neo4j.exceptions import ConstraintError

from app.models.entities import (
    EventCategory, FoodItem, GuestGroup, Order, OrderItem, OrderStatus, PaymentStatus, Question, Role, User,
)
from app.models.neo4j.db import query, read, write
from app.models.repositories import (
    EmailAlreadyRegistered, FoodItemRepository, OrderRepository, QuestionRepository, UserRepository,
)


def _now():
    return datetime.now().replace(microsecond=0)


def _native(value):
    """neo4j.time.Date/DateTime -> datetime.date/datetime (None stays None)."""
    return value.to_native() if value is not None else None


def _next_ids(label, count=1):
    """Cypher fragment that reserves `count` ids for `label` and binds the first one to `first_id`."""
    return (f"MERGE (counter:Counter {{name: '{label}'}}) "
            f"SET counter.value = coalesce(counter.value, 0) + {count} "
            f"WITH counter.value - {count} + 1 AS first_id ")


# Users

class Neo4jUserRepository(UserRepository):
    def add(self, user):
        def work(tx):
            return tx.run(
                _next_ids("User") +
                "CREATE (u:User {id: first_id, name: $name, email: $email,"
                " password_hash: $password_hash, role: $role}) RETURN u.id AS id",
                name=user.name, email=user.email.lower(), password_hash=user.password_hash,
                role=user.role.value,
            ).single()["id"]
        try:
            user.id = write(work)
        except ConstraintError as e:
            raise EmailAlreadyRegistered(user.email) from e
        user.email = user.email.lower()
        return user

    def get(self, user_id):
        return self._one("MATCH (u:User {id: $value}) RETURN u {.*} AS u", user_id)

    def get_by_email(self, email):
        # Emails are stored in lower case, so the lookup ignores case.
        return self._one("MATCH (u:User {email: $value}) RETURN u {.*} AS u", email.lower())

    @staticmethod
    def _one(cypher, value):
        rows = query(cypher, value=value)
        if not rows:
            return None
        u = rows[0]["u"]
        return User(id=u["id"], name=u["name"], email=u["email"],
                    password_hash=u["password_hash"], role=Role(u["role"]))


# Food items

# Returns one food item per row as `f`, with its categories and its allergens and dietary labels
# in the order they were entered.
_FOOD_RETURN = """
RETURN f {
    .*,
    categories: COLLECT { MATCH (f)-[:IN_CATEGORY]->(c:EventCategory)
                          RETURN c {.id, .name} ORDER BY c.name },
    allergens: COLLECT { MATCH (f)-[r:CONTAINS]->(a:Allergen) RETURN a.name ORDER BY r.position },
    dietary_labels: COLLECT { MATCH (f)-[r:HAS_LABEL]->(l:DietaryLabel) RETURN l.name ORDER BY r.position }
} AS f
ORDER BY f.name, f.id
"""

# Graph query for the menu filter (C1): follow CONTAINS and HAS_LABEL from each food item.
_PUBLISHED = """
MATCH (f:FoodItem {published: true})
WHERE ($category_id IS NULL OR EXISTS { (f)-[:IN_CATEGORY]->(:EventCategory {id: $category_id}) })
  AND NOT EXISTS { (f)-[:CONTAINS]->(a:Allergen) WHERE a.name IN $exclude_allergens }
  AND all(label IN $require_labels WHERE EXISTS { (f)-[:HAS_LABEL]->(:DietaryLabel {name: label}) })
"""


class Neo4jFoodItemRepository(FoodItemRepository):
    def list_categories(self):
        rows = query("MATCH (c:EventCategory) RETURN c.id AS id, c.name AS name ORDER BY c.name")
        return [EventCategory(id=r["id"], name=r["name"]) for r in rows]

    def get_category(self, category_id):
        rows = query("MATCH (c:EventCategory {id: $id}) RETURN c.id AS id, c.name AS name", id=category_id)
        return EventCategory(id=rows[0]["id"], name=rows[0]["name"]) if rows else None

    def add_category(self, category):
        def work(tx):
            return tx.run(_next_ids("EventCategory") +
                          "CREATE (c:EventCategory {id: first_id, name: $name}) RETURN c.id AS id",
                          name=category.name).single()["id"]
        category.id = write(work)
        return category

    def add(self, item):
        def work(tx):
            item_id = tx.run(_next_ids("FoodItem") +
                             "CREATE (f:FoodItem {id: first_id}) RETURN f.id AS id").single()["id"]
            self._save(tx, item_id, item)
            return item_id
        item.id = write(work)
        return item

    def update(self, item):
        write(self._save, item.id, item)
        return item

    def delete(self, item_id):
        # DETACH DELETE also removes the OF_ITEM relationships from order lines; the lines keep
        # their copied name and price, so old orders don't change.
        write(lambda tx: tx.run("MATCH (f:FoodItem {id: $id}) DETACH DELETE f", id=item_id).consume())

    def get(self, item_id):
        rows = query("MATCH (f:FoodItem {id: $id})" + _FOOD_RETURN, id=item_id)
        return self._to_food_item(rows[0]["f"]) if rows else None

    def list_all(self):
        return [self._to_food_item(r["f"]) for r in query("MATCH (f:FoodItem)" + _FOOD_RETURN)]

    def list_published(self, category_id=None, exclude_allergens=(), require_labels=()):
        rows = query(_PUBLISHED + _FOOD_RETURN, category_id=category_id,
                     exclude_allergens=list(exclude_allergens), require_labels=list(require_labels))
        return [self._to_food_item(r["f"]) for r in rows]

    def list_allergens(self):
        rows = query("MATCH (:FoodItem {published: true})-[:CONTAINS]->(a:Allergen)"
                     " RETURN DISTINCT a.name AS name ORDER BY name")
        return [r["name"] for r in rows]

    def list_dietary_labels(self):
        rows = query("MATCH (:FoodItem {published: true})-[:HAS_LABEL]->(l:DietaryLabel)"
                     " RETURN DISTINCT l.name AS name ORDER BY name")
        return [r["name"] for r in rows]

    @staticmethod
    def _save(tx, item_id, item):
        """Set the properties and replace the relationships of food item `item_id`."""
        tx.run(
            "MATCH (f:FoodItem {id: $id})"
            " SET f.name = $name, f.description = $description, f.price_nok = $price_nok,"
            "     f.minimum_quantity = $minimum_quantity, f.published = $published, f.image = $image"
            " WITH f OPTIONAL MATCH (f)-[r:IN_CATEGORY|CONTAINS|HAS_LABEL]->() DELETE r",
            id=item_id, name=item.name, description=item.description, price_nok=item.price_nok,
            minimum_quantity=item.minimum_quantity, published=bool(item.published), image=item.image,
        ).consume()
        tx.run(
            "MATCH (f:FoodItem {id: $id})"
            " UNWIND $category_ids AS category_id"
            " MATCH (c:EventCategory {id: category_id})"
            " CREATE (f)-[:IN_CATEGORY]->(c)",
            id=item_id, category_ids=[c.id for c in item.event_categories],
        ).consume()
        # Allergens and labels are shared nodes (MERGE), which is what the menu filter follows.
        # `position` keeps the order they were entered in.
        tx.run(
            "MATCH (f:FoodItem {id: $id})"
            " UNWIND range(0, size($names) - 1) AS i"
            " MERGE (a:Allergen {name: $names[i]})"
            " CREATE (f)-[:CONTAINS {position: i}]->(a)",
            id=item_id, names=list(item.allergens),
        ).consume()
        tx.run(
            "MATCH (f:FoodItem {id: $id})"
            " UNWIND range(0, size($names) - 1) AS i"
            " MERGE (l:DietaryLabel {name: $names[i]})"
            " CREATE (f)-[:HAS_LABEL {position: i}]->(l)",
            id=item_id, names=list(item.dietary_labels),
        ).consume()

    @staticmethod
    def _to_food_item(f):
        return FoodItem(
            id=f["id"], name=f["name"], description=f["description"], price_nok=f["price_nok"],
            minimum_quantity=f["minimum_quantity"], published=f["published"], image=f.get("image"),
            allergens=list(f["allergens"]), dietary_labels=list(f["dietary_labels"]),
            event_categories=[EventCategory(id=c["id"], name=c["name"]) for c in f["categories"]],
        )


# Orders

_ORDER_RETURN = """
RETURN o {
    .*,
    customer_id: u.id,
    items: COLLECT { MATCH (o)-[:HAS_LINE]->(l:OrderLine)
                     OPTIONAL MATCH (l)-[:OF_ITEM]->(f:FoodItem)
                     RETURN l {.*, food_item_id: f.id} ORDER BY l.position },
    guest_groups: COLLECT { MATCH (o)-[:HAS_GUEST_GROUP]->(g:GuestGroup)
                            RETURN g {.*} ORDER BY g.position }
} AS o
ORDER BY o.created_at DESC, o.id DESC
"""


class Neo4jOrderRepository(OrderRepository):
    def add(self, order):
        order.created_at = order.created_at or _now()

        def work(tx):
            record = tx.run(
                "MATCH (u:User {id: $customer_id}) WITH u " + _next_ids("Order") +
                ", u CREATE (u)-[:PLACED]->(o:Order {id: first_id, event_date: $event_date,"
                " number_of_guests: $number_of_guests, delivery_address: $delivery_address,"
                " status: $status, payment_status: $payment_status, created_at: $created_at})"
                " RETURN o.id AS id",
                customer_id=order.customer_id, event_date=order.event_date,
                number_of_guests=order.number_of_guests, delivery_address=order.delivery_address,
                status=OrderStatus(order.status).value,
                payment_status=PaymentStatus(order.payment_status).value,
                created_at=order.created_at,
            ).single()
            if record is None:
                raise ValueError(f"Unknown customer {order.customer_id!r}")
            order_id = record["id"]

            lines = [{"position": i, "food_item_id": item.food_item_id, "food_name": item.food_name,
                      "quantity": item.quantity, "unit_price_nok": item.unit_price_nok}
                     for i, item in enumerate(order.items)]
            line_ids = []
            if lines:
                # The line keeps a copy of the name and price; OF_ITEM points to the current food item.
                line_ids = tx.run(
                    "MATCH (o:Order {id: $order_id}) WITH o " + _next_ids("OrderLine", len(lines)) +
                    ", o UNWIND $lines AS line"
                    " CREATE (o)-[:HAS_LINE]->(l:OrderLine {id: first_id + line.position,"
                    "   position: line.position, food_name: line.food_name, quantity: line.quantity,"
                    "   unit_price_nok: line.unit_price_nok})"
                    " WITH l, line OPTIONAL MATCH (f:FoodItem {id: line.food_item_id})"
                    " FOREACH (_ IN CASE WHEN f IS NULL THEN [] ELSE [1] END | CREATE (l)-[:OF_ITEM]->(f))"
                    " RETURN l.id AS id ORDER BY l.position",
                    order_id=order_id, lines=lines,
                ).value("id")

            tx.run(
                "MATCH (o:Order {id: $order_id})"
                " UNWIND $groups AS g"
                " CREATE (o)-[:HAS_GUEST_GROUP]->(:GuestGroup {position: g.position,"
                "   description: g.description, size: g.size, allergy_notes: g.allergy_notes,"
                "   dietary_notes: g.dietary_notes})",
                order_id=order_id,
                groups=[{"position": i, "description": g.description, "size": g.size,
                         "allergy_notes": g.allergy_notes, "dietary_notes": g.dietary_notes}
                        for i, g in enumerate(order.guest_groups)],
            ).consume()
            return order_id, line_ids

        order.id, line_ids = write(work)
        for item, line_id in zip(order.items, line_ids):
            item.id = line_id
        return order

    def get(self, order_id):
        return self._one("MATCH (u:User)-[:PLACED]->(o:Order {id: $order_id})", order_id=order_id)

    def get_for_customer(self, order_id, customer_id):
        # Both ids must match: customers only see their own orders.
        return self._one("MATCH (u:User {id: $customer_id})-[:PLACED]->(o:Order {id: $order_id})",
                         order_id=order_id, customer_id=customer_id)

    def list_for_customer(self, customer_id):
        rows = query("MATCH (u:User {id: $customer_id})-[:PLACED]->(o:Order)" + _ORDER_RETURN,
                     customer_id=customer_id)
        return [self._to_order(r["o"]) for r in rows]

    def list_all(self, status=None, event_date=None):
        rows = query(
            "MATCH (u:User)-[:PLACED]->(o:Order)"
            " WHERE ($status IS NULL OR o.status = $status)"
            "   AND ($event_date IS NULL OR o.event_date = $event_date)" + _ORDER_RETURN,
            status=OrderStatus(status).value if status is not None else None, event_date=event_date,
        )
        return [self._to_order(r["o"]) for r in rows]

    def update_status(self, order_id, status):
        self._set(order_id, "status", OrderStatus(status).value)

    def update_payment_status(self, order_id, payment_status):
        self._set(order_id, "payment_status", PaymentStatus(payment_status).value)

    @staticmethod
    def _set(order_id, prop, value):
        # prop is one of two fixed names above, never user input.
        write(lambda tx: tx.run(f"MATCH (o:Order {{id: $id}}) SET o.{prop} = $value",
                                id=order_id, value=value).consume())

    def _one(self, match, **params):
        rows = query(match + _ORDER_RETURN, **params)
        return self._to_order(rows[0]["o"]) if rows else None

    @staticmethod
    def _to_order(o):
        return Order(
            id=o["id"], customer_id=o["customer_id"], event_date=_native(o["event_date"]),
            number_of_guests=o["number_of_guests"], delivery_address=o["delivery_address"],
            status=OrderStatus(o["status"]), payment_status=PaymentStatus(o["payment_status"]),
            created_at=_native(o["created_at"]),
            items=[OrderItem(id=i["id"], food_item_id=i["food_item_id"], food_name=i["food_name"],
                             quantity=i["quantity"], unit_price_nok=i["unit_price_nok"])
                   for i in o["items"]],
            guest_groups=[GuestGroup(description=g["description"], size=g["size"],
                                     allergy_notes=g["allergy_notes"], dietary_notes=g["dietary_notes"])
                          for g in o["guest_groups"]],
        )


# Questions

_QUESTION_MATCH = "MATCH (u:User)-[:ASKED]->(q:Question)-[:ABOUT]->(o:Order) "
_QUESTION_RETURN = " RETURN q {.*, customer_id: u.id, order_id: o.id} AS q"


class Neo4jQuestionRepository(QuestionRepository):
    def add(self, question):
        question.created_at = question.created_at or _now()

        def work(tx):
            record = tx.run(
                "MATCH (u:User {id: $customer_id}), (o:Order {id: $order_id}) WITH u, o " +
                _next_ids("Question") +
                ", u, o CREATE (u)-[:ASKED]->(q:Question {id: first_id, question: $question,"
                " answer: $answer, created_at: $created_at, answered_at: $answered_at})-[:ABOUT]->(o)"
                " RETURN q.id AS id",
                customer_id=question.customer_id, order_id=question.order_id,
                question=question.question, answer=question.answer,
                created_at=question.created_at, answered_at=question.answered_at,
            ).single()
            if record is None:
                raise ValueError("Unknown customer or order")
            return record["id"]

        question.id = write(work)
        return question

    def get(self, question_id):
        rows = query(_QUESTION_MATCH + "WHERE q.id = $id" + _QUESTION_RETURN, id=question_id)
        return self._to_question(rows[0]["q"]) if rows else None

    def list_for_order(self, order_id):
        rows = query(_QUESTION_MATCH + "WHERE o.id = $order_id" + _QUESTION_RETURN +
                     " ORDER BY q.created_at, q.id", order_id=order_id)
        return [self._to_question(r["q"]) for r in rows]

    def list_all(self, unanswered_only=False):
        rows = query(_QUESTION_MATCH + "WHERE NOT $unanswered_only OR q.answer IS NULL" +
                     _QUESTION_RETURN + " ORDER BY q.created_at DESC, q.id DESC",
                     unanswered_only=unanswered_only)
        return [self._to_question(r["q"]) for r in rows]

    def answer(self, question_id, text):
        write(lambda tx: tx.run("MATCH (q:Question {id: $id}) SET q.answer = $text, q.answered_at = $now",
                                id=question_id, text=text, now=_now()).consume())

    @staticmethod
    def _to_question(q):
        return Question(
            id=q["id"], order_id=q["order_id"], customer_id=q["customer_id"], question=q["question"],
            answer=q.get("answer"), created_at=_native(q["created_at"]),
            answered_at=_native(q.get("answered_at")),
        )
