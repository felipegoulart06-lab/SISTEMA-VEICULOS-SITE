"""CRUD e métricas do CRM (clientes, financeiro, propostas, agenda, etc.)."""

import json
from datetime import datetime, timedelta

from sqlalchemy import func, select

from loja.database import get_session
from loja.models import (
    Atividade,
    Avaliacao,
    Cliente,
    Compromisso,
    Depoimento,
    Documento,
    Financiamento,
    Lancamento,
    Lead,
    LeadAtividade,
    LeadTarefa,
    Popup,
    Proposta,
    VeiculoCusto,
    VeiculoDB,
)

STATUS_LEAD = [
    "novo",
    "contato",
    "negociacao",
    "financiamento",
    "fechado",
    "perdido",
]
LABEL_LEAD = {
    "novo": "Novo",
    "contato": "Contato realizado",
    "negociacao": "Negociação",
    "financiamento": "Financiamento",
    "fechado": "Fechado",
    "perdido": "Perdido",
}
STATUS_PROPOSTA = ["rascunho", "enviada", "aprovada", "recusada"]
TIPOS_COMPROMISSO = [
    "visita",
    "test_drive",
    "entrega",
    "retorno",
    "lembrete",
]
TIPOS_DOCUMENTO = ["recibo", "contrato", "procuracao", "declaracao", "entrega"]
CATEGORIAS_FINANCEIRO = [
    "venda",
    "compra",
    "despesa",
    "comissao",
    "manutencao",
    "marketing",
    "geral",
]


def _expunge_all(db, rows):
    for r in rows:
        db.expunge(r)
    return list(rows)


def registrar_atividade(texto: str, tipo: str = "geral") -> None:
    with get_session() as db:
        db.add(Atividade(texto=texto[:300], tipo=tipo))
        db.commit()


def listar_atividades(limite: int = 12) -> list[Atividade]:
    with get_session() as db:
        rows = db.scalars(
            select(Atividade).order_by(Atividade.criado_em.desc()).limit(limite)
        ).all()
        return _expunge_all(db, rows)


# ---- Clientes ----

def listar_clientes() -> list[Cliente]:
    with get_session() as db:
        rows = db.scalars(select(Cliente).order_by(Cliente.nome)).all()
        return _expunge_all(db, rows)


def obter_cliente(cliente_id: int) -> Cliente | None:
    with get_session() as db:
        c = db.get(Cliente, cliente_id)
        if c:
            db.expunge(c)
        return c


def salvar_cliente(dados: dict, cliente_id: int | None = None) -> int:
    with get_session() as db:
        if cliente_id:
            c = db.get(Cliente, cliente_id)
            if not c:
                return 0
        else:
            c = Cliente()
            db.add(c)
        for k, v in dados.items():
            if hasattr(c, k):
                setattr(c, k, v)
        db.commit()
        db.refresh(c)
        if not cliente_id:
            registrar_atividade(f"Cliente cadastrado: {c.nome}", "cliente")
        return c.id


def excluir_cliente(cliente_id: int) -> None:
    with get_session() as db:
        c = db.get(Cliente, cliente_id)
        if c:
            db.delete(c)
            db.commit()


# ---- Lead histórico / tarefas ----

def listar_lead_atividades(lead_id: int) -> list[LeadAtividade]:
    with get_session() as db:
        rows = db.scalars(
            select(LeadAtividade)
            .where(LeadAtividade.lead_id == lead_id)
            .order_by(LeadAtividade.criado_em.desc())
        ).all()
        return _expunge_all(db, rows)


def adicionar_lead_atividade(lead_id: int, texto: str) -> None:
    with get_session() as db:
        db.add(LeadAtividade(lead_id=lead_id, texto=texto))
        db.commit()


def listar_lead_tarefas(lead_id: int) -> list[LeadTarefa]:
    with get_session() as db:
        rows = db.scalars(
            select(LeadTarefa)
            .where(LeadTarefa.lead_id == lead_id)
            .order_by(LeadTarefa.criado_em.desc())
        ).all()
        return _expunge_all(db, rows)


def salvar_lead_tarefa(dados: dict, tarefa_id: int | None = None) -> None:
    with get_session() as db:
        if tarefa_id:
            t = db.get(LeadTarefa, tarefa_id)
            if not t:
                return
        else:
            t = LeadTarefa()
            db.add(t)
        for k, v in dados.items():
            if hasattr(t, k):
                setattr(t, k, v)
        db.commit()


def mover_lead_status(lead_id: int, status: str) -> None:
    with get_session() as db:
        lead = db.get(Lead, lead_id)
        if not lead or status not in STATUS_LEAD:
            return
        anterior = lead.status
        lead.status = status
        db.add(LeadAtividade(
            lead_id=lead_id,
            texto=f"Status: {LABEL_LEAD.get(anterior, anterior)} → {LABEL_LEAD.get(status, status)}",
        ))
        db.commit()
    registrar_atividade(
        f"Lead {lead_id} movido para {LABEL_LEAD.get(status, status)}", "lead"
    )


# ---- Veículo custos ----

def listar_custos_veiculo(veiculo_id: int) -> list[VeiculoCusto]:
    with get_session() as db:
        rows = db.scalars(
            select(VeiculoCusto)
            .where(VeiculoCusto.veiculo_id == veiculo_id)
            .order_by(VeiculoCusto.data.desc())
        ).all()
        return _expunge_all(db, rows)


def salvar_custo_veiculo(dados: dict) -> None:
    with get_session() as db:
        c = VeiculoCusto()
        db.add(c)
        for k, v in dados.items():
            if hasattr(c, k):
                setattr(c, k, v)
        db.commit()


def excluir_custo_veiculo(custo_id: int) -> None:
    with get_session() as db:
        c = db.get(VeiculoCusto, custo_id)
        if c:
            db.delete(c)
            db.commit()


# ---- Avaliações enriquecidas ----

def salvar_avaliacao_completa(avaliacao_id: int, dados: dict) -> None:
    with get_session() as db:
        a = db.get(Avaliacao, avaliacao_id)
        if not a:
            return
        for k, v in dados.items():
            if hasattr(a, k):
                setattr(a, k, v)
        sugerido = float(dados.get("valor_sugerido", a.valor_sugerido) or 0)
        pago = float(dados.get("valor_pago", a.valor_pago) or 0)
        if "margem" not in dados or dados.get("margem") is None:
            a.margem = sugerido - pago if pago else 0
        db.commit()


# ---- Financeiro ----

def listar_lancamentos(tipo: str | None = None) -> list[Lancamento]:
    with get_session() as db:
        q = select(Lancamento).order_by(Lancamento.criado_em.desc())
        if tipo:
            q = q.where(Lancamento.tipo == tipo)
        rows = db.scalars(q).all()
        return _expunge_all(db, rows)


def salvar_lancamento(dados: dict, lancamento_id: int | None = None) -> None:
    with get_session() as db:
        if lancamento_id:
            l = db.get(Lancamento, lancamento_id)
            if not l:
                return
        else:
            l = Lancamento()
            db.add(l)
        for k, v in dados.items():
            if hasattr(l, k):
                setattr(l, k, v)
        db.commit()
    if not lancamento_id:
        registrar_atividade(
            f"Lançamento: {dados.get('descricao', '')}", "financeiro"
        )


def excluir_lancamento(lancamento_id: int) -> None:
    with get_session() as db:
        l = db.get(Lancamento, lancamento_id)
        if l:
            db.delete(l)
            db.commit()


def resumo_financeiro() -> dict:
    with get_session() as db:
        agora = datetime.now()
        inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        entradas = db.scalar(
            select(func.coalesce(func.sum(Lancamento.valor), 0)).where(
                Lancamento.tipo == "entrada",
                Lancamento.pago.is_(True),
                Lancamento.criado_em >= inicio_mes,
            )
        ) or 0
        saidas = db.scalar(
            select(func.coalesce(func.sum(Lancamento.valor), 0)).where(
                Lancamento.tipo == "saida",
                Lancamento.pago.is_(True),
                Lancamento.criado_em >= inicio_mes,
            )
        ) or 0
        a_receber = db.scalar(
            select(func.coalesce(func.sum(Lancamento.valor), 0)).where(
                Lancamento.tipo == "entrada",
                Lancamento.pago.is_(False),
            )
        ) or 0
        a_pagar = db.scalar(
            select(func.coalesce(func.sum(Lancamento.valor), 0)).where(
                Lancamento.tipo == "saida",
                Lancamento.pago.is_(False),
            )
        ) or 0
        return {
            "entradas_mes": float(entradas),
            "saidas_mes": float(saidas),
            "fluxo_mes": float(entradas) - float(saidas),
            "a_receber": float(a_receber),
            "a_pagar": float(a_pagar),
        }


# ---- Propostas ----

def listar_propostas() -> list[Proposta]:
    with get_session() as db:
        rows = db.scalars(select(Proposta).order_by(Proposta.criado_em.desc())).all()
        return _expunge_all(db, rows)


def obter_proposta(proposta_id: int) -> Proposta | None:
    with get_session() as db:
        p = db.get(Proposta, proposta_id)
        if p:
            db.expunge(p)
        return p


def salvar_proposta(dados: dict, proposta_id: int | None = None) -> int:
    with get_session() as db:
        if proposta_id:
            p = db.get(Proposta, proposta_id)
            if not p:
                return 0
        else:
            p = Proposta()
            db.add(p)
        for k, v in dados.items():
            if hasattr(p, k):
                setattr(p, k, v)
        db.commit()
        db.refresh(p)
        return p.id


def excluir_proposta(proposta_id: int) -> None:
    with get_session() as db:
        p = db.get(Proposta, proposta_id)
        if p:
            db.delete(p)
            db.commit()


# ---- Agenda ----

def listar_compromissos(dia: datetime | None = None) -> list[Compromisso]:
    with get_session() as db:
        q = select(Compromisso).order_by(Compromisso.data_hora)
        if dia:
            ini = dia.replace(hour=0, minute=0, second=0, microsecond=0)
            fim = ini + timedelta(days=1)
            q = q.where(Compromisso.data_hora >= ini, Compromisso.data_hora < fim)
        rows = db.scalars(q).all()
        return _expunge_all(db, rows)


def listar_compromissos_semana() -> list[Compromisso]:
    with get_session() as db:
        ini = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fim = ini + timedelta(days=7)
        rows = db.scalars(
            select(Compromisso)
            .where(Compromisso.data_hora >= ini, Compromisso.data_hora < fim)
            .order_by(Compromisso.data_hora)
        ).all()
        return _expunge_all(db, rows)


def salvar_compromisso(dados: dict, compromisso_id: int | None = None) -> None:
    with get_session() as db:
        if compromisso_id:
            c = db.get(Compromisso, compromisso_id)
            if not c:
                return
        else:
            c = Compromisso()
            db.add(c)
        for k, v in dados.items():
            if hasattr(c, k):
                setattr(c, k, v)
        db.commit()


def excluir_compromisso(compromisso_id: int) -> None:
    with get_session() as db:
        c = db.get(Compromisso, compromisso_id)
        if c:
            db.delete(c)
            db.commit()


# ---- Depoimentos / Popup ----

def listar_depoimentos(apenas_ativos: bool = False) -> list[Depoimento]:
    with get_session() as db:
        q = select(Depoimento).order_by(Depoimento.id.desc())
        if apenas_ativos:
            q = q.where(Depoimento.ativo.is_(True))
        rows = db.scalars(q).all()
        return _expunge_all(db, rows)


def salvar_depoimento(dados: dict, depoimento_id: int | None = None) -> None:
    with get_session() as db:
        if depoimento_id:
            d = db.get(Depoimento, depoimento_id)
            if not d:
                return
        else:
            d = Depoimento()
            db.add(d)
        for k, v in dados.items():
            if hasattr(d, k):
                setattr(d, k, v)
        db.commit()


def excluir_depoimento(depoimento_id: int) -> None:
    with get_session() as db:
        d = db.get(Depoimento, depoimento_id)
        if d:
            db.delete(d)
            db.commit()


def listar_popups() -> list[Popup]:
    with get_session() as db:
        rows = db.scalars(select(Popup).order_by(Popup.id.desc())).all()
        return _expunge_all(db, rows)


def obter_popup_ativo() -> Popup | None:
    with get_session() as db:
        p = db.scalar(select(Popup).where(Popup.ativo.is_(True)).limit(1))
        if p:
            db.expunge(p)
        return p


def salvar_popup(dados: dict, popup_id: int | None = None) -> None:
    with get_session() as db:
        if dados.get("ativo"):
            for p in db.scalars(select(Popup)).all():
                p.ativo = False
        if popup_id:
            p = db.get(Popup, popup_id)
            if not p:
                return
        else:
            p = Popup()
            db.add(p)
        for k, v in dados.items():
            if hasattr(p, k):
                setattr(p, k, v)
        db.commit()


def excluir_popup(popup_id: int) -> None:
    with get_session() as db:
        p = db.get(Popup, popup_id)
        if p:
            db.delete(p)
            db.commit()


# ---- Documentos ----

def listar_documentos() -> list[Documento]:
    with get_session() as db:
        rows = db.scalars(select(Documento).order_by(Documento.criado_em.desc())).all()
        return _expunge_all(db, rows)


def obter_documento(doc_id: int) -> Documento | None:
    with get_session() as db:
        d = db.get(Documento, doc_id)
        if d:
            db.expunge(d)
        return d


def salvar_documento(dados: dict, doc_id: int | None = None) -> int:
    with get_session() as db:
        if doc_id:
            d = db.get(Documento, doc_id)
            if not d:
                return 0
        else:
            d = Documento()
            db.add(d)
        for k, v in dados.items():
            if hasattr(d, k):
                setattr(d, k, v)
        db.commit()
        db.refresh(d)
        return d.id


def excluir_documento(doc_id: int) -> None:
    with get_session() as db:
        d = db.get(Documento, doc_id)
        if d:
            db.delete(d)
            db.commit()


def template_documento(tipo: str, loja: dict, cliente: str = "", veiculo: str = "", valor: str = "") -> str:
    nome = loja.get("nome", "Loja")
    endereco = loja.get("endereco", "")
    cidade = f"{loja.get('cidade', '')}/{loja.get('estado', '')}"
    templates = {
        "recibo": f"""
            <h2>RECIBO</h2>
            <p><strong>{nome}</strong> — {endereco}, {cidade}</p>
            <p>Recebemos de <strong>{cliente or '________'}</strong>
            a quantia de <strong>{valor or 'R$ ________'}</strong>
            referente a <strong>{veiculo or '________'}</strong>.</p>
            <p>Data: ____/____/________</p>
            <p>Assinatura: ________________________</p>
        """,
        "contrato": f"""
            <h2>CONTRATO DE COMPRA E VENDA (SIMPLIFICADO)</h2>
            <p>Vendedor: <strong>{nome}</strong> — CNPJ {loja.get('cnpj', '')}</p>
            <p>Comprador: <strong>{cliente or '________'}</strong></p>
            <p>Veículo: <strong>{veiculo or '________'}</strong></p>
            <p>Valor: <strong>{valor or 'R$ ________'}</strong></p>
            <p>As partes acordam a venda do veículo nas condições acima.</p>
            <p>{cidade}, ____/____/________</p>
        """,
        "procuracao": f"""
            <h2>PROCURAÇÃO</h2>
            <p>Eu, <strong>{cliente or '________'}</strong>, nomeio e constituo
            procurador(a) a loja <strong>{nome}</strong> para atos relativos ao veículo
            <strong>{veiculo or '________'}</strong>.</p>
        """,
        "declaracao": f"""
            <h2>DECLARAÇÃO</h2>
            <p><strong>{nome}</strong> declara para os devidos fins que
            <strong>{cliente or '________'}</strong> negociou o veículo
            <strong>{veiculo or '________'}</strong>.</p>
        """,
        "entrega": f"""
            <h2>TERMO DE ENTREGA</h2>
            <p>Cliente <strong>{cliente or '________'}</strong> declara ter recebido
            o veículo <strong>{veiculo or '________'}</strong> em perfeitas condições,
            com documentação e chaves.</p>
            <p>{cidade}, ____/____/________</p>
        """,
    }
    return templates.get(tipo, templates["recibo"])


# ---- Relatórios / dashboard expandido ----

def metricas_crm() -> dict:
    with get_session() as db:
        agora = datetime.now()
        inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0)

        vendidos_mes = db.scalars(
            select(VeiculoDB).where(
                VeiculoDB.status == "vendido",
                VeiculoDB.atualizado_em >= inicio_mes,
            )
        ).all()
        faturamento = sum(v.preco for v in vendidos_mes)
        lucro = sum((v.preco - (v.custo or 0)) for v in vendidos_mes)

        # fallback: lançamentos de entrada no mês
        fat_lanc = db.scalar(
            select(func.coalesce(func.sum(Lancamento.valor), 0)).where(
                Lancamento.tipo == "entrada",
                Lancamento.pago.is_(True),
                Lancamento.criado_em >= inicio_mes,
            )
        ) or 0
        if faturamento == 0 and fat_lanc:
            faturamento = float(fat_lanc)

        disponiveis = db.scalar(
            select(func.count()).select_from(VeiculoDB).where(
                VeiculoDB.status == "disponivel"
            )
        ) or 0
        vendidos = db.scalar(
            select(func.count()).select_from(VeiculoDB).where(
                VeiculoDB.status == "vendido"
            )
        ) or 0
        leads_novos = db.scalar(
            select(func.count()).select_from(Lead).where(Lead.status == "novo")
        ) or 0
        # pipeline antigo + novo
        leads_neg = db.scalar(
            select(func.count()).select_from(Lead).where(
                Lead.status.in_(["negociacao", "contato", "financiamento", "contatado", "visita", "proposta"])
            )
        ) or 0
        aval_novas = db.scalar(
            select(func.count()).select_from(Avaliacao).where(Avaliacao.status == "novo")
        ) or 0

        top = db.scalars(
            select(VeiculoDB)
            .where(VeiculoDB.status == "disponivel")
            .order_by(VeiculoDB.visualizacoes.desc(), VeiculoDB.destaque.desc())
            .limit(5)
        ).all()
        top_anuncios = [
            {"id": v.id, "nome": f"{v.marca} {v.modelo}", "views": v.visualizacoes or 0}
            for v in top
        ]

        agenda = db.scalars(
            select(Compromisso)
            .where(Compromisso.data_hora >= hoje, Compromisso.data_hora < hoje + timedelta(days=1))
            .order_by(Compromisso.data_hora)
            .limit(8)
        ).all()
        agenda_dia = [
            {
                "id": c.id,
                "titulo": c.titulo,
                "hora": c.data_hora.strftime("%H:%M"),
                "tipo": c.tipo,
            }
            for c in agenda
        ]

        return {
            "faturamento_mes": float(faturamento),
            "lucro_estimado": float(lucro),
            "disponiveis": disponiveis,
            "vendidos": vendidos,
            "leads_novos": leads_novos,
            "leads_negociacao": leads_neg,
            "avaliacoes_novas": aval_novas,
            "top_anuncios": top_anuncios,
            "agenda_dia": agenda_dia,
        }


def lucro_por_veiculo() -> list[dict]:
    with get_session() as db:
        rows = db.scalars(
            select(VeiculoDB).where(VeiculoDB.status == "vendido")
        ).all()
        resultado = []
        for v in rows:
            custos_extra = db.scalar(
                select(func.coalesce(func.sum(VeiculoCusto.valor), 0)).where(
                    VeiculoCusto.veiculo_id == v.id
                )
            ) or 0
            custo_total = (v.custo or 0) + float(custos_extra)
            resultado.append({
                "id": v.id,
                "veiculo": f"{v.marca} {v.modelo}",
                "preco": v.preco,
                "custo": custo_total,
                "lucro": v.preco - custo_total,
            })
        return resultado


def relatorio_vendas() -> list[dict]:
    with get_session() as db:
        rows = db.scalars(
            select(VeiculoDB)
            .where(VeiculoDB.status == "vendido")
            .order_by(VeiculoDB.atualizado_em.desc())
        ).all()
        return [
            {
                "id": v.id,
                "veiculo": f"{v.marca} {v.modelo} {v.ano}",
                "preco": v.preco,
                "custo": v.custo or 0,
                "lucro": v.preco - (v.custo or 0),
                "data": v.atualizado_em.strftime("%d/%m/%Y") if v.atualizado_em else "",
            }
            for v in rows
        ]


def relatorio_leads() -> list[dict]:
    with get_session() as db:
        rows = db.scalars(select(Lead).order_by(Lead.criado_em.desc())).all()
        return [
            {
                "id": l.id,
                "nome": l.nome,
                "telefone": l.telefone,
                "origem": l.origem,
                "status": l.status,
                "vendedor": getattr(l, "vendedor", "") or "",
                "data": l.criado_em.strftime("%d/%m/%Y"),
            }
            for l in rows
        ]


STATUS_FINANCIAMENTO = ["novo", "analise", "aprovado", "recusado", "cancelado"]
LABEL_FINANCIAMENTO = {
    "novo": "Novo",
    "analise": "Em análise",
    "aprovado": "Aprovado",
    "recusado": "Recusado",
    "cancelado": "Cancelado",
}


def listar_financiamentos() -> list[Financiamento]:
    with get_session() as db:
        rows = db.scalars(
            select(Financiamento).order_by(Financiamento.criado_em.desc())
        ).all()
        for r in rows:
            db.expunge(r)
        return list(rows)


def obter_financiamento(fin_id: int) -> Financiamento | None:
    with get_session() as db:
        f = db.get(Financiamento, fin_id)
        if f:
            db.expunge(f)
        return f


def salvar_financiamento_site(dados: dict) -> int:
    resumo = (
        f"Financiamento — {dados.get('veiculo_marca', '')} "
        f"{dados.get('veiculo_modelo', '')} · "
        f"Entrada R$ {float(dados.get('valor_entrada') or 0):,.2f} · "
        f"{int(dados.get('qtd_prestacoes') or 0)}x"
    ).replace(",", "X").replace(".", ",").replace("X", ".")

    with get_session() as db:
        lead = Lead(
            nome=dados["nome"],
            telefone=dados.get("celular") or dados.get("telefone", ""),
            email=dados.get("email", ""),
            origem="financiamento",
            status="financiamento",
            veiculo_id=dados.get("veiculo_id"),
            observacoes=resumo,
        )
        db.add(lead)
        db.flush()
        fin = Financiamento(
            nome=dados["nome"],
            cpf=dados.get("cpf", ""),
            celular=dados.get("celular") or dados.get("telefone", ""),
            email=dados.get("email", ""),
            veiculo_marca=dados.get("veiculo_marca", ""),
            veiculo_modelo=dados.get("veiculo_modelo", ""),
            veiculo_ano_fab=str(dados.get("veiculo_ano_fab", "")),
            veiculo_ano_mod=str(dados.get("veiculo_ano_mod", "")),
            veiculo_cor=dados.get("veiculo_cor", ""),
            valor_veiculo=float(dados.get("valor_veiculo") or 0),
            valor_entrada=float(dados.get("valor_entrada") or 0),
            qtd_prestacoes=int(dados.get("qtd_prestacoes") or 0),
            veiculo_id=dados.get("veiculo_id"),
            lead_id=lead.id,
            status="novo",
            dados_json=json.dumps(dados, ensure_ascii=False),
        )
        db.add(fin)
        db.commit()
        db.refresh(fin)
        fin_id = fin.id

    registrar_atividade(
        f"Nova solicitação de financiamento: {dados['nome']}", "financiamento"
    )
    return fin_id


def salvar_financiamento_admin(dados: dict, fin_id: int) -> None:
    with get_session() as db:
        f = db.get(Financiamento, fin_id)
        if not f:
            return
        for chave, valor in dados.items():
            if hasattr(f, chave):
                setattr(f, chave, valor)
        db.commit()


def excluir_financiamento(fin_id: int) -> None:
    with get_session() as db:
        f = db.get(Financiamento, fin_id)
        if f:
            db.delete(f)
            db.commit()


def dados_financiamento_formatados(fin: Financiamento) -> str:
    try:
        extra = json.loads(fin.dados_json or "{}")
    except json.JSONDecodeError:
        extra = {}
    linhas = [
        "=== DADOS DO VEÍCULO ===",
        f"Marca: {fin.veiculo_marca}",
        f"Modelo: {fin.veiculo_modelo}",
        f"Ano Fab.: {fin.veiculo_ano_fab} / Mod.: {fin.veiculo_ano_mod}",
        f"Cor: {fin.veiculo_cor}",
        f"Valor: R$ {fin.valor_veiculo:,.2f}",
        f"Entrada: R$ {fin.valor_entrada:,.2f}",
        f"Prestações: {fin.qtd_prestacoes}",
        "",
        "=== SOLICITANTE ===",
        f"Nome: {fin.nome}",
        f"CPF: {fin.cpf}",
        f"Celular: {fin.celular}",
        f"E-mail: {fin.email}",
    ]
    for chave, valor in sorted(extra.items()):
        if chave.startswith("_") or valor in (None, "", 0):
            continue
        rotulo = chave.replace("_", " ").title()
        linhas.append(f"{rotulo}: {valor}")
    return "\n".join(linhas).replace(",", "X").replace(".", ",").replace("X", ".")
