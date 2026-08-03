"""Sincroniza dados de tenant SQLite local para schema Postgres (Supabase)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, inspect as sa_inspect, select, text
from sqlalchemy.orm import sessionmaker

from loja.db_config import schema_tenant, usando_postgres
from loja.models import Base, VeiculoDB
from loja.plataforma import (
    caminho_db_conta,
    engine_tenant,
    get_tenant_sessionmaker,
)
from loja.provisionamento import COLUNAS_NOVAS_TENANT

FK_CANDIDATAS = (
    "veiculo_id",
    "cliente_id",
    "lead_id",
    "campanha_id",
    "proposta_id",
    "usuario_id",
    "categoria_id",
)

DEFAULTS_INSERT = {
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
    "cidade": "",
}


def _atualizar_sqlite_legado(engine) -> None:
    """Garante colunas novas no SQLite antes de ler os dados."""
    insp = sa_inspect(engine)
    with engine.begin() as conn:
        for tabela, colunas in COLUNAS_NOVAS_TENANT.items():
            if tabela not in insp.get_table_names():
                continue
            existentes = {c["name"] for c in insp.get_columns(tabela)}
            for coluna, tipo in colunas.items():
                if coluna not in existentes:
                    conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}"))


def _colunas_sqlite(engine, tabela: str) -> set[str]:
    insp = sa_inspect(engine)
    if tabela not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(tabela)}


def _ids_validos_fonte(src, tabelas) -> dict[str, set[int]]:
    validos: dict[str, set[int]] = {}
    for tabela in tabelas:
        if "id" not in tabela.c:
            continue
        cols = _colunas_sqlite(src.get_bind(), tabela.name)
        if "id" not in cols:
            continue
        rows = src.execute(select(tabela.c.id)).all()
        validos[tabela.name] = {int(r[0]) for r in rows if r[0] is not None}
    return validos


def _mapa_fk_para_tabela(tabela) -> dict[str, str]:
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


def _sanitizar_fks(
    payload: list[dict],
    fk_mapa: dict[str, str],
    ids_validos: dict[str, set[int]],
) -> int:
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
            if ref not in ids_validos.get(pai, set()):
                item[col] = None
                zeradas += 1
    return zeradas


def _ler_linhas_fonte(src, tabela, src_engine) -> list[dict]:
    cols_fonte = _colunas_sqlite(src_engine, tabela.name)
    if not cols_fonte:
        return []
    cols = [tabela.c[nome] for nome in tabela.c.keys() if nome in cols_fonte]
    if not cols:
        return []
    return [dict(r) for r in src.execute(select(*cols)).mappings().all()]


def caminho_sqlite_tenant(slug: str) -> Path | None:
    """Retorna o SQLite local da empresa, se existir."""
    path = caminho_db_conta(slug)
    if path.exists():
        return path
    if slug == "sigma":
        legacy = caminho_db_conta(slug).parent.parent / "loja.db"
        if legacy.exists():
            return legacy
    return None


def tenant_postgres_vazio(slug: str) -> bool:
    """True se o tenant Postgres não tem veículos (precisa sincronizar)."""
    if not usando_postgres():
        return False
    Session = get_tenant_sessionmaker(slug)
    with Session() as db:
        total = db.scalar(select(VeiculoDB.id).limit(1))
    return total is None


def sqlite_tem_dados(slug: str, path: Path) -> bool:
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )
    _atualizar_sqlite_legado(engine)
    with engine.connect() as conn:
        if "veiculos" not in sa_inspect(engine).get_table_names():
            return False
        n = conn.execute(text("SELECT COUNT(*) FROM veiculos")).scalar() or 0
        return n > 0


def migrar_sqlite_para_postgres(slug: str, sqlite_path: Path) -> None:
    """Copia todas as tabelas do SQLite local para o schema Postgres do tenant."""
    if not usando_postgres():
        raise RuntimeError("DATABASE_URL Postgres não configurada.")
    if not sqlite_path.exists():
        raise FileNotFoundError(sqlite_path)

    src_engine = create_engine(
        f"sqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False},
    )
    _atualizar_sqlite_legado(src_engine)
    SrcSession = sessionmaker(bind=src_engine, autoflush=False, autocommit=False)

    engine_tenant(slug)
    Base.metadata.create_all(bind=engine_tenant(slug))
    DstSession = get_tenant_sessionmaker(slug)
    schema = schema_tenant(slug)

    tabelas = list(Base.metadata.sorted_tables)
    with SrcSession() as src, DstSession() as dst:
        ids_validos = _ids_validos_fonte(src, tabelas)
        for tabela in tabelas:
            nome = tabela.name
            rows = _ler_linhas_fonte(src, tabela, src_engine)
            if not rows:
                continue
            dst.execute(text(f'TRUNCATE TABLE "{schema}"."{nome}" CASCADE'))
            payload = []
            for item in rows:
                for chave, valor in list(item.items()):
                    if valor is None and chave in DEFAULTS_INSERT:
                        item[chave] = DEFAULTS_INSERT[chave]
                payload.append(item)

            fk_mapa = _mapa_fk_para_tabela(tabela)
            _sanitizar_fks(payload, fk_mapa, ids_validos)
            try:
                dst.execute(tabela.insert(), payload)
            except Exception:
                dst.rollback()
                for item in payload:
                    for fk in FK_CANDIDATAS:
                        if fk in item:
                            item[fk] = None
                dst.execute(tabela.insert(), payload)
        dst.commit()


def sincronizar_tenant_sqlite_se_vazio(slug: str) -> bool:
    """Se Postgres está vazio e há SQLite local com dados, sincroniza."""
    if not usando_postgres() or not tenant_postgres_vazio(slug):
        return False
    path = caminho_sqlite_tenant(slug)
    if path is None or not sqlite_tem_dados(slug, path):
        return False
    migrar_sqlite_para_postgres(slug, path)
    from loja.cache_local import invalidar_conta, invalidar_queries, invalidar_tenant

    invalidar_tenant(slug)
    invalidar_queries("plat:contas")
    invalidar_conta(None)
    return True
