"""Configura NiceGUI para export ASGI na Vercel (sem ui.run)."""

from __future__ import annotations

import os

from nicegui import core
from nicegui.storage import set_storage_secret

from loja.vercel import em_vercel


def secret_key() -> str:
    chave = (os.getenv("SECRET_KEY") or "").strip()
    if len(chave) >= 32:
        return chave
    return "sigma-erp-secret-change-in-production"


def configurar_export_vercel() -> None:
    """Prepara storage e config do NiceGUI quando `app` é exportado para a Vercel."""
    if not em_vercel():
        return
    try:
        core.app.config.add_run_config(
            reload=False,
            title="Gestão Veículos",
            viewport="width=device-width, initial-scale=1",
            favicon="",
            dark=False,
            language=None,
            binding_refresh_interval=0.1,
            reconnect_timeout=30.0,
            message_history_length=1000,
            tailwind=True,
            unocss=None,
            prod_js=True,
            show_welcome_message=False,
            cache_control_directives=(
                "public, max-age=31536000, immutable, stale-while-revalidate=31536000"
            ),
            markdown=False,
        )
        set_storage_secret(secret_key(), None)
        core.app.setup()
    except Exception as err:
        print(f"[vercel] setup NiceGUI: {err}")
