from nicegui import ui

from loja.auth import (
    deve_trocar_senha,
    fazer_login,
    redirecionar_se_logado,
    redirecionar_se_master_logado,
)
from loja.plataforma import motivo_bloqueio
from loja.roteamento_host import erp_admin_url, erp_trocar_senha_url, get_contexto_host


def pagina_login() -> None:
    """Login único do ERP — todas as empresas entram por esta tela."""
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    ui.add_head_html('<link rel="stylesheet" href="/static/admin.css?v=27">')
    redirecionar_se_master_logado()
    redirecionar_se_logado()

    ui.add_head_html(
        "<style>:root { --erp-accent: #c0392b; --erp-accent-hover: #a93226; }</style>"
    )

    with ui.element("div").classes("erp-login-page erp-login-empresa"):
        with ui.element("div").classes("erp-login-brand"):
            ui.html('<div class="erp-login-brand-logo">Gestão Veículos</div>')
            ui.html('<p class="erp-login-brand-loja">ERP das lojas</p>')
            ui.html(
                '<ul class="erp-login-features">'
                "<li>Login único para todas as empresas</li>"
                "<li>Seu e-mail identifica a loja automaticamente</li>"
                "<li>Dados isolados por conta</li>"
                "</ul>"
            )
            ui.html(
                '<p class="erp-login-brand-copy">'
                "Use o e-mail e a senha fornecidos pelo Administrador Master"
                "</p>"
            )

        with ui.element("div").classes("erp-login-form-side"):
            with ui.element("div").classes("erp-login-card"):
                ui.html(
                    '<div class="erp-login-card-topo">'
                    "<h1>Entrar no ERP</h1>"
                    "<p>Acesso exclusivo das empresas cadastradas na plataforma</p>"
                    "</div>"
                )
                ctx = get_contexto_host()
                if ctx.modo == "erp" and ctx.host:
                    ui.html(
                        f'<p class="erp-ajuda mst-dominios-preview">'
                        f"Acesso via <code>{ctx.host}</code></p>"
                    )

                email = ui.input("E-mail da empresa").props(
                    "outlined dense hide-bottom-space autofocus"
                ).classes("erp-login-field")
                token = ui.input(
                    "Senha",
                    password=True,
                    password_toggle_button=True,
                ).props("outlined dense hide-bottom-space").classes("erp-login-field")

                def entrar() -> None:
                    ctx = get_contexto_host()
                    if fazer_login(email.value or "", token.value or ""):
                        if ctx.modo == "erp" and ctx.slug:
                            from loja.auth import conta_slug
                            if conta_slug() != ctx.slug:
                                from loja.auth import fazer_logout
                                fazer_logout()
                                ui.notify(
                                    "Esta conta não pertence a este subdomínio.",
                                    type="negative",
                                )
                                return
                        if deve_trocar_senha():
                            ui.notify(
                                "Defina uma nova senha para continuar.",
                                type="warning",
                            )
                            ui.navigate.to(erp_trocar_senha_url())
                            return
                        ui.notify("Login realizado!", type="positive")
                        ui.navigate.to(erp_admin_url())
                    else:
                        bloqueio = motivo_bloqueio(email.value or "")
                        ui.notify(
                            bloqueio or "E-mail ou senha inválidos.",
                            type="negative",
                            timeout=6000 if bloqueio else None,
                        )

                token.on("keydown.enter", entrar)

                ui.button("Entrar no ERP", on_click=entrar).classes(
                    "erp-login-btn"
                ).props("unelevated no-caps")

                with ui.element("div").classes("erp-login-rodape-card"):
                    ui.html(
                        '<span class="erp-login-badge">Demo SIGMA</span>'
                        "<code>admin@sigma.com</code>"
                        '<span class="erp-login-sep">·</span>'
                        "<code>admin123</code>"
                    )
