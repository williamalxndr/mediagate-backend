import os
from urllib.parse import quote, urlsplit

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


def production_database_url():
    database_url = env("DATABASE_URL", default="")  # noqa: F405
    pg_vars = {
        "PGDATABASE": os.environ.get("PGDATABASE", ""),
        "PGHOST": os.environ.get("PGHOST", ""),
        "PGPASSWORD": os.environ.get("PGPASSWORD", ""),
        "PGPORT": os.environ.get("PGPORT", "5432"),
        "PGUSER": os.environ.get("PGUSER", ""),
    }

    if database_url:
        parsed = urlsplit(database_url)
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            return database_url

    if all(pg_vars.values()) and pg_vars["PGHOST"] not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        user = quote(pg_vars["PGUSER"], safe="")
        password = quote(pg_vars["PGPASSWORD"], safe="")
        host = pg_vars["PGHOST"]
        port = pg_vars["PGPORT"]
        name = quote(pg_vars["PGDATABASE"], safe="")
        return f"postgres://{user}:{password}@{host}:{port}/{name}"

    if os.environ.get("RAILWAY_ENVIRONMENT_NAME") and database_url:
        raise ImproperlyConfigured(
            "DATABASE_URL points to localhost inside Railway. Reference the "
            "Postgres service variable instead, for example "
            "DATABASE_URL=${{ Postgres.DATABASE_URL }}."
        )

    if os.environ.get("RAILWAY_ENVIRONMENT_NAME"):
        raise ImproperlyConfigured(
            "No Railway Postgres connection variables found. Add a Postgres "
            "service and reference its DATABASE_URL or PG* variables in the "
            "backend service."
        )

    return env("DATABASE_URL")  # noqa: F405

DATABASES = {
    "default": env.db_url_config(production_database_url()),  # noqa: F405
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405
