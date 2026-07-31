from nicegui import ui

from loja.auth import deve_trocar_senha, fazer_login, redirecionar_se_logado
from loja.plataforma import motivo_bloqueio


def pagina_login() -> None:
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    ui.add_head_html('<link rel="stylesheet" href="/static/admin.css?v=20">')
    redirecionar_se_logado()

    ui.add_head_html(
        "<style>:root { --erp-accent: #c0392b; --erp-accent-hover: #a93226; }</style>"
    )

    with ui.element("div").classes("erp-login-page"):
        with ui.element("div").classes("erp-login-brand"):
            ui.html('<div class="erp-login-brand-logo">Gestão Veículos</div>')
            ui.html('<p class="erp-login-brand-loja">Acesso da loja</p>')
            ui.html(
                '<ul class="erp-login-features">'
                "<li>ERP completo da sua loja</li>"
                "<li>Site público white label</li>"
                "<li>Dados isolados por conta</li>"
                "</ul>"
            )
            ui.html(
                '<p class="erp-login-brand-copy">'
                "Entre com o e-mail e a senha fornecidos pelo Administrador Master"
                "</p>"
            )

        with ui.element("div").classes("erp-login-form-side"):
            with ui.element("div").classes("erp-login-card"):
                ui.html(
                    '<div class="erp-login-card-topo">'
                    "<h1>Login da empresa</h1>"
                    "<p>Use o e-mail e a senha do administrador</p>"
                    "</div>"
                )

                email = ui.input("E-mail").props(
                    "outlined dense hide-bottom-space"
                ).classes("erp-login-field")
                token = ui.input("Senha", password=True).props(
                    "outlined dense hide-bottom-space"
                ).classes("erp-login-field")

                def entrar() -> None:
                    if fazer_login(email.value or "", token.value or ""):
                        if deve_trocar_senha():
                            ui.notify(
                                "Defina uma nova senha para continuar.",
                                type="warning",
                            )
                            ui.navigate.to("/admin/trocar-senha")
                            return
                        ui.notify("Login realizado!", type="positive")
                        ui.navigate.to("/admin")
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
                        '<span class="erp-login-badge">Demo</span>'
                        "<code>admin@sigma.com</code>"
                        '<span class="erp-login-sep">·</span>'
                        "<code>admin123</code>"
                    )
                    ui.html(
                        '<div style="margin-top:8px;font-size:12px">'
                        '<a href="/master/login">Acesso Master →</a></div>'
                    )
