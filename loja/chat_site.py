"""Painel de chat lateral fixo no site público."""

from __future__ import annotations

import asyncio
import html
from urllib.parse import quote

from nicegui import ui

from loja.campos_formulario import input_numero, input_texto, textarea_texto
from loja.ia_chat import responder_ia, validar_nome, validar_telefone
from loja.repositorio import salvar_lead
from loja.tenant_ctx import get_tenant_slug, ligar_tenant, site_url, tenant_escopo


def montar_painel_chat(loja: dict, wa: str, email: str):
    ia_ativa = bool(loja.get("ia_ativa"))
    nome_ia = loja.get("nome_ia") or "Assistente Virtual"
    titulo = nome_ia if ia_ativa else "Central de Atendimento"
    # Captura o tenant da página — callbacks/async não herdam ContextVar
    slug_loja = get_tenant_slug()

    estado: dict = {
        "aberto": False,
        "fase": "inicio" if ia_ativa else "manual",
        "nome": "",
        "telefone": "",
        "mensagens": [],
        "digitando": False,
        "historico_ia": [],
    }

    painel_ref: dict = {"el": None}
    campo_ref: dict = {"el": None}

    def scroll_fim() -> None:
        ui.run_javascript(
            "const el = document.querySelector('.site-chat-mensagens');"
            "if (el) el.scrollTop = el.scrollHeight;"
        )

    @ui.refreshable
    def area_mensagens() -> None:
        for msg in estado["mensagens"]:
            texto = html.escape(msg["texto"]).replace("\n", "<br>")
            ui.html(
                f'<div class="site-chat-msg site-chat-msg-{msg["tipo"]}">'
                f'<div class="site-chat-balao">{texto}</div></div>'
            )
        if estado["digitando"]:
            ui.html(
                '<div class="site-chat-msg site-chat-msg-bot">'
                '<div class="site-chat-balao site-chat-digitando">'
                '<span></span><span></span><span></span></div></div>'
            )

    def atualizar_painel() -> None:
        el = painel_ref["el"]
        if el is None:
            return
        if estado["aberto"]:
            el.classes(add="aberto")
        else:
            el.classes(remove="aberto")
        if ia_ativa:
            area_mensagens.refresh()

    def fechar_painel() -> None:
        estado["aberto"] = False
        atualizar_painel()

    def bot_fala(texto: str, delay: float = 1.2) -> None:
        estado["digitando"] = True
        area_mensagens.refresh()
        scroll_fim()

        def exibir() -> None:
            estado["digitando"] = False
            estado["mensagens"].append({"tipo": "bot", "texto": texto})
            estado["historico_ia"].append({"tipo": "bot", "texto": texto})
            area_mensagens.refresh()
            scroll_fim()

        ui.timer(delay, exibir, once=True)

    def _com_tenant() -> None:
        if slug_loja:
            ligar_tenant(slug_loja)

    def registrar_lead_chat(obs: str) -> None:
        if not estado["nome"] or not estado["telefone"]:
            return
        _com_tenant()
        salvar_lead({
            "nome": estado["nome"],
            "telefone": estado["telefone"],
            "email": email,
            "origem": "ia_chat",
            "status": "novo",
            "observacoes": obs,
        })

    async def ia_responder(pergunta: str) -> None:
        estado["digitando"] = True
        area_mensagens.refresh()
        scroll_fim()
        try:
            with tenant_escopo(slug_loja or ""):
                if slug_loja:
                    ligar_tenant(slug_loja)
                resposta = await responder_ia(
                    pergunta,
                    estado["historico_ia"],
                    loja,
                    nome_ia,
                )
        except Exception:
            resposta = (
                "Desculpe, tive um problema agora. "
                f"Fale conosco pelo WhatsApp {loja.get('whatsapp', '')} "
                f"ou acesse {site_url('/contato', slug_loja)}."
            )
        estado["digitando"] = False
        estado["mensagens"].append({"tipo": "bot", "texto": resposta})
        estado["historico_ia"].append({"tipo": "bot", "texto": resposta})
        area_mensagens.refresh()
        scroll_fim()
        registrar_lead_chat(
            "[Chat IA]\n"
            + "\n".join(
                f"{'Cliente' if m['tipo'] == 'user' else nome_ia}: {m['texto']}"
                for m in estado["historico_ia"]
            )
        )

    def processar_envio() -> None:
        campo = campo_ref["el"]
        if campo is None:
            return
        texto = (campo.value or "").strip()
        if not texto or estado["digitando"]:
            return
        campo.value = ""

        if estado["fase"] == "nome":
            if not validar_nome(texto):
                bot_fala("Por favor, informe seu nome completo (nome e sobrenome).", 0.8)
                return
            estado["nome"] = texto.upper()
            estado["mensagens"].append({"tipo": "user", "texto": texto.upper()})
            estado["fase"] = "telefone"
            area_mensagens.refresh()
            bot_fala(f"Prazer, {texto.split()[0]}! Qual é o seu número de telefone?", 1.2)
            return

        if estado["fase"] == "telefone":
            if not validar_telefone(texto):
                bot_fala("Informe um telefone válido com DDD (10 ou 11 dígitos).", 0.8)
                return
            estado["telefone"] = "".join(c for c in texto if c.isdigit())
            estado["mensagens"].append({"tipo": "user", "texto": texto})
            estado["fase"] = "conversa"
            area_mensagens.refresh()
            bot_fala(
                f"Prazer, {texto.split()[0]}! Eu sou {nome_ia}. Em que posso te ajudar?",
                1.4,
            )
            return

        if estado["fase"] == "conversa":
            estado["mensagens"].append({"tipo": "user", "texto": texto})
            estado["historico_ia"].append({"tipo": "user", "texto": texto})
            area_mensagens.refresh()
            scroll_fim()
            asyncio.create_task(ia_responder(texto))

    def abrir_painel() -> None:
        estado["aberto"] = True
        atualizar_painel()
        if ia_ativa and estado["fase"] == "inicio":
            estado["fase"] = "nome"
            bot_fala("Olá! Antes de começarmos, qual é o seu nome completo?", 1.4)

    def toggle_painel() -> None:
        if estado["aberto"]:
            fechar_painel()
        else:
            abrir_painel()

    painel_ref["el"] = ui.element("div").classes("site-chat-panel")
    with painel_ref["el"]:
        with ui.element("div").classes("site-chat-topo"):
            with ui.element("div").classes("site-chat-topo-info"):
                ui.html(
                    f'<span class="site-chat-topo-nome">{titulo}</span>'
                    f'<span class="site-chat-topo-status">'
                    f'{"Online" if ia_ativa else loja["nome"]}</span>'
                )
            ui.button(icon="close", on_click=fechar_painel).props(
                "flat dense round"
            ).classes("site-chat-fechar")

        if ia_ativa:
            with ui.element("div").classes("site-chat-mensagens"):
                area_mensagens()
            with ui.element("div").classes("site-chat-rodape"):
                with ui.row().classes("w-full items-center no-wrap gap-2"):
                    campo_ref["el"] = ui.input(
                        placeholder="Digite sua mensagem...",
                    ).props("dense outlined hide-bottom-space").classes(
                        "site-chat-campo flex-1"
                    )
                    ui.button(icon="send", on_click=processar_envio).classes(
                        "site-chat-btn-send"
                    ).props("flat dense round")
                    campo_ref["el"].on(
                        "keydown.enter",
                        lambda: processar_envio(),
                    )
        else:
            with ui.element("div").classes("site-chat-manual form-site"):
                ui.html(
                    f'<div class="site-chat-manual-titulo">Central de Atendimento</div>'
                    f'<p class="site-chat-manual-sub">Equipe {loja["nome"]}</p>'
                )
                if loja.get("telefone"):
                    ui.html(
                        f'<p class="site-chat-manual-linha">'
                        f"<strong>Telefone:</strong> {loja['telefone']}</p>"
                    )
                if wa:
                    ui.link(
                        "Chamar no WhatsApp",
                        f"https://wa.me/55{wa}?text="
                        f"{quote('Olá! Gostaria de falar com a equipe.')}",
                    ).classes("btn btn-preto site-chat-wa").props(
                        "target=_blank no-caps"
                    )
                ui.html('<p class="site-chat-manual-divisor">Ou deixe sua mensagem:</p>')
                nome_f = input_texto("Seu nome").classes("w-full")
                tel_f = input_numero("Telefone / WhatsApp").classes("w-full")
                msg_f = textarea_texto("Mensagem").classes("w-full")

                def enviar_manual() -> None:
                    if not nome_f.value or not tel_f.value:
                        ui.notify("Preencha nome e telefone.", type="warning")
                        return
                    _com_tenant()
                    salvar_lead({
                        "nome": nome_f.value.strip(),
                        "telefone": tel_f.value.strip(),
                        "email": email,
                        "origem": "site",
                        "status": "novo",
                        "observacoes": (
                            f"[Atendimento online] {msg_f.value or 'Solicitou contato.'}"
                        ),
                    })
                    ui.notify("Mensagem enviada! Retornaremos em breve.", type="positive")
                    nome_f.value = ""
                    tel_f.value = ""
                    msg_f.value = ""
                    fechar_painel()

                ui.button("Enviar mensagem", on_click=enviar_manual).classes(
                    "btn btn-preto w-full site-chat-btn-enviar"
                ).props("unelevated no-caps")

    return toggle_painel
