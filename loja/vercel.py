"""Detecção do runtime Vercel."""

from __future__ import annotations

import os


def em_vercel() -> bool:
    """True quando a app roda como Vercel Function (FastAPI/NiceGUI)."""
    if (os.getenv("VERCEL") or "").strip() == "1":
        return True
    env = (os.getenv("VERCEL_ENV") or "").strip().lower()
    return env in {"production", "preview", "development"}
