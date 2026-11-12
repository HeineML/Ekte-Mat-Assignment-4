"""Application configuration. Secrets come from environment variables, never from the repository.

Flask reads a local `.env` file into the environment (python-dotenv); see `.env.example`.
"""
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


class Config:
    # Set SECRET_KEY in the environment for anything beyond local development.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-secret")
    # Browsers won't send the session cookie with form posts from other sites.
    SESSION_COOKIE_SAMESITE = "Lax"
    STORAGE = "neo4j"
    # Connection to the Neo4j Aura instance (or any Neo4j 5 server).
    NEO4J_URI = os.environ.get("NEO4J_URI")
    NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
    NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE") or None
    # Uploaded food pictures (A2). Served as static files, so the folder must stay under app/static.
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB per request


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test"
    # A separate instance: every test deletes all data in it. tests/conftest.py skips the
    # database tests when these aren't set.
    NEO4J_URI = os.environ.get("NEO4J_TEST_URI")
    NEO4J_USER = os.environ.get("NEO4J_TEST_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_TEST_PASSWORD")
    NEO4J_DATABASE = os.environ.get("NEO4J_TEST_DATABASE") or None
    UPLOAD_FOLDER = None  # set per test by tests/conftest.py
