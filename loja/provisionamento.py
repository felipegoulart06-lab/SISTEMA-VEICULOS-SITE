"""Provisionamento automático de uma empresa (tenant) White Label.

Ao criar uma empresa no Painel Master, este módulo executa todas as etapas
necessárias para entregar um ERP e um Site prontos, isolados e vazios.

Regras da arquitetura:
- Cada empresa possui banco de dados próprio (isolamento físico por tenant).
- Cada empresa possui um único usuário administrador.
- Nenhum dado é compartilhado entre empresas.
"""

from __future__ import annotations

import json
import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from passlib.hash import pbkdf2_sha256
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from loja.models import (
    Base,
    CategoriaTenant,
    ConectorIntegracao,
    ConfigLoja,
    ConfiguracaoTenant,
    LogTenant,
    PaginaSite,
    Usuario,
)

from loja.paths import dir_storage

STORAGE_DIR = dir_storage()
PASTAS_STORAGE = (
    "veiculos", "documentos", "logos", "uploads", "backups", "temp",
)

# ------------------------------------------------------------------ páginas

PAGINAS_PADRAO = [
    {
        "slug": "inicial", "titulo": "Página Inicial", "rota": "/",
        "no_menu": True, "ordem": 1,
        "conteudo_html": "",
        "seo_descricao": "Confira nosso estoque de veículos.",
    },
    {
        "slug": "estoque", "titulo": "Estoque", "rota": "/estoque",
        "no_menu": True, "ordem": 2,
        "conteudo_html": "",
        "seo_descricao": "Veículos disponíveis para venda.",
    },
    {
        "slug": "veiculo", "titulo": "Detalhes do Veículo",
        "rota": "/veiculo/{id}", "no_menu": False, "ordem": 3,
        "conteudo_html": "",
        "seo_descricao": "Informações completas do veículo.",
    },
    {
        "slug": "sobre", "titulo": "Sobre", "rota": "/empresa",
        "no_menu": True, "ordem": 4,
        "conteudo_html": (
            "<h2>Sobre a empresa</h2>"
            "<p>Descreva aqui a história da sua empresa, o tempo de mercado "
            "e o que diferencia o seu atendimento.</p>"
        ),
        "seo_descricao": "Conheça nossa empresa.",
    },
    {
        "slug": "contato", "titulo": "Contato", "rota": "/contato",
        "no_menu": True, "ordem": 5,
        "conteudo_html": (
            "<h2>Fale conosco</h2>"
            "<p>Preencha o formulário ou utilize os canais de atendimento.</p>"
        ),
        "seo_descricao": "Entre em contato conosco.",
    },
    {
        "slug": "privacidade", "titulo": "Política de Privacidade",
        "rota": "/privacidade", "no_menu": True, "ordem": 6,
        "conteudo_html": (
            "<h2>Política de Privacidade</h2>"
            "<p>Esta política descreve como coletamos, utilizamos e "
            "armazenamos as informações fornecidas pelos visitantes deste "
            "site.</p>"
            "<h3>Dados coletados</h3>"
            "<p>Coletamos apenas os dados informados voluntariamente nos "
            "formulários de contato, proposta, avaliação e financiamento.</p>"
            "<h3>Uso das informações</h3>"
            "<p>As informações são utilizadas exclusivamente para atendimento "
            "comercial e não são vendidas a terceiros.</p>"
            "<h3>Cookies</h3>"
            "<p>Utilizamos cookies para melhorar a navegação e medir o "
            "desempenho das páginas.</p>"
            "<p><em>Revise este texto com seu jurídico antes de publicar.</em></p>"
        ),
        "seo_descricao": "Política de privacidade do site.",
    },
    {
        "slug": "lgpd", "titulo": "LGPD", "rota": "/lgpd",
        "no_menu": True, "ordem": 7,
        "conteudo_html": (
            "<h2>LGPD — Lei Geral de Proteção de Dados</h2>"
            "<p>Tratamos os dados pessoais de acordo com a Lei nº 13.709/2018.</p>"
            "<h3>Seus direitos</h3>"
            "<ul>"
            "<li>Confirmar a existência de tratamento dos seus dados</li>"
            "<li>Acessar, corrigir e atualizar seus dados</li>"
            "<li>Solicitar a exclusão dos dados</li>"
            "<li>Revogar o consentimento a qualquer momento</li>"
            "</ul>"
            "<h3>Encarregado de dados</h3>"
            "<p>Informe aqui o e-mail do responsável pelo tratamento de dados.</p>"
            "<p><em>Revise este texto com seu jurídico antes de publicar.</em></p>"
        ),
        "seo_descricao": "Informações sobre a LGPD.",
    },
]

# --------------------------------------------------------------- categorias

CATEGORIAS_PADRAO = {
    "veiculo_tipo": [
        "Automóvel", "SUV", "Picape", "Utilitário", "Caminhão", "Moto",
    ],
    "financeiro_entrada": [
        "Venda de veículo", "Serviços", "Comissão", "Outras receitas",
    ],
    "financeiro_saida": [
        "Compra de veículo", "Preparação", "Marketing", "Despesas fixas",
        "Impostos", "Outras despesas",
    ],
    "documento": ["Recibo", "Contrato", "Procuração", "Termo de entrega"],
    "lead_origem": [
        "Site", "WhatsApp", "Telefone", "Indicação", "Marketplace", "Balcão",
    ],
}

# ------------------------------------------------------------ configurações


def _configuracoes_padrao(nome: str, email: str, cor: str, tema: str,
                          idioma: str, fuso: str, plano: str) -> list[dict]:
    return [
        {
            "grupo": "tema", "chave": "tema.aparencia",
            "descricao": "Cores e aparência do site",
            "valor": {
                "tema": tema or "padrao",
                "cor_primaria": cor,
                "cor_secundaria": "#1f2937",
                "fonte": "Inter",
                "modo": "claro",
                "botoes_arredondados": True,
            },
        },
        {
            "grupo": "seo", "chave": "seo.geral",
            "descricao": "Otimização para buscadores",
            "valor": {
                "titulo": nome,
                "descricao": f"{nome} — veículos seminovos selecionados.",
                "palavras_chave": "",
                "google_analytics": "",
                "google_tag_manager": "",
                "facebook_pixel": "",
                "indexar": True,
                "sitemap": True,
            },
        },
        {
            "grupo": "crm", "chave": "crm.geral",
            "descricao": "Funil e regras de atendimento",
            "valor": {
                "etapas": ["novo", "contato", "negociacao", "fechado", "perdido"],
                "prazo_primeiro_contato_min": 15,
                "notificar_novo_lead": True,
                "distribuicao": "unica",
            },
        },
        {
            "grupo": "financeiro", "chave": "financeiro.geral",
            "descricao": "Regras financeiras da empresa",
            "valor": {
                "moeda": "BRL",
                "regime": "simples",
                "dia_fechamento": 30,
                "comissao_padrao_pct": 0,
                "alerta_vencimento_dias": 3,
            },
        },
        {
            "grupo": "site", "chave": "site.geral",
            "descricao": "Comportamento do site público",
            "valor": {
                "publicado": True,
                "mostrar_precos": True,
                "mostrar_estoque_esgotado": False,
                "veiculos_por_pagina": 12,
                "chat_ativo": False,
                "banner_principal": "",
            },
        },
        {
            "grupo": "erp", "chave": "erp.geral",
            "descricao": "Preferências do ERP",
            "valor": {
                "idioma": idioma,
                "fuso_horario": fuso,
                "formato_data": "DD/MM/AAAA",
                "itens_por_pagina": 20,
                "exigir_placa": False,
            },
        },
        {
            "grupo": "email", "chave": "email.smtp",
            "descricao": "Envio de e-mails da empresa",
            "valor": {
                "ativo": False,
                "host": "",
                "porta": 587,
                "usuario": "",
                "senha": "",
                "remetente": email,
                "tls": True,
            },
        },
        {
            "grupo": "notificacoes", "chave": "notificacoes.geral",
            "descricao": "Alertas do sistema",
            "valor": {
                "novo_lead": True,
                "nova_proposta": True,
                "novo_financiamento": True,
                "vencimento_financeiro": True,
                "resumo_diario": False,
                "canal": "sistema",
            },
        },
        {
            "grupo": "whatsapp", "chave": "whatsapp.conexao",
            "descricao": "Conexão do WhatsApp",
            "valor": {
                "conectado": False,
                "status": "desconectado",
                "numero": "",
                "mensagem_padrao": "Olá! Tenho interesse em um veículo.",
                "provedor": "",
            },
        },
        {
            "grupo": "marketplaces", "chave": "marketplaces.geral",
            "descricao": "Publicação em portais",
            "valor": {
                "publicar_automatico": False,
                "conectados": [],
                "status": "desconectado",
            },
        },
        {
            "grupo": "whitelabel", "chave": "whitelabel.identidade",
            "descricao": "Identidade da marca",
            "valor": {
                "nome": nome,
                "logo": "",
                "favicon": "",
                "cor_primaria": cor,
                "tema": tema or "padrao",
                "idioma": idioma,
                "fuso_horario": fuso,
                "plano": plano,
            },
        },
        {
            "grupo": "storage", "chave": "storage.geral",
            "descricao": "Armazenamento exclusivo da empresa",
            "valor": {"tipo": "local", "pasta": "", "limite_gb": 0},
        },
    ]


# ------------------------------------------------------------------ relatório


@dataclass
class Etapa:
    ordem: int
    titulo: str
    ok: bool = True
    detalhe: str = ""


@dataclass
class ResultadoProvisionamento:
    slug: str
    email: str
    senha_temporaria: str
    storage: str
    etapas: list[Etapa] = field(default_factory=list)

    @property
    def sucesso(self) -> bool:
        return all(e.ok for e in self.etapas)

    def registrar(self, ordem: int, titulo: str, detalhe: str = "") -> None:
        self.etapas.append(Etapa(ordem, titulo, True, detalhe))


def gerar_senha_temporaria(tamanho: int = 10) -> str:
    alfabeto = string.ascii_letters + string.digits
    corpo = "".join(secrets.choice(alfabeto) for _ in range(tamanho))
    return f"{corpo[:5]}-{corpo[5:]}"


def gerar_token_longo(tamanho: int = 25) -> str:
    """Token alfanumérico (ex.: 25 dígitos/letras) para senha temporária."""
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


def pasta_storage(slug: str) -> Path:
    return STORAGE_DIR / slug


def criar_storage(slug: str) -> Path:
    base = pasta_storage(slug)
    for sub in PASTAS_STORAGE:
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def remover_storage(slug: str) -> None:
    import shutil

    base = pasta_storage(slug)
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)


# --------------------------------------------------------------- etapas base


def _criar_configuracao_loja(db: Session, dados: dict) -> None:
    db.add(ConfigLoja(
        nome_sistema="Gestão Veículos",
        nome=dados["nome"],
        logo_texto=(dados["nome"].split()[0][:20] if dados["nome"] else "Loja"),
        email=dados["email"],
        cor_primaria=dados["cor"],
        cor_secundaria="#1f2937",
        tema=dados["tema"],
        idioma=dados["idioma"],
        fuso_horario=dados["fuso"],
        tenant_slug=dados["slug"],
        logo_url=dados["logo"],
        favicon_url=dados["favicon"],
        plano=dados["plano"],
        seo_titulo=dados["nome"],
        seo_descricao=f"{dados['nome']} — veículos seminovos selecionados.",
        sobre="", cidade="", estado="", telefone="", whatsapp="",
        endereco="", horario="", banner_url="",
    ))


def _criar_admin(db: Session, email: str, senha: str, nome: str) -> None:
    db.add(Usuario(
        email=email.lower(),
        senha_hash=pbkdf2_sha256.hash(senha),
        nome=nome or "Administrador",
        ativo=True,
        senha_temporaria=True,
        precisa_trocar_senha=True,
    ))


def _criar_configuracoes(db: Session, dados: dict) -> int:
    itens = _configuracoes_padrao(
        dados["nome"], dados["email"], dados["cor"], dados["tema"],
        dados["idioma"], dados["fuso"], dados["plano"],
    )
    for item in itens:
        if item["chave"] == "storage.geral":
            item["valor"]["pasta"] = str(pasta_storage(dados["slug"]))
        db.add(ConfiguracaoTenant(
            grupo=item["grupo"],
            chave=item["chave"],
            descricao=item["descricao"],
            valor_json=json.dumps(item["valor"], ensure_ascii=False),
        ))
    return len(itens)


def _criar_categorias(db: Session) -> int:
    total = 0
    for grupo, nomes in CATEGORIAS_PADRAO.items():
        for ordem, nome in enumerate(nomes, start=1):
            db.add(CategoriaTenant(
                grupo=grupo,
                nome=nome,
                slug=nome.lower().replace(" ", "-"),
                ordem=ordem,
            ))
            total += 1
    return total


def _criar_paginas(db: Session, nome_empresa: str) -> int:
    for pagina in PAGINAS_PADRAO:
        db.add(PaginaSite(
            slug=pagina["slug"],
            titulo=pagina["titulo"],
            rota=pagina["rota"],
            conteudo_html=pagina["conteudo_html"],
            seo_titulo=f"{pagina['titulo']} — {nome_empresa}",
            seo_descricao=pagina["seo_descricao"],
            no_menu=pagina["no_menu"],
            ordem=pagina["ordem"],
            sistema=True,
            publicada=True,
        ))
    return len(PAGINAS_PADRAO)


def _criar_marketplaces(db: Session) -> int:
    from loja.integracoes import CATALOGO_CONECTORES

    for item in CATALOGO_CONECTORES:
        db.add(ConectorIntegracao(
            codigo=item["codigo"],
            nome=item["nome"],
            categoria=item.get("categoria", "marketplace"),
            descricao=item.get("descricao", ""),
            disponivel=item.get("disponivel", True),
            ordem=item.get("ordem", 0),
            ativo=False,
            status_msg="Desconectado",
        ))
    return len(CATALOGO_CONECTORES)


def _registrar_logs_iniciais(db: Session, nome: str) -> None:
    db.add_all([
        LogTenant(
            tipo="sistema", mensagem=f"Empresa {nome} provisionada.",
        ),
        LogTenant(
            tipo="sistema", mensagem="ERP criado vazio.",
        ),
        LogTenant(
            tipo="sistema", mensagem="Site criado vazio com páginas padrão.",
        ),
    ])


# ------------------------------------------------------------------ execução


def provisionar_empresa(
    slug: str,
    nome: str,
    email: str,
    senha_temporaria: str | None = None,
    cor: str = "#c0392b",
    tema: str = "padrao",
    idioma: str = "pt-BR",
    fuso: str = "America/Sao_Paulo",
    logo: str = "",
    favicon: str = "",
    plano: str = "",
) -> ResultadoProvisionamento:
    """Cria banco isolado, ERP vazio, site vazio e o administrador único."""
    from loja.db_config import schema_tenant, usando_postgres
    from loja.plataforma import (
        caminho_db_conta,
        get_tenant_sessionmaker,
        liberar_engine,
        engine_tenant,
        plataforma_engine,
    )
    from sqlalchemy import text

    senha = senha_temporaria or gerar_senha_temporaria()
    dados = {
        "slug": slug, "nome": nome, "email": email.lower(), "cor": cor,
        "tema": tema or "padrao", "idioma": idioma, "fuso": fuso,
        "logo": logo, "favicon": favicon, "plano": plano,
    }
    resultado = ResultadoProvisionamento(
        slug=slug, email=dados["email"], senha_temporaria=senha, storage="",
    )

    # 1. Banco/schema exclusivo do tenant
    liberar_engine(slug)
    if usando_postgres():
        schema = schema_tenant(slug)
        with plataforma_engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            conn.execute(text(f'GRANT ALL ON SCHEMA "{schema}" TO CURRENT_USER'))
    else:
        caminho = caminho_db_conta(slug)
        if caminho.exists():
            caminho.unlink()
    engine = engine_tenant(slug)
    resultado.registrar(1, "Empresa (tenant) criada", slug)

    # 2. Estrutura completa de tabelas
    Base.metadata.create_all(bind=engine)
    total_tabelas = len(Base.metadata.sorted_tables)
    resultado.registrar(
        2, "Tabelas da empresa criadas", f"{total_tabelas} tabelas",
    )

    SessionLocal = get_tenant_sessionmaker(slug)
    with SessionLocal() as db:
        _criar_configuracao_loja(db, dados)
        resultado.registrar(3, "Configurações da empresa criadas")

        _criar_admin(db, dados["email"], senha, "Administrador")
        resultado.registrar(4, "Usuário administrador criado", dados["email"])
        resultado.registrar(
            5, "Senha temporária gerada", "troca obrigatória no 1º acesso",
        )

        total_cfg = _criar_configuracoes(db, dados)
        resultado.registrar(
            6, "Configurações de tema, SEO, CRM, financeiro, site e ERP",
            f"{total_cfg} grupos",
        )

        total_cat = _criar_categorias(db)
        resultado.registrar(7, "Categorias padrão criadas", f"{total_cat} itens")

        total_pag = _criar_paginas(db, nome)
        resultado.registrar(8, "Páginas do site criadas", f"{total_pag} páginas")

        total_mkt = _criar_marketplaces(db)
        resultado.registrar(
            9, "Marketplaces criados desconectados", f"{total_mkt} portais",
        )
        resultado.registrar(10, "WhatsApp criado desconectado")
        resultado.registrar(11, "E-mail e notificações configurados")

        _registrar_logs_iniciais(db, nome)
        resultado.registrar(12, "Logs exclusivos da empresa criados")

        db.commit()

    # 13. Storage exclusivo
    base_storage = criar_storage(slug)
    resultado.storage = str(base_storage)
    resultado.registrar(13, "Storage exclusivo criado", str(base_storage))

    # 14. Verificação: ERP e site precisam nascer vazios
    vazio_ok, detalhe = verificar_ambiente_vazio(slug)
    resultado.etapas.append(
        Etapa(14, "ERP e Site verificados vazios", vazio_ok, detalhe)
    )

    return resultado


COLUNAS_NOVAS_TENANT = {
    "usuarios": {
        "senha_temporaria": "BOOLEAN DEFAULT 0",
        "precisa_trocar_senha": "BOOLEAN DEFAULT 0",
        "ultimo_acesso": "DATETIME",
        "criado_em": "DATETIME",
    },
    "config_loja": {
        "tenant_slug": "VARCHAR(80) DEFAULT ''",
        "logo_url": "VARCHAR(500) DEFAULT ''",
        "favicon_url": "VARCHAR(500) DEFAULT ''",
        "cor_secundaria": "VARCHAR(7) DEFAULT '#1f2937'",
        "tema": "VARCHAR(40) DEFAULT 'padrao'",
        "idioma": "VARCHAR(10) DEFAULT 'pt-BR'",
        "fuso_horario": "VARCHAR(60) DEFAULT 'America/Sao_Paulo'",
        "plano": "VARCHAR(60) DEFAULT ''",
    },
    "veiculos": {
        "imagem_destaque": "VARCHAR(500) DEFAULT ''",
    },
    "depoimentos": {
        "cidade": "VARCHAR(80) DEFAULT ''",
    },
}


def migrar_tenant(slug: str, nome: str, email: str) -> None:
    """Leva um tenant antigo para a estrutura atual, sem perder dados."""
    from sqlalchemy import text
    from sqlalchemy import inspect as sa_inspect

    from loja.db_config import schema_tenant, usando_postgres
    from loja.plataforma import engine_tenant, get_tenant_sessionmaker

    engine = engine_tenant(slug)
    Base.metadata.create_all(bind=engine)

    schema = schema_tenant(slug) if usando_postgres() else None
    insp = sa_inspect(engine)
    if usando_postgres():
        tabelas = set(insp.get_table_names(schema=schema))
    else:
        tabelas = set(insp.get_table_names())
    with engine.begin() as conn:
        for tabela, colunas in COLUNAS_NOVAS_TENANT.items():
            if tabela not in tabelas:
                continue
            existentes = {
                c["name"]
                for c in (
                    insp.get_columns(tabela, schema=schema)
                    if schema
                    else insp.get_columns(tabela)
                )
            }
            for coluna, tipo in colunas.items():
                if coluna not in existentes:
                    alvo = f'"{schema}"."{tabela}"' if schema else tabela
                    tipo_sql = tipo.replace("DATETIME", "TIMESTAMP") if schema else tipo
                    conn.execute(
                        text(f"ALTER TABLE {alvo} ADD COLUMN {coluna} {tipo_sql}")
                    )

    SessionLocal = get_tenant_sessionmaker(slug)
    with SessionLocal() as db:
        cfg = db.scalar(select(ConfigLoja).limit(1))
        if cfg is None:
            cfg = ConfigLoja(
                nome_sistema="Gestão Veículos",
                nome=nome or "Minha Loja",
                email=email or "",
                logo_texto=(nome or "LOJA")[:20].upper(),
                tenant_slug=slug,
                cor_primaria="#c0392b",
            )
            db.add(cfg)
            db.flush()
        elif not cfg.tenant_slug:
            cfg.tenant_slug = slug

        if db.scalar(select(PaginaSite).limit(1)) is None:
            _criar_paginas(db, nome)

        if db.scalar(select(CategoriaTenant).limit(1)) is None:
            _criar_categorias(db)

        if db.scalar(select(ConfiguracaoTenant).limit(1)) is None:
            _criar_configuracoes(db, {
                "slug": slug, "nome": nome, "email": email,
                "cor": cfg.cor_primaria if cfg else "#c0392b",
                "tema": "padrao", "idioma": "pt-BR",
                "fuso": "America/Sao_Paulo", "plano": "",
            })

        if db.scalar(select(ConectorIntegracao).limit(1)) is None:
            _criar_marketplaces(db)

        db.commit()


TABELAS_QUE_NASCEM_VAZIAS = [
    ("veiculos", "Estoque"),
    ("clientes", "Clientes"),
    ("leads", "Leads"),
    ("lancamentos", "Financeiro"),
    ("propostas", "Propostas"),
    ("avaliacoes", "Avaliações"),
    ("financiamentos", "Financiamentos"),
    ("compromissos", "Agenda"),
    ("documentos", "Documentos"),
    ("campanhas", "Marketing"),
    ("depoimentos", "Depoimentos"),
    ("popups", "Popups"),
    ("veiculo_custos", "Custos de veículo"),
    ("lead_atividades", "Atividades de lead"),
    ("lead_tarefas", "Tarefas de lead"),
    ("sync_integracao", "Fila de integrações"),
]


def verificar_ambiente_vazio(slug: str) -> tuple[bool, str]:
    """Confirma que nenhum módulo nasceu com dado herdado."""
    from sqlalchemy import text

    from loja.db_config import schema_tenant, usando_postgres
    from loja.plataforma import engine_tenant, get_tenant_sessionmaker
    from loja.models import Usuario

    schema = schema_tenant(slug) if usando_postgres() else None

    def _count(conn, tabela: str) -> int:
        if schema:
            sql = text(f'SELECT COUNT(*) FROM "{schema}"."{tabela}"')
        else:
            sql = text(f"SELECT COUNT(*) FROM {tabela}")
        try:
            return conn.execute(sql).scalar() or 0
        except Exception:
            return 0

    sujos: list[str] = []
    engine = engine_tenant(slug)
    with engine.connect() as conn:
        for tabela, rotulo in TABELAS_QUE_NASCEM_VAZIAS:
            total = _count(conn, tabela)
            if total:
                sujos.append(f"{rotulo} ({total})")

    SessionLocal = get_tenant_sessionmaker(slug)
    with SessionLocal() as db:
        usuarios = db.scalar(
            select(func.count()).select_from(Usuario)
        ) or 0
    if usuarios != 1:
        sujos.append(f"Usuários ({usuarios})")
    if sujos:
        return False, "Com dados: " + ", ".join(sujos)
    return True, f"{len(TABELAS_QUE_NASCEM_VAZIAS)} módulos vazios · 1 administrador"


# ------------------------------------------------------- acesso às configs


def ler_config(chave: str, padrao: dict | None = None) -> dict:
    """Lê uma configuração do tenant ativo."""
    from loja.database import get_session

    with get_session() as db:
        item = db.scalar(
            select(ConfiguracaoTenant).where(ConfiguracaoTenant.chave == chave)
        )
        if item is None:
            return dict(padrao or {})
        try:
            return json.loads(item.valor_json)
        except json.JSONDecodeError:
            return dict(padrao or {})


def salvar_config(chave: str, valor: dict, grupo: str = "geral") -> None:
    """Grava uma configuração do tenant ativo."""
    from loja.database import get_session

    with get_session() as db:
        item = db.scalar(
            select(ConfiguracaoTenant).where(ConfiguracaoTenant.chave == chave)
        )
        if item is None:
            item = ConfiguracaoTenant(grupo=grupo, chave=chave)
            db.add(item)
        item.valor_json = json.dumps(valor, ensure_ascii=False)
        item.atualizado_em = datetime.now()
        db.commit()


def registrar_log_tenant(
    mensagem: str, tipo: str = "sistema", nivel: str = "info",
) -> None:
    """Log isolado da empresa ativa."""
    from loja.database import get_session

    try:
        with get_session() as db:
            db.add(LogTenant(tipo=tipo, nivel=nivel, mensagem=mensagem[:500]))
            db.commit()
    except Exception:
        pass
