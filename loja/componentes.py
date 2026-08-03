from nicegui import ui

from loja.chat_site import montar_painel_chat
from loja.campos_formulario import input_email, input_numero, input_texto
from loja.config import MENU
from loja.repositorio import (
    Veiculo,
    config_como_dict,
    formatar_km,
    formatar_preco,
    listar_marcas,
    salvar_lead,
)
from loja.tenant_ctx import get_tenant_slug, ligar_tenant, site_url

from loja.whitelabel import bloco_empresa_html, css_tema, endereco_linha


def _loja() -> dict:
    return config_como_dict()


def injetar_tema() -> None:
    ui.add_head_html(
        '<link rel="stylesheet" '
        'href="https://fonts.googleapis.com/icon?family=Material+Icons">'
    )
    ui.add_head_html(css_tema(_loja()))


def _logo_html(loja: dict) -> str:
    logo = loja["logo_texto"]
    if loja.get("slogan"):
        return f'{logo} <span>{loja["slogan"]}</span>'
    return logo


def barra_social() -> None:
    loja = _loja()
    fb = (loja.get("facebook") or "").strip()
    ig = (loja.get("instagram") or "").strip()
    email = (loja.get("email") or "").strip()
    links: list[tuple[str, str]] = []
    if fb and fb not in {"#", "http://", "https://"}:
        links.append(("Facebook", fb))
    if ig and ig not in {"#", "http://", "https://"}:
        links.append(("Instagram", ig))
    if email:
        links.append(("E-mail", f"mailto:{email}"))
    if not links:
        return
    with ui.element("div").classes("barra-social"):
        with ui.element("div").classes("conteudo"):
            for rotulo, href in links:
                alvo = "target=_blank" if not href.startswith("mailto:") else ""
                ui.link(rotulo, href).props(alvo)


def cabecalho(
    buscar_fn,
    navegar_spa=None,
    nav_refs: dict | None = None,
    rota_ativa: str | None = None,
) -> None:
    loja = _loja()
    estado_menu = {"aberto": False}
    nav_ref = {"el": None}

    def alternar_menu() -> None:
        estado_menu["aberto"] = not estado_menu["aberto"]
        nav = nav_ref["el"]
        if nav is None:
            return
        if estado_menu["aberto"]:
            nav.classes(add="aberto")
        else:
            nav.classes(remove="aberto")

    def fechar_menu() -> None:
        estado_menu["aberto"] = False
        nav = nav_ref["el"]
        if nav is not None:
            nav.classes(remove="aberto")

    with ui.element("div").classes("cabecalho-principal"):
        with ui.element("div").classes("conteudo"):
            with ui.element("div").classes("logo"):
                ui.html(_logo_html(loja))

            ui.button("☰", on_click=alternar_menu).props("flat dense").classes("btn-menu")

            nav_ref["el"] = ui.element("nav").classes("menu-nav")
            with nav_ref["el"]:
                for rotulo, href in MENU:
                    if navegar_spa is not None:
                        ativo = "ativo" if rota_ativa == href else ""
                        item = ui.element("div").classes(f"site-nav-item {ativo}")
                        item.style("cursor:pointer")
                        item.on(
                            "click",
                            lambda e, h=href: (navegar_spa(h), fechar_menu()),
                        )
                        with item:
                            ui.html(f"<span>{rotulo}</span>")
                        if nav_refs is not None:
                            nav_refs[href] = item
                    else:
                        ui.link(rotulo, site_url(href)).on("click", alternar_menu)

            with ui.element("div").classes("busca-cabecalho"):
                campo = ui.input(placeholder="Buscar veículo...").props(
                    "dense outlined hide-bottom-space"
                ).classes("campo-busca")
                ui.button(
                    "BUSCAR",
                    on_click=lambda: buscar_fn(campo.value),
                ).classes("btn btn-preto").props("no-caps unelevated")


def banner() -> None:
    loja = _loja()
    url = loja.get("banner_url") or (
        "https://images.unsplash.com/photo-1555215695-3004980ad54e?w=1400&q=80"
    )
    with ui.element("div").classes("banner"):
        ui.image(url).props("no-spinner")


def sidebar_marcas(marca_atual: str | None, ao_clicar) -> None:
    marcas = listar_marcas()
    with ui.element("aside").classes("sidebar-marcas"):
        ui.html("<h2>SHOWROOM / MARCAS</h2>")
        with ui.element("ul").classes("lista-marcas"):
            cls = "ativo" if marca_atual is None else ""
            with ui.element("li"):
                ui.button(
                    "TODAS AS MARCAS",
                    on_click=lambda: ao_clicar(None),
                ).props("flat no-caps unelevated").classes(f"todas {cls}")

            for marca in marcas:
                cls = "ativo" if marca_atual == marca else ""
                with ui.element("li"):
                    ui.button(
                        marca,
                        on_click=lambda m=marca: ao_clicar(m),
                    ).props("flat no-caps unelevated").classes(cls)


def dialog_interesse(v: Veiculo) -> None:
    slug = get_tenant_slug()
    with ui.dialog() as dlg, ui.card().classes("modal-interesse form-site"):
        ui.html(
            f'<div class="modal-interesse-titulo">Tenho interesse</div>'
            f'<p style="margin-bottom:12px;color:#666;font-size:14px">'
            f"{v.marca} {v.modelo} — {formatar_preco(v.preco)}</p>"
        )
        nome = input_texto("Seu nome").classes("w-full")
        telefone = input_numero("WhatsApp / Telefone").classes("w-full")
        email = input_email("E-mail (opcional)").classes("w-full")

        def enviar() -> None:
            if not nome.value or not telefone.value:
                ui.notify("Preencha nome e telefone.", type="warning")
                return
            if slug:
                ligar_tenant(slug)
            salvar_lead({
                "nome": nome.value.strip(),
                "telefone": telefone.value.strip(),
                "email": email.value or "",
                "origem": "site",
                "status": "novo",
                "veiculo_id": v.id,
                "observacoes": f"Interesse via site — {v.marca} {v.modelo}",
            })
            dlg.close()
            ui.notify("Recebemos seu contato! Em breve retornaremos.", type="positive")

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
            ui.button("Enviar", on_click=enviar).classes("btn btn-preto").props(
                "unelevated no-caps"
            )

    dlg.open()


def ir_detalhe_veiculo(v: Veiculo) -> None:
    ui.navigate.to(site_url(f"/veiculo/{v.id}"))


def card_destaque(v: Veiculo) -> None:
    loja = _loja()
    foto = (getattr(v, "imagem_destaque", None) or "").strip() or v.imagem
    with ui.element("div").classes("card-destaque"):
        with ui.element("div").classes("foto").on("click", lambda: ir_detalhe_veiculo(v)):
            ui.image(foto).props("no-spinner")
        with ui.element("div").classes("info"):
            ui.html(f"<h3>{v.marca} {v.modelo}</h3>")
            ui.html(
                f'<div class="specs-destaque">'
                f"<span>📅 {v.ano}</span>"
                f"<span>🛣 {formatar_km(v.km)}</span>"
                f"<span>⛽ {v.combustivel}</span>"
                f"<span>⚙ {v.cambio}</span>"
                f"</div>"
            )
            ui.html(f'<div class="preco-destaque">{formatar_preco(v.preco)}</div>')
            with ui.element("div").classes("botoes-destaque"):
                ui.button(
                    "VER DETALHES",
                    on_click=lambda: ir_detalhe_veiculo(v),
                ).classes("btn btn-preto").props("no-caps unelevated")
                ui.button(
                    "TENHO INTERESSE",
                    on_click=lambda: dialog_interesse(v),
                ).classes("btn btn-contorno").props("no-caps flat")
            ui.html(
                f'<div class="contato-destaque">{bloco_empresa_html(loja)}</div>'
            )


def card_veiculo(v: Veiculo) -> None:
    with ui.element("div").classes("card-veiculo"):
        with ui.element("div").classes("foto").on("click", lambda: ir_detalhe_veiculo(v)):
            ui.image(v.imagem).props("no-spinner")
        with ui.element("div").classes("corpo"):
            ui.html(f"<h4>{v.marca} {v.modelo} {v.ano}</h4>")
            ui.html(f'<div class="preco">{formatar_preco(v.preco)}</div>')
            ui.html(
                f'<div class="specs">{v.cambio}, {v.combustivel}, '
                f"{formatar_km(v.km)}</div>"
            )
            with ui.element("div").classes("botoes-card"):
                ui.button(
                    "VER DETALHES",
                    on_click=lambda: ir_detalhe_veiculo(v),
                ).classes("btn btn-preto").props(
                    "no-caps unelevated dense"
                )
                ui.button(
                    "TENHO INTERESSE",
                    on_click=lambda: dialog_interesse(v),
                ).classes("btn btn-contorno").props("no-caps flat dense")


def secao_sobre() -> None:
    loja = _loja()
    with ui.element("section").classes("secao-sobre"):
        ui.html(f"<h2>Sobre a {loja['nome']}, {loja['cidade']}</h2>")
        ui.html(f"<p>{loja.get('sobre', '')}</p>")
        extras = []
        if loja.get("razao_social"):
            extras.append(f"<strong>Razão social:</strong> {loja['razao_social']}")
        if loja.get("cnpj"):
            extras.append(f"<strong>CNPJ:</strong> {loja['cnpj']}")
        end = endereco_linha(loja)
        if end:
            extras.append(f"<strong>Endereço:</strong> {end}")
        if extras:
            ui.html(
                f'<div class="dados-empresa-sobre">{"<br>".join(extras)}</div>'
            )
        def _ir_empresa() -> None:
            ir = getattr(ui.context.client, "site_ir", None)
            if callable(ir):
                ir("/empresa")
            else:
                ui.navigate.to(site_url("/empresa"))

        ui.button(
            "Conheça nossa história →",
            on_click=_ir_empresa,
        ).props("flat no-caps").classes("secao-sobre-link")


def _whatsapp_numero(loja: dict) -> str:
    return (
        loja.get("whatsapp", "")
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "")
        .replace("-", "")
    )


def botao_avaliacao_flutuante(avaliacao_spa=None) -> None:
    """CTA de avaliação no canto inferior esquerdo (aparece ao rolar para baixo)."""
    if avaliacao_spa is not None:
        btn = ui.element("div").classes("site-btn-avaliacao")
        btn.style("cursor:pointer")
        btn.on("click", lambda: avaliacao_spa("/avaliacao"))
        with btn:
            ui.html(
                '<span class="material-icons">directions_car</span>'
                "<span>Avalie seu usado</span>"
            )
    else:
        with ui.link(target=site_url("/avaliacao")).classes("site-btn-avaliacao"):
            ui.html(
                '<span class="material-icons">directions_car</span>'
                "<span>Avalie seu usado</span>"
            )
    ui.add_body_html(
        """
<script>
(function () {
  if (window.__siteBtnAvaliacaoBound) return;
  window.__siteBtnAvaliacaoBound = true;
  var lastY = window.scrollY || 0;
  function atualizar() {
    var el = document.querySelector('.site-btn-avaliacao');
    if (!el) return;
    var y = window.scrollY || 0;
    if (y < 100) {
      el.classList.remove('visivel');
    } else if (y > lastY + 4) {
      el.classList.add('visivel');
    } else if (y < lastY - 4) {
      el.classList.remove('visivel');
    }
    lastY = y;
  }
  window.addEventListener('scroll', atualizar, { passive: true });
  atualizar();
})();
</script>
"""
    )


def barra_lateral_site(avaliacao_spa=None) -> None:
    """Redes sociais fixas à direita + chat de atendimento + avaliação."""
    loja = _loja()
    wa = _whatsapp_numero(loja)
    fb = (loja.get("facebook") or "").strip()
    ig = (loja.get("instagram") or "").strip()
    email = (loja.get("email") or "").strip()

    toggle_chat = montar_painel_chat(loja, wa, email)

    redes: list[tuple[str, str, str]] = []
    if fb and fb not in {"#", "http://", "https://"}:
        redes.append(("f", fb, "fb"))
    if ig and ig not in {"#", "http://", "https://"}:
        redes.append(("in", ig, "ig"))
    if wa:
        redes.append(("w", f"https://wa.me/55{wa}", "wa"))
    if email:
        redes.append(("@", f"mailto:{email}", "em"))

    if redes:
        with ui.element("div").classes("site-redes-fixas"):
            for rotulo, href, cls in redes:
                props = "target=_blank" if not href.startswith("mailto:") else ""
                ui.link(rotulo, href).classes(cls).props(props)

    with ui.button(on_click=toggle_chat).classes("site-btn-atendimento").props(
        "flat unelevated no-caps"
    ).tooltip("Atendimento online"):
        ui.html('<span class="material-icons">support_agent</span>')

    botao_avaliacao_flutuante(avaliacao_spa)


def encerrar_pagina_site(avaliacao_spa=None) -> None:
    rodape()
    # Fora do fluxo do layout (evita stretch virar “faixa” na tela)
    barra_lateral_site(avaliacao_spa)


def rodape() -> None:
    loja = _loja()
    with ui.element("footer").classes("rodape"):
        with ui.element("div").classes("conteudo"):
            with ui.element("div").classes("rodape-info"):
                ui.html(bloco_empresa_html(loja))
            with ui.element("div").classes("logo-rodape"):
                ui.html(_logo_html(loja))
            with ui.element("div").classes("rodape-info direita"):
                links = []
                if loja.get("email"):
                    links.append(loja["email"])
                if loja.get("facebook"):
                    links.append(f'<a href="{loja["facebook"]}" target="_blank">Facebook</a>')
                if loja.get("instagram"):
                    links.append(f'<a href="{loja["instagram"]}" target="_blank">Instagram</a>')
                if loja.get("whatsapp"):
                    links.append(f"WhatsApp: {loja['whatsapp']}")
                ui.html(
                    f"<strong>Contato</strong><br>{'<br>'.join(links) if links else '—'}"
                )
        with ui.element("div").classes("rodape-base"):
            cnpj = f" · CNPJ {loja['cnpj']}" if loja.get("cnpj") else ""
            ui.html(
                f"© 2026 {loja['nome']}{cnpj} — Todos os direitos reservados."
                f'<span class="rodape-legal">'
                f'<a href="{site_url("/privacidade")}">Política de Privacidade</a>'
                f'<a href="{site_url("/lgpd")}">LGPD</a></span>'
            )
