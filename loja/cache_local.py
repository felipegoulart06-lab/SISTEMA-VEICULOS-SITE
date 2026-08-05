"""Caches em memória para cortar round-trips lentos ao Postgres remoto."""

from __future__ import annotations

import time
from typing import Any

# slug -> bool
_tenant_ok: dict[str, bool] = {}

# slug -> (monotonic_ts, dict)
_config: dict[str, tuple[float, dict]] = {}
_institucional: dict[str, tuple[float, dict]] = {}
_metricas: dict[str, tuple[float, list]] = {}
_marcas: dict[str, tuple[float, list]] = {}
_facetas: dict[str, tuple[float, dict]] = {}
_depoimentos: dict[str, tuple[float, list]] = {}
_html: dict[str, tuple[float, str]] = {}

# conta_id -> (monotonic_ts, snapshot dict)
_conta: dict[int, tuple[float, dict]] = {}

TTL_CONFIG = 300.0
TTL_INST = 300.0
TTL_METRICAS = 120.0
TTL_MARCAS = 120.0
TTL_FACETAS = 180.0
TTL_DEPOIMENTOS = 300.0
TTL_HTML_HOME = 90.0
TTL_HTML_ESTOQUE = 60.0
TTL_HTML_PAGINA = 300.0
TTL_CONTA = 300.0
TTL_QUERY = 180.0

# cache genérico de consultas: chave -> (ts, valor)
_queries: dict[str, tuple[float, Any]] = {}


def tenant_conhecido(slug: str) -> bool | None:
    return _tenant_ok.get((slug or "").lower().strip())


def marcar_tenant(slug: str, existe: bool) -> None:
    key = (slug or "").lower().strip()
    if not key:
        return
    _tenant_ok[key] = existe


def get_config_cache(slug: str) -> dict | None:
    return _get_ttl(_config, slug, TTL_CONFIG)


def set_config_cache(slug: str, dados: dict) -> None:
    _set_ttl(_config, slug, dict(dados))


def get_institucional_cache(slug: str) -> dict | None:
    return _get_ttl(_institucional, slug, TTL_INST)


def set_institucional_cache(slug: str, dados: dict) -> None:
    _set_ttl(_institucional, slug, dict(dados))


def get_metricas_cache(slug: str) -> list | None:
    return _get_ttl(_metricas, slug, TTL_METRICAS)


def set_metricas_cache(slug: str, dados: list) -> None:
    _set_ttl(_metricas, slug, list(dados))


def get_marcas_cache(slug: str) -> list | None:
    return _get_ttl(_marcas, slug, TTL_MARCAS)


def set_marcas_cache(slug: str, dados: list) -> None:
    _set_ttl(_marcas, slug, list(dados))


def get_facetas_cache(slug: str) -> dict | None:
    return _get_ttl(_facetas, slug, TTL_FACETAS)


def set_facetas_cache(slug: str, dados: dict) -> None:
    _set_ttl(_facetas, slug, dict(dados))


def get_depoimentos_cache(slug: str) -> list | None:
    return _get_ttl(_depoimentos, slug, TTL_DEPOIMENTOS)


def set_depoimentos_cache(slug: str, dados: list) -> None:
    _set_ttl(_depoimentos, slug, list(dados))


def get_html_cache(slug: str, chave: str, ttl: float) -> str | None:
    key = f"{(slug or '').lower().strip()}:{chave}"
    hit = _html.get(key)
    if not hit:
        return None
    ts, html = hit
    if time.monotonic() - ts > ttl:
        _html.pop(key, None)
        return None
    return html


def set_html_cache(slug: str, chave: str, html: str) -> None:
    key = f"{(slug or '').lower().strip()}:{chave}"
    if not key.strip(":"):
        return
    _html[key] = (time.monotonic(), html)


def invalidar_site_html(slug: str | None = None) -> None:
    if not slug:
        _html.clear()
        _facetas.clear()
        _depoimentos.clear()
        return
    prefixo = f"{slug.lower().strip()}:"
    for k in list(_html.keys()):
        if k.startswith(prefixo):
            _html.pop(k, None)
    _facetas.pop(slug.lower().strip(), None)
    _depoimentos.pop(slug.lower().strip(), None)


def get_conta_cache(conta_id: int) -> dict | None:
    hit = _conta.get(int(conta_id or 0))
    if not hit:
        return None
    ts, dados = hit
    if time.monotonic() - ts > TTL_CONTA:
        _conta.pop(int(conta_id), None)
        return None
    return dict(dados)


def set_conta_cache(conta_id: int, dados: dict) -> None:
    _conta[int(conta_id)] = (time.monotonic(), dict(dados))


def invalidar_tenant(slug: str | None = None) -> None:
    """Limpa caches de um tenant (ou todos)."""
    if not slug:
        _tenant_ok.clear()
        _config.clear()
        _institucional.clear()
        _metricas.clear()
        _marcas.clear()
        _facetas.clear()
        _depoimentos.clear()
        _html.clear()
        _queries.clear()
        return
    key = slug.lower().strip()
    _tenant_ok.pop(key, None)
    _config.pop(key, None)
    _institucional.pop(key, None)
    _metricas.pop(key, None)
    _marcas.pop(key, None)
    _facetas.pop(key, None)
    _depoimentos.pop(key, None)
    invalidar_site_html(key)
    prefixo = f"{key}:"
    for qk in list(_queries.keys()):
        if qk.startswith(prefixo):
            _queries.pop(qk, None)


def invalidar_conta(conta_id: int | None = None) -> None:
    if conta_id is None:
        _conta.clear()
    else:
        _conta.pop(int(conta_id), None)


def invalidar_config(slug: str | None = None) -> None:
    if not slug:
        _config.clear()
        _institucional.clear()
        _html.clear()
        return
    key = slug.lower().strip()
    _config.pop(key, None)
    _institucional.pop(key, None)
    invalidar_site_html(key)


def invalidar_listagens(slug: str | None = None) -> None:
    """Limpa caches de marcas/métricas/queries (após CRUD)."""
    if not slug:
        _metricas.clear()
        _marcas.clear()
        _facetas.clear()
        _depoimentos.clear()
        _html.clear()
        _queries.clear()
        return
    key = slug.lower().strip()
    _metricas.pop(key, None)
    _marcas.pop(key, None)
    _facetas.pop(key, None)
    _depoimentos.pop(key, None)
    invalidar_site_html(key)
    prefixo = f"{key}:"
    for qk in list(_queries.keys()):
        if qk.startswith(prefixo) or qk.startswith("plat:"):
            _queries.pop(qk, None)


def get_query(chave: str, ttl: float = TTL_QUERY) -> Any | None:
    hit = _queries.get(chave)
    if not hit:
        return None
    ts, dados = hit
    if time.monotonic() - ts > ttl:
        _queries.pop(chave, None)
        return None
    if isinstance(dados, dict):
        return dict(dados)
    if isinstance(dados, list):
        return list(dados)
    return dados


def set_query(chave: str, dados: Any) -> None:
    _queries[chave] = (time.monotonic(), dados)


def invalidar_queries(prefixo: str | None = None) -> None:
    if not prefixo:
        _queries.clear()
        return
    for qk in list(_queries.keys()):
        if qk.startswith(prefixo):
            _queries.pop(qk, None)


def _get_ttl(store: dict[str, tuple[float, Any]], slug: str, ttl: float) -> Any | None:
    key = (slug or "").lower().strip()
    hit = store.get(key)
    if not hit:
        return None
    ts, dados = hit
    if time.monotonic() - ts > ttl:
        store.pop(key, None)
        return None
    if isinstance(dados, dict):
        return dict(dados)
    if isinstance(dados, list):
        return list(dados)
    return dados


def _set_ttl(store: dict[str, tuple[float, Any]], slug: str, dados: Any) -> None:
    key = (slug or "").lower().strip()
    if not key:
        return
    store[key] = (time.monotonic(), dados)
