from urllib.parse import quote

from nicegui import ui

from loja.crm_repo import listar_depoimentos
from loja.institucional import metricas_institucionais, obter_institucional
from loja.repositorio import config_como_dict, listar_marcas
from loja.tenant_ctx import site_url
from loja.whitelabel import bloco_empresa_html


def montar_pagina_empresa() -> None:
    loja = config_como_dict()
    inst = obter_institucional()
    marcas = listar_marcas()
    deps = listar_depoimentos(apenas_ativos=True)
    metricas = metricas_institucionais()

    titulo = inst.get("titulo") or f"CONHEÇA A {loja.get('nome', 'NOSSA LOJA').upper()}"
    subtitulo = inst.get("subtitulo") or "Tradição, confiança e o carro certo para você"
    intro = inst.get("intro") or loja.get("sobre") or ""
    imagem = inst.get("imagem_url") or loja.get("banner_url") or (
        "https://images.unsplash.com/photo-1555215695-3004980ad54e?w=1400&q=80"
    )

    ui.html(
        f'<div class="pagina-topo-institucional">'
        f"<h1>{_esc(titulo)}</h1>"
        f'<p class="pagina-topo-sub">{_esc(subtitulo)}</p>'
        f"</div>"
    )

    if intro:
        with ui.element("section").classes("empresa-intro"):
            ui.html(
                f'<div class="empresa-texto-principal"><p>{_esc(intro)}</p></div>'
            )

    with ui.element("div").classes("empresa-banner-full"):
        ui.image(imagem).props("no-spinner")

    with ui.element("section").classes("empresa-valores"):
        ui.html(
            f'<h2 class="secao-titulo-centro">'
            f'{_esc(inst.get("pilares_titulo") or "NOSSOS PILARES")}</h2>'
        )
        with ui.element("div").classes("empresa-cards-grid"):
            for p in (inst.get("pilares") or [])[:3]:
                _card_valor(
                    p.get("icone") or "star",
                    p.get("titulo") or "",
                    p.get("texto") or "",
                )

    with ui.element("section").classes("empresa-numeros"):
        with ui.element("div").classes("empresa-numeros-grid"):
            for valor, rotulo in metricas:
                _numero(valor, rotulo)

    with ui.element("section").classes("empresa-missao"):
        with ui.element("div").classes("empresa-duas-colunas"):
            with ui.element("div").classes("empresa-bloco"):
                ui.html(f"<h3>{_esc(inst.get('missao_titulo') or 'Missão')}</h3>")
                ui.html(f"<p>{_esc(inst.get('missao_texto') or '')}</p>")
            with ui.element("div").classes("empresa-bloco"):
                ui.html(f"<h3>{_esc(inst.get('visao_titulo') or 'Visão')}</h3>")
                ui.html(f"<p>{_esc(inst.get('visao_texto') or '')}</p>")

    with ui.element("section").classes("empresa-marcas"):
        ui.html('<h2 class="secao-titulo-centro">MARCAS QUE TRABALHAMOS</h2>')
        if marcas:
            with ui.element("div").classes("empresa-tags-marcas"):
                for m in marcas:
                    ui.link(
                        m, f"{site_url('/estoque')}?marca={quote(m)}"
                    ).classes("empresa-tag-marca")
        else:
            ui.html(
                '<p class="empresa-marcas-vazio">'
                "As marcas do seu estoque aparecerão automaticamente aqui."
                "</p>"
            )

    with ui.element("section").classes("empresa-depoimentos"):
        ui.html('<h2 class="secao-titulo-centro">O QUE DIZEM NOSSOS CLIENTES</h2>')
        if deps:
            with ui.element("div").classes("depoimentos-grade"):
                for d in deps:
                    cidade = (getattr(d, "cidade", None) or "").strip()
                    tag = (
                        f'<span class="depoimento-cidade">{_esc(cidade)}</span>'
                        if cidade
                        else ""
                    )
                    ui.html(
                        f'<blockquote class="depoimento-card">'
                        f"<p>“{_esc(d.texto)}”</p>"
                        f"<footer>{'★' * (d.nota or 5)} — {_esc(d.nome)}"
                        f"{tag}</footer>"
                        f"</blockquote>"
                    )
        else:
            ui.html(
                '<p class="empresa-marcas-vazio">'
                "Depoimentos publicados no ERP aparecerão nesta seção."
                "</p>"
            )

    with ui.element("section").classes("empresa-dados"):
        ui.html('<h2 class="secao-titulo-centro">DADOS DA EMPRESA</h2>')
        ui.html(f'<div class="empresa-dados-box">{bloco_empresa_html(loja)}</div>')

    with ui.element("section").classes("empresa-cta-final"):
        ui.html("<h3>Pronto para encontrar seu próximo carro?</h3>")
        ui.html("<p>Explore nosso estoque ou fale com nossa equipe agora mesmo.</p>")
        with ui.element("div").classes("empresa-cta-botoes"):
            ui.link("Ver estoque", site_url("/estoque")).classes("btn btn-preto")
            ui.link("Fale conosco", site_url("/contato")).classes("btn btn-contorno")


def _esc(texto: str) -> str:
    return (
        (texto or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _card_valor(icone: str, titulo: str, texto: str) -> None:
    ui.html(
        f'<article class="empresa-card-valor">'
        f'<span class="material-icons">{_esc(icone)}</span>'
        f"<h3>{_esc(titulo)}</h3><p>{_esc(texto)}</p></article>"
    )


def _numero(valor: str, rotulo: str) -> None:
    ui.html(
        f'<div class="empresa-numero-item">'
        f"<strong>{_esc(valor)}</strong><span>{_esc(rotulo)}</span></div>"
    )
