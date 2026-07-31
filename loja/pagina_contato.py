from urllib.parse import quote

from nicegui import ui

from loja.campos_formulario import input_email, input_numero, input_texto, textarea_texto
from loja.repositorio import config_como_dict, salvar_lead
from loja.tenant_ctx import get_tenant_slug, ligar_tenant
from loja.whitelabel import bloco_empresa_html, endereco_linha


ASSUNTOS = {
    "geral": "Dúvida geral",
    "estoque": "Veículo do estoque",
    "financiamento": "Financiamento",
    "avaliacao": "Vender meu carro",
    "pos_venda": "Pós-venda",
}


def montar_pagina_contato() -> None:
    loja = config_como_dict()
    endereco = endereco_linha(loja)
    wa_num = (
        loja.get("whatsapp", "")
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "")
        .replace("-", "")
    )
    map_src = (
        f"https://maps.google.com/maps?q={quote(endereco)}&t=&z=15&ie=UTF8&iwloc=&output=embed"
        if endereco else ""
    )

    ui.html(
        f'<div class="pagina-topo-institucional">'
        f"<h1>FALE CONOSCO</h1>"
        f"<p class=\"pagina-topo-sub\">Estamos prontos para ajudar você a realizar o melhor negócio</p>"
        f"</div>"
    )

    with ui.element("div").classes("contato-layout"):
        with ui.element("div").classes("contato-form-col"):
            ui.html('<h2 class="contato-secao-titulo">Envie sua mensagem</h2>')
            ui.html(
                "<p class=\"contato-secao-desc\">Preencha o formulário e retornaremos "
                "o mais breve possível por telefone, WhatsApp ou e-mail.</p>"
            )

            with ui.element("div").classes("form-avaliacao contato-form form-site"):
                nome = input_texto("Nome completo", placeholder="Seu nome", classes="form-full")
                with ui.element("div").classes("form-grid"):
                    email = input_email("E-mail", placeholder="seu@email.com")
                    telefone = input_numero(
                        "Telefone / WhatsApp", placeholder="46999999999",
                    )
                assunto = ui.select(
                    ASSUNTOS, label="Assunto", value="geral",
                ).props("outlined dense").classes("form-full")
                mensagem = textarea_texto(
                    "Mensagem", placeholder="Como podemos ajudar?", classes="form-full",
                )

                slug = get_tenant_slug()

                def enviar() -> None:
                    if not nome.value or not telefone.value:
                        ui.notify("Preencha nome e telefone.", type="warning")
                        return
                    if not mensagem.value:
                        ui.notify("Escreva sua mensagem.", type="warning")
                        return
                    if slug:
                        ligar_tenant(slug)
                    rotulo = ASSUNTOS.get(assunto.value, "Contato")
                    salvar_lead({
                        "nome": nome.value.strip(),
                        "telefone": telefone.value.strip(),
                        "email": email.value or "",
                        "origem": "contato",
                        "status": "novo",
                        "observacoes": (
                            f"[{rotulo}] {mensagem.value.strip()}"
                        ),
                    })
                    ui.notify(
                        "Mensagem enviada! Em breve nossa equipe entrará em contato.",
                        type="positive",
                    )
                    nome.value = ""
                    email.value = ""
                    telefone.value = ""
                    mensagem.value = ""

                ui.button(
                    "Enviar mensagem",
                    on_click=enviar,
                ).classes("btn btn-preto btn-enviar-avaliacao").props(
                    "unelevated no-caps"
                )

        with ui.element("div").classes("contato-info-col"):
            ui.html('<h2 class="contato-secao-titulo">Canais de atendimento</h2>')
            _card_contato("call", "Telefone", loja.get("telefone", "—"))
            _card_contato("chat", "WhatsApp", loja.get("whatsapp", "—"))
            _card_contato("mail", "E-mail", loja.get("email", "—"))
            _card_contato("schedule", "Horário", loja.get("horario", "—"))
            _card_contato("place", "Endereço", endereco or "—")

            with ui.element("div").classes("contato-acoes-rapidas"):
                if wa_num:
                    ui.link(
                        "Chamar no WhatsApp",
                        f"https://wa.me/55{wa_num}?text={quote('Olá! Gostaria de falar com a loja.')}",
                    ).classes("btn btn-preto").props("target=_blank")
                if loja.get("email"):
                    ui.link(
                        "Enviar e-mail",
                        f"mailto:{loja['email']}",
                    ).classes("btn btn-contorno")

            ui.html(
                f'<div class="contato-dados-legais">{bloco_empresa_html(loja)}</div>'
            )

    if map_src:
        with ui.element("section").classes("contato-mapa"):
            ui.html('<h2 class="secao-titulo-centro">COMO CHEGAR</h2>')
            ui.html(
                f'<iframe class="contato-mapa-iframe" src="{map_src}" '
                f'loading="lazy" referrerpolicy="no-referrer-when-downgrade" '
                f'title="Mapa da loja"></iframe>'
            )


def _card_contato(icone: str, titulo: str, valor: str) -> None:
    ui.html(
        f'<article class="contato-card-info">'
        f'<span class="material-icons">{icone}</span>'
        f"<div><strong>{titulo}</strong><span>{valor}</span></div></article>"
    )
