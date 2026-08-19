"""Ajustes de runtime do NiceGUI — WebSocket, MIME types e buffers."""

from __future__ import annotations

import mimetypes

# 16 MB — padrão engine.io é 1 MB e estoura com tabelas/painéis grandes
WS_BUFFER_BYTES = 16 * 1024 * 1024

_patch_serverless_feito = False


def _patch_nicegui_serverless() -> None:
    """Vercel/Lambda não suporta ProcessPoolExecutor (SemLock /dev/shm)."""
    global _patch_serverless_feito
    if _patch_serverless_feito:
        return
    _patch_serverless_feito = True

    import nicegui.run as ng_run

    def setup_sem_pool() -> None:
        ng_run.process_pool = None
        ng_run._pool_context = None
        ng_run._pool_uses_implicit_fork = False

    ng_run.setup = setup_sem_pool

    _cpu_original = ng_run.cpu_bound

    async def cpu_bound_serverless(callback, *args, **kwargs):
        if ng_run.process_pool is None:
            return await ng_run.io_bound(callback, *args, **kwargs)
        return await _cpu_original(callback, *args, **kwargs)

    ng_run.cpu_bound = cpu_bound_serverless


def preparar_runtime() -> None:
    """Chamar antes de ui.run() — idempotente."""
    mimetypes.add_type("text/javascript", ".mjs")
    mimetypes.add_type("text/javascript", ".js")

    from loja.vercel import em_vercel

    if em_vercel():
        _patch_nicegui_serverless()

    from nicegui import core

    eio = getattr(core.sio, "eio", None)
    if eio is not None:
        eio.max_http_buffer_size = WS_BUFFER_BYTES
