import os

# Carrega variáveis do ficheiro .env se existir
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass  # python-dotenv não instalado — usa variáveis de ambiente do sistema

class Config:
    SECRET_KEY     = os.environ.get("SECRET_KEY",     "muda-esta-chave-secreta-para-producao")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "muda-esta-chave-jwt-para-producao")

    SQLALCHEMY_DATABASE_URI    = os.environ.get("DATABASE_URL", "sqlite:///database.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SMTP — Email notifications
    SMTP_HOST      = os.environ.get("SMTP_HOST",      "smtp.gmail.com")
    SMTP_PORT      = int(os.environ.get("SMTP_PORT",  587))
    SMTP_USER      = os.environ.get("SMTP_USER",      "")
    SMTP_PASSWORD  = os.environ.get("SMTP_PASSWORD",  "")
    SMTP_FROM      = os.environ.get("SMTP_FROM",      "")
    SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "AgroCaua")
    SMTP_TLS       = os.environ.get("SMTP_TLS",       "True").lower() == "true"
    SMTP_SSL       = os.environ.get("SMTP_SSL",       "False").lower() == "true"

    # Admin email (receives contact forms and critical alerts)
    ADMIN_EMAIL    = os.environ.get("SMTP_USER", "")
