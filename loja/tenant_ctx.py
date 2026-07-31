"""Contexto de tenant (empresa) por request / aba do navegador.

Ordem de resolução do slug ativo:
1. ContextVar (escopo do request/handler atual)
2. app.storage.client["tenant_slug"] (aba — site público e ERP)
3. app.storage.user["conta_slug"] (sessão do admin da empresa)

O site público sempre grava o slug da URL no client storage, para que
callbacks (formulários, chat, timers) não caiam no tenant de outro login.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

from nicegui import app

_slug_ctx: ContextVar[str | None] = ContextVar("tenant_slug", default=None)


def set_tenant_slug(slug: str | None) -> None:
    _slug_ctx.set((slug or "").strip().lower() or None)


def _storage_client_slug() -> str | None:
    try:
        valor = app.storage.client.get("tenant_slug")
        return (valor or "").strip().lower() or None
    except Exception:
        return None


def _storage_user_slug() -> str | None:
    try:
        valor = app.storage.user.get("conta_slug")
        return (valor or "").strip().lower() or None
    except Exception:
        return None


def get_tenant_slug() -> str | None:
    return _slug_ctx.get() or _storage_client_slug() or _storage_user_slug()


def ligar_tenant(slug: str | None) -> None:
    """Define o tenant no ContextVar e no storage da aba."""
    normalizado = (slug or "").strip().lower() or None
    set_tenant_slug(normalizado)
    try:
        if normalizado:
            app.storage.client["tenant_slug"] = normalizado
        else:
            app.storage.client.pop("tenant_slug", None)
    except Exception:
        pass


def limpar_tenant() -> None:
    ligar_tenant(None)


@contextmanager
def tenant_escopo(slug: str):
    """Garante o tenant apenas durante o bloco (útil em tasks/timers)."""
    anterior = _slug_ctx.get()
    set_tenant_slug(slug)
    try:
        yield
    finally:
        set_tenant_slug(anterior)


def site_base(slug: str | None = None) -> str:
    """Prefixo do site público. Ex: /loja/sigma"""
    ativo = (slug or get_tenant_slug() or "").strip().lower()
    if not ativo:
        return ""
    return f"/loja/{ativo}"


def site_url(caminho: str = "/", slug: str | None = None) -> str:
    """Monta URL do site público com prefixo da loja."""
    base = site_base(slug)
    if not caminho.startswith("/"):
        caminho = "/" + caminho
    if caminho == "/":
        return base + "/" if base else "/"
    return f"{base}{caminho}" if base else caminho


def resolver_link_site(link: str, slug: str | None = None) -> str:
    """Normaliza links salvos no ERP (relativos ou absolutos) para o site da loja."""
    link = (link or "").strip()
    if not link:
        return site_url("/", slug)
    if link.startswith(("http://", "https://", "mailto:", "tel:")):
        return link
    if link.startswith("/loja/"):
        return link
    return site_url(link, slug)
