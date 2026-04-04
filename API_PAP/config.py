import os

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

def _fix_db_url(url):
    """Railway fornece postgres:// — SQLAlchemy precisa de postgresql+psycopg2://"""
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url and url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url

class Config:
    SECRET_KEY     = os.environ.get("SECRET_KEY",     "muda-esta-chave-secreta-para-producao")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "muda-esta-chave-jwt-para-producao")

    _db_url = os.environ.get("DATABASE_URL", "sqlite:///database.db")
    SQLALCHEMY_DATABASE_URI    = _fix_db_url(_db_url)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS  = {
        "pool_pre_ping": True,       # reconecta após idle
        "pool_recycle":  280,        # recicla conexões antes do timeout (Railway: 300s)
    }

    # SMTP
    SMTP_HOST      = os.environ.get("SMTP_HOST",      "smtp.gmail.com")
    SMTP_PORT      = int(os.environ.get("SMTP_PORT",  587))
    SMTP_USER      = os.environ.get("SMTP_USER",      "")
    SMTP_PASSWORD  = os.environ.get("SMTP_PASSWORD",  "")
    SMTP_FROM      = os.environ.get("SMTP_FROM",      "")
    SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "AgroCaua")
    SMTP_TLS       = os.environ.get("SMTP_TLS",       "True").lower() == "true"
    SMTP_SSL       = os.environ.get("SMTP_SSL",       "False").lower() == "true"

    ADMIN_EMAIL    = os.environ.get("SMTP_USER", "")
