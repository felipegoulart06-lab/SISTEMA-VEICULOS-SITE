"""Ajustes de runtime do NiceGUI — WebSocket, MIME types e buffers."""

from __future__ import annotations

import mimetypes

# 16 MB — padrão engine.io é 1 MB e estoura com tabelas/painéis grandes
WS_BUFFER_BYTES = 16 * 1024 * 1024


def preparar_runtime() -> None:
    """Chamar antes de ui.run() — idempotente."""
    mimetypes.add_type("text/javascript", ".mjs")
    mimetypes.add_type("text/javascript", ".js")

    from nicegui import core

    eio = getattr(core.sio, "eio", None)
    if eio is not None:
        eio.max_http_buffer_size = WS_BUFFER_BYTES
