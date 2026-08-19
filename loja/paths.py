"""Caminhos de dados — /tmp na Vercel (disco efêmero)."""

from __future__ import annotations

import os
from pathlib import Path

from loja.vercel import em_vercel


def raiz_projeto() -> Path:
    return Path(__file__).resolve().parent.parent


def dir_dados() -> Path:
    if em_vercel():
        base = Path(os.getenv("SIGMA_DADOS_DIR", "/tmp/sigma-dados"))
    else:
        base = raiz_projeto() / "dados"
    _garantir_dir(base)
    return base


def dir_storage() -> Path:
    base = dir_dados() / "storage"
    _garantir_dir(base)
    return base


def dir_contas() -> Path:
    base = dir_dados() / "contas"
    _garantir_dir(base)
    return base


def _garantir_dir(caminho: Path) -> None:
    try:
        caminho.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
