"""Migra dados de tenants SQLite locais para o Supabase Postgres."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)

from loja.migracao_sqlite import (  # noqa: E402
    caminho_sqlite_tenant,
    migrar_sqlite_para_postgres,
)
from loja.plataforma import listar_contas  # noqa: E402


def main() -> None:
    alvos: list[tuple[str, Path]] = []
    for conta in listar_contas():
        path = caminho_sqlite_tenant(conta.slug)
        if path is not None:
            alvos.append((conta.slug, path))

    if not alvos:
        print("Nenhum SQLite local encontrado para migrar.")
        return

    for slug, path in alvos:
        print(f"Migrando {slug} de {path.name}...")
        migrar_sqlite_para_postgres(slug, path)
        print(f"OK tenant '{slug}'")


if __name__ == "__main__":
    main()
