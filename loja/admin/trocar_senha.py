"""Troca obrigatória de senha no primeiro acesso da empresa."""

from nicegui import app, ui

from loja.auth import concluir_troca_senha, deve_trocar_senha, logado


def pagina_trocar_senha() -> None:
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    ui.add_head_html('<link rel="stylesheet" href="/static/admin.css?v=20">')
    ui.add_head_html(
        "<style>:root { --erp-accent: #c0392b; --erp-accent-hover: #a93226; }"
        "</style>"
    )

    if not logado():
        ui.navigate.to("/admin/login")
        return
    if not deve_trocar_senha():
        ui.navigate.to("/admin")
        return

    empresa = app.storage.user.get("usuario_nome", "sua empresa")
    email = app.storage.user.get("usuario_email", "")

    with ui.element("div").classes("erp-login-page"):
        with ui.element("div").classes("erp-login-brand"):
            ui.html('<div class="erp-login-brand-logo">Primeiro acesso</div>')
            ui.html(f'<p class="erp-login-brand-loja">{empresa}</p>')
            ui.html(
                '<ul class="erp-login-features">'
                "<li>Sua senha atual é temporária</li>"
                "<li>Defina uma senha própria para continuar</li>"
                "<li>Somente você tem acesso a esta empresa</li>"
                "</ul>"
            )

        with ui.element("div").classes("erp-login-form-side"):
            with ui.element("div").classes("erp-login-card"):
                ui.html(
                    '<div class="erp-login-card-topo">'
                    "<h1>Defina sua senha</h1>"
                    f"<p>Conta: {email}</p></div>"
                )
                nova = ui.input("Nova senha", password=True).props(
                    "outlined dense hide-bottom-space"
                ).classes("erp-login-field")
                confirma = ui.input("Repita a nova senha", password=True).props(
                    "outlined dense hide-bottom-space"
                ).classes("erp-login-field")
                ui.html(
                    '<p class="erp-ajuda">Mínimo de 8 caracteres, '
                    "com letras e números.</p>"
                )

                def salvar() -> None:
                    senha = nova.value or ""
                    if len(senha) < 8:
                        ui.notify(
                            "A senha precisa ter ao menos 8 caracteres.",
                            type="warning",
                        )
                        return
                    if senha.isalpha() or senha.isdigit():
                        ui.notify(
                            "Combine letras e números.", type="warning",
                        )
                        return
                    if senha != (confirma.value or ""):
                        ui.notify("As senhas não conferem.", type="warning")
                        return
                    try:
                        concluir_troca_senha(senha)
                    except ValueError as err:
                        ui.notify(str(err), type="negative")
                        return
                    ui.notify("Senha atualizada!", type="positive")
                    ui.navigate.to("/admin")

                confirma.on("keydown.enter", salvar)
                ui.button("Salvar e entrar", on_click=salvar).classes(
                    "erp-login-btn"
                ).props("unelevated no-caps")
