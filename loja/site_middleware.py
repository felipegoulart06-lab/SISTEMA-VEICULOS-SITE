"""Middleware que serve o site público em HTML no domínio da loja."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from loja.plataforma import obter_conta_por_slug
from loja.roteamento_host import get_contexto_host
from loja.site_html import html_empresa_bloqueada, tentar_responder_html

_PREFIXOS_IGNORADOS = (
    "/static",
    "/media",
    "/admin",
    "/master",
    "/login",
    "/loja",
    "/health",
    "/_nicegui",
    "/socket.io",
)


def _deve_ignorar(path: str) -> bool:
    for prefixo in _PREFIXOS_IGNORADOS:
        if path == prefixo or path.startswith(prefixo + "/"):
            return True
    return False


class SiteHtmlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        ctx = get_contexto_host()
        if ctx.modo == "bloqueado":
            conta = obter_conta_por_slug(ctx.slug or "")
            nome = conta.nome if conta else ""
            return html_empresa_bloqueada(nome)

        if ctx.modo != "site" or not ctx.slug:
            return await call_next(request)

        path = request.url.path or "/"
        if _deve_ignorar(path):
            return await call_next(request)

        resposta = await tentar_responder_html(ctx.slug, path, request)
        if resposta is not None:
            return resposta
        return await call_next(request)
