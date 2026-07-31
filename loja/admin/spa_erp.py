"""Navegação SPA do ERP — painéis ficam em memória (show/hide, sem rebuild)."""

from __future__ import annotations

import time
from collections.abc import Callable

from nicegui import ui

from loja.admin.agenda import pagina_agenda
from loja.admin.avaliacoes import pagina_avaliacoes_admin
from loja.admin.clientes import pagina_clientes
from loja.admin.configuracoes import pagina_configuracoes
from loja.admin.dashboard import pagina_dashboard
from loja.admin.depoimentos import pagina_depoimentos
from loja.admin.documentos import pagina_documentos
from loja.admin.financiamentos import pagina_financiamentos_admin
from loja.admin.financeiro import pagina_financeiro
from loja.admin.institucional import pagina_institucional
from loja.admin.layout import (
    MENU_ADMIN,
    MENU_BLOQUEADO,
    _css_admin,
    _titulo_pagina,
)
from loja.admin.leads import pagina_leads
from loja.admin.marketing import pagina_marketing
from loja.admin.propostas import pagina_propostas
from loja.admin.relatorios import pagina_relatorios
from loja.admin.site_config import pagina_site
from loja.admin.veiculos import pagina_veiculos
from loja.auth import (
    conta_slug,
    exigir_login,
    fazer_logout,
    impersonando,
    sair_da_loja,
    usuario_nome,
)
from loja.repositorio import config_como_dict
from loja.tenant_ctx import ligar_tenant, site_url

ROTAS_ERP: dict[str, Callable] = {
    "/admin": pagina_dashboard,
    "/admin/veiculos": pagina_veiculos,
    "/admin/clientes": pagina_clientes,
    "/admin/leads": pagina_leads,
    "/admin/avaliacoes": pagina_avaliacoes_admin,
    "/admin/propostas": pagina_propostas,
    "/admin/financiamentos": pagina_financiamentos_admin,
    "/admin/financeiro": pagina_financeiro,
    "/admin/agenda": pagina_agenda,
    "/admin/documentos": pagina_documentos,
    "/admin/relatorios": pagina_relatorios,
    "/admin/marketing": pagina_marketing,
    "/admin/campanhas": pagina_marketing,
    "/admin/depoimentos": pagina_depoimentos,
    "/admin/site": pagina_site,
    "/admin/site/institucional": pagina_institucional,
    "/admin/configuracoes": pagina_configuracoes,
}

# Painéis em memória: clique vira só show/hide
TTL_PAINEL = 3600.0
PREFETCH = tuple(
    href for href in ROTAS_ERP
    if href not in ("/admin/campanhas", "/admin/site/institucional")
)


def normalizar_rota_erp(path: str | None) -> str:
    path = "/" + (path or "").strip("/")
    if path == "/":
        return "/admin"
    if not path.startswith("/admin"):
        path = "/admin" + ("" if path == "/" else path)
    if path == "/admin/campanhas":
        return "/admin/marketing"
    if path == "/admin/integracoes":
        return "/admin"
    if path in ROTAS_ERP:
        return path
    return "/admin"


def montar_erp_spa(rota_inicial: str = "/admin") -> None:
    if not exigir_login():
        return

    slug = conta_slug()
    if slug:
        ligar_tenant(slug)
    _css_admin()
    cfg = config_como_dict()
    nome_sistema = cfg.get("nome_sistema", "Gestão Veículos")
    link_site = site_url("/")

    estado = {"rota": normalizar_rota_erp(rota_inicial)}
    sidebar_ref = {"el": None}
    backdrop_ref = {"el": None}
    menu_mobile = {"aberto": False}
    titulo_lbl = {"el": None}
    nav_refs: dict[str, object] = {}
    host_ref = {"el": None}
    paineis: dict[str, dict] = {}

    def _aplicar_menu(aberto: bool) -> None:
        sb = sidebar_ref["el"]
        bd = backdrop_ref["el"]
        if sb is None:
            return
        if aberto:
            sb.classes(add="aberto")
            if bd is not None:
                bd.classes(add="aberto")
        else:
            sb.classes(remove="aberto")
            if bd is not None:
                bd.classes(remove="aberto")

    def toggle_sidebar() -> None:
        menu_mobile["aberto"] = not menu_mobile["aberto"]
        _aplicar_menu(menu_mobile["aberto"])

    def fechar_sidebar() -> None:
        menu_mobile["aberto"] = False
        _aplicar_menu(False)

    def _marcar_ativo(href: str) -> None:
        for link, el in nav_refs.items():
            if el is None:
                continue
            if link == href:
                el.classes(add="ativo")
            else:
                el.classes(remove="ativo")
        if titulo_lbl["el"] is not None:
            titulo_lbl["el"].set_text(_titulo_pagina(href))

    def _esconder_todos() -> None:
        for p in paineis.values():
            el = p.get("el")
            if el is not None:
                el.set_visibility(False)

    def _montar_painel(destino: str, visivel: bool = True) -> None:
        host = host_ref["el"]
        if host is None:
            return
        if destino in paineis:
            try:
                paineis[destino]["el"].delete()
            except Exception:
                pass
            paineis.pop(destino, None)
        with host:
            painel = ui.element("div").classes("erp-conteudo erp-spa-painel")
            if not visivel:
                painel.set_visibility(False)
            with painel:
                fn = ROTAS_ERP.get(destino, pagina_dashboard)
                fn()
            paineis[destino] = {"el": painel, "ts": time.monotonic()}

    def _mostrar(destino: str, forcar: bool = False) -> None:
        agora = time.monotonic()
        existente = paineis.get(destino)
        fresco = (
            existente
            and not forcar
            and (agora - existente["ts"]) < TTL_PAINEL
        )
        _esconder_todos()
        if fresco:
            existente["el"].set_visibility(True)
            return
        _montar_painel(destino, visivel=True)

    def invalidar_painel(href: str | None = None) -> None:
        if href is None:
            alvos = list(paineis.keys())
        else:
            alvos = [normalizar_rota_erp(href)]
        for dest in alvos:
            p = paineis.pop(dest, None)
            if p and p.get("el") is not None:
                try:
                    p["el"].delete()
                except Exception:
                    pass
        if estado["rota"] in alvos or href is None:
            _mostrar(estado["rota"], forcar=True)

    def ir(href: str, forcar: bool = False) -> None:
        if href in MENU_BLOQUEADO:
            ui.notify(MENU_BLOQUEADO[href], type="warning")
            return
        destino = normalizar_rota_erp(href)
        mesma = destino == estado["rota"]
        estado["rota"] = destino
        _marcar_ativo(destino)
        fechar_sidebar()
        ui.run_javascript(f'history.pushState({{}}, "", "{destino}");')
        if mesma and not forcar and destino in paineis:
            return

        agora = time.monotonic()
        existente = paineis.get(destino)
        fresco = (
            existente
            and not forcar
            and (agora - existente["ts"]) < TTL_PAINEL
        )
        if fresco:
            _esconder_todos()
            existente["el"].set_visibility(True)
            return

        # Feedback imediato no menu; monta conteúdo no próximo tick
        _esconder_todos()
        if host_ref["el"] is not None and "loading" not in paineis:
            with host_ref["el"]:
                loading = ui.element("div").classes(
                    "erp-conteudo erp-spa-painel erp-spa-loading"
                )
                with loading:
                    ui.html("<p style='padding:24px;color:#6b7280'>Carregando…</p>")
                paineis["loading"] = {"el": loading, "ts": agora}
        elif "loading" in paineis:
            paineis["loading"]["el"].set_visibility(True)

        def _depois() -> None:
            if estado["rota"] != destino:
                return
            try:
                _mostrar(destino, forcar=forcar)
            finally:
                load = paineis.pop("loading", None)
                if load and load.get("el") is not None:
                    try:
                        load["el"].delete()
                    except Exception:
                        pass

        ui.timer(0.01, _depois, once=True)

    ui.context.client.erp_ir = ir  # type: ignore[attr-defined]
    ui.context.client.erp_invalidar_painel = invalidar_painel  # type: ignore[attr-defined]

    with ui.element("div").classes("erp-app"):
        backdrop_ref["el"] = ui.element("div").classes(
            "erp-sidebar-backdrop"
        ).on("click", fechar_sidebar)
        sidebar_ref["el"] = ui.element("aside").classes("erp-sidebar")
        with sidebar_ref["el"]:
            with ui.element("div").classes("erp-sidebar-topo"):
                ui.html(f'<div class="erp-logo-text">{nome_sistema}</div>')
                ui.html(f'<p class="erp-loja-nome">{cfg["nome"]}</p>')

            with ui.element("nav").classes("erp-nav"):
                grupo_atual = object()
                for grupo, item_titulo, href, icone in MENU_ADMIN:
                    if grupo != grupo_atual:
                        grupo_atual = grupo
                        if grupo:
                            ui.html(f'<div class="erp-nav-label">{grupo}</div>')
                        else:
                            ui.html('<div class="erp-nav-label">Início</div>')
                    if href in MENU_BLOQUEADO:
                        msg = MENU_BLOQUEADO[href]
                        ui.html(
                            f'<span class="erp-nav-item erp-nav-item-bloqueado" '
                            f'title="{msg}">'
                            f'<span class="erp-nav-item-inner">'
                            f'<span class="material-icons erp-nav-ico">{icone}</span>'
                            f"<span>{item_titulo}</span>"
                            f"</span>"
                            f'<span class="erp-nav-bloqueio-overlay">'
                            f'<span class="material-icons erp-nav-cadeado">lock</span>'
                            f"</span></span>"
                        )
                    else:
                        ativo = "ativo" if estado["rota"] == href else ""
                        item = ui.element("div").classes(f"erp-nav-item {ativo}")
                        item.style("cursor:pointer")
                        item.on("click", lambda e, h=href: ir(h))
                        with item:
                            ui.html(
                                f'<span class="material-icons erp-nav-ico">{icone}</span>'
                                f"<span>{item_titulo}</span>"
                            )
                        nav_refs[href] = item

            with ui.element("div").classes("erp-sidebar-rodape"):
                ui.html(
                    f'<a href="{link_site}" target="_blank" class="erp-btn-outline">'
                    f'<span class="material-icons">open_in_new</span>'
                    f"Ver site público</a>"
                )
                if impersonando():
                    ui.button(
                        "Voltar ao Master",
                        on_click=lambda: (
                            sair_da_loja(), ui.navigate.to("/master/empresas"),
                        ),
                    ).props("flat no-caps").classes("erp-btn-sair")
                else:
                    ui.button(
                        "Sair da conta",
                        on_click=lambda: (
                            fazer_logout(), ui.navigate.to("/admin/login"),
                        ),
                    ).props("flat no-caps").classes("erp-btn-sair")

        with ui.element("div").classes("erp-main"):
            with ui.element("header").classes("erp-topbar"):
                with ui.element("div").classes("erp-topbar-esq"):
                    ui.button("☰", on_click=toggle_sidebar).classes(
                        "erp-menu-mobile"
                    ).props("flat dense")
                    with ui.element("div").classes("erp-topbar-titulos"):
                        titulo_lbl["el"] = ui.label(
                            _titulo_pagina(estado["rota"])
                        ).classes("erp-topbar-h1")
                        ui.label("CRM da sua loja").classes("erp-topbar-sub")
                with ui.element("div").classes("erp-topbar-dir"):
                    with ui.element("div").classes("erp-user-pill"):
                        with ui.element("div").classes("erp-user-info"):
                            ui.label(usuario_nome()).classes("erp-usuario-nome")
                            ui.label("Administrador").classes("erp-usuario-cargo")
                        with ui.element("div").classes("erp-avatar"):
                            ui.label(usuario_nome()[0].upper())

            host_ref["el"] = ui.element("div").classes("erp-spa-host")
            with host_ref["el"]:
                pass
            _mostrar(estado["rota"], forcar=True)

    fila = [r for r in PREFETCH if r != estado["rota"]]

    def _prefetch_proximo() -> None:
        while fila:
            rota = fila.pop(0)
            if rota in paineis or rota == estado["rota"]:
                continue
            try:
                _montar_painel(rota, visivel=False)
            except Exception:
                pass
            if fila:
                ui.timer(0.2, _prefetch_proximo, once=True)
            return

    ui.timer(0.3, _prefetch_proximo, once=True)
