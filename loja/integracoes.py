"""
Conectores de marketplaces — pensado para lojista leigo.

Hoje: fila + simulação de sync (pronto para plugar APIs reais depois).
Quando o lojista liga um conector e cadastra/altera um veículo, o sistema
enfileira o envio automaticamente.
"""

from datetime import datetime

from sqlalchemy import select

from loja.database import get_session
from loja.models import ConectorIntegracao, SyncIntegracao, VeiculoDB

# Catálogo oficial — ordem de importância para o lojista BR
CATALOGO_CONECTORES = [
    {
        "codigo": "webmotors",
        "nome": "Webmotors",
        "categoria": "marketplace",
        "descricao": "Maior portal de carros do Brasil. Seus anúncios aparecem para milhares de compradores.",
        "disponivel": True,
        "ordem": 1,
    },
    {
        "codigo": "icarros",
        "nome": "iCarros",
        "categoria": "marketplace",
        "descricao": "Portal clássico de seminovos. Bom para alcançar compradores que pesquisam preço.",
        "disponivel": True,
        "ordem": 2,
    },
    {
        "codigo": "olx",
        "nome": "OLX",
        "categoria": "marketplace",
        "descricao": "Classificados com muito volume local. Ideal para vender rápido na sua região.",
        "disponivel": True,
        "ordem": 3,
    },
    {
        "codigo": "mercadolivre",
        "nome": "Mercado Livre",
        "categoria": "marketplace",
        "descricao": "Alcance nacional. Clientes já estão acostumados a comprar por lá.",
        "disponivel": True,
        "ordem": 4,
    },
    {
        "codigo": "mobiauto",
        "nome": "Mobiauto",
        "categoria": "marketplace",
        "descricao": "Marketplace focado em seminovos e gestão de anúncios para lojas.",
        "disponivel": True,
        "ordem": 5,
    },
    {
        "codigo": "usadosbr",
        "nome": "UsadosBR",
        "categoria": "marketplace",
        "descricao": "Portal de usados com boa presença em várias regiões do Brasil.",
        "disponivel": True,
        "ordem": 6,
    },
    {
        "codigo": "carrosnaweb",
        "nome": "Carros na Web",
        "categoria": "marketplace",
        "descricao": "Classificados automotivos com histórico forte no mercado brasileiro.",
        "disponivel": True,
        "ordem": 7,
    },
    {
        "codigo": "chavesnamao",
        "nome": "Chaves na Mão",
        "categoria": "classificados",
        "descricao": "Portal de classificados de veículos e imóveis — boa exposição regional.",
        "disponivel": True,
        "ordem": 8,
    },
    {
        "codigo": "autoline",
        "nome": "Autoline",
        "categoria": "classificados",
        "descricao": "Classificados automotivos para anunciar seu estoque em mais um canal.",
        "disponivel": True,
        "ordem": 9,
    },
    {
        "codigo": "autoavaliar",
        "nome": "Auto Avaliar",
        "categoria": "gestao",
        "descricao": "Mais voltado a avaliação e gestão de usados. Útil no fluxo de compra de veículos.",
        "disponivel": True,
        "ordem": 10,
    },
    {
        "codigo": "instacarro",
        "nome": "InstaCarro",
        "categoria": "gestao",
        "descricao": "Processo específico de compra/venda rápida. Ative se a sua loja trabalha com eles.",
        "disponivel": True,
        "ordem": 11,
    },
    {
        "codigo": "karvi",
        "nome": "Karvi",
        "categoria": "marketplace",
        "descricao": "Integração disponível quando a parceria estiver liberada. Deixe pronto para ligar.",
        "disponivel": False,
        "ordem": 12,
    },
]

LABEL_CATEGORIA = {
    "marketplace": "Marketplaces",
    "classificados": "Classificados",
    "gestao": "Avaliação e gestão",
}


def seed_conectores() -> None:
    with get_session() as db:
        existentes = {c.codigo for c in db.scalars(select(ConectorIntegracao)).all()}
        for item in CATALOGO_CONECTORES:
            if item["codigo"] in existentes:
                # atualiza nome/descrição/ordem se já existe
                c = db.scalar(
                    select(ConectorIntegracao).where(
                        ConectorIntegracao.codigo == item["codigo"]
                    )
                )
                if c:
                    c.nome = item["nome"]
                    c.categoria = item["categoria"]
                    c.descricao = item["descricao"]
                    c.disponivel = item["disponivel"]
                    c.ordem = item["ordem"]
                continue
            db.add(ConectorIntegracao(
                codigo=item["codigo"],
                nome=item["nome"],
                categoria=item["categoria"],
                descricao=item["descricao"],
                disponivel=item["disponivel"],
                ordem=item["ordem"],
                ativo=False,
                status_msg="Desligado",
            ))
        db.commit()


def listar_conectores() -> list[ConectorIntegracao]:
    with get_session() as db:
        rows = db.scalars(
            select(ConectorIntegracao).order_by(ConectorIntegracao.ordem)
        ).all()
        for r in rows:
            db.expunge(r)
        return list(rows)


def obter_conector(codigo: str) -> ConectorIntegracao | None:
    with get_session() as db:
        c = db.scalar(
            select(ConectorIntegracao).where(ConectorIntegracao.codigo == codigo)
        )
        if c:
            db.expunge(c)
        return c


def salvar_conector(codigo: str, dados: dict) -> None:
    with get_session() as db:
        c = db.scalar(
            select(ConectorIntegracao).where(ConectorIntegracao.codigo == codigo)
        )
        if not c:
            return
        for k, v in dados.items():
            if hasattr(c, k):
                setattr(c, k, v)
        if c.ativo and c.disponivel:
            if c.login and c.codigo_acesso:
                c.status_msg = "Ligado — sincronizando anúncios"
            elif c.login or c.codigo_acesso:
                c.status_msg = "Ligado — falta completar o acesso"
            else:
                c.status_msg = "Ligado — aguardando dados de acesso"
        elif not c.disponivel:
            c.status_msg = "Em breve"
            c.ativo = False
        else:
            c.status_msg = "Desligado"
        db.commit()


def ligar_conector(codigo: str, ligado: bool) -> str:
    """Retorna mensagem amigável para o lojista."""
    with get_session() as db:
        c = db.scalar(
            select(ConectorIntegracao).where(ConectorIntegracao.codigo == codigo)
        )
        if not c:
            return "Conector não encontrado."
        if ligado and not c.disponivel:
            return f"{c.nome} ainda não está disponível. Em breve!"
        c.ativo = ligado
        if ligado:
            if c.login and c.codigo_acesso:
                c.status_msg = "Ligado — sincronizando anúncios"
                msg = f"{c.nome} ligado! Novos veículos serão enviados automaticamente."
            else:
                c.status_msg = "Ligado — falta completar o acesso"
                msg = (
                    f"{c.nome} ligado. Complete o e-mail e o código de acesso "
                    "para começar a enviar anúncios."
                )
        else:
            c.status_msg = "Desligado"
            msg = f"{c.nome} desligado. Não enviaremos mais anúncios para lá."
        db.commit()
        return msg


def listar_conectores_ativos() -> list[ConectorIntegracao]:
    with get_session() as db:
        rows = db.scalars(
            select(ConectorIntegracao).where(
                ConectorIntegracao.ativo.is_(True),
                ConectorIntegracao.disponivel.is_(True),
            )
        ).all()
        for r in rows:
            db.expunge(r)
        return list(rows)


def _veiculo_label(v: VeiculoDB) -> str:
    return f"{v.marca} {v.modelo} {v.ano}".strip()


def enfileirar_sync_veiculo(veiculo_id: int, acao: str = "enviar") -> int:
    """
    Quando um veículo é criado/alterado/excluído, agenda sync
    em todos os conectores ligados.
    """
    with get_session() as db:
        v = db.get(VeiculoDB, veiculo_id) if acao != "remover" else None
        nome = _veiculo_label(v) if v else f"Veículo #{veiculo_id}"

        # se vendeu ou despublicou → tratar como remover dos portais
        if v and acao != "remover":
            if v.status == "vendido" or not getattr(v, "publicado", True):
                acao = "remover"
            elif acao == "enviar":
                acao = "atualizar" if v.id else "enviar"

        ativos = db.scalars(
            select(ConectorIntegracao).where(
                ConectorIntegracao.ativo.is_(True),
                ConectorIntegracao.disponivel.is_(True),
            )
        ).all()
        if not ativos:
            return 0

        count = 0
        for c in ativos:
            status, mensagem = _executar_sync(c, v, nome, acao)
            db.add(SyncIntegracao(
                conector_codigo=c.codigo,
                veiculo_id=veiculo_id if acao != "remover" or v else veiculo_id,
                veiculo_nome=nome,
                acao=acao,
                status=status,
                mensagem=mensagem,
            ))
            c.ultimo_sync = datetime.now()
            if status == "ok":
                c.status_msg = "Ligado — último envio ok"
            elif status == "aguardando":
                c.status_msg = "Ligado — falta completar o acesso"
            else:
                c.status_msg = f"Atenção: {mensagem[:80]}"
            count += 1
        db.commit()
        return count


def _executar_sync(
    conector: ConectorIntegracao,
    veiculo: VeiculoDB | None,
    nome: str,
    acao: str,
) -> tuple[str, str]:
    """
    Ponto único para plugar APIs reais no futuro.
    Sem credenciais: status 'aguardando' (não assusta o lojista).
    Com credenciais: simula sucesso (modo demonstração / fila pronta).
    """
    verbo = {
        "enviar": "enviado para",
        "atualizar": "atualizado em",
        "remover": "removido de",
    }.get(acao, "sincronizado com")

    if not conector.login or not conector.codigo_acesso:
        return (
            "aguardando",
            f"{nome}: conector {conector.nome} ligado, mas falta e-mail/código de acesso.",
        )

    # Aqui entrará a chamada real à API de cada portal.
    # Por enquanto: sucesso simulado para o lojista já ver o fluxo completo.
    return "ok", f"{nome} foi {verbo} {conector.nome}."


def sincronizar_estoque_completo() -> int:
    """Reenvia todo o estoque publicado para os conectores ligados."""
    total = 0
    with get_session() as db:
        veiculos = db.scalars(
            select(VeiculoDB).where(
                VeiculoDB.status == "disponivel",
                VeiculoDB.publicado.is_(True),
            )
        ).all()
        ids = [v.id for v in veiculos]
    for vid in ids:
        total += enfileirar_sync_veiculo(vid, acao="atualizar")
    return total


def listar_sync_logs(limite: int = 40) -> list[SyncIntegracao]:
    with get_session() as db:
        rows = db.scalars(
            select(SyncIntegracao)
            .order_by(SyncIntegracao.criado_em.desc())
            .limit(limite)
        ).all()
        for r in rows:
            db.expunge(r)
        return list(rows)


def resumo_integracoes() -> dict:
    from sqlalchemy import func

    with get_session() as db:
        todos = db.scalars(select(ConectorIntegracao)).all()
        ligados = sum(1 for c in todos if c.ativo and c.disponivel)
        disponiveis = sum(1 for c in todos if c.disponivel)
        erros = db.scalar(
            select(func.count()).select_from(SyncIntegracao).where(
                SyncIntegracao.status == "erro"
            )
        ) or 0
        return {
            "ligados": ligados,
            "disponiveis": disponiveis,
            "total": len(todos),
            "tem_erro": erros > 0,
        }
