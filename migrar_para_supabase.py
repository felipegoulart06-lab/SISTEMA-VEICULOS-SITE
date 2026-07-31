"""Migra dados de um tenant SQLite local para o schema Postgres no Supabase."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)

from loja.db_config import schema_tenant, usando_postgres  # noqa: E402
from loja.models import Base  # noqa: E402
from loja.plataforma import (  # noqa: E402
    engine_tenant,
    get_tenant_sessionmaker,
    listar_contas,
)

FK_CANDIDATAS = (
    "veiculo_id",
    "cliente_id",
    "lead_id",
    "campanha_id",
    "proposta_id",
    "usuario_id",
    "categoria_id",
)


def _ids_validos_fonte(src, tabelas) -> dict[str, set[int]]:
    """IDs presentes no SQLite por tabela (para limpar FKs órfãs)."""
    validos: dict[str, set[int]] = {}
    for tabela in tabelas:
        if "id" not in tabela.c:
            continue
        rows = src.execute(select(tabela.c.id)).all()
        validos[tabela.name] = {int(r[0]) for r in rows if r[0] is not None}
    return validos


def _mapa_fk_para_tabela(tabela) -> dict[str, str]:
    """coluna_fk -> nome da tabela pai."""
    mapa: dict[str, str] = {}
    for col in tabela.columns:
        for fk in col.foreign_keys:
            mapa[col.name] = fk.column.table.name
    convencao = {
        "veiculo_id": "veiculos",
        "cliente_id": "clientes",
        "lead_id": "leads",
        "campanha_id": "campanhas",
        "proposta_id": "propostas",
        "usuario_id": "usuarios",
        "categoria_id": "categorias_tenant",
    }
    for nome, pai in convencao.items():
        if nome in tabela.c and nome not in mapa:
            mapa[nome] = pai
    return mapa


def _sanitizar_fks(payload: list[dict], fk_mapa: dict[str, str], ids_validos: dict[str, set[int]]) -> int:
    zeradas = 0
    for item in payload:
        for col, pai in fk_mapa.items():
            if col not in item or item[col] is None:
                continue
            try:
                ref = int(item[col])
            except (TypeError, ValueError):
                item[col] = None
                zeradas += 1
                continue
            permitidos = ids_validos.get(pai, set())
            if ref not in permitidos:
                item[col] = None
                zeradas += 1
    return zeradas


def migrar_sqlite_para_postgres(slug: str, sqlite_path: Path) -> None:
    if not usando_postgres():
        raise RuntimeError("DATABASE_URL Postgres não configurada.")
    if not sqlite_path.exists():
        raise FileNotFoundError(sqlite_path)

    src_engine = create_engine(
        f"sqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False},
    )
    SrcSession = sessionmaker(bind=src_engine, autoflush=False, autocommit=False)

    dst_engine = engine_tenant(slug)
    Base.metadata.create_all(bind=dst_engine)
    DstSession = get_tenant_sessionmaker(slug)
    schema = schema_tenant(slug)

    defaults = {
        "criado_em": datetime.now(),
        "atualizado_em": datetime.now(),
        "senha_temporaria": False,
        "precisa_trocar_senha": False,
        "ativo": True,
        "ativa": True,
        "publicado": True,
        "pago": False,
        "concluida": False,
        "concluido": False,
        "destaque": False,
        "disponivel": True,
        "sistema": True,
        "publicada": False,
        "no_menu": False,
        "ordem": 0,
        "visualizacoes": 0,
        "nota": 5,
        "valor": 0,
        "custo": 0,
        "preco": 0,
        "km": 0,
        "ano": 2020,
        "status": "novo",
    }

    tabelas = list(Base.metadata.sorted_tables)
    with SrcSession() as src, DstSession() as dst:
        ids_validos = _ids_validos_fonte(src, tabelas)
        for tabela in tabelas:
            nome = tabela.name
            rows = src.execute(select(tabela)).mappings().all()
            if not rows:
                continue
            dst.execute(text(f'TRUNCATE TABLE "{schema}"."{nome}" CASCADE'))
            payload = []
            for r in rows:
                item = dict(r)
                for chave, valor in list(item.items()):
                    if valor is None and chave in defaults:
                        item[chave] = defaults[chave]
                payload.append(item)

            fk_mapa = _mapa_fk_para_tabela(tabela)
            zeradas = _sanitizar_fks(payload, fk_mapa, ids_validos)
            try:
                dst.execute(tabela.insert(), payload)
            except Exception:
                dst.rollback()
                # Último recurso: zera todas as FKs candidatas e tenta de novo
                for item in payload:
                    for fk in FK_CANDIDATAS:
                        if fk in item:
                            item[fk] = None
                dst.execute(tabela.insert(), payload)
                print(f"  {nome}: {len(payload)} registros (FKs zeradas após erro)")
            else:
                extra = f" ({zeradas} FKs órfãs limpas)" if zeradas else ""
                print(f"  {nome}: {len(payload)} registros{extra}")
        dst.commit()
    print(f"OK tenant '{slug}' -> schema {schema}")


def main() -> None:
    contas_dir = ROOT / "dados" / "contas"
    legacy = ROOT / "dados" / "loja.db"
    contas = {c.slug: c for c in listar_contas()}

    alvos: list[tuple[str, Path]] = []
    for slug in contas:
        path = contas_dir / f"{slug}.db"
        if path.exists():
            alvos.append((slug, path))
    if "sigma" in contas and not any(s == "sigma" for s, _ in alvos) and legacy.exists():
        alvos.append(("sigma", legacy))

    if not alvos:
        print("Nenhum SQLite local encontrado para migrar.")
        return

    for slug, path in alvos:
        print(f"Migrando {slug} de {path.name}...")
        migrar_sqlite_para_postgres(slug, path)


if __name__ == "__main__":
    main()
