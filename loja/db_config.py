"""Configuração de banco — Supabase Postgres (produção) ou SQLite (local)."""

from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv(
    "SUPABASE_URL", "https://twhzjmdfxueuerivoxhx.supabase.co",
).rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_PROJECT_ID = os.getenv("SUPABASE_PROJECT_ID", "twhzjmdfxueuerivoxhx")


def _montar_database_url() -> str:
    """Prioridade: USE_LOCAL_SQLITE > DATABASE_URL > SUPABASE_* > vazio (SQLite)."""
    # Velocidade local: ignore Postgres remoto (Canada = ~0,5s por query)
    flag = (os.getenv("USE_LOCAL_SQLITE") or "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return ""

    explicita = (os.getenv("DATABASE_URL") or "").strip()
    if explicita:
        return explicita

    user = (os.getenv("SUPABASE_DB_USER") or "").strip()
    password = (os.getenv("SUPABASE_DB_PASSWORD") or "").strip()
    host = (os.getenv("SUPABASE_DB_HOST") or "").strip()
    port = (os.getenv("SUPABASE_DB_PORT") or "5432").strip()
    dbname = (os.getenv("SUPABASE_DB_NAME") or "postgres").strip()
    if user and password and host:
        return (
            f"postgresql+psycopg://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/{dbname}?sslmode=require"
        )
    return ""


@lru_cache(maxsize=1)
def database_url() -> str:
    return _montar_database_url()


def usando_postgres() -> bool:
    url = database_url().lower()
    return url.startswith("postgresql") or url.startswith("postgres")


def schema_tenant(slug: str) -> str:
    """Nome de schema Postgres seguro a partir do slug."""
    limpo = "".join(c if c.isalnum() else "_" for c in (slug or "").lower())
    limpo = limpo.strip("_") or "empresa"
    if limpo[0].isdigit():
        limpo = f"t_{limpo}"
    return f"tenant_{limpo}"[:63]
