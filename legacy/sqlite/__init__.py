"""SQLite storage backend. Only app.models may import this package."""
from importlib.resources import files

from app.models.repositories import Repositories
from app.models.sqlite.db import close_db, get_db
from app.models.sqlite.repositories import (
    SqliteFoodItemRepository, SqliteOrderRepository, SqliteQuestionRepository, SqliteUserRepository,
)


class SqliteRepositories(Repositories):
    def __init__(self):
        self.users = SqliteUserRepository()
        self.food = SqliteFoodItemRepository()
        self.orders = SqliteOrderRepository()
        self.questions = SqliteQuestionRepository()

    def reset(self):
        schema = files(__package__).joinpath("schema.sql").read_text(encoding="utf-8")
        get_db().executescript(schema)


def init_app(app):
    app.teardown_appcontext(close_db)
    return SqliteRepositories()
