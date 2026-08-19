"""Entrypoint Vercel — fallback com erro visível se main.py falhar no import."""

from __future__ import annotations

import traceback

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

try:
    from main import app  # NiceGUI App (subclasse FastAPI)
except Exception as exc:
    _trace = traceback.format_exc()
    print(f"[vercel_app] import main falhou:\n{_trace}")

    app = FastAPI(title="Sigma — diagnóstico Vercel")

    @app.get("/health")
    def health():
        return JSONResponse(
            {"status": "import_error", "detail": str(exc)},
            status_code=503,
        )

    @app.get("/{path:path}")
    def catch_all(path: str):
        return PlainTextResponse(
            f"Erro ao carregar aplicacao:\n\n{_trace}",
            status_code=503,
            media_type="text/plain; charset=utf-8",
        )
