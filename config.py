import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Shared application configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "local-development-key-change-me")
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    ALLOWED_EXTENSIONS = {"pdf"}
    MAX_FILE_SIZE = 25 * 1024 * 1024
    MAX_FILES = 20
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SEND_FILE_MAX_AGE_DEFAULT = 0


class DevelopmentConfig(Config):
    """Configuration used when running the local development server."""

    DEBUG = True


class ProductionConfig(Config):
    """Configuration used by a production WSGI server."""

    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
