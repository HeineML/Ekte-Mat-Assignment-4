"""Application configuration. Secrets come from environment variables, never from the repository."""
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


class Config:
    # Set SECRET_KEY in the environment for anything beyond local development.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-secret")
    STORAGE = "sqlite"
    DATABASE = os.environ.get("DATABASE", os.path.join(BASE_DIR, "instance", "ektemat.sqlite"))


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test"
    DATABASE = ":memory:"
