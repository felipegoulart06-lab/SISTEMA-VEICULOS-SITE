"""Helpers white label — formatação de dados da loja."""

from __future__ import annotations

import html
import re

from nicegui import ui

from loja.models import ConfigLoja

_FAVICON_OK = re.compile(r"^(https?://|/|data:image/)", re.I)


def cfg_dict(c: ConfigLoja) -> dict:
    logo = c.logo_texto.strip() or c.nome.split()[0] if c.nome else "Loja"
    return {
        "nome_sistema": c.nome_sistema or "Gestão Veículos",
        "nome": c.nome,
        "razao_social": c.razao_social,
        "cnpj": c.cnpj,
        "slogan": c.slogan,
        "logo_texto": logo,
        "cidade": c.cidade,
        "estado": c.estado,
        "bairro": c.bairro,
        "cep": c.cep,
        "endereco": c.endereco,
        "telefone": c.telefone,
        "whatsapp": c.whatsapp,
        "email": c.email,
        "horario": c.horario,
        "facebook": c.facebook,
        "instagram": c.instagram,
        "sobre": c.sobre,
        "banner_url": c.banner_url,
        "cor_primaria": c.cor_primaria or "#c0392b",
        "dominio": getattr(c, "dominio", "") or "",
        "seo_titulo": getattr(c, "seo_titulo", "") or "",
        "seo_descricao": getattr(c, "seo_descricao", "") or "",
        "favicon_url": getattr(c, "favicon_url", "") or "",
        "nome_ia": getattr(c, "nome_ia", "") or "Assistente Virtual",
        "ia_ativa": bool(getattr(c, "ia_ativa", False)),
    }


def titulo_aba_erp(cfg: dict) -> str:
    return (cfg.get("nome_sistema") or "Gestão Veículos").strip()


def titulo_aba_site(cfg: dict, pagina: str = "") -> str:
    base = (cfg.get("seo_titulo") or cfg.get("nome") or "Loja").strip()
    if pagina:
        return f"{pagina} — {base}"
    return base


def html_favicon(cfg: dict) -> str:
    url = (cfg.get("favicon_url") or "").strip()
    if not url or not _FAVICON_OK.match(url):
        return ""
    seguro = html.escape(url, quote=True)
    return (
        f'<link rel="icon" href="{seguro}">'
        f'<link rel="shortcut icon" href="{seguro}">'
    )


def aplicar_marca_navegador(cfg: dict, titulo: str | None = None) -> None:
    """Define título e favicon da aba do navegador (ERP ou site)."""
    ui.page_title(titulo or titulo_aba_erp(cfg))
    fav = html_favicon(cfg)
    if fav:
        ui.add_head_html(fav)


def endereco_linha(cfg: dict) -> str:
    partes = []
    if cfg.get("endereco"):
        partes.append(cfg["endereco"])
    if cfg.get("bairro"):
        partes.append(cfg["bairro"])
    cidade_uf = ""
    if cfg.get("cidade"):
        cidade_uf = cfg["cidade"]
    if cfg.get("estado"):
        cidade_uf = f"{cidade_uf} - {cfg['estado']}" if cidade_uf else cfg["estado"]
    if cidade_uf:
        partes.append(cidade_uf)
    if cfg.get("cep"):
        partes.append(f"CEP {cfg['cep']}")
    return " · ".join(partes) if partes else cfg.get("endereco", "")


def bloco_empresa_html(cfg: dict) -> str:
    linhas = [f"<strong>{cfg['nome']}</strong>"]
    if cfg.get("razao_social"):
        linhas.append(f"Razão social: {cfg['razao_social']}")
    if cfg.get("cnpj"):
        linhas.append(f"CNPJ: {cfg['cnpj']}")
    end = endereco_linha(cfg)
    if end:
        linhas.append(end)
    if cfg.get("telefone"):
        linhas.append(f"Tel: {cfg['telefone']}")
    if cfg.get("whatsapp"):
        linhas.append(f"WhatsApp: {cfg['whatsapp']}")
    if cfg.get("email"):
        linhas.append(cfg["email"])
    if cfg.get("horario"):
        linhas.append(cfg["horario"])
    return "<br>".join(linhas)


def css_tema(cfg: dict) -> str:
    cor = cfg.get("cor_primaria", "#c0392b")
    return (
        f"<style>:root {{ --vermelho: {cor}; --cor-primaria: {cor}; "
        f"--erp-accent: {cor}; }}</style>"
    )
