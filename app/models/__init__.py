"""Model layer: domain entities, repository interfaces, domain rules and storage.

Controllers and views import only from this package (entities and get_repos()), never from
the storage implementation (Neo4j, in app/models/neo4j/). The Oblig 4 SQLite implementation is
kept for reference in legacy/sqlite/ and is not used.
"""
from flask import current_app


def init_storage(app):
    """Create the repositories for the configured STORAGE backend and attach them to the app."""
    backend = app.config["STORAGE"]
    if backend == "neo4j":
        from app.models import neo4j
        app.extensions["repos"] = neo4j.init_app(app)
    else:
        raise ValueError(f"Unknown STORAGE backend: {backend!r}")

    from app.models.seed import register_commands
    register_commands(app)


def get_repos():
    """The Repositories bundle for the running app (users, food, orders, questions)."""
    return current_app.extensions["repos"]
