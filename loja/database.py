import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from passlib.hash import pbkdf2_sha256
from sqlalchemy import create_engine, select, text
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session, sessionmaker

from loja.models import (
    Avaliacao,
    Base,
    Campanha,
    Cliente,
    Compromisso,
    ConfigLoja,
    Depoimento,
    Documento,
    Lancamento,
    Lead,
    LeadAtividade,
    Popup,
    Proposta,
    Usuario,
    VeiculoCusto,
    VeiculoDB,
)

load_dotenv()

from loja.paths import dir_dados

DADOS_DIR = dir_dados()
DATABASE_URL = f"sqlite:///{DADOS_DIR / 'loja.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class TenantIndisponivel(RuntimeError):
    """O tenant ativo não possui banco de dados provisionado."""


def get_session() -> Session:
    """Sessão obrigatória do tenant ativo. Sem slug → erro (sem fallback)."""
    from loja.plataforma import (
        _tenant_engines,
        caminho_db_conta,
        get_tenant_sessionmaker,
        tenant_existe,
    )
    from loja.tenant_ctx import get_tenant_slug

    slug = get_tenant_slug()
    if not slug:
        raise TenantIndisponivel(
            "Nenhuma empresa ativa no contexto. Operação bloqueada."
        )
    # Se o engine já está em cache, o tenant existe — evita query extra.
    if slug not in _tenant_engines:
        if not tenant_existe(slug) and not caminho_db_conta(slug).exists():
            raise TenantIndisponivel(
                f"A empresa '{slug}' não possui banco provisionado."
            )
    return get_tenant_sessionmaker(slug)()


def init_db() -> None:
    from loja.db_config import usando_postgres
    from loja.plataforma import (
        caminho_db_conta,
        init_plataforma,
        listar_contas,
        tenant_existe,
    )
    from loja.tenant_ctx import set_tenant_slug

    init_plataforma()

    # Seed do loja.db legado só faz sentido no modo SQLite local
    if not usando_postgres():
        Base.metadata.create_all(bind=engine)
        _migrar_colunas()
        with SessionLocal() as db:
            if db.scalar(select(ConfigLoja).limit(1)) is None:
                db.add(ConfigLoja(
                    nome_sistema="Gestão Veículos",
                    nome="SIGMA Multimarcas",
                    razao_social="Sigma Multimarcas Ltda",
                    cnpj="00.000.000/0001-00",
                    slogan="Multimarcas",
                    logo_texto="SIGMA",
                    cidade="Pato Branco",
                    estado="PR",
                    bairro="Centro",
                    cep="85501-000",
                    telefone="(46) 3225-1234",
                    whatsapp="(46) 99999-1234",
                    endereco="Av. Tupi, 1234",
                    email="contato@sigmamultimarcas.com.br",
                    horario="Seg a Sex: 8h30 às 18h | Sáb: 8h30 às 12h",
                    facebook="https://facebook.com",
                    instagram="https://instagram.com",
                    sobre=(
                        "A Sigma Multimarcas atua há mais de 15 anos no mercado "
                        "automotivo de Pato Branco e região."
                    ),
                    banner_url=(
                        "https://images.unsplash.com/photo-1555215695-3004980ad54e"
                        "?w=1400&q=80"
                    ),
                ))
                db.commit()

            if db.scalar(select(Usuario).limit(1)) is None:
                email = os.getenv("ADMIN_EMAIL", "admin@sigma.com")
                senha = os.getenv("ADMIN_SENHA", "admin123")
                db.add(Usuario(
                    email=email,
                    senha_hash=pbkdf2_sha256.hash(senha),
                    nome="Administrador",
                ))
                db.commit()

            if db.scalar(select(VeiculoDB).limit(1)) is None:
                _seed_veiculos(db)

            if db.scalar(select(Campanha).limit(1)) is None:
                db.add_all([
                    Campanha(nome="Google Ads — Estoque geral", origem="google"),
                    Campanha(nome="Instagram — Stories", origem="instagram"),
                    Campanha(nome="Site — Formulário", origem="site"),
                ])
                db.commit()

            if db.scalar(select(Lead).limit(1)) is None:
                _seed_leads(db)

            _normalizar_status_leads(db)
            _seed_crm_demo(db)

    # Conectores são por empresa + aquecimento de engines/caches
    from loja.cache_local import marcar_tenant
    from loja.integracoes import seed_conectores
    from loja.plataforma import engine_tenant
    from loja.repositorio import config_como_dict

    for conta in listar_contas():
        if not tenant_existe(conta.slug) and not caminho_db_conta(conta.slug).exists():
            continue
        marcar_tenant(conta.slug, True)
        set_tenant_slug(conta.slug)
        try:
            engine_tenant(conta.slug)
            try:
                config_como_dict()
            except Exception:
                pass
            seed_conectores()
        finally:
            set_tenant_slug(None)


def _normalizar_status_leads(db: Session) -> None:
    mapa = {
        "contatado": "contato",
        "visita": "negociacao",
        "proposta": "negociacao",
        "fechou": "fechado",
    }
    mudou = False
    for lead in db.scalars(select(Lead)).all():
        if lead.status in mapa:
            lead.status = mapa[lead.status]
            mudou = True
    if mudou:
        db.commit()


def _seed_crm_demo(db: Session) -> None:
    _seed_dados_modulos_crm(db)


def _seed_dados_modulos_crm(db: Session) -> None:
    """Dados fictícios extras para testar CRM (avaliações, propostas, financeiro…)."""
    agora = datetime.now()

    if db.scalar(select(Cliente).limit(1)) is None:
        db.add_all([
            Cliente(
                tipo="PF", nome="João Pereira", documento="123.456.789-00",
                telefone="(46) 99900-1111", email="joao@email.com",
                cidade="Pato Branco", observacoes="Cliente recorrente",
            ),
            Cliente(
                tipo="PJ", nome="Transportes Sul Ltda", documento="12.345.678/0001-90",
                telefone="(46) 3220-0000", email="compras@transul.com",
                cidade="Pato Branco",
            ),
            Cliente(
                tipo="PF", nome="Fernanda Alves", documento="987.654.321-00",
                telefone="(46) 99123-4567", email="fernanda@email.com",
                cidade="Francisco Beltrão",
            ),
            Cliente(
                tipo="PF", nome="Ricardo Motta", documento="111.222.333-44",
                telefone="(46) 98877-6655", email="ricardo.motta@email.com",
                cidade="Pato Branco", observacoes="Interessado em SUV",
            ),
        ])
        db.commit()

    clientes = {c.nome: c for c in db.scalars(select(Cliente)).all()}
    veiculos = list(db.scalars(select(VeiculoDB)).all())
    v_tcross = next((v for v in veiculos if "T-CROSS" in v.modelo), veiculos[0] if veiculos else None)
    v_gol = next((v for v in veiculos if "GOL" in v.modelo), veiculos[1] if len(veiculos) > 1 else v_tcross)
    v_jeep = next((v for v in veiculos if "COMPASS" in v.modelo), veiculos[2] if len(veiculos) > 2 else v_tcross)

    if db.scalar(select(Avaliacao).limit(1)) is None:
        db.add_all([
            Avaliacao(
                marca="CHEVROLET", modelo="ONIX LT", ano="2019", km="45000",
                combustivel="FLEX", cambio="MANUAL", cor="PRATA",
                nome="Lucas Henrique", telefone="(46) 99944-1122",
                email="lucas@email.com", status="novo",
                valor_fipe=52000, valor_sugerido=48000,
                obs_interna="Pneus bons, pequeno risco lateral.",
            ),
            Avaliacao(
                marca="TOYOTA", modelo="COROLLA XEI", ano="2018", km="78000",
                combustivel="FLEX", cambio="AUTOMÁTICO", cor="BRANCO",
                nome="Patricia Nunes", telefone="(46) 98833-2211",
                status="analise", valor_fipe=85000, valor_sugerido=79000,
                valor_pago=76000, margem=3000,
            ),
            Avaliacao(
                marca="HONDA", modelo="CIVIC EXL", ano="2017", km="92000",
                combustivel="GASOLINA", cambio="AUTOMÁTICO", cor="PRETO",
                nome="Marcos Oliveira", telefone="(46) 97722-3344",
                status="aprovado", valor_fipe=72000, valor_sugerido=68000,
            ),
        ])
        db.commit()

    if db.scalar(select(Proposta).limit(1)) is None:
        joao = clientes.get("João Pereira")
        fernanda = clientes.get("Fernanda Alves")
        db.add_all([
            Proposta(
                cliente_id=joao.id if joao else None,
                veiculo_id=v_tcross.id if v_tcross else None,
                cliente_nome="João Pereira",
                valor=v_tcross.preco * 0.97 if v_tcross else 135000,
                status="enviada",
                texto="Entrada de 30% + 48x. Veículo revisado e com garantia.",
            ),
            Proposta(
                cliente_id=fernanda.id if fernanda else None,
                veiculo_id=v_jeep.id if v_jeep else None,
                cliente_nome="Fernanda Alves",
                valor=v_jeep.preco if v_jeep else 119000,
                status="rascunho",
                texto="Proposta sujeita à aprovação de crédito.",
            ),
            Proposta(
                cliente_nome="Cliente balcão — Carlos",
                veiculo_id=v_gol.id if v_gol else None,
                valor=v_gol.preco if v_gol else 42900,
                status="aprovada",
                texto="Pagamento à vista com desconto.",
            ),
        ])
        db.commit()

    if db.scalar(select(Lancamento).limit(1)) is None:
        db.add_all([
            Lancamento(
                tipo="entrada", categoria="venda", descricao="Entrada venda T-Cross",
                valor=42000, pago=True, veiculo_id=v_tcross.id if v_tcross else None,
                vencimento=agora,
            ),
            Lancamento(
                tipo="saida", categoria="preparacao", descricao="Funilaria e polimento",
                valor=2800, pago=True, veiculo_id=v_tcross.id if v_tcross else None,
                vencimento=agora,
            ),
            Lancamento(
                tipo="saida", categoria="fixo", descricao="Aluguel loja — mês",
                valor=4500, pago=False, vencimento=agora.replace(day=10),
            ),
            Lancamento(
                tipo="entrada", categoria="comissao", descricao="Comissão vendedor",
                valor=1500, pago=False, comissao_pct=3,
                veiculo_id=v_gol.id if v_gol else None,
                vencimento=agora.replace(day=15),
            ),
            Lancamento(
                tipo="saida", categoria="marketing", descricao="Anúncios Google Ads",
                valor=1200, pago=True, vencimento=agora,
            ),
        ])
        db.commit()

    if db.scalar(select(Documento).limit(1)) is None:
        db.add_all([
            Documento(
                tipo="recibo",
                titulo="Recibo — João Pereira",
                cliente_nome="João Pereira",
                conteudo_html=(
                    "<h3>RECIBO DE SINAL</h3>"
                    "<p>Recebemos de João Pereira o valor de R$ 5.000,00 "
                    "referente a sinal de negociação do veículo T-Cross.</p>"
                ),
            ),
            Documento(
                tipo="contrato",
                titulo="Contrato — Fernanda Alves",
                cliente_nome="Fernanda Alves",
                conteudo_html=(
                    "<h3>CONTRATO DE COMPRA E VENDA</h3>"
                    "<p>Partes: Sigma Multimarcas e Fernanda Alves.</p>"
                    "<p>Veículo: Jeep Compass Longitude 2020.</p>"
                ),
            ),
        ])
        db.commit()

    if v_tcross and db.scalar(
        select(VeiculoCusto).where(VeiculoCusto.veiculo_id == v_tcross.id).limit(1)
    ) is None:
        db.add_all([
            VeiculoCusto(
                veiculo_id=v_tcross.id, descricao="Revisão mecânica", valor=890,
            ),
            VeiculoCusto(
                veiculo_id=v_tcross.id, descricao="Higienização interna", valor=350,
            ),
        ])
        db.commit()

    leads = list(db.scalars(select(Lead)).all())
    if leads and db.scalar(select(LeadAtividade).limit(1)) is None:
        lead = leads[0]
        db.add_all([
            LeadAtividade(
                lead_id=lead.id,
                texto="Lead entrou pelo Google Ads — interesse no T-Cross",
            ),
            LeadAtividade(
                lead_id=lead.id,
                texto="WhatsApp respondido, aguardando visita",
            ),
        ])
        db.commit()

    if db.scalar(select(Depoimento).limit(1)) is None:
        db.add_all([
            Depoimento(
                nome="Maria Silva",
                texto="Atendimento excelente e carro impecável. Recomendo!",
                nota=5, cidade="Pato Branco", ativo=True,
            ),
            Depoimento(
                nome="Pedro Costa",
                texto="Negociação justa e entrega rápida.",
                nota=5, cidade="Francisco Beltrão", ativo=True,
            ),
        ])
        db.commit()

    if db.scalar(select(Popup).limit(1)) is None:
        db.add(Popup(
            titulo="Financiamento facilitado",
            texto="Aproveite condições especiais neste mês. Fale conosco!",
            link="/estoque",
            ativo=False,
        ))
        db.commit()

    if db.scalar(select(Compromisso).limit(1)) is None:
        agora = datetime.now().replace(minute=0, second=0, microsecond=0)
        db.add_all([
            Compromisso(
                titulo="Test drive — T-Cross",
                tipo="test_drive",
                data_hora=agora.replace(hour=15),
                observacoes="Cliente Carlos",
            ),
            Compromisso(
                titulo="Retorno proposta Ana",
                tipo="retorno",
                data_hora=agora.replace(hour=17),
            ),
        ])
        db.commit()


def _migrar_colunas() -> None:
    novas = {
        "nome_sistema": "VARCHAR(120) DEFAULT 'Gestão Veículos'",
        "razao_social": "VARCHAR(200) DEFAULT ''",
        "cnpj": "VARCHAR(20) DEFAULT ''",
        "slogan": "VARCHAR(80) DEFAULT ''",
        "estado": "VARCHAR(2) DEFAULT ''",
        "bairro": "VARCHAR(80) DEFAULT ''",
        "cep": "VARCHAR(12) DEFAULT ''",
        "facebook": "VARCHAR(200) DEFAULT ''",
        "instagram": "VARCHAR(200) DEFAULT ''",
        "dominio": "VARCHAR(200) DEFAULT ''",
        "seo_titulo": "VARCHAR(160) DEFAULT ''",
        "seo_descricao": "VARCHAR(300) DEFAULT ''",
        "nome_ia": "VARCHAR(120) DEFAULT 'Assistente Virtual'",
        "ia_ativa": "BOOLEAN DEFAULT 0",
        "tenant_slug": "VARCHAR(80) DEFAULT ''",
        "logo_url": "VARCHAR(500) DEFAULT ''",
        "favicon_url": "VARCHAR(500) DEFAULT ''",
        "cor_secundaria": "VARCHAR(7) DEFAULT '#1f2937'",
        "tema": "VARCHAR(40) DEFAULT 'padrao'",
        "idioma": "VARCHAR(10) DEFAULT 'pt-BR'",
        "fuso_horario": "VARCHAR(60) DEFAULT 'America/Sao_Paulo'",
        "plano": "VARCHAR(60) DEFAULT ''",
    }
    insp = sa_inspect(engine)
    if "config_loja" not in insp.get_table_names():
        return
    existentes = {c["name"] for c in insp.get_columns("config_loja")}
    with engine.begin() as conn:
        for coluna, tipo in novas.items():
            if coluna not in existentes:
                conn.execute(text(f"ALTER TABLE config_loja ADD COLUMN {coluna} {tipo}"))
        if "nome_sistema" not in existentes:
            conn.execute(text(
                "UPDATE config_loja SET nome_sistema = 'Gestão Veículos' "
                "WHERE nome_sistema IS NULL OR nome_sistema = ''"
            ))

    _migrar_usuarios(insp)
    _migrar_veiculos(insp)
    _migrar_leads(insp)
    _migrar_avaliacoes(insp)
    _migrar_depoimentos(insp)


def _migrar_usuarios(insp) -> None:
    if "usuarios" not in insp.get_table_names():
        return
    novas = {
        "senha_temporaria": "BOOLEAN DEFAULT 0",
        "precisa_trocar_senha": "BOOLEAN DEFAULT 0",
        "ultimo_acesso": "DATETIME",
        "criado_em": "DATETIME",
    }
    existentes = {c["name"] for c in insp.get_columns("usuarios")}
    with engine.begin() as conn:
        for coluna, tipo in novas.items():
            if coluna not in existentes:
                conn.execute(text(f"ALTER TABLE usuarios ADD COLUMN {coluna} {tipo}"))


def _migrar_veiculos(insp) -> None:
    if "veiculos" not in insp.get_table_names():
        return
    novas = {
        "cor": "VARCHAR(30) DEFAULT 'BRANCO'",
        "tipo": "VARCHAR(40) DEFAULT 'AUTOMÓVEL'",
        "badge": "VARCHAR(40) DEFAULT 'PRONTA ENTREGA'",
        "info_extra": "VARCHAR(200) DEFAULT ''",
        "placa": "VARCHAR(12) DEFAULT ''",
        "chassi": "VARCHAR(30) DEFAULT ''",
        "renavam": "VARCHAR(20) DEFAULT ''",
        "fipe": "FLOAT DEFAULT 0",
        "videos_url": "VARCHAR(500) DEFAULT ''",
        "opcionais": "TEXT DEFAULT ''",
        "etiquetas": "VARCHAR(200) DEFAULT ''",
        "publicado": "BOOLEAN DEFAULT 1",
        "historico_texto": "TEXT DEFAULT ''",
        "visualizacoes": "INTEGER DEFAULT 0",
        "imagem_destaque": "VARCHAR(500) DEFAULT ''",
    }
    existentes = {c["name"] for c in insp.get_columns("veiculos")}
    with engine.begin() as conn:
        for coluna, tipo in novas.items():
            if coluna not in existentes:
                conn.execute(text(f"ALTER TABLE veiculos ADD COLUMN {coluna} {tipo}"))
        if "info_extra" not in existentes:
            conn.execute(text(
                "UPDATE veiculos SET info_extra = "
                "'Acompanha manual e chave reserva' WHERE info_extra = '' OR info_extra IS NULL"
            ))


def _migrar_leads(insp) -> None:
    if "leads" not in insp.get_table_names():
        return
    novas = {
        "vendedor": "VARCHAR(80) DEFAULT ''",
        "cliente_id": "INTEGER",
    }
    existentes = {c["name"] for c in insp.get_columns("leads")}
    with engine.begin() as conn:
        for coluna, tipo in novas.items():
            if coluna not in existentes:
                conn.execute(text(f"ALTER TABLE leads ADD COLUMN {coluna} {tipo}"))


def _migrar_avaliacoes(insp) -> None:
    if "avaliacoes" not in insp.get_table_names():
        return
    novas = {
        "fotos_url": "TEXT DEFAULT ''",
        "valor_fipe": "FLOAT DEFAULT 0",
        "valor_sugerido": "FLOAT DEFAULT 0",
        "valor_pago": "FLOAT DEFAULT 0",
        "margem": "FLOAT DEFAULT 0",
        "obs_interna": "TEXT DEFAULT ''",
    }
    existentes = {c["name"] for c in insp.get_columns("avaliacoes")}
    with engine.begin() as conn:
        for coluna, tipo in novas.items():
            if coluna not in existentes:
                conn.execute(text(f"ALTER TABLE avaliacoes ADD COLUMN {coluna} {tipo}"))


def _migrar_depoimentos(insp) -> None:
    if "depoimentos" not in insp.get_table_names():
        return
    novas = {
        "cidade": "VARCHAR(80) DEFAULT ''",
    }
    existentes = {c["name"] for c in insp.get_columns("depoimentos")}
    with engine.begin() as conn:
        for coluna, tipo in novas.items():
            if coluna not in existentes:
                conn.execute(text(f"ALTER TABLE depoimentos ADD COLUMN {coluna} {tipo}"))


def _seed_veiculos(db: Session) -> None:
    estoque = [
        ("VOLKSWAGEN", "T-CROSS HL TSI", 2020, 70220, "FLEX", "AUTOMÁTICO",
         139_900, "https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?w=800&q=80", True),
        ("PEUGEOT", "208 ACTIVE MT", 2020, 45800, "FLEX", "MANUAL", 49_900,
         "https://images.unsplash.com/photo-1609521263040-f5eee461b67e?w=600&q=80", False),
        ("FIAT", "ARGO DRIVE 1.0", 2021, 32100, "FLEX", "MANUAL", 54_900,
         "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=600&q=80", False),
        ("HYUNDAI", "HB20 SENSE 1.0", 2019, 61200, "FLEX", "MANUAL", 47_500,
         "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=600&q=80", False),
        ("FORD", "KA SE 1.0", 2018, 78400, "FLEX", "MANUAL", 38_900,
         "https://images.unsplash.com/photo-1494976388531-d1058494cdd8?w=600&q=80", False),
        ("RENAULT", "SANDERO ZEN 1.0", 2020, 52300, "FLEX", "MANUAL", 44_900,
         "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=600&q=80", False),
        ("JEEP", "RENEGADE SPORT", 2019, 89100, "FLEX", "AUTOMÁTICO", 89_900,
         "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=600&q=80", False),
        ("CITROEN", "C3 FEEL 1.0", 2021, 28900, "FLEX", "MANUAL", 62_900,
         "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=600&q=80", False),
        ("BMW", "320i GP", 2018, 65400, "GASOLINA", "AUTOMÁTICO", 159_900,
         "https://images.unsplash.com/photo-1555215695-3004980ad54e?w=600&q=80", False),
        ("VOLKSWAGEN", "GOL 1.0 MPI", 2017, 95600, "FLEX", "MANUAL", 42_900,
         "https://images.unsplash.com/photo-1542362567-b07e54358753?w=600&q=80", False),
        ("PEUGEOT", "2008 GRIFFE", 2021, 41200, "FLEX", "AUTOMÁTICO", 98_900,
         "https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=600&q=80", False),
        ("FIAT", "TORO ENDURANCE", 2020, 73500, "DIESEL", "AUTOMÁTICO", 112_900,
         "https://images.unsplash.com/photo-1533473357621-052a1c8f016b?w=600&q=80", False),
        ("HYUNDAI", "CRETA ATTITUDE", 2019, 58800, "FLEX", "AUTOMÁTICO", 79_900,
         "https://images.unsplash.com/photo-1617531653332-bd46c24f2068?w=600&q=80", False),
        ("FORD", "RANGER XLS", 2018, 112000, "DIESEL", "MANUAL", 124_900,
         "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&q=80", False),
        ("RENAULT", "KWID ZEN 1.0", 2022, 18400, "FLEX", "MANUAL", 52_900,
         "https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=600&q=80", False),
        ("JEEP", "COMPASS LONGITUDE", 2020, 62100, "FLEX", "AUTOMÁTICO", 119_900,
         "https://images.unsplash.com/photo-1609521263040-f5eee461b67e?w=600&q=80", False),
    ]
    for marca, modelo, ano, km, comb, camb, preco, img, dest in estoque:
        db.add(VeiculoDB(
            marca=marca, modelo=modelo, ano=ano, km=km,
            combustivel=comb, cambio=camb, preco=preco,
            imagem=img, destaque=dest, status="disponivel",
        ))
    db.commit()


def _seed_leads(db: Session) -> None:
    v1 = db.scalar(select(VeiculoDB).where(VeiculoDB.modelo.like("%T-CROSS%")))
    camp = db.scalar(select(Campanha).where(Campanha.origem == "google"))
    db.add_all([
        Lead(
            nome="Carlos Mendes", telefone="(46) 99911-2233",
            origem="google", utm_source="google", utm_campaign="estoque-marco",
            status="contatado", veiculo_id=v1.id if v1 else None,
            campanha_id=camp.id if camp else None,
        ),
        Lead(
            nome="Ana Souza", telefone="(46) 98822-3344",
            origem="instagram", status="novo",
        ),
        Lead(
            nome="Roberto Lima", telefone="(46) 97733-4455",
            origem="site", status="visita",
        ),
    ])
    db.commit()
