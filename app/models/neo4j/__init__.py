"""Neo4j storage backend. Only app.models may import this package."""
from app.models.neo4j.db import get_driver, run_schema, write
from app.models.neo4j.repositories import (
    Neo4jFoodItemRepository, Neo4jOrderRepository, Neo4jQuestionRepository, Neo4jUserRepository,
)
from app.models.repositories import Repositories

# Unique ids for the nodes the app looks up by id, unique emails (stored in lower case) and one
# node per category, allergen, dietary label and id counter.
CONSTRAINTS = [
    *(f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
      for label in ["User", "FoodItem", "EventCategory", "Order", "OrderLine", "Question"]),
    "CREATE CONSTRAINT user_email IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
    *(f"CREATE CONSTRAINT {label.lower()}_name IF NOT EXISTS FOR (n:{label}) REQUIRE n.name IS UNIQUE"
      for label in ["EventCategory", "Allergen", "DietaryLabel", "Counter"]),
]

# Drivers whose database already has the constraints; they survive deleting the data.
_constrained = set()


class Neo4jRepositories(Repositories):
    def __init__(self):
        self.users = Neo4jUserRepository()
        self.food = Neo4jFoodItemRepository()
        self.orders = Neo4jOrderRepository()
        self.questions = Neo4jQuestionRepository()

    def reset(self):
        """Delete every node and relationship (ids start at 1 again) and make sure the constraints exist."""
        write(lambda tx: tx.run("MATCH (n) DETACH DELETE n").consume())
        driver = get_driver()
        if id(driver) not in _constrained:
            run_schema(CONSTRAINTS)
            _constrained.add(id(driver))


def init_app(app):
    return Neo4jRepositories()
