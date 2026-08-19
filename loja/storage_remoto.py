"""Armazenamento de arquivos — local (Docker) ou Supabase Storage (Vercel)."""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from loja.db_config import SUPABASE_URL
from loja.provisionamento import pasta_storage
from loja.vercel import em_vercel

_BUCKET = (os.getenv("SUPABASE_STORAGE_BUCKET") or "media").strip()
_SERVICE_KEY = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()


def usar_storage_remoto() -> bool:
    if em_vercel():
        return True
    flag = (os.getenv("SUPABASE_STORAGE") or "").strip().lower()
    return flag in {"1", "true", "yes", "on"} and bool(_SERVICE_KEY)


def _url_publica_supabase(caminho: str) -> str:
    base = SUPABASE_URL.rstrip("/")
    return f"{base}/storage/v1/object/public/{_BUCKET}/{caminho.lstrip('/')}"


def salvar_bytes(slug: str, subpasta: str, nome: str, conteudo: bytes, mime: str) -> str:
    """Persiste arquivo e devolve URL pública."""
    if usar_storage_remoto():
        return _salvar_supabase(slug, subpasta, nome, conteudo, mime)
    pasta = pasta_storage(slug) / subpasta
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / nome
    destino.write_bytes(conteudo)
    return f"/media/{slug}/{subpasta}/{nome}"


def _salvar_supabase(
    slug: str, subpasta: str, nome: str, conteudo: bytes, mime: str,
) -> str:
    if not _SERVICE_KEY:
        raise RuntimeError(
            "Defina SUPABASE_SERVICE_ROLE_KEY na Vercel para uploads de imagens."
        )
    caminho = f"{slug}/{subpasta}/{nome}"
    url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/{_BUCKET}/{caminho}"
    headers = {
        "Authorization": f"Bearer {_SERVICE_KEY}",
        "Content-Type": mime,
        "x-upsert": "true",
    }
    resp = httpx.post(url, content=conteudo, headers=headers, timeout=60.0)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Supabase Storage: {resp.status_code} {resp.text[:200]}")
    return _url_publica_supabase(caminho)


def resolver_url_media(url: str) -> str:
    """Normaliza URLs /media/... para Supabase quando aplicável."""
    if not url or url.startswith(("http://", "https://", "data:")):
        return url
    if not usar_storage_remoto():
        return url
    prefixo = "/media/"
    if not url.startswith(prefixo):
        return url
    resto = url[len(prefixo):].lstrip("/")
    return _url_publica_supabase(resto)
