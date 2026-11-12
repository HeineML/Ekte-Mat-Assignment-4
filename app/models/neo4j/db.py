"""Neo4j connection handling with the official `neo4j` driver.

A driver holds a connection pool and is expensive to create, so there is one per connection
setting for the whole process (tests create many apps against the same instance), closed when
the process exits. Every repository call runs as one managed transaction: `read()` and `write()`
commit on success, roll back on error and retry transient errors such as a lost connection.
"""
import atexit

from flask import current_app
from neo4j import GraphDatabase

_drivers = {}


def get_driver():
    config = current_app.config
    key = (config["NEO4J_URI"], config["NEO4J_USER"], config["NEO4J_PASSWORD"])
    if key not in _drivers:
        if not config["NEO4J_URI"] or not config["NEO4J_PASSWORD"]:
            raise RuntimeError("Neo4j is not configured. Set NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD "
                               "(for example in .env, see .env.example).")
        _drivers[key] = GraphDatabase.driver(config["NEO4J_URI"], auth=key[1:])
    return _drivers[key]


def _session():
    return get_driver().session(database=current_app.config["NEO4J_DATABASE"])


def read(work, *args):
    """Run work(tx, *args) in one read transaction and return its result."""
    with _session() as session:
        return session.execute_read(work, *args)


def write(work, *args):
    """Run work(tx, *args) in one write transaction and return its result."""
    with _session() as session:
        return session.execute_write(work, *args)


def query(cypher, **params):
    """Run a single read query and return its rows as dicts."""
    return read(lambda tx: tx.run(cypher, params).data())


def run_schema(statements):
    """Run schema statements (constraints) one by one; they can't share a transaction with data."""
    with _session() as session:
        for statement in statements:
            session.run(statement).consume()


@atexit.register
def _close_drivers():
    for driver in _drivers.values():
        driver.close()
    _drivers.clear()
