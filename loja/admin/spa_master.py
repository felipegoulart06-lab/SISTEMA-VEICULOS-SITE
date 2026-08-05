"""Navegação SPA do Master — painéis em memória (show/hide)."""

from __future__ import annotations

import time
from collections.abc import Callable

from nicegui import ui

from loja.admin.master import (
    MENU_MASTER,
    _css_master,
    pagina_master_config,
    pagina_master_dashboard,
    pagina_master_dominios,
    pagina_master_empresas,
    pagina_master_logs,
    pagina_master_planos,
)
from loja.auth import exigir_master, fazer_logout_master, master_nome
from loja.plataforma import obter_config_plataforma

ROTAS_MASTER: dict[str, Callable] = {
    "/master": pagina_master_dashboard,
    "/master/empresas": pagina_master_empresas,
    "/master/planos": pagina_master_planos,
    "/master/dominios": pagina_master_dominios,
    "/master/logs": pagina_master_logs,
    "/master/configuracoes": pagina_master_config,
}

TTL_PAINEL = 600.0
MAX_PAINEIS_CACHE = 3


def normalizar_rota_master(path: str | None) -> str:
    path = "/" + (path or "").strip("/")
    if path in ("/", "/master/lojas", "/master/contas"):
        return (
            "/master/empresas"
            if path in ("/master/lojas", "/master/contas")
            else "/master"
        )
    if not path.startswith("/master"):
        path = "/master" + ("" if path == "/" else path)
    if path in ROTAS_MASTER:
        return path
    return "/master"


def montar_master_spa(rota_inicial: str = "/master") -> None:
    if not exigir_master():
        return
    _css_master()
    cfg = obter_config_plataforma()
    estado = {"rota": normalizar_rota_master(rota_inicial)}
    sidebar_ref = {"el": None}
    backdrop_ref = {"el": None}
    aberto = {"v": False}
    titulo_lbl = {"el": None}
    nav_refs: dict[str, object] = {}
    host_ref = {"el": None}
    paineis: dict[str, dict] = {}

    def _aplicar_menu(ligado: bool) -> None:
        sb = sidebar_ref["el"]
        bd = backdrop_ref["el"]
        if sb is None:
            return
        if ligado:
            sb.classes(add="aberto")
            if bd is not None:
                bd.classes(add="aberto")
        else:
            sb.classes(remove="aberto")
            if bd is not None:
                bd.classes(remove="aberto")

    def toggle_sidebar() -> None:
        aberto["v"] = not aberto["v"]
        _aplicar_menu(aberto["v"])

    def fechar_sidebar() -> None:
        aberto["v"] = False
        _aplicar_menu(False)

    def _titulo(href: str) -> str:
        return next((t for t, h, _ in MENU_MASTER if h == href), "Painel")

    def _marcar_ativo(href: str) -> None:
        for link, el in nav_refs.items():
            if el is None:
                continue
            if link == href:
                el.classes(add="ativo")
            else:
                el.classes(remove="ativo")
        if titulo_lbl["el"] is not None:
            titulo_lbl["el"].set_text(_titulo(href))

    def _esconder_todos() -> None:
        for p in paineis.values():
            el = p.get("el")
            if el is not None:
                el.set_visibility(False)

    def _evictar_paineis(destino: str) -> None:
        reservados = {destino, "loading"}
        while len(paineis) > MAX_PAINEIS_CACHE:
            candidatos = [
                (k, v) for k, v in paineis.items() if k not in reservados
            ]
            if not candidatos:
                break
            chave, info = min(candidatos, key=lambda x: x[1].get("ts", 0))
            el = info.get("el")
            if el is not None:
                try:
                    el.delete()
                except Exception:
                    pass
            paineis.pop(chave, None)

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
                fn = ROTAS_MASTER.get(destino, pagina_master_dashboard)
                fn()
            paineis[destino] = {"el": painel, "ts": time.monotonic()}
        _evictar_paineis(destino)

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

    def ir(href: str, forcar: bool = False) -> None:
        destino = normalizar_rota_master(href)
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

    with ui.element("div").classes("erp-app"):
        backdrop_ref["el"] = ui.element("div").classes(
            "erp-sidebar-backdrop"
        ).on("click", fechar_sidebar)
        sidebar_ref["el"] = ui.element("aside").classes("erp-sidebar")
        with sidebar_ref["el"]:
            with ui.element("div").classes("erp-sidebar-topo"):
                ui.html(
                    f'<div class="erp-logo-text">{cfg.nome_plataforma}</div>'
                )
                ui.html('<p class="erp-loja-nome">Administrador Master</p>')

            with ui.element("nav").classes("erp-nav"):
                for item_titulo, href, icone in MENU_MASTER:
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
                ui.html(f'<span class="mst-versao">v{cfg.versao}</span>')
                ui.button(
                    "Sair do Master",
                    on_click=lambda: (
                        fazer_logout_master(), ui.navigate.to("/master/login"),
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
                            _titulo(estado["rota"])
                        ).classes("erp-topbar-h1")
                        ui.label("Controle da plataforma").classes("erp-topbar-sub")
                with ui.element("div").classes("erp-topbar-dir"):
                    with ui.element("div").classes("erp-user-pill"):
                        with ui.element("div").classes("erp-user-info"):
                            ui.label(master_nome()).classes("erp-usuario-nome")
                            ui.label("Master").classes("erp-usuario-cargo")
                        with ui.element("div").classes("erp-avatar"):
                            ui.label(master_nome()[0].upper())

            host_ref["el"] = ui.element("div").classes("erp-spa-host")
            with host_ref["el"]:
                pass
            _mostrar(estado["rota"], forcar=True)
