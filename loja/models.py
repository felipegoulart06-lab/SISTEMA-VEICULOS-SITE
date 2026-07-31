from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    """Administrador único da empresa. Não há múltiplos usuários por tenant."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(200))
    nome: Mapped[str] = mapped_column(String(100), default="Administrador")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    senha_temporaria: Mapped[bool] = mapped_column(Boolean, default=False)
    precisa_trocar_senha: Mapped[bool] = mapped_column(Boolean, default=False)
    ultimo_acesso: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True,
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ConfigLoja(Base):
    __tablename__ = "config_loja"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    nome_sistema: Mapped[str] = mapped_column(String(120), default="Gestão Veículos")
    nome: Mapped[str] = mapped_column(String(120), default="Minha Loja")
    razao_social: Mapped[str] = mapped_column(String(200), default="")
    cnpj: Mapped[str] = mapped_column(String(20), default="")
    slogan: Mapped[str] = mapped_column(String(80), default="")
    logo_texto: Mapped[str] = mapped_column(String(60), default="")
    cidade: Mapped[str] = mapped_column(String(80), default="")
    estado: Mapped[str] = mapped_column(String(2), default="")
    bairro: Mapped[str] = mapped_column(String(80), default="")
    cep: Mapped[str] = mapped_column(String(12), default="")
    endereco: Mapped[str] = mapped_column(String(200), default="")
    telefone: Mapped[str] = mapped_column(String(30), default="")
    whatsapp: Mapped[str] = mapped_column(String(30), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    horario: Mapped[str] = mapped_column(String(120), default="")
    facebook: Mapped[str] = mapped_column(String(200), default="")
    instagram: Mapped[str] = mapped_column(String(200), default="")
    sobre: Mapped[str] = mapped_column(Text, default="")
    banner_url: Mapped[str] = mapped_column(String(500), default="")
    cor_primaria: Mapped[str] = mapped_column(String(7), default="#c0392b")
    dominio: Mapped[str] = mapped_column(String(200), default="")
    seo_titulo: Mapped[str] = mapped_column(String(160), default="")
    seo_descricao: Mapped[str] = mapped_column(String(300), default="")
    nome_ia: Mapped[str] = mapped_column(String(120), default="Assistente Virtual")
    ia_ativa: Mapped[bool] = mapped_column(Boolean, default=False)
    # White label — espelha a conta da plataforma
    tenant_slug: Mapped[str] = mapped_column(String(80), default="")
    logo_url: Mapped[str] = mapped_column(String(500), default="")
    favicon_url: Mapped[str] = mapped_column(String(500), default="")
    cor_secundaria: Mapped[str] = mapped_column(String(7), default="#1f2937")
    tema: Mapped[str] = mapped_column(String(40), default="padrao")
    idioma: Mapped[str] = mapped_column(String(10), default="pt-BR")
    fuso_horario: Mapped[str] = mapped_column(
        String(60), default="America/Sao_Paulo",
    )
    plano: Mapped[str] = mapped_column(String(60), default="")


class ConfiguracaoTenant(Base):
    """Configurações por módulo (tema, seo, crm, financeiro, site, erp...).

    Chave/valor em JSON para que novos módulos não exijam migração de schema.
    """

    __tablename__ = "configuracoes_tenant"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    grupo: Mapped[str] = mapped_column(String(40), index=True)
    chave: Mapped[str] = mapped_column(String(60), unique=True)
    valor_json: Mapped[str] = mapped_column(Text, default="{}")
    descricao: Mapped[str] = mapped_column(String(200), default="")
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now,
    )


class CategoriaTenant(Base):
    """Categorias padrão (veículos, financeiro, documentos, leads)."""

    __tablename__ = "categorias_tenant"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    grupo: Mapped[str] = mapped_column(String(40), index=True)
    nome: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(80), default="")
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)


class PaginaSite(Base):
    """Páginas do site da empresa, criadas vazias no provisionamento."""

    __tablename__ = "paginas_site"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    titulo: Mapped[str] = mapped_column(String(120))
    conteudo_html: Mapped[str] = mapped_column(Text, default="")
    seo_titulo: Mapped[str] = mapped_column(String(160), default="")
    seo_descricao: Mapped[str] = mapped_column(String(300), default="")
    rota: Mapped[str] = mapped_column(String(80), default="")
    sistema: Mapped[bool] = mapped_column(Boolean, default=True)
    publicada: Mapped[bool] = mapped_column(Boolean, default=True)
    no_menu: Mapped[bool] = mapped_column(Boolean, default=False)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now,
    )


class LogTenant(Base):
    """Log exclusivo da empresa — nunca compartilhado entre tenants."""

    __tablename__ = "logs_tenant"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30), default="sistema")
    nivel: Mapped[str] = mapped_column(String(12), default="info")
    mensagem: Mapped[str] = mapped_column(String(500), default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Campanha(Base):
    __tablename__ = "campanhas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    origem: Mapped[str] = mapped_column(String(60), default="site")
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    leads: Mapped[list["Lead"]] = relationship(back_populates="campanha")


class VeiculoDB(Base):
    __tablename__ = "veiculos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marca: Mapped[str] = mapped_column(String(40))
    modelo: Mapped[str] = mapped_column(String(80))
    ano: Mapped[int] = mapped_column(Integer)
    km: Mapped[int] = mapped_column(Integer, default=0)
    combustivel: Mapped[str] = mapped_column(String(20), default="FLEX")
    cambio: Mapped[str] = mapped_column(String(20), default="MANUAL")
    preco: Mapped[float] = mapped_column(Float)
    custo: Mapped[float] = mapped_column(Float, default=0)
    imagem: Mapped[str] = mapped_column(String(500), default="")
    imagem_destaque: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="disponivel")
    destaque: Mapped[bool] = mapped_column(Boolean, default=False)
    descricao: Mapped[str] = mapped_column(Text, default="")
    cor: Mapped[str] = mapped_column(String(30), default="BRANCO")
    tipo: Mapped[str] = mapped_column(String(40), default="AUTOMÓVEL")
    badge: Mapped[str] = mapped_column(String(40), default="PRONTA ENTREGA")
    info_extra: Mapped[str] = mapped_column(String(200), default="")
    placa: Mapped[str] = mapped_column(String(12), default="")
    chassi: Mapped[str] = mapped_column(String(30), default="")
    renavam: Mapped[str] = mapped_column(String(20), default="")
    fipe: Mapped[float] = mapped_column(Float, default=0)
    videos_url: Mapped[str] = mapped_column(String(500), default="")
    opcionais: Mapped[str] = mapped_column(Text, default="")
    etiquetas: Mapped[str] = mapped_column(String(200), default="")
    publicado: Mapped[bool] = mapped_column(Boolean, default=True)
    historico_texto: Mapped[str] = mapped_column(Text, default="")
    visualizacoes: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    leads: Mapped[list["Lead"]] = relationship(back_populates="veiculo")
    custos: Mapped[list["VeiculoCusto"]] = relationship(back_populates="veiculo")


class VeiculoCusto(Base):
    __tablename__ = "veiculo_custos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    veiculo_id: Mapped[int] = mapped_column(Integer, ForeignKey("veiculos.id"))
    descricao: Mapped[str] = mapped_column(String(200))
    valor: Mapped[float] = mapped_column(Float, default=0)
    data: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    veiculo: Mapped[VeiculoDB] = relationship(back_populates="custos")


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(2), default="PF")  # PF | PJ
    nome: Mapped[str] = mapped_column(String(160))
    documento: Mapped[str] = mapped_column(String(30), default="")  # CPF/CNPJ
    telefone: Mapped[str] = mapped_column(String(30), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    endereco: Mapped[str] = mapped_column(String(200), default="")
    cidade: Mapped[str] = mapped_column(String(80), default="")
    observacoes: Mapped[str] = mapped_column(Text, default="")
    documentos_texto: Mapped[str] = mapped_column(Text, default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    telefone: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(120), default="")
    origem: Mapped[str] = mapped_column(String(60), default="site")
    utm_source: Mapped[str] = mapped_column(String(80), default="")
    utm_campaign: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default="novo")
    observacoes: Mapped[str] = mapped_column(Text, default="")
    vendedor: Mapped[str] = mapped_column(String(80), default="")
    cliente_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.id"), nullable=True
    )
    veiculo_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("veiculos.id"), nullable=True
    )
    campanha_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("campanhas.id"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    veiculo: Mapped[VeiculoDB | None] = relationship(back_populates="leads")
    campanha: Mapped[Campanha | None] = relationship(back_populates="leads")
    atividades: Mapped[list["LeadAtividade"]] = relationship(back_populates="lead")
    tarefas: Mapped[list["LeadTarefa"]] = relationship(back_populates="lead")


class LeadAtividade(Base):
    __tablename__ = "lead_atividades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"))
    texto: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    lead: Mapped[Lead] = relationship(back_populates="atividades")


class LeadTarefa(Base):
    __tablename__ = "lead_tarefas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"))
    titulo: Mapped[str] = mapped_column(String(200))
    lembrete_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    concluida: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    lead: Mapped[Lead] = relationship(back_populates="tarefas")


class Avaliacao(Base):
    __tablename__ = "avaliacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marca: Mapped[str] = mapped_column(String(40), default="")
    modelo: Mapped[str] = mapped_column(String(80), default="")
    ano: Mapped[str] = mapped_column(String(10), default="")
    renavam: Mapped[str] = mapped_column(String(20), default="")
    km: Mapped[str] = mapped_column(String(20), default="")
    revisao_autorizada: Mapped[bool] = mapped_column(Boolean, default=False)
    cor: Mapped[str] = mapped_column(String(30), default="")
    sinistro: Mapped[bool] = mapped_column(Boolean, default=False)
    combustivel: Mapped[str] = mapped_column(String(20), default="")
    cambio: Mapped[str] = mapped_column(String(20), default="")
    estado_pneus: Mapped[str] = mapped_column(String(30), default="")
    acessorio_extra: Mapped[str] = mapped_column(String(120), default="")
    nome: Mapped[str] = mapped_column(String(120))
    ddi: Mapped[str] = mapped_column(String(6), default="55")
    telefone: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(120), default="")
    data_nascimento: Mapped[str] = mapped_column(String(12), default="")
    endereco: Mapped[str] = mapped_column(String(200), default="")
    profissao: Mapped[str] = mapped_column(String(80), default="")
    cpf: Mapped[str] = mapped_column(String(20), default="")
    como_conheceu: Mapped[str] = mapped_column(String(120), default="")
    intencao: Mapped[str] = mapped_column(String(30), default="vender_comprar")
    veiculo_interesse: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default="novo")
    fotos_url: Mapped[str] = mapped_column(Text, default="")
    valor_fipe: Mapped[float] = mapped_column(Float, default=0)
    valor_sugerido: Mapped[float] = mapped_column(Float, default=0)
    valor_pago: Mapped[float] = mapped_column(Float, default=0)
    margem: Mapped[float] = mapped_column(Float, default=0)
    obs_interna: Mapped[str] = mapped_column(Text, default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Lancamento(Base):
    __tablename__ = "lancamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(10))  # entrada | saida
    categoria: Mapped[str] = mapped_column(String(60), default="geral")
    descricao: Mapped[str] = mapped_column(String(200))
    valor: Mapped[float] = mapped_column(Float, default=0)
    vencimento: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pago: Mapped[bool] = mapped_column(Boolean, default=False)
    comissao_pct: Mapped[float] = mapped_column(Float, default=0)
    veiculo_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("veiculos.id"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Proposta(Base):
    __tablename__ = "propostas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.id"), nullable=True
    )
    veiculo_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("veiculos.id"), nullable=True
    )
    cliente_nome: Mapped[str] = mapped_column(String(160), default="")
    valor: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(20), default="rascunho")
    texto: Mapped[str] = mapped_column(Text, default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Compromisso(Base):
    __tablename__ = "compromissos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200))
    tipo: Mapped[str] = mapped_column(String(40), default="lembrete")
    data_hora: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    observacoes: Mapped[str] = mapped_column(Text, default="")
    lead_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("leads.id"), nullable=True
    )
    cliente_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.id"), nullable=True
    )
    concluido: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Depoimento(Base):
    __tablename__ = "depoimentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    texto: Mapped[str] = mapped_column(Text)
    nota: Mapped[int] = mapped_column(Integer, default=5)
    cidade: Mapped[str] = mapped_column(String(80), default="")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Popup(Base):
    __tablename__ = "popups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(120), default="")
    texto: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(300), default="")
    ativo: Mapped[bool] = mapped_column(Boolean, default=False)


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40))  # recibo, contrato, etc
    titulo: Mapped[str] = mapped_column(String(160))
    conteudo_html: Mapped[str] = mapped_column(Text, default="")
    cliente_nome: Mapped[str] = mapped_column(String(160), default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Financiamento(Base):
    __tablename__ = "financiamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(160))
    cpf: Mapped[str] = mapped_column(String(20), default="")
    celular: Mapped[str] = mapped_column(String(30), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    veiculo_marca: Mapped[str] = mapped_column(String(60), default="")
    veiculo_modelo: Mapped[str] = mapped_column(String(80), default="")
    veiculo_ano_fab: Mapped[str] = mapped_column(String(6), default="")
    veiculo_ano_mod: Mapped[str] = mapped_column(String(6), default="")
    veiculo_cor: Mapped[str] = mapped_column(String(30), default="")
    valor_veiculo: Mapped[float] = mapped_column(Float, default=0)
    valor_entrada: Mapped[float] = mapped_column(Float, default=0)
    qtd_prestacoes: Mapped[int] = mapped_column(Integer, default=0)
    veiculo_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("veiculos.id"), nullable=True
    )
    lead_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("leads.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="novo")
    dados_json: Mapped[str] = mapped_column(Text, default="{}")
    observacoes_interna: Mapped[str] = mapped_column(Text, default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Atividade(Base):
    __tablename__ = "atividades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    texto: Mapped[str] = mapped_column(String(300))
    tipo: Mapped[str] = mapped_column(String(40), default="geral")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ConectorIntegracao(Base):
    """Marketplace / portal conectado ao ERP (ligar/desligar)."""

    __tablename__ = "conectores_integracao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)
    nome: Mapped[str] = mapped_column(String(80))
    categoria: Mapped[str] = mapped_column(String(40), default="marketplace")
    descricao: Mapped[str] = mapped_column(String(300), default="")
    ativo: Mapped[bool] = mapped_column(Boolean, default=False)
    disponivel: Mapped[bool] = mapped_column(Boolean, default=True)
    login: Mapped[str] = mapped_column(String(160), default="")
    codigo_acesso: Mapped[str] = mapped_column(String(300), default="")
    ultimo_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status_msg: Mapped[str] = mapped_column(String(200), default="")
    ordem: Mapped[int] = mapped_column(Integer, default=0)


class SyncIntegracao(Base):
    """Histórico de envio de veículos para cada conector."""

    __tablename__ = "sync_integracao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conector_codigo: Mapped[str] = mapped_column(String(40))
    veiculo_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("veiculos.id"), nullable=True
    )
    veiculo_nome: Mapped[str] = mapped_column(String(160), default="")
    acao: Mapped[str] = mapped_column(String(20), default="enviar")  # enviar|atualizar|remover
    status: Mapped[str] = mapped_column(String(20), default="pendente")  # pendente|ok|erro
    mensagem: Mapped[str] = mapped_column(String(300), default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
