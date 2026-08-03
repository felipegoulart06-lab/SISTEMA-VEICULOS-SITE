"""Modelos da plataforma White Label — MVP.

Escopo desta versão: empresas, planos, licença, domínios e logs simples.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PlataformaBase(DeclarativeBase):
    pass


class AdminMaster(PlataformaBase):
    __tablename__ = "admin_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(200))
    nome: Mapped[str] = mapped_column(String(100), default="Administrador Master")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Plano(PlataformaBase):
    """Plano contratado. Nesta versão só existe o Starter."""

    __tablename__ = "planos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), unique=True)
    descricao: Mapped[str] = mapped_column(String(300), default="")
    preco_mensal: Mapped[float] = mapped_column(Float, default=0)
    limite_veiculos: Mapped[int] = mapped_column(Integer, default=0)
    dias_licenca: Mapped[int] = mapped_column(Integer, default=30)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)


class Conta(PlataformaBase):
    """Empresa White Label: um ERP e um site isolados, um único administrador."""

    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    token_hash: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="teste")
    plano_id: Mapped[int | None] = mapped_column(
        ForeignKey("planos.id"), nullable=True,
    )
    # Licença
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    vencimento_em: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True,
    )
    # Desativação: exclusão só liberada após 31 dias
    desativada_em: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True,
    )
    # Domínios — somente o Admin Master edita
    subdominio: Mapped[str] = mapped_column(String(200), default="")
    dominio_site: Mapped[str] = mapped_column(String(200), default="")
    dominio_erp: Mapped[str] = mapped_column(String(200), default="")
    # Identidade
    logo_url: Mapped[str] = mapped_column(String(500), default="")
    favicon_url: Mapped[str] = mapped_column(String(500), default="")
    tema_cor: Mapped[str] = mapped_column(String(7), default="#c0392b")
    observacoes: Mapped[str] = mapped_column(String(500), default="")
    ultimo_acesso: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True,
    )
    # Compatibilidade com bases criadas antes do MVP
    dominio_proprio: Mapped[str] = mapped_column(String(200), default="")
    tema: Mapped[str] = mapped_column(String(40), default="padrao")
    idioma: Mapped[str] = mapped_column(String(10), default="pt-BR")
    fuso_horario: Mapped[str] = mapped_column(
        String(60), default="America/Sao_Paulo",
    )
    provisionada_em: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True,
    )


class LogPlataforma(PlataformaBase):
    """Log simples: só os eventos de ciclo de vida da empresa."""

    __tablename__ = "logs_plataforma"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30), default="empresa_criada")
    mensagem: Mapped[str] = mapped_column(String(500), default="")
    conta_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conta_nome: Mapped[str] = mapped_column(String(120), default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # Compatibilidade com a base anterior
    nivel: Mapped[str] = mapped_column(String(12), default="info")


class ConfigPlataforma(PlataformaBase):
    __tablename__ = "config_plataforma"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    nome_plataforma: Mapped[str] = mapped_column(
        String(120), default="Plataforma White Label",
    )
    logo_url: Mapped[str] = mapped_column(String(500), default="")
    cor_primaria: Mapped[str] = mapped_column(String(7), default="#1e3a5f")
    dominio_base: Mapped[str] = mapped_column(
        String(120), default="plataforma.com.br",
    )
    versao: Mapped[str] = mapped_column(String(20), default="1.0.0")
    # Campos legados mantidos para não quebrar bases já criadas
    smtp_host: Mapped[str] = mapped_column(String(160), default="")
    smtp_porta: Mapped[int] = mapped_column(Integer, default=587)
    smtp_usuario: Mapped[str] = mapped_column(String(160), default="")
    smtp_senha: Mapped[str] = mapped_column(String(200), default="")
    smtp_remetente: Mapped[str] = mapped_column(String(160), default="")
    changelog: Mapped[str] = mapped_column(Text, default="")
