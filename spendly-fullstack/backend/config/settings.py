import os
from datetime import timedelta
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load .env FIRST before reading any values
load_dotenv(override=True)

# Read each value individually AFTER dotenv loads
_HOST  = os.getenv("MYSQL_HOST", "localhost")
_PORT  = os.getenv("MYSQL_PORT", "3306")
_USER  = os.getenv("MYSQL_USER", "root")
_PASS  = quote_plus(os.getenv("MYSQL_PASSWORD", ""))   # URL-encode special chars
_DB    = os.getenv("MYSQL_DB", "spendly")

_DB_URI = f"mysql+pymysql://{_USER}:{_PASS}@{_HOST}:{_PORT}/{_DB}?charset=utf8mb4"


class Config:
    SECRET_KEY     = os.getenv("SECRET_KEY", "spendly-secret-change-in-production")
    DEBUG          = os.getenv("DEBUG", "true").lower() == "true"

    MYSQL_HOST     = _HOST
    MYSQL_PORT     = int(_PORT)
    MYSQL_USER     = _USER
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB       = _DB

    SQLALCHEMY_DATABASE_URI        = _DB_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS      = {"pool_recycle": 280, "pool_pre_ping": True}

    JWT_SECRET_KEY            = os.getenv("JWT_SECRET_KEY", "jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(hours=int(os.getenv("JWT_ACCESS_HOURS", "24")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "30")))

    RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    STRIPE_SECRET_KEY   = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUB_KEY      = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SEC  = os.getenv("STRIPE_WEBHOOK_SECRET", "")
