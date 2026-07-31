from nicegui import ui

from loja.auth import (
    conta_slug,
    fazer_logout,
    impersonando,
    sair_da_loja,
    usuario_nome,
)
from loja.repositorio import config_como_dict
from loja.tenant_ctx import ligar_tenant, site_url


# (grupo, titulo, href, icone)
MENU_ADMIN = [
    (None, "Dashboard", "/admin", "dashboard"),
    ("Comercial", "Veículos", "/admin/veiculos", "directions_car"),
    ("Comercial", "Clientes", "/admin/clientes", "badge"),
    ("Comercial", "Leads", "/admin/leads", "view_kanban"),
    ("Comercial", "Avaliações", "/admin/avaliacoes", "request_quote"),
    ("Comercial", "Propostas", "/admin/propostas", "description"),
    ("Comercial", "Financiamentos", "/admin/financiamentos", "account_balance"),
    ("Gestão", "Financeiro", "/admin/financeiro", "payments"),
    ("Gestão", "Agenda", "/admin/agenda", "event"),
    ("Gestão", "Documentos", "/admin/documentos", "folder"),
    ("Gestão", "Relatórios", "/admin/relatorios", "bar_chart"),
    ("Marketing", "Marketing", "/admin/marketing", "campaign"),
    ("Marketing", "Depoimentos", "/admin/depoimentos", "star"),
    ("Sistema", "Site", "/admin/site", "language"),
    ("Sistema", "Integrações", "/admin/integracoes", "hub"),
    ("Sistema", "Configurações", "/admin/configuracoes", "settings"),
]

# Rotas visíveis no menu, mas indisponíveis por enquanto
MENU_BLOQUEADO: dict[str, str] = {
    "/admin/integracoes": "Integrações estará disponível em breve.",
}


def _css_admin() -> None:
    from loja.whitelabel import css_tema

    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    ui.add_head_html(
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2'
        '?family=Inter:wght@400;500;600;700;800&display=swap">'
    )
    ui.add_head_html('<link rel="stylesheet" href="/static/admin.css?v=22">')
    ui.add_head_html(css_tema(config_como_dict()))


def layout_admin(pagina_atual: str, conteudo_fn) -> None:
    slug = conta_slug()
    if slug:
        ligar_tenant(slug)
    _css_admin()
    cfg = config_como_dict()
    nome_sistema = cfg.get("nome_sistema", "Gestão Veículos")
    sidebar_ref = {"el": None}
    backdrop_ref = {"el": None}
    menu_mobile = {"aberto": False}
    link_site = site_url("/")

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

    titulo = _titulo_pagina(pagina_atual)

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
                        elif grupo_atual is None or grupo is None:
                            ui.html('<div class="erp-nav-label">Início</div>')
                    ativo = "ativo" if pagina_atual == href else ""
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
                        ui.html(
                            f'<a href="{href}" class="erp-nav-item {ativo}">'
                            f'<span class="material-icons erp-nav-ico">{icone}</span>'
                            f"<span>{item_titulo}</span></a>"
                        )

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
                    ui.html(
                        f'<div class="erp-topbar-titulos">'
                        f"<h1>{titulo}</h1>"
                        f"<span>CRM da sua loja</span></div>"
                    )
                with ui.element("div").classes("erp-topbar-dir"):
                    with ui.element("div").classes("erp-user-pill"):
                        with ui.element("div").classes("erp-user-info"):
                            ui.label(usuario_nome()).classes("erp-usuario-nome")
                            ui.label("Administrador").classes("erp-usuario-cargo")
                        with ui.element("div").classes("erp-avatar"):
                            ui.label(usuario_nome()[0].upper())

            with ui.element("div").classes("erp-conteudo"):
                conteudo_fn()


def _titulo_pagina(href: str) -> str:
    for _, titulo, link, _ in MENU_ADMIN:
        if link == href:
            return titulo
    return "Painel"


def ajuda(texto: str) -> None:
    ui.html(f'<p class="erp-ajuda">{texto}</p>')


def confirmar_exclusao(o_que: str, ao_confirmar, detalhe: str = "") -> None:
    """Compatibilidade — preferir ConfirmacaoExclusao().pedir() na página."""
    ConfirmacaoExclusao().pedir(o_que, ao_confirmar, detalhe)


class ConfirmacaoExclusao:
    """Diálogo de confirmação — instanciar uma vez no início de cada página admin."""

    def pedir(self, o_que: str, ao_confirmar, detalhe: str = "") -> None:
        texto = f"Tem certeza que deseja excluir {o_que}?"
        if detalhe:
            texto += f" {detalhe}"

        with ui.dialog().props("persistent") as dlg, ui.card().classes(
            "erp-dialog erp-dialog-confirm"
        ):
            ui.label("Confirmar exclusão").classes("erp-dialog-titulo")
            ui.label(texto).classes("erp-confirm-text")
            ui.label("Esta ação não pode ser desfeita.").classes("erp-confirm-aviso")

            def cancelar() -> None:
                dlg.close()

            def confirmar() -> None:
                dlg.close()
                ao_confirmar()

            with ui.row().classes("erp-dialog-botoes"):
                ui.button("Não, cancelar", on_click=cancelar).props("flat no-caps")
                ui.button(
                    "Sim, excluir",
                    on_click=confirmar,
                ).props("color=negative unelevated no-caps")

        dlg.open()


def id_do_evento(e, campo: str = "id") -> int:
    """Extrai ID numérico de eventos da tabela NiceGUI."""
    args = e.args
    if isinstance(args, dict):
        return int(args.get(campo, args.get("id", 0)))
    if isinstance(args, (list, tuple)) and args:
        return int(args[0])
    return int(args)
