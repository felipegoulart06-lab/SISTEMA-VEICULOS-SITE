from dataclasses import dataclass
from datetime import datetime, timedelta

from passlib.hash import pbkdf2_sha256
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from loja.database import get_session
from loja.models import Avaliacao, Campanha, ConfigLoja, Lead, Usuario, VeiculoDB
from loja.whitelabel import cfg_dict


@dataclass
class Veiculo:
    id: int
    marca: str
    modelo: str
    ano: int
    km: int
    combustivel: str
    cambio: str
    preco: float
    imagem: str
    destaque: bool = False
    status: str = "disponivel"
    custo: float = 0
    descricao: str = ""
    cor: str = "BRANCO"
    tipo: str = "AUTOMÓVEL"
    badge: str = "PRONTA ENTREGA"
    info_extra: str = ""
    imagem_destaque: str = ""


@dataclass
class FiltrosEstoque:
    marca: str | None = None
    ano: int | None = None
    combustivel: str | None = None
    cor: str | None = None
    tipo: str | None = None
    busca: str = ""
    ordenar: str = "recente"
    pagina: int = 1


ITENS_POR_PAGINA = 8


STATUS_VEICULO = ["disponivel", "reservado", "vendido", "rascunho"]
STATUS_LEAD = [
    "novo", "contato", "negociacao", "financiamento", "fechado", "perdido",
]
COMBUSTIVEIS = ["FLEX", "GASOLINA", "DIESEL", "ELÉTRICO", "HÍBRIDO"]
CAMBIOS = ["MANUAL", "AUTOMÁTICO", "AUTOMATIZADO"]
ORIGENS = ["site", "google", "instagram", "facebook", "olx", "indicacao", "balcao", "financiamento", "contato", "ia_chat"]
STATUS_AVALIACAO = ["novo", "analisado", "contatado", "fechou", "perdido"]
ESTADO_PNEUS = ["BOM", "REGULAR", "RUIM"]

# mapear status antigos do seed
_LEAD_STATUS_MAP = {
    "contatado": "contato",
    "visita": "negociacao",
    "proposta": "negociacao",
    "fechou": "fechado",
}


def _to_veiculo(v: VeiculoDB) -> Veiculo:
    publicado = getattr(v, "publicado", True)
    status = v.status if publicado else "rascunho"
    return Veiculo(
        id=v.id, marca=v.marca, modelo=v.modelo, ano=v.ano, km=v.km,
        combustivel=v.combustivel, cambio=v.cambio, preco=v.preco,
        imagem=v.imagem, destaque=v.destaque, status=status,
        custo=v.custo, descricao=v.descricao or "",
        cor=v.cor or "BRANCO", tipo=v.tipo or "AUTOMÓVEL",
        badge=v.badge or "PRONTA ENTREGA",
        info_extra=v.info_extra or "",
        imagem_destaque=getattr(v, "imagem_destaque", "") or "",
    )


def formatar_preco(valor: float) -> str:
    inteiro, centavos = f"{valor:.2f}".split(".")
    inteiro_fmt = f"{int(inteiro):,}".replace(",", ".")
    return f"R$ {inteiro_fmt},{centavos}"


def formatar_km(km: int) -> str:
    return f"{km:,}".replace(",", ".") + " KM"


def obter_config() -> ConfigLoja:
    with get_session() as db:
        cfg = db.scalar(select(ConfigLoja).limit(1))
        if cfg is None:
            raise RuntimeError("Configuração da loja não encontrada.")
        db.expunge(cfg)
        return cfg


def config_como_dict() -> dict:
    from loja.cache_local import get_config_cache, set_config_cache
    from loja.tenant_ctx import get_tenant_slug

    slug = get_tenant_slug() or ""
    cached = get_config_cache(slug)
    if cached is not None:
        return cached
    dados = cfg_dict(obter_config())
    if slug:
        set_config_cache(slug, dados)
    return dados


def salvar_config(dados: dict) -> None:
    from loja.cache_local import invalidar_config
    from loja.tenant_ctx import get_tenant_slug

    with get_session() as db:
        cfg = db.scalar(select(ConfigLoja).limit(1))
        if cfg is None:
            return
        for chave, valor in dados.items():
            if hasattr(cfg, chave):
                setattr(cfg, chave, valor)
        db.commit()
    invalidar_config(get_tenant_slug())


def listar_marcas() -> list[str]:
    from loja.cache_local import get_marcas_cache, set_marcas_cache
    from loja.tenant_ctx import get_tenant_slug

    slug = get_tenant_slug() or ""
    cached = get_marcas_cache(slug)
    if cached is not None:
        return cached
    with get_session() as db:
        rows = db.scalars(
            select(VeiculoDB.marca)
            .where(VeiculoDB.status == "disponivel")
            .distinct()
            .order_by(VeiculoDB.marca)
        ).all()
        resultado = list(rows)
    if slug:
        set_marcas_cache(slug, resultado)
    return resultado


def filtrar_veiculos(
    marca: str | None = None,
    busca: str = "",
    apenas_disponiveis: bool = True,
    limite: int | None = None,
) -> list[Veiculo]:
    from sqlalchemy.orm import load_only

    with get_session() as db:
        q = select(VeiculoDB)
        if limite:
            q = q.options(
                load_only(
                    VeiculoDB.id,
                    VeiculoDB.marca,
                    VeiculoDB.modelo,
                    VeiculoDB.ano,
                    VeiculoDB.km,
                    VeiculoDB.combustivel,
                    VeiculoDB.cambio,
                    VeiculoDB.preco,
                    VeiculoDB.imagem,
                    VeiculoDB.imagem_destaque,
                    VeiculoDB.destaque,
                    VeiculoDB.status,
                    VeiculoDB.publicado,
                    VeiculoDB.cor,
                    VeiculoDB.tipo,
                    VeiculoDB.badge,
                    VeiculoDB.custo,
                )
            )
        if apenas_disponiveis:
            q = q.where(
                VeiculoDB.status == "disponivel",
                VeiculoDB.publicado.is_(True),
            )
        if marca:
            q = q.where(VeiculoDB.marca == marca)
        q = q.order_by(VeiculoDB.destaque.desc(), VeiculoDB.id)
        if limite:
            q = q.limit(limite)
        rows = db.scalars(q).all()
        resultado = [_to_veiculo(v) for v in rows]
        if busca.strip():
            termo = busca.strip().lower()
            resultado = [
                v for v in resultado
                if termo in v.modelo.lower()
                or termo in v.marca.lower()
                or str(v.ano) in termo
            ]
        return resultado


def listar_todos_veiculos() -> list[VeiculoDB]:
    with get_session() as db:
        rows = db.scalars(
            select(VeiculoDB).order_by(VeiculoDB.id.desc())
        ).all()
        for r in rows:
            db.expunge(r)
        return list(rows)


LIMITE_LISTAGEM_ERP = 500


def listar_veiculos_resumo(limite: int = LIMITE_LISTAGEM_ERP) -> list[VeiculoDB]:
    """Campos mínimos para tabelas — evita TEXT pesados no WebSocket."""
    from sqlalchemy.orm import load_only

    with get_session() as db:
        rows = db.scalars(
            select(VeiculoDB)
            .options(
                load_only(
                    VeiculoDB.id,
                    VeiculoDB.marca,
                    VeiculoDB.modelo,
                    VeiculoDB.placa,
                    VeiculoDB.ano,
                    VeiculoDB.preco,
                    VeiculoDB.status,
                    VeiculoDB.publicado,
                    VeiculoDB.destaque,
                )
            )
            .order_by(VeiculoDB.id.desc())
            .limit(limite)
        ).all()
        for r in rows:
            db.expunge(r)
        return list(rows)


def listar_veiculos_opcoes(limite: int = LIMITE_LISTAGEM_ERP) -> dict[int, str]:
    """Mapa id → rótulo para selects e kanban."""
    with get_session() as db:
        rows = db.execute(
            select(VeiculoDB.id, VeiculoDB.marca, VeiculoDB.modelo)
            .order_by(VeiculoDB.id.desc())
            .limit(limite)
        ).all()
        return {r.id: f"{r.marca} {r.modelo}" for r in rows}


def obter_veiculo(veiculo_id: int) -> VeiculoDB | None:
    with get_session() as db:
        v = db.get(VeiculoDB, veiculo_id)
        if v:
            db.expunge(v)
        return v


def obter_veiculo_publico(veiculo_id: int) -> VeiculoDB | None:
    v = obter_veiculo(veiculo_id)
    if v is None or v.status != "disponivel":
        return None
    if not getattr(v, "publicado", True):
        return None
    return v


def incrementar_visualizacoes(veiculo_id: int) -> None:
    with get_session() as db:
        v = db.get(VeiculoDB, veiculo_id)
        if v is None:
            return
        v.visualizacoes = (getattr(v, "visualizacoes", 0) or 0) + 1
        db.commit()


def salvar_veiculo(dados: dict, veiculo_id: int | None = None) -> None:
    from loja.cache_local import invalidar_listagens
    from loja.tenant_ctx import get_tenant_slug

    with get_session() as db:
        if veiculo_id:
            v = db.get(VeiculoDB, veiculo_id)
            if not v:
                return
            novo = False
        else:
            v = VeiculoDB()
            db.add(v)
            novo = True
        for chave, valor in dados.items():
            if hasattr(v, chave):
                setattr(v, chave, valor)
        db.flush()
        if getattr(v, "destaque", False):
            for outro in db.scalars(
                select(VeiculoDB).where(
                    VeiculoDB.destaque.is_(True),
                    VeiculoDB.id != v.id,
                )
            ).all():
                outro.destaque = False
        db.commit()
        db.refresh(v)
        vid = v.id
        acao = "enviar" if novo else "atualizar"

    invalidar_listagens(get_tenant_slug())

    # Sincroniza com marketplaces ligados (não bloqueia o cadastro se falhar)
    try:
        from loja.integracoes import enfileirar_sync_veiculo

        enfileirar_sync_veiculo(vid, acao=acao)
    except Exception:
        pass


def excluir_veiculo(veiculo_id: int) -> None:
    try:
        from loja.integracoes import enfileirar_sync_veiculo

        enfileirar_sync_veiculo(veiculo_id, acao="remover")
    except Exception:
        pass
    with get_session() as db:
        v = db.get(VeiculoDB, veiculo_id)
        if v:
            db.delete(v)
            db.commit()


def veiculo_destaque(lista: list[Veiculo]) -> Veiculo | None:
    for v in lista:
        if v.destaque:
            return v
    return lista[0] if lista else None


def _query_estoque(db: Session, f: FiltrosEstoque):
    q = select(VeiculoDB).where(
        VeiculoDB.status == "disponivel",
        VeiculoDB.publicado.is_(True),
    )
    if f.marca:
        q = q.where(VeiculoDB.marca == f.marca)
    if f.ano:
        q = q.where(VeiculoDB.ano == f.ano)
    if f.combustivel:
        q = q.where(VeiculoDB.combustivel == f.combustivel)
    if f.cor:
        q = q.where(VeiculoDB.cor == f.cor)
    if f.tipo:
        q = q.where(VeiculoDB.tipo == f.tipo)
    return q


def _ordenar_query(q, ordenar: str):
    if ordenar == "menor_preco":
        return q.order_by(VeiculoDB.preco.asc())
    if ordenar == "maior_preco":
        return q.order_by(VeiculoDB.preco.desc())
    if ordenar == "ano_desc":
        return q.order_by(VeiculoDB.ano.desc(), VeiculoDB.id.desc())
    return q.order_by(VeiculoDB.id.desc())


def facetas_estoque() -> dict:
    with get_session() as db:
        todos = db.scalars(
            select(VeiculoDB).where(
                VeiculoDB.status == "disponivel",
                VeiculoDB.publicado.is_(True),
            )
        ).all()

        def agrupar(campo: str) -> list[tuple]:
            c: dict = {}
            for v in todos:
                k = getattr(v, campo)
                c[k] = c.get(k, 0) + 1
            if campo == "ano":
                return sorted(c.items(), key=lambda x: -x[0])
            return sorted(c.items(), key=lambda x: (-x[1], str(x[0])))

        return {
            "tipo": agrupar("tipo"),
            "marca": agrupar("marca"),
            "ano": agrupar("ano"),
            "combustivel": agrupar("combustivel"),
            "cor": agrupar("cor"),
            "total": len(todos),
        }


def filtrar_estoque(f: FiltrosEstoque) -> tuple[list[Veiculo], int]:
    with get_session() as db:
        q = _ordenar_query(_query_estoque(db, f), f.ordenar)
        rows = db.scalars(q).all()
        resultado = [_to_veiculo(v) for v in rows]
        if f.busca.strip():
            termo = f.busca.strip().lower()
            resultado = [
                v for v in resultado
                if termo in v.modelo.lower()
                or termo in v.marca.lower()
                or str(v.ano) in termo
            ]
        total = len(resultado)
        inicio = (f.pagina - 1) * ITENS_POR_PAGINA
        return resultado[inicio:inicio + ITENS_POR_PAGINA], total


def listar_leads(limite: int = 300) -> list[Lead]:
    with get_session() as db:
        rows = db.scalars(
            select(Lead).order_by(Lead.criado_em.desc()).limit(limite)
        ).all()
        for r in rows:
            db.expunge(r)
        return list(rows)


def salvar_lead(dados: dict, lead_id: int | None = None) -> None:
    from loja.crm_repo import registrar_atividade

    limpos = dict(dados)
    for campo in ("nome", "telefone", "email", "observacoes", "origem", "vendedor"):
        if campo in limpos and isinstance(limpos[campo], str):
            limpos[campo] = limpos[campo].strip()
    if not lead_id and not limpos.get("nome"):
        raise ValueError("Nome do lead é obrigatório.")
    if "status" in limpos and limpos["status"] in _LEAD_STATUS_MAP:
        limpos["status"] = _LEAD_STATUS_MAP[limpos["status"]]

    with get_session() as db:
        if lead_id:
            lead = db.get(Lead, lead_id)
            if not lead:
                return
        else:
            lead = Lead()
            db.add(lead)
        for chave, valor in limpos.items():
            if hasattr(lead, chave):
                setattr(lead, chave, valor)
        db.commit()
        if not lead_id:
            registrar_atividade(f"Novo lead: {lead.nome}", "lead")


def excluir_lead(lead_id: int) -> None:
    with get_session() as db:
        lead = db.get(Lead, lead_id)
        if lead:
            db.delete(lead)
            db.commit()


def listar_campanhas() -> list[Campanha]:
    with get_session() as db:
        rows = db.scalars(select(Campanha).order_by(Campanha.id)).all()
        for r in rows:
            db.expunge(r)
        return list(rows)


def salvar_campanha(dados: dict, campanha_id: int | None = None) -> None:
    with get_session() as db:
        if campanha_id:
            c = db.get(Campanha, campanha_id)
            if not c:
                return
        else:
            c = Campanha()
            db.add(c)
        for chave, valor in dados.items():
            if hasattr(c, chave):
                setattr(c, chave, valor)
        db.commit()


def metricas_dashboard() -> dict:
    from loja.cache_local import get_query, set_query
    from loja.crm_repo import listar_atividades, metricas_crm
    from loja.tenant_ctx import get_tenant_slug

    slug = get_tenant_slug() or "_"
    chave = f"{slug}:metricas_dashboard"
    cached = get_query(chave, ttl=60)
    if cached is not None:
        return cached

    with get_session() as db:
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        semana = hoje - timedelta(days=7)

        reserv = db.scalar(
            select(func.count()).select_from(VeiculoDB)
            .where(VeiculoDB.status == "reservado")
        ) or 0
        valor_estoque = db.scalar(
            select(func.sum(VeiculoDB.preco)).where(
                VeiculoDB.status.in_(["disponivel", "reservado"])
            )
        ) or 0
        leads_semana = db.scalar(
            select(func.count()).select_from(Lead).where(Lead.criado_em >= semana)
        ) or 0
        leads_hoje = db.scalar(
            select(func.count()).select_from(Lead).where(Lead.criado_em >= hoje)
        ) or 0
        por_origem = db.execute(
            select(Lead.origem, func.count())
            .group_by(Lead.origem)
            .order_by(func.count().desc())
        ).all()

    crm = metricas_crm()
    atividades = listar_atividades(10)
    resultado = {
        "disponiveis": crm["disponiveis"],
        "reservados": reserv,
        "vendidos": crm["vendidos"],
        "valor_estoque": valor_estoque,
        "leads_novos": crm["leads_novos"],
        "leads_semana": leads_semana,
        "leads_hoje": leads_hoje,
        "avaliacoes_novas": crm["avaliacoes_novas"],
        "por_origem": list(por_origem),
        "faturamento_mes": crm["faturamento_mes"],
        "lucro_estimado": crm["lucro_estimado"],
        "leads_negociacao": crm["leads_negociacao"],
        "top_anuncios": crm["top_anuncios"],
        "agenda_dia": crm["agenda_dia"],
        "atividades": [
            {"texto": a.texto, "quando": a.criado_em.strftime("%d/%m %H:%M")}
            for a in atividades
        ],
    }
    set_query(chave, resultado)
    return resultado


def salvar_avaliacao(dados: dict) -> None:
    with get_session() as db:
        a = Avaliacao()
        db.add(a)
        for chave, valor in dados.items():
            if hasattr(a, chave):
                setattr(a, chave, valor)
        db.commit()


def listar_avaliacoes() -> list[Avaliacao]:
    with get_session() as db:
        rows = db.scalars(
            select(Avaliacao).order_by(Avaliacao.criado_em.desc())
        ).all()
        for r in rows:
            db.expunge(r)
        return list(rows)


def salvar_avaliacao_status(avaliacao_id: int, status: str) -> None:
    with get_session() as db:
        a = db.get(Avaliacao, avaliacao_id)
        if a:
            a.status = status
            db.commit()


def excluir_avaliacao(avaliacao_id: int) -> None:
    with get_session() as db:
        a = db.get(Avaliacao, avaliacao_id)
        if a:
            db.delete(a)
            db.commit()


def autenticar(email: str, senha: str) -> Usuario | None:
    with get_session() as db:
        user = db.scalar(select(Usuario).where(Usuario.email == email, Usuario.ativo))
        if user and pbkdf2_sha256.verify(senha, user.senha_hash):
            db.expunge(user)
            return user
        return None
