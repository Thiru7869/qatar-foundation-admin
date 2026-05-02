import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY     = os.environ.get("SECRET_KEY",     "qf-admin-portal-secret-2024")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "qf-jwt-secret-2024")

    JWT_EXPIRY_HOURS        = 2
    JWT_REMEMBER_ME_DAYS    = 30
    RESET_TOKEN_EXPIRES_HOURS = 1

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'qatar.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS      = {"pool_pre_ping": True}

    # Email via Resend
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
    MAIL_FROM      = os.environ.get("MAIL_FROM", "Qatar Foundation <onboarding@resend.dev>")

    CORS_ORIGINS = "*"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}