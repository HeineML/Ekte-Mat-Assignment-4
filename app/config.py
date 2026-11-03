"""Application configuration. Secrets come from environment variables, never from the repository."""
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


class Config:
    # Set SECRET_KEY in the environment for anything beyond local development.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-secret")
    # Browsers won't send the session cookie with form posts from other sites.
    SESSION_COOKIE_SAMESITE = "Lax"
    STORAGE = "sqlite"
    DATABASE = os.environ.get("DATABASE", os.path.join(BASE_DIR, "instance", "ektemat.sqlite"))
    # Uploaded food pictures (A2). Served as static files, so the folder must stay under app/static.
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB per request


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test"
    # Set per test by tests/conftest.py. ":memory:" can't be used because every
    # new connection would get its own empty database.
    DATABASE = None
    UPLOAD_FOLDER = None
