import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    _db_url = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    if _db_url.startswith("postgresql://"):
        # Use the psycopg3 driver (has prebuilt wheels everywhere, incl. Vercel's Linux
        # runtime and Windows dev machines without a C build toolchain).
        _db_url = _db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        # Serverless functions are short-lived; avoid holding a pool across invocations.
        "pool_recycle": 280,
    }

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_COOKIE_NAME = "access_token"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_COOKIE_SECURE = os.environ.get("JWT_COOKIE_SECURE", "true").lower() == "true"
    JWT_COOKIE_SAMESITE = "Lax"
    # CSRF for state-changing requests is handled by Flask-WTF (session-based token in every
    # HTML form) plus the SameSite=Lax cookie policy above, rather than JWT's double-submit
    # scheme, since this app is server-rendered rather than a separate JS API client.
    JWT_COOKIE_CSRF_PROTECT = False

    WTF_CSRF_TIME_LIMIT = None
    # The token itself (bound to the signed session) plus SameSite=Lax already stop CSRF;
    # the extra mandatory-Referer check under WTF_CSRF_SSL_STRICT rejects real logins whenever
    # a browser/extension/proxy strips the Referer header on an HTTPS POST, which is common
    # enough (strict tracking protection, some ad blockers, some corporate proxies) to disable it.
    WTF_CSRF_SSL_STRICT = False

    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@foodies.com")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")

    MAX_FAILED_LOGIN_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_MINUTES = 15
