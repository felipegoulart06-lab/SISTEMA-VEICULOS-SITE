"""Normalização de datas (Postgres retorna timezone-aware)."""

from __future__ import annotations

from datetime import datetime


def naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is not None:
        return dt.replace(tzinfo=None)
    return dt


def agora() -> datetime:
    return datetime.now()
