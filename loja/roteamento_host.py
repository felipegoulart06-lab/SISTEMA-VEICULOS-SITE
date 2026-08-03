"""Resolução de tenant pelo Host (subdomínio ERP ou domínio do site)."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Literal

from loja.plataforma import normalizar_dominio, obter_conta_por_dominio_site, obter_conta_por_subdominio

ModoHost = Literal["local", "erp", "site"]

HOSTS_LOCAIS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})

_ctx_host: ContextVar["ContextoHost | None"] = ContextVar("contexto_host", default=None)


@dataclass
class ContextoHost:
    modo: ModoHost
    slug: str | None = None
    host: str = ""


def normalizar_host(host: str) -> str:
    return normalizar_dominio((host or "").split(":")[0])


def eh_host_local(host: str) -> bool:
    h = normalizar_host(host)
    if not h:
        return True
    if h in HOSTS_LOCAIS:
        return True
    return h.endswith(".localhost") or h.endswith(".local")


def resolver_contexto_host(host: str) -> ContextoHost:
    """Define se o acesso é local (dev), ERP (subdomínio) ou site (domínio próprio)."""
    h = normalizar_host(host)
    if eh_host_local(h):
        return ContextoHost(modo="local", host=h)

    conta = obter_conta_por_subdominio(h)
    if conta is not None:
        return ContextoHost(modo="erp", slug=conta.slug, host=h)

    conta = obter_conta_por_dominio_site(h)
    if conta is not None:
        return ContextoHost(modo="site", slug=conta.slug, host=h)

    return ContextoHost(modo="local", host=h)


def set_contexto_host(ctx: ContextoHost) -> None:
    _ctx_host.set(ctx)


def get_contexto_host() -> ContextoHost:
    ctx = _ctx_host.get()
    if ctx is not None:
        return ctx
    return ContextoHost(modo="local")


def erp_login_url() -> str:
    if get_contexto_host().modo == "erp":
        return "/login"
    return "/admin/login"


def erp_admin_url(caminho: str = "") -> str:
    """Painel ERP — sempre em /admin (também no subdomínio da empresa)."""
    base = "/admin"
    if not caminho:
        return base
    if not caminho.startswith("/"):
        caminho = "/" + caminho
    return f"{base}{caminho}"


def erp_trocar_senha_url() -> str:
    if get_contexto_host().modo == "erp":
        return "/trocar-senha"
    return "/admin/trocar-senha"
