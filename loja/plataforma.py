"""Plataforma White Label — MVP.

Responsabilidades desta camada:
- Autenticar o Administrador Master e o administrador de cada empresa.
- Criar, editar, suspender e excluir empresas.
- Controlar status, licença, plano e domínios.
- Registrar os logs de ciclo de vida da empresa.
"""

from __future__ import annotations

import os
import re
import secrets
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from passlib.hash import pbkdf2_sha256
from sqlalchemy import create_engine, func, or_, select, text
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session, sessionmaker

from loja.db_config import database_url, schema_tenant, usando_postgres
from loja.models import Usuario
from loja.plataforma_models import (
    AdminMaster,
    ConfigPlataforma,
    Conta,
    LogPlataforma,
    Plano,
    PlataformaBase,
)

if TYPE_CHECKING:
    from loja.provisionamento import ResultadoProvisionamento

load_dotenv()

from loja.paths import dir_dados

DADOS_DIR = dir_dados()
CONTAS_DIR = DADOS_DIR / "contas"

_pg_engine = None


def _engine_plataforma():
    """Engine único da plataforma (Postgres em produção, SQLite local)."""
    global _pg_engine
    if usando_postgres():
        if _pg_engine is None:
            _pg_engine = create_engine(
                database_url(),
                # Sem pre_ping: cada check é 1 RTT (~0,5–1s) até o pooler remoto.
                pool_pre_ping=False,
                pool_recycle=280,
                pool_size=12,
                max_overflow=24,
                pool_timeout=30,
            )
        return _pg_engine
    return create_engine(
        f"sqlite:///{DADOS_DIR / 'plataforma.db'}",
        connect_args={"check_same_thread": False},
    )


plataforma_engine = _engine_plataforma()
PlataformaSession = sessionmaker(
    bind=plataforma_engine, autoflush=False, autocommit=False,
)

_tenant_engines: dict[str, object] = {}
_tenant_sessions: dict[str, sessionmaker] = {}

# Status da empresa
STATUS_CONTA = ["teste", "ativa", "suspensa", "cancelada"]
STATUS_LABEL = {
    "teste": "Em teste",
    "ativa": "Ativa",
    "suspensa": "Desativada",
    "cancelada": "Cancelada",
}
STATUS_COM_ACESSO = ("teste", "ativa")
DIAS_PARA_EXCLUSAO = 31
# Status exibidos ao criar empresa no Master
STATUS_CRIACAO = {
    "ativa": "Ativo",
    "suspensa": "Desativado",
}

# Logs — apenas o ciclo de vida da empresa
TIPOS_LOG = [
    "empresa_criada",
    "empresa_editada",
    "empresa_suspensa",
    "empresa_excluida",
    "dominio_alterado",
]
LOG_LABEL = {
    "empresa_criada": "Empresa criada",
    "empresa_editada": "Empresa editada",
    "empresa_suspensa": "Empresa suspensa",
    "empresa_excluida": "Empresa excluída",
    "dominio_alterado": "Domínio alterado",
}


# ------------------------------------------------------------------ sessões

def get_plataforma_session() -> Session:
    return PlataformaSession()


def caminho_db_conta(slug: str) -> Path:
    """Caminho legado SQLite (ainda usado em modo local)."""
    return CONTAS_DIR / f"{slug}.db"


def garantir_schema_tenant(slug: str) -> str:
    """Cria o schema Postgres da empresa, se necessário."""
    from loja.cache_local import marcar_tenant, tenant_conhecido

    schema = schema_tenant(slug)
    if not usando_postgres():
        return schema
    # Evita CREATE SCHEMA em todo cold-start de engine se já sabemos que existe
    if tenant_conhecido(slug) is True:
        return schema
    with plataforma_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        conn.execute(text(f'GRANT ALL ON SCHEMA "{schema}" TO CURRENT_USER'))
    marcar_tenant(slug, True)
    return schema


def tenant_existe(slug: str) -> bool:
    from loja.cache_local import marcar_tenant, tenant_conhecido

    slug = (slug or "").lower().strip()
    if not slug:
        return False
    cached = tenant_conhecido(slug)
    if cached is not None:
        return cached
    if usando_postgres():
        schema = schema_tenant(slug)
        with plataforma_engine.connect() as conn:
            ok = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.schemata "
                    "WHERE schema_name = :s"
                ),
                {"s": schema},
            ).scalar() is not None
        marcar_tenant(slug, ok)
        return ok
    ok = caminho_db_conta(slug).exists()
    marcar_tenant(slug, ok)
    return ok


def engine_tenant(slug: str):
    """Engine do ERP/site da empresa (schema Postgres ou arquivo SQLite)."""
    slug = slug.lower().strip()
    if slug in _tenant_engines:
        return _tenant_engines[slug]

    if usando_postgres():
        schema = garantir_schema_tenant(slug)
        eng = plataforma_engine.execution_options(
            schema_translate_map={None: schema},
        )
    else:
        eng = create_engine(
            f"sqlite:///{caminho_db_conta(slug)}",
            connect_args={"check_same_thread": False},
        )

    _tenant_engines[slug] = eng
    _tenant_sessions[slug] = sessionmaker(
        bind=eng, autoflush=False, autocommit=False,
    )
    return eng


def get_tenant_sessionmaker(slug: str) -> sessionmaker:
    engine_tenant(slug)
    return _tenant_sessions[slug.lower().strip()]


def liberar_engine(slug: str) -> None:
    """Libera cache do tenant (necessário antes de apagar SQLite no Windows)."""
    from loja.cache_local import invalidar_tenant

    slug = slug.lower().strip()
    eng = _tenant_engines.pop(slug, None)
    _tenant_sessions.pop(slug, None)
    invalidar_tenant(slug)
    if eng is not None and not usando_postgres():
        eng.dispose()


def slugify(texto: str) -> str:
    texto = (texto or "").lower().strip()
    for origem, destino in (
        ("àáâãä", "a"), ("èéêë", "e"), ("ìíîï", "i"),
        ("òóôõö", "o"), ("ùúûü", "u"), ("ç", "c"),
    ):
        texto = re.sub(f"[{origem}]", destino, texto)
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return re.sub(r"-+", "-", texto).strip("-")[:60] or secrets.token_hex(4)


def normalizar_dominio(dominio: str) -> str:
    dominio = (dominio or "").strip().lower()
    dominio = re.sub(r"^https?://", "", dominio)
    return dominio.strip("/").split("/")[0]


def obter_dominio_base(db: Session | None = None) -> str:
    """Domínio raiz usado para gerar subdomínios únicos por empresa."""
    if db is None:
        with get_plataforma_session() as sess:
            return obter_dominio_base(sess)
    cfg = db.scalar(select(ConfigPlataforma).limit(1))
    base = (cfg.dominio_base if cfg else "plataforma.com.br") or "plataforma.com.br"
    return normalizar_dominio(base) or "plataforma.com.br"


def gerar_dominios_empresa(slug: str, base: str | None = None) -> dict[str, str]:
    """Gera subdomínio ERP; domínio do site é configurado depois pelo Master."""
    slug = (slug or "").strip().lower()
    base = normalizar_dominio(base) if base else obter_dominio_base()
    if not base:
        base = "plataforma.com.br"
    sub = f"{slug}.{base}"
    return {
        "subdominio": sub,
        "dominio_site": "",
        "dominio_erp": sub,
    }


def _dominio_em_uso(db: Session, dominio: str, exceto_id: int | None = None) -> bool:
    if not dominio:
        return False
    for campo in ("subdominio", "dominio_site", "dominio_erp"):
        q = select(Conta.id).where(getattr(Conta, campo) == dominio)
        if exceto_id:
            q = q.where(Conta.id != exceto_id)
        if db.scalar(q):
            return True
    return False


# --------------------------------------------------------------------- init

def _migrar_plataforma() -> None:
    insp = sa_inspect(plataforma_engine)
    tabelas = set(insp.get_table_names())
    tipo_dt = "TIMESTAMPTZ" if usando_postgres() else "DATETIME"

    novas_empresas = {
        "status": "VARCHAR(20) DEFAULT 'teste'",
        "plano_id": "INTEGER",
        "vencimento_em": tipo_dt,
        "desativada_em": tipo_dt,
        "subdominio": "VARCHAR(200) DEFAULT ''",
        "dominio_site": "VARCHAR(200) DEFAULT ''",
        "dominio_erp": "VARCHAR(200) DEFAULT ''",
        "logo_url": "VARCHAR(500) DEFAULT ''",
        "favicon_url": "VARCHAR(500) DEFAULT ''",
        "tema_cor": "VARCHAR(7) DEFAULT '#c0392b'",
        "observacoes": "VARCHAR(500) DEFAULT ''",
        "ultimo_acesso": tipo_dt,
        "dominio_proprio": "VARCHAR(200) DEFAULT ''",
        "tema": "VARCHAR(40) DEFAULT 'padrao'",
        "idioma": "VARCHAR(10) DEFAULT 'pt-BR'",
        "fuso_horario": "VARCHAR(60) DEFAULT 'America/Sao_Paulo'",
        "provisionada_em": tipo_dt,
        "ativa": "BOOLEAN DEFAULT TRUE",
    }
    novas_config = {
        "dominio_base": "VARCHAR(120) DEFAULT 'plataforma.com.br'",
        "versao": "VARCHAR(20) DEFAULT '1.0.0'",
    }
    novas_planos = {
        "descricao": "VARCHAR(300) DEFAULT ''",
        "dias_licenca": "INTEGER DEFAULT 30",
    }
    novas_admin_master = {
        "totp_secret": "VARCHAR(64)",
    }

    for tabela, colunas in (
        ("empresas", novas_empresas),
        ("contas", novas_empresas),  # legado SQLite
        ("config_plataforma", novas_config),
        ("planos", novas_planos),
        ("admin_master", novas_admin_master),
    ):
        if tabela not in tabelas:
            continue
        existentes = {c["name"] for c in insp.get_columns(tabela)}
        for coluna, tipo in colunas.items():
            if coluna in existentes:
                continue
            # Transação isolada: falha de privilege não aborta as demais
            if_not = " IF NOT EXISTS" if usando_postgres() else ""
            try:
                with plataforma_engine.begin() as conn:
                    conn.execute(
                        text(
                            f'ALTER TABLE "{tabela}" '
                            f"ADD COLUMN{if_not} {coluna} {tipo}"
                        )
                    )
            except Exception:
                pass


def init_plataforma() -> None:
    PlataformaBase.metadata.create_all(bind=plataforma_engine)
    _migrar_plataforma()

    with get_plataforma_session() as db:
        if db.scalar(select(AdminMaster).limit(1)) is None:
            db.add(AdminMaster(
                email=os.getenv("MASTER_EMAIL", "master@plataforma.com"),
                senha_hash=pbkdf2_sha256.hash(
                    os.getenv("MASTER_SENHA", "master123")
                ),
                nome="Administrador Master",
            ))
            db.commit()

        if db.scalar(select(ConfigPlataforma).limit(1)) is None:
            db.add(ConfigPlataforma())
            db.commit()

        if db.scalar(select(Plano).where(Plano.nome == "Starter")) is None:
            db.add(Plano(
                nome="Starter",
                descricao="Plano inicial da plataforma.",
                preco_mensal=149.0,
                limite_veiculos=50,
                dias_licenca=30,
                ordem=1,
            ))
            db.commit()

        _migrar_conta_inicial(db)
        _limpar_dados_legado(db)
        _garantir_datas_desativacao(db)

    _garantir_estrutura_tenants()


def _garantir_datas_desativacao(db: Session) -> None:
    """Empresas já suspensas sem data passam a contar 31 dias a partir de agora."""
    from loja.tempo import agora

    agora_dt = agora()
    alterou = False
    for c in db.scalars(
        select(Conta).where(
            Conta.status == "suspensa",
            Conta.desativada_em.is_(None),
        )
    ).all():
        c.desativada_em = agora_dt
        c.ativa = False
        alterou = True
    if alterou:
        db.commit()


def _limpar_dados_legado(db: Session) -> None:
    """Remove o que ficou de versões anteriores ao MVP."""
    starter = db.scalar(select(Plano).where(Plano.nome == "Starter"))
    if starter is None:
        return

    for log in db.scalars(
        select(LogPlataforma).where(LogPlataforma.tipo.notin_(TIPOS_LOG))
    ).all():
        db.delete(log)

    for plano in db.scalars(select(Plano).where(Plano.id != starter.id)).all():
        em_uso = db.scalars(
            select(Conta).where(Conta.plano_id == plano.id)
        ).all()
        for conta in em_uso:
            conta.plano_id = starter.id
        db.delete(plano)

    # Toda empresa precisa de plano e data de vencimento da licença.
    for conta in db.scalars(select(Conta)).all():
        if conta.plano_id is None:
            conta.plano_id = starter.id
        if conta.vencimento_em is None:
            base = db.get(Plano, conta.plano_id) or starter
            conta.vencimento_em = conta.criado_em + timedelta(
                days=base.dias_licenca
            )
    db.commit()


def _migrar_conta_inicial(db: Session) -> None:
    """Traz o loja.db de demonstração para o formato de empresa."""
    if db.scalar(select(Conta).where(Conta.slug == "sigma")) is not None:
        return

    loja_antiga = DADOS_DIR / "loja.db"
    email = os.getenv("ADMIN_EMAIL", "admin@sigma.com")
    token = os.getenv("ADMIN_SENHA", "admin123")
    starter = db.scalar(select(Plano).where(Plano.nome == "Starter"))

    if usando_postgres():
        if not tenant_existe("sigma") and loja_antiga.exists():
            # Provisiona schema vazio; dados são migrados depois se necessário.
            from loja.models import Base
            eng = engine_tenant("sigma")
            Base.metadata.create_all(bind=eng)
        elif not tenant_existe("sigma"):
            from loja.models import Base
            eng = engine_tenant("sigma")
            Base.metadata.create_all(bind=eng)
    else:
        if not loja_antiga.exists():
            return
        destino = caminho_db_conta("sigma")
        if not destino.exists():
            shutil.copy2(loja_antiga, destino)

    conta = Conta(
        nome="SIGMA Multimarcas",
        email=email,
        token_hash=pbkdf2_sha256.hash(token),
        slug="sigma",
        ativa=True,
        status="ativa",
        plano_id=starter.id if starter else None,
        vencimento_em=datetime.now() + timedelta(days=365),
        observacoes="Empresa inicial migrada do ERP de demonstração.",
    )
    db.add(conta)
    db.commit()
    db.refresh(conta)
    _sincronizar_usuario_tenant("sigma", email, token, "Administrador")
    _aplicar_dominios_padrao(db, conta)
    db.commit()


def _aplicar_dominios_padrao(db: Session, conta: Conta) -> None:
    doms = gerar_dominios_empresa(conta.slug, obter_dominio_base(db))
    if not conta.subdominio:
        conta.subdominio = doms["subdominio"]
    if not conta.dominio_erp:
        conta.dominio_erp = conta.subdominio or doms["subdominio"]


def _garantir_estrutura_tenants() -> None:
    """Aplica a estrutura atual às empresas já existentes."""
    from loja.migracao_sqlite import sincronizar_tenant_sqlite_se_vazio
    from loja.provisionamento import criar_storage, migrar_tenant

    for conta in listar_contas():
        if not tenant_existe(conta.slug) and not caminho_db_conta(conta.slug).exists():
            continue
        try:
            migrar_tenant(conta.slug, conta.nome, conta.email)
            criar_storage(conta.slug)
            sincronizar_tenant_sqlite_se_vazio(conta.slug)
        except Exception:  # noqa: BLE001 - init não pode derrubar o app
            continue

    with get_plataforma_session() as db:
        alterou = False
        for conta in db.scalars(select(Conta)).all():
            antes = (conta.subdominio, conta.dominio_site, conta.dominio_erp)
            _aplicar_dominios_padrao(db, conta)
            if (conta.subdominio, conta.dominio_site, conta.dominio_erp) != antes:
                alterou = True
            if conta.status not in STATUS_CONTA:
                conta.status = "ativa"
                alterou = True
            conta.ativa = conta.status in STATUS_COM_ACESSO
        if alterou:
            db.commit()


# --------------------------------------------------------------------- logs

def registrar_log(
    tipo: str,
    mensagem: str,
    conta_id: int | None = None,
    conta_nome: str = "",
) -> None:
    """Grava apenas os eventos de ciclo de vida previstos no MVP."""
    if tipo not in TIPOS_LOG:
        return
    try:
        with get_plataforma_session() as db:
            db.add(LogPlataforma(
                tipo=tipo,
                mensagem=mensagem[:500],
                conta_id=conta_id,
                conta_nome=conta_nome,
            ))
            db.commit()
    except Exception:
        pass


def listar_logs(
    tipo: str | None = None,
    desde: datetime | None = None,
    ate: datetime | None = None,
    limite: int = 150,
) -> list[LogPlataforma]:
    with get_plataforma_session() as db:
        q = select(LogPlataforma).order_by(LogPlataforma.criado_em.desc())
        if tipo:
            q = q.where(LogPlataforma.tipo == tipo)
        if desde:
            q = q.where(LogPlataforma.criado_em >= desde)
        if ate:
            q = q.where(LogPlataforma.criado_em <= ate)
        rows = db.scalars(q.limit(limite)).all()
        for r in rows:
            db.expunge(r)
        return list(rows)


# --------------------------------------------------------------------- auth

def autenticar_master(email: str, senha: str) -> AdminMaster | None:
    with get_plataforma_session() as db:
        user = db.scalar(
            select(AdminMaster).where(
                AdminMaster.email == email.strip().lower(),
                AdminMaster.ativo.is_(True),
            )
        )
        if user and pbkdf2_sha256.verify(senha, user.senha_hash):
            db.expunge(user)
            return user
    return None


def empresa_pode_acessar(conta: Conta) -> tuple[bool, str]:
    """Regra única de acesso ao ERP."""
    from loja.tempo import agora, naive

    if conta.status == "suspensa" or not conta.ativa:
        return False, "Empresa desativada. Fale com o administrador da plataforma."
    if conta.status == "cancelada":
        return False, "Empresa cancelada."
    venc = naive(conta.vencimento_em)
    if venc and venc < agora():
        return False, "Licença vencida. Fale com o administrador da plataforma."
    return True, ""


def autenticar_conta(email: str, senha: str) -> Conta | None:
    """Login da empresa com o e-mail e a senha do administrador único."""
    email = email.strip().lower()
    with get_plataforma_session() as db:
        c = db.scalar(select(Conta).where(Conta.email == email))
        if c is None:
            return None
        liberado, _ = empresa_pode_acessar(c)
        if not liberado:
            return None
        slug, conta_id = c.slug, c.id
        token_hash = c.token_hash

    valido = False
    if tenant_existe(slug) or caminho_db_conta(slug).exists():
        SessionLocal = get_tenant_sessionmaker(slug)
        with SessionLocal() as tdb:
            user = tdb.scalar(
                select(Usuario).where(
                    Usuario.email == email, Usuario.ativo.is_(True),
                )
            )
            if user and pbkdf2_sha256.verify(senha, user.senha_hash):
                user.ultimo_acesso = datetime.now()
                tdb.commit()
                valido = True
    if not valido and pbkdf2_sha256.verify(senha, token_hash):
        valido = True
    if not valido:
        return None

    with get_plataforma_session() as db:
        c = db.get(Conta, conta_id)
        c.ultimo_acesso = datetime.now()
        db.commit()
        db.refresh(c)
        db.expunge(c)
    return c


def motivo_bloqueio(email: str) -> str:
    """Mensagem exibida no login quando a empresa não pode acessar."""
    with get_plataforma_session() as db:
        c = db.scalar(select(Conta).where(Conta.email == email.strip().lower()))
        if c is None:
            return ""
        liberado, motivo = empresa_pode_acessar(c)
        return "" if liberado else motivo


def precisa_trocar_senha(slug: str, email: str) -> bool:
    if not (tenant_existe(slug) or caminho_db_conta(slug).exists()):
        return False
    SessionLocal = get_tenant_sessionmaker(slug)
    with SessionLocal() as db:
        user = db.scalar(
            select(Usuario).where(Usuario.email == email.strip().lower())
        )
        return bool(user and user.precisa_trocar_senha)


def trocar_senha_tenant(slug: str, email: str, nova_senha: str) -> None:
    SessionLocal = get_tenant_sessionmaker(slug)
    with SessionLocal() as db:
        user = db.scalar(
            select(Usuario).where(Usuario.email == email.strip().lower())
        )
        if user is None:
            raise ValueError("Usuário não encontrado.")
        user.senha_hash = pbkdf2_sha256.hash(nova_senha)
        user.senha_temporaria = False
        user.precisa_trocar_senha = False
        db.commit()
    conta = obter_conta_por_slug(slug)
    if conta:
        with get_plataforma_session() as db:
            c = db.get(Conta, conta.id)
            c.token_hash = pbkdf2_sha256.hash(nova_senha)
            db.commit()


def _sincronizar_usuario_tenant(
    slug: str, email: str, token: str, nome: str,
    forcar_troca: bool = False,
) -> None:
    SessionLocal = get_tenant_sessionmaker(slug)
    with SessionLocal() as db:
        user = db.scalar(select(Usuario).where(Usuario.email == email.lower()))
        if user is None:
            user = Usuario(email=email.lower(), nome=nome, ativo=True)
            db.add(user)
        user.senha_hash = pbkdf2_sha256.hash(token)
        user.nome = nome
        user.ativo = True
        user.senha_temporaria = forcar_troca
        user.precisa_trocar_senha = forcar_troca
        db.commit()


# ----------------------------------------------------------------- empresas

def listar_contas(apenas_ativas: bool = False) -> list[Conta]:
    from loja.cache_local import get_query, set_query

    chave = f"plat:contas:{int(apenas_ativas)}"
    cached = get_query(chave, ttl=45)
    if cached is not None:
        out = []
        for snap in cached:
            c = Conta()
            for k, v in snap.items():
                if hasattr(c, k):
                    setattr(c, k, v)
            out.append(c)
        return out

    with get_plataforma_session() as db:
        q = select(Conta).order_by(Conta.criado_em.desc())
        if apenas_ativas:
            q = q.where(Conta.status.in_(STATUS_COM_ACESSO))
        rows = db.scalars(q).all()
        snaps = []
        for r in rows:
            db.expunge(r)
            snaps.append({
                "id": r.id, "nome": r.nome, "email": r.email, "slug": r.slug,
                "status": r.status, "ativa": r.ativa,
                "vencimento_em": r.vencimento_em, "plano_id": r.plano_id,
                "criado_em": r.criado_em, "desativada_em": r.desativada_em,
                "subdominio": r.subdominio,
                "dominio_site": r.dominio_site, "dominio_erp": r.dominio_erp,
                "tema_cor": r.tema_cor, "logo_url": r.logo_url,
                "favicon_url": r.favicon_url, "observacoes": r.observacoes,
            })
        set_query(chave, snaps)
        return list(rows)


def _conta_acessivel(conta: Conta | None) -> Conta | None:
    """None se a conta não existir ou estiver bloqueada (desativada, vencida…)."""
    if conta is None:
        return None
    liberado, _ = empresa_pode_acessar(conta)
    return conta if liberado else None


def invalidar_cache_conta(slug: str, conta_id: int) -> None:
    """Limpa caches de domínio/slug/conta após desativar ou editar empresa."""
    from loja.cache_local import (
        invalidar_conta,
        invalidar_queries,
        invalidar_site_html,
        invalidar_tenant,
    )

    invalidar_conta(conta_id)
    invalidar_queries("plat:contas")
    invalidar_queries("plat:host")
    invalidar_queries(f"plat:slug:{(slug or '').lower().strip()}")
    invalidar_tenant(slug)
    invalidar_site_html(slug)


def obter_conta(conta_id: int) -> Conta | None:
    from loja.cache_local import get_conta_cache, set_conta_cache

    cid = int(conta_id or 0)
    if not cid:
        return None
    snap = get_conta_cache(cid)
    if snap is not None:
        c = Conta()
        for k, v in snap.items():
            if hasattr(c, k):
                setattr(c, k, v)
        return c
    with get_plataforma_session() as db:
        c = db.get(Conta, cid)
        if c:
            db.expunge(c)
            set_conta_cache(cid, {
                "id": c.id,
                "nome": c.nome,
                "email": c.email,
                "slug": c.slug,
                "status": c.status,
                "ativa": c.ativa,
                "vencimento_em": c.vencimento_em,
                "plano_id": c.plano_id,
            })
        return c


def obter_conta_por_slug(slug: str) -> Conta | None:
    from loja.cache_local import get_query, set_query

    key = (slug or "").lower().strip()
    if not key:
        return None
    chave = f"plat:slug:{key}"
    cached = get_query(chave, ttl=300)
    if cached is not None:
        return _conta_acessivel(_conta_de_snap(cached))
    with get_plataforma_session() as db:
        c = db.scalar(select(Conta).where(Conta.slug == key))
        if c:
            db.expunge(c)
            set_query(chave, _conta_snap(c))
            return c
    return None


def _conta_snap(c: Conta) -> dict:
    return {
        "id": c.id,
        "slug": c.slug,
        "nome": c.nome,
        "ativa": c.ativa,
        "status": c.status,
    }


def _conta_de_snap(snap: dict) -> Conta:
    c = Conta()
    for k, v in snap.items():
        if hasattr(c, k):
            setattr(c, k, v)
    return c


def _cache_host(tipo: str, variantes: list[str], conta: Conta | None) -> None:
    from loja.cache_local import set_query

    if not variantes:
        return
    snap = _conta_snap(conta) if conta else None
    if snap is None:
        return
    for h in variantes:
        set_query(f"plat:host:{tipo}:{h}", snap)


def _conta_cache_host(tipo: str, variantes: list[str]) -> Conta | None:
    from loja.cache_local import get_query

    for h in variantes:
        cached = get_query(f"plat:host:{tipo}:{h}", ttl=300)
        if cached is not None:
            ok = _conta_acessivel(_conta_de_snap(cached))
            if ok is not None:
                return ok
    return None


def aquecer_cache_dominios() -> None:
    """Pré-carrega mapa domínio→empresa (evita cold-start lento no site)."""
    try:
        for c in listar_contas(apenas_ativas=True):
            if c.dominio_site:
                _cache_host("site", _variantes_host(c.dominio_site), c)
            if c.subdominio:
                _cache_host("erp", _variantes_host(c.subdominio), c)
            from loja.cache_local import set_query
            set_query(f"plat:slug:{c.slug}", _conta_snap(c))
    except Exception as err:
        print(f"[startup] cache dominios: {err}")


def aquecer_site_tenants() -> None:
    """Pré-aquece engines Postgres, config e marcas de cada loja ativa."""
    from loja.repositorio import config_como_dict, listar_marcas
    from loja.tenant_ctx import set_tenant_slug

    try:
        for c in listar_contas(apenas_ativas=True):
            set_tenant_slug(c.slug)
            try:
                engine_tenant(c.slug)
                config_como_dict()
                listar_marcas()
            finally:
                set_tenant_slug(None)
    except Exception as err:
        print(f"[startup] aquecer site: {err}")


def _variantes_host(host: str) -> list[str]:
    h = normalizar_dominio(host)
    if not h:
        return []
    variantes = [h]
    if h.startswith("www."):
        variantes.append(h[4:])
    else:
        variantes.append(f"www.{h}")
    return variantes


def obter_conta_bloqueada_por_host(host: str) -> Conta | None:
    """Empresa desativada cujo domínio ainda aponta para a plataforma (sem cache)."""
    variantes = _variantes_host(host)
    if not variantes:
        return None
    if obter_conta_por_subdominio(host) or obter_conta_por_dominio_site(host):
        return None
    with get_plataforma_session() as db:
        c = db.scalar(
            select(Conta).where(
                or_(
                    Conta.dominio_site.in_(variantes),
                    Conta.subdominio.in_(variantes),
                    Conta.dominio_erp.in_(variantes),
                ),
                Conta.ativa.is_(False),
            )
        )
        if c:
            db.expunge(c)
            return c
    return None


def obter_conta_por_subdominio(host: str) -> Conta | None:
    """Empresa cujo subdomínio ERP coincide com o Host."""
    variantes = _variantes_host(host)
    if not variantes:
        return None
    hit = _conta_cache_host("erp", variantes)
    if hit is not None:
        return hit
    with get_plataforma_session() as db:
        c = db.scalar(
            select(Conta).where(
                Conta.ativa.is_(True),
                or_(
                    Conta.subdominio.in_(variantes),
                    Conta.dominio_erp.in_(variantes),
                ),
            )
        )
        if c:
            db.expunge(c)
            _cache_host("erp", variantes, c)
            return c
    return None


def obter_conta_por_dominio_site(host: str) -> Conta | None:
    """Empresa cujo domínio público do site coincide com o Host."""
    variantes = _variantes_host(host)
    if not variantes:
        return None
    hit = _conta_cache_host("site", variantes)
    if hit is not None:
        return hit
    with get_plataforma_session() as db:
        c = db.scalar(
            select(Conta).where(
                Conta.dominio_site.in_(variantes),
                Conta.ativa.is_(True),
            )
        )
        if c:
            db.expunge(c)
            _cache_host("site", variantes, c)
            return c
    return None


def criar_conta(
    nome: str,
    email: str,
    slug: str | None = None,
    token: str | None = None,
    plano_id: int | None = None,
    status: str = "teste",
    dias_licenca: int | None = None,
    logo_url: str = "",
    favicon_url: str = "",
    tema_cor: str = "#c0392b",
    observacoes: str = "",
) -> tuple[Conta, str, "ResultadoProvisionamento"]:
    """Cria a empresa, provisiona ERP + site limpos e gera domínios exclusivos."""
    from loja.provisionamento import provisionar_empresa

    email = email.strip().lower()
    nome = nome.strip()
    slug = slugify(slug or nome)
    senha_informada = (token or "").strip()
    if not senha_informada:
        raise ValueError("Informe a senha temporária do administrador.")

    with get_plataforma_session() as db:
        if db.scalar(select(Conta).where(Conta.email == email)):
            raise ValueError("Já existe uma empresa com este e-mail.")
        base_slug = slug
        n = 1
        while db.scalar(select(Conta).where(Conta.slug == slug)):
            slug = f"{base_slug}-{n}"
            n += 1
        plano = db.get(Plano, plano_id) if plano_id else None
        if plano is None:
            plano = db.scalar(select(Plano).order_by(Plano.ordem, Plano.id))
        plano_id = plano.id if plano else None
        plano_nome = plano.nome if plano else ""
        dias = dias_licenca or (plano.dias_licenca if plano else 30)
        base = obter_dominio_base(db)
        doms = gerar_dominios_empresa(slug, base)
        for dom in doms.values():
            if _dominio_em_uso(db, dom):
                raise ValueError(f"Domínio {dom} já está em uso por outra empresa.")

    relatorio = provisionar_empresa(
        slug=slug, nome=nome, email=email, senha_temporaria=senha_informada,
        cor=tema_cor or "#c0392b", logo=logo_url or "",
        favicon=favicon_url or "", plano=plano_nome,
    )
    senha = relatorio.senha_temporaria

    status_final = status if status in STATUS_CRIACAO else "ativa"
    if status_final == "suspensa":
        desativada = datetime.now()
    else:
        desativada = None

    with get_plataforma_session() as db:
        conta = Conta(
            nome=nome,
            email=email,
            token_hash=pbkdf2_sha256.hash(senha),
            slug=slug,
            status=status_final,
            ativa=status_final in STATUS_COM_ACESSO,
            desativada_em=desativada,
            plano_id=plano_id,
            vencimento_em=datetime.now() + timedelta(days=dias),
            subdominio=doms["subdominio"],
            dominio_site=doms["dominio_site"],
            dominio_erp=doms["dominio_erp"],
            logo_url=logo_url or "",
            favicon_url=favicon_url or "",
            tema_cor=tema_cor or "#c0392b",
            observacoes=observacoes or "",
            provisionada_em=datetime.now(),
        )
        db.add(conta)
        db.commit()
        db.refresh(conta)
        conta_id = conta.id
        db.expunge(conta)

    registrar_log("empresa_criada", f"Empresa criada: {nome}", conta_id, nome)
    from loja.cache_local import invalidar_queries
    invalidar_queries("plat:contas")
    return conta, senha, relatorio


def atualizar_conta(conta_id: int, dados: dict) -> None:
    """Edita a empresa e registra o log adequado."""
    from loja.cache_local import invalidar_conta

    dominios_alterados: list[str] = []
    with get_plataforma_session() as db:
        c = db.get(Conta, conta_id)
        if c is None:
            return
        nome = c.nome
        for campo in ("subdominio", "dominio_site", "dominio_erp"):
            if campo in dados:
                novo = normalizar_dominio(dados[campo])
                dados[campo] = novo
                if novo != getattr(c, campo):
                    dominios_alterados.append(f"{campo}={novo or '—'}")
        for chave, valor in dados.items():
            if hasattr(c, chave):
                setattr(c, chave, valor)
        if "status" in dados:
            c.ativa = c.status in STATUS_COM_ACESSO
        db.commit()
        nome = c.nome

    invalidar_conta(conta_id)
    from loja.cache_local import invalidar_queries
    invalidar_queries("plat:contas")
    registrar_log("empresa_editada", f"Empresa editada: {nome}", conta_id, nome)
    if dominios_alterados:
        registrar_log(
            "dominio_alterado",
            f"Domínios de {nome}: {', '.join(dominios_alterados)}",
            conta_id, nome,
        )


def atualizar_dominios(
    conta_id: int,
    subdominio: str,
    dominio_site: str,
    dominio_erp: str = "",
) -> None:
    """Somente o Admin Master altera domínios."""
    alterados: list[str] = []
    with get_plataforma_session() as db:
        c = db.get(Conta, conta_id)
        if c is None:
            return
        novos = {
            "subdominio": normalizar_dominio(subdominio),
            "dominio_site": normalizar_dominio(dominio_site),
            "dominio_erp": normalizar_dominio(dominio_erp)
            or normalizar_dominio(subdominio),
        }
        for campo, valor in novos.items():
            if valor != getattr(c, campo):
                alterados.append(f"{campo.replace('_', ' ')}: {valor or '—'}")
                setattr(c, campo, valor)
        nome = c.nome
        db.commit()
    if alterados:
        from loja.cache_local import invalidar_queries

        invalidar_queries("plat:host")
        invalidar_queries("plat:slug")
        registrar_log(
            "dominio_alterado",
            f"Domínios de {nome} — {', '.join(alterados)}",
            conta_id, nome,
        )


def alterar_status_conta(conta_id: int, status: str) -> None:
    from loja.tempo import agora

    if status not in STATUS_CONTA:
        return
    with get_plataforma_session() as db:
        c = db.get(Conta, conta_id)
        if c is None:
            return
        c.status = status
        c.ativa = status in STATUS_COM_ACESSO
        if status == "suspensa":
            if c.desativada_em is None:
                c.desativada_em = agora()
        else:
            c.desativada_em = None
        nome = c.nome
        slug = c.slug
        db.commit()
    invalidar_cache_conta(slug, conta_id)
    tipo = "empresa_suspensa" if status == "suspensa" else "empresa_editada"
    registrar_log(
        tipo, f"Empresa {nome} agora está {STATUS_LABEL[status]}.",
        conta_id, nome,
    )


def data_liberacao_exclusao(conta: Conta) -> datetime | None:
    """Data a partir da qual a exclusão fica liberada (desativada_em + 31 dias)."""
    from loja.tempo import naive

    if conta.status != "suspensa":
        return None
    base = naive(getattr(conta, "desativada_em", None))
    if base is None:
        return None
    return base + timedelta(days=DIAS_PARA_EXCLUSAO)


def dias_restantes_exclusao(conta: Conta) -> int | None:
    """Dias restantes até poder excluir. 0 = já pode. None = não desativada."""
    from loja.tempo import agora

    liberacao = data_liberacao_exclusao(conta)
    if liberacao is None:
        return None
    resto = (liberacao.date() - agora().date()).days
    return max(0, resto)


def pode_excluir_conta(conta: Conta) -> bool:
    dias = dias_restantes_exclusao(conta)
    return dias is not None and dias == 0


def renovar_licenca(conta_id: int, dias: int = 30) -> datetime | None:
    from loja.tempo import agora, naive

    with get_plataforma_session() as db:
        c = db.get(Conta, conta_id)
        if c is None:
            return None
        base = max(naive(c.vencimento_em) or agora(), agora())
        c.vencimento_em = base + timedelta(days=dias)
        nome, novo = c.nome, c.vencimento_em
        db.commit()
    from loja.cache_local import invalidar_conta
    invalidar_conta(conta_id)
    registrar_log(
        "empresa_editada",
        f"Licença de {nome} renovada até {naive(novo):%d/%m/%Y}.", conta_id, nome,
    )
    return novo


def regenerar_token(conta_id: int) -> str:
    """Nova senha temporária, com troca obrigatória no próximo acesso."""
    from loja.provisionamento import gerar_senha_temporaria

    token = gerar_senha_temporaria()
    with get_plataforma_session() as db:
        c = db.get(Conta, conta_id)
        if not c:
            raise ValueError("Empresa não encontrada.")
        c.token_hash = pbkdf2_sha256.hash(token)
        nome, slug, email = c.nome, c.slug, c.email
        db.commit()
    _sincronizar_usuario_tenant(slug, email, token, "Administrador", True)
    registrar_log(
        "empresa_editada", f"Nova senha temporária para {nome}.", conta_id, nome,
    )
    return token


def excluir_conta(conta_id: int) -> None:
    from loja.cache_local import invalidar_conta, invalidar_queries
    from loja.provisionamento import remover_storage

    with get_plataforma_session() as db:
        c = db.get(Conta, conta_id)
        if not c:
            return
        if not pode_excluir_conta(c):
            dias = dias_restantes_exclusao(c)
            if dias is None:
                raise ValueError(
                    "Desative a empresa e aguarde 31 dias para excluir."
                )
            raise ValueError(
                f"Exclusão liberada em {dias} dia(s). Aguarde o prazo."
            )
        slug, nome = c.slug, c.nome
        db.delete(c)
        db.commit()
    invalidar_conta(conta_id)
    invalidar_queries("plat:contas")

    liberar_engine(slug)
    if usando_postgres():
        schema = schema_tenant(slug)
        with plataforma_engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    else:
        path = caminho_db_conta(slug)
        if path.exists():
            try:
                path.unlink()
            except PermissionError:
                path.rename(path.with_suffix(".db.removido"))
    remover_storage(slug)
    registrar_log("empresa_excluida", f"Empresa excluída: {nome}", None, nome)


# -------------------------------------------------------------------- planos

def listar_planos(apenas_ativos: bool = False) -> list[Plano]:
    with get_plataforma_session() as db:
        q = select(Plano).order_by(Plano.ordem, Plano.id)
        if apenas_ativos:
            q = q.where(Plano.ativo.is_(True))
        rows = db.scalars(q).all()
        for r in rows:
            db.expunge(r)
        return list(rows)


def obter_plano(plano_id: int) -> Plano | None:
    with get_plataforma_session() as db:
        p = db.get(Plano, plano_id)
        if p:
            db.expunge(p)
        return p


def salvar_plano(dados: dict, plano_id: int | None = None) -> None:
    with get_plataforma_session() as db:
        p = db.get(Plano, plano_id) if plano_id else Plano()
        if p is None:
            return
        if not plano_id:
            db.add(p)
        for chave, valor in dados.items():
            if hasattr(p, chave):
                setattr(p, chave, valor)
        db.commit()


def excluir_plano(plano_id: int) -> None:
    with get_plataforma_session() as db:
        if db.scalar(
            select(func.count(Conta.id)).where(Conta.plano_id == plano_id)
        ):
            raise ValueError("Existem empresas usando este plano.")
        p = db.get(Plano, plano_id)
        if p:
            db.delete(p)
            db.commit()


# ------------------------------------------------------------- configuração

_cfg_plat_cache: tuple[float, ConfigPlataforma] | None = None


def obter_config_plataforma() -> ConfigPlataforma:
    import time

    global _cfg_plat_cache
    if _cfg_plat_cache and time.monotonic() - _cfg_plat_cache[0] < 60:
        return _cfg_plat_cache[1]
    with get_plataforma_session() as db:
        cfg = db.scalar(select(ConfigPlataforma).limit(1))
        if cfg is None:
            cfg = ConfigPlataforma()
            db.add(cfg)
            db.commit()
            db.refresh(cfg)
        db.expunge(cfg)
        _cfg_plat_cache = (time.monotonic(), cfg)
        return cfg


def salvar_config_plataforma(dados: dict) -> None:
    global _cfg_plat_cache
    _cfg_plat_cache = None
    with get_plataforma_session() as db:
        cfg = db.scalar(select(ConfigPlataforma).limit(1))
        if cfg is None:
            cfg = ConfigPlataforma()
            db.add(cfg)
        for chave, valor in dados.items():
            if hasattr(cfg, chave):
                setattr(cfg, chave, valor)
        db.commit()


# --------------------------------------------------------------- dashboard

def estatisticas_plataforma() -> dict:
    contas = listar_contas()
    return {
        "total": len(contas),
        "ativas": sum(1 for c in contas if c.status == "ativa"),
        "teste": sum(1 for c in contas if c.status == "teste"),
        "suspensas": sum(1 for c in contas if c.status == "suspensa"),
        "canceladas": sum(1 for c in contas if c.status == "cancelada"),
    }


def ultimas_contas(limite: int = 5) -> list[Conta]:
    return listar_contas()[:limite]
