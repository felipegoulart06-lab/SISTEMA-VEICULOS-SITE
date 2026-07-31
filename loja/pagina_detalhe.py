from urllib.parse import quote

from nicegui import ui

from loja.tenant_ctx import site_url
from loja.componentes import dialog_interesse
from loja.models import VeiculoDB
from loja.repositorio import (
    _to_veiculo,
    config_como_dict,
    formatar_km,
    formatar_preco,
    incrementar_visualizacoes,
    listar_marcas,
    obter_veiculo_publico,
)
from loja.whitelabel import bloco_empresa_html, endereco_linha


def montar_pagina_detalhe(veiculo_id: int) -> bool:
    v = obter_veiculo_publico(veiculo_id)
    if v is None:
        return False

    incrementar_visualizacoes(veiculo_id)
    loja = config_como_dict()
    fotos = _fotos_galeria(v)
    galeria = {"idx": 0}

    def ir_foto(delta: int) -> None:
        galeria["idx"] = (galeria["idx"] + delta) % len(fotos)
        galeria_principal.refresh()
        galeria_thumbs.refresh()

    def ir_foto_idx(idx: int) -> None:
        galeria["idx"] = idx
        galeria_principal.refresh()
        galeria_thumbs.refresh()

    titulo = f"{v.marca} {v.modelo} {v.ano}"
    endereco = endereco_linha(loja)
    maps_href = f"https://www.google.com/maps/search/?api=1&query={quote(endereco)}"
    wa_num = loja.get("whatsapp", "").replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
    wa_texto = quote(f"Olá! Tenho interesse no {titulo} — {formatar_preco(v.preco)}")
    fin_url = (
        f"{site_url('/financiamento')}?marca={quote(v.marca)}&modelo={quote(v.modelo)}"
        f"&ano={v.ano}&cor={quote(v.cor or '')}&valor={v.preco}&veiculo_id={v.id}"
    )
    mail_assunto = quote(f"Interesse: {titulo}")
    mail_corpo = quote(
        f"Olá,\n\nGostaria de mais informações sobre:\n{titulo}\n"
        f"Preço: {formatar_preco(v.preco)}\n"
    )

    @ui.refreshable
    def galeria_principal() -> None:
        idx = galeria["idx"]
        with ui.element("div").classes("detalhe-galeria-principal"):
            if len(fotos) > 1:
                ui.button("‹", on_click=lambda: ir_foto(-1)).classes(
                    "detalhe-galeria-nav nav-esq"
                ).props("flat round dense")
            ui.image(fotos[idx]).props("no-spinner").classes("detalhe-galeria-img")
            if len(fotos) > 1:
                ui.button("›", on_click=lambda: ir_foto(1)).classes(
                    "detalhe-galeria-nav nav-dir"
                ).props("flat round dense")
            ui.html(
                f'<span class="detalhe-galeria-contador">{idx + 1} de {len(fotos)}</span>'
            )

    @ui.refreshable
    def galeria_thumbs() -> None:
        with ui.element("div").classes("detalhe-galeria-thumbs"):
            for i, url in enumerate(fotos):
                cls = "ativo" if i == galeria["idx"] else ""
                with ui.element("button").classes(f"detalhe-thumb {cls}").on(
                    "click", lambda _, idx=i: ir_foto_idx(idx)
                ):
                    ui.image(url).props("no-spinner")

    with ui.element("div").classes("pagina-detalhe"):
        _barra_acoes(loja, mail_assunto, mail_corpo)

        with ui.element("div").classes("detalhe-conteudo"):
            with ui.element("div").classes("detalhe-grid-topo"):
                with ui.element("div").classes("detalhe-col-galeria"):
                    galeria_principal()
                    galeria_thumbs()

                with ui.element("div").classes("detalhe-col-dados"):
                    ui.html('<h2 class="detalhe-secao-titulo">Dados do veículo</h2>')
                    _lista_dados(v)

                with ui.element("div").classes("detalhe-col-compra"):
                    ui.html(f'<div class="detalhe-preco">{formatar_preco(v.preco)}</div>')
                    if v.badge:
                        ui.html(f'<span class="detalhe-badge">{v.badge}</span>')
                    veiculo_pub = _to_veiculo(v)
                    with ui.element("div").classes("detalhe-cta-principal"):
                        ui.button(
                            "SOLICITAR PROPOSTA",
                            on_click=lambda: dialog_interesse(veiculo_pub),
                        ).classes("btn btn-preto detalhe-btn-cta").props("no-caps unelevated")
                        ui.link(
                            "FINANCIAMENTO",
                            fin_url,
                        ).classes("btn btn-contorno detalhe-btn-cta")
                    ui.html(
                        f'<div class="detalhe-loja-box">{bloco_empresa_html(loja)}</div>'
                    )
                    with ui.element("div").classes("detalhe-cta-secundario"):
                        ui.link("Ver mapa", maps_href).classes("btn btn-contorno flex-1").props(
                            "target=_blank"
                        )
                        ui.link("Ver estoque", site_url("/estoque")).classes("btn btn-contorno flex-1")

            _secao_detalhes(v, loja, wa_num, wa_texto)
            _secao_opcionais(v)
            _secao_mais_pesquisados()

        _flutuantes(loja, wa_num, titulo, fin_url)

    return True


def _fotos_galeria(v: VeiculoDB) -> list[str]:
    urls: list[str] = []
    if v.imagem and v.imagem.strip():
        urls.append(v.imagem.strip())
    extras = (getattr(v, "fotos_url", None) or "").replace(",", "\n")
    for linha in extras.split("\n"):
        u = linha.strip()
        if u and u not in urls:
            urls.append(u)
    if not urls:
        urls.append(
            "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=800&q=80"
        )
    return urls


def _barra_acoes(loja: dict, assunto: str, corpo: str) -> None:
    with ui.element("div").classes("detalhe-barra-acoes"):
        with ui.element("div").classes("detalhe-barra-conteudo"):
            ui.button("← Voltar", on_click=lambda: ui.navigate.to(site_url("/estoque"))).props(
                "flat dense no-caps"
            ).classes("detalhe-acao-btn")
            ui.button(
                "Imprimir página",
                on_click=lambda: ui.run_javascript("window.print()"),
            ).props("flat dense no-caps").classes("detalhe-acao-btn")
            ui.button(
                "Compartilhar",
                on_click=lambda: ui.run_javascript(
                    "navigator.clipboard.writeText(window.location.href);"
                    "alert('Link copiado!');"
                ),
            ).props("flat dense no-caps").classes("detalhe-acao-btn")
            ui.link(
                "Enviar por e-mail",
                f"mailto:{loja.get('email', '')}?subject={assunto}&body={corpo}",
            ).classes("detalhe-acao-btn")


def _lista_dados(v: VeiculoDB) -> None:
    itens = [
        ("directions_car", "Marca", v.marca),
        ("drive_eta", "Modelo", v.modelo),
        ("event", "Ano", str(v.ano)),
        ("speed", "Quilometragem", formatar_km(v.km)),
        ("local_gas_station", "Combustível", v.combustivel),
        ("settings", "Câmbio", v.cambio),
        ("palette", "Cor", v.cor or "—"),
        ("category", "Tipo", v.tipo or "AUTOMÓVEL"),
    ]
    if getattr(v, "fipe", 0) and v.fipe > 0:
        itens.append(("price_check", "Referência FIPE", formatar_preco(v.fipe)))

    with ui.element("ul").classes("detalhe-lista-dados"):
        for icone, rotulo, valor in itens:
            ui.html(
                f'<li class="detalhe-dado-item">'
                f'<span class="material-icons detalhe-dado-ico">{icone}</span>'
                f'<div class="detalhe-dado-texto">'
                f"<strong>{rotulo}</strong><span>{valor}</span></div></li>"
            )


def _secao_detalhes(v: VeiculoDB, loja: dict, wa_num: str, wa_texto: str) -> None:
    descricao = (v.descricao or "").strip()
    historico = (getattr(v, "historico_texto", None) or "").strip()
    info = (v.info_extra or "").strip()

    with ui.element("section").classes("detalhe-secao-full"):
        ui.html('<h2 class="detalhe-secao-titulo">Detalhes</h2>')
        with ui.element("div").classes("detalhe-texto-bloco"):
            if descricao:
                ui.html(f"<p><strong>Descrição</strong></p><p>{descricao}</p>")
            else:
                ui.html(
                    f"<p><strong>Descrição</strong></p>"
                    f"<p>{v.marca} {v.modelo} {v.ano} — {v.combustivel}, "
                    f"{v.cambio}, {formatar_km(v.km)}. Veículo disponível "
                    f"para pronta entrega. Entre em contato para agendar visita.</p>"
                )

            ui.html(
                "<p><strong>Características</strong></p>"
                "<ul class='detalhe-lista-texto'>"
                f"<li>Motor / combustível: {v.combustivel}</li>"
                f"<li>Câmbio: {v.cambio}</li>"
                f"<li>Cor: {v.cor or '—'}</li>"
                f"<li>Tipo: {v.tipo or 'AUTOMÓVEL'}</li>"
                f"<li>Ano: {v.ano}</li>"
                f"<li>Quilometragem: {formatar_km(v.km)}</li>"
                "</ul>"
            )

            if historico:
                ui.html(f"<p><strong>Histórico</strong></p><p>{historico}</p>")
            if info:
                ui.html(f"<p><strong>Informações adicionais</strong></p><p>{info}</p>")

            ui.html(
                f"<p><strong>Preço</strong></p>"
                f"<p>{formatar_preco(v.preco)} — consulte condições de pagamento "
                f"e financiamento.</p>"
                f"<p><strong>Contato</strong></p>"
                f"<p>{loja.get('telefone', '')} · WhatsApp {loja.get('whatsapp', '')} · "
                f"<a href='https://wa.me/55{wa_num}?text={wa_texto}' target='_blank'>"
                f"Falar no WhatsApp</a></p>"
            )


def _secao_opcionais(v: VeiculoDB) -> None:
    texto = (getattr(v, "opcionais", None) or "").strip()
    if not texto:
        texto = (
            "Ar-condicionado, direção hidráulica, vidros elétricos, "
            "travas elétricas, airbag, freios ABS."
        )

    with ui.element("section").classes("detalhe-secao-full detalhe-opcionais"):
        ui.html('<h2 class="detalhe-secao-titulo">Opcionais</h2>')
        itens = [i.strip() for i in texto.replace(";", ",").split(",") if i.strip()]
        if len(itens) > 1:
            ui.html(
                "<ul class='detalhe-opcionais-lista'>"
                + "".join(f"<li>{item}</li>" for item in itens)
                + "</ul>"
            )
        else:
            ui.html(f"<p class='detalhe-opcionais-texto'>{texto}</p>")


def _secao_mais_pesquisados() -> None:
    marcas = listar_marcas()[:10]
    if not marcas:
        return
    with ui.element("section").classes("detalhe-mais-pesquisados"):
        ui.html("<h3>Mais pesquisados</h3>")
        with ui.element("div").classes("detalhe-tags"):
            for marca in marcas:
                ui.link(marca, f"{site_url('/estoque')}?marca={quote(marca)}").classes("detalhe-tag")


def _flutuantes(loja: dict, wa_num: str, titulo: str, fin_url: str = "/financiamento") -> None:
    ui.link(
        "Simular financiamento",
        fin_url,
    ).classes("detalhe-financiamento-flutuante")
