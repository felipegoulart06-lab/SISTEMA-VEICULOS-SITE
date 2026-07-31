from nicegui import ui

from loja.componentes import (
    barra_social,
    cabecalho,
    dialog_interesse,
    injetar_tema,
    rodape,
)
from loja.repositorio import (
    FiltrosEstoque,
    ITENS_POR_PAGINA,
    Veiculo,
    config_como_dict,
    facetas_estoque,
    filtrar_estoque,
    formatar_km,
    formatar_preco,
)
from loja.tenant_ctx import site_url
from loja.whitelabel import bloco_empresa_html


ORDENACOES = {
    "recente": "Mais recente",
    "menor_preco": "Menor preço",
    "maior_preco": "Maior preço",
    "ano_desc": "Ano mais novo",
}


def montar_pagina_estoque(filtros: FiltrosEstoque, refresh_ref: dict) -> None:
    @ui.refreshable
    def conteudo() -> None:
        veiculos, total = filtrar_estoque(filtros)
        facets = facetas_estoque()
        total_paginas = max(1, (total + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)
        loja = config_como_dict()

        with ui.element("div").classes("estoque-layout"):
            _sidebar_filtros(filtros, facets, conteudo.refresh)

            with ui.element("div").classes("estoque-principal"):
                _cabecalho_lista(filtros, total, conteudo.refresh)

                if not veiculos:
                    ui.html(
                        '<p class="estoque-vazio">Nenhum veículo encontrado '
                        "com os filtros selecionados.</p>"
                    )
                else:
                    with ui.element("div").classes("estoque-lista"):
                        for v in veiculos:
                            _card_lista(v, loja)

                _paginacao(filtros, filtros.pagina, total_paginas, conteudo.refresh)

    refresh_ref["refresh"] = conteudo.refresh

    with ui.element("div").classes("pagina-estoque"):
        conteudo()


def _sidebar_filtros(f: FiltrosEstoque, facets: dict, refresh) -> None:
    with ui.element("aside").classes("filtro-sidebar"):
        ui.html("<h2 class=\"filtro-titulo\">Filtrar Resultado</h2>")

        if f.marca or f.ano or f.combustivel or f.cor or f.tipo:
            ui.button(
                "Limpar filtros",
                on_click=lambda: (_limpar_filtros(f), refresh()),
            ).props("flat dense no-caps").classes("filtro-limpar")

        _grupo_filtro("TIPO", facets["tipo"], "tipo", f, refresh)
        _grupo_filtro("MARCA", facets["marca"], "marca", f, refresh)
        _grupo_filtro("ANO", facets["ano"], "ano", f, refresh, fmt=lambda x: str(x))
        _grupo_filtro("COMBUSTÍVEL", facets["combustivel"], "combustivel", f, refresh)
        _grupo_filtro("COR", facets["cor"], "cor", f, refresh)


def _grupo_filtro(titulo, itens, campo, f: FiltrosEstoque, refresh, fmt=None) -> None:
    if not itens:
        return
    fmt = fmt or (lambda x: str(x))
    ui.html(f'<h3 class="filtro-grupo">{titulo}</h3>')
    with ui.element("ul").classes("filtro-lista"):
        for valor, qtd in itens:
            ativo = getattr(f, campo) == valor
            cls = "ativo" if ativo else ""
            label = fmt(valor)
            ui.button(
                f"{label} ({qtd})",
                on_click=lambda v=valor, c=campo: (_toggle_filtro(f, c, v), refresh()),
            ).props("flat dense no-caps").classes(f"filtro-item {cls}")


def _toggle_filtro(f: FiltrosEstoque, campo: str, valor) -> None:
    atual = getattr(f, campo)
    setattr(f, campo, None if atual == valor else valor)
    f.pagina = 1


def _limpar_filtros(f: FiltrosEstoque) -> None:
    f.marca = f.ano = f.combustivel = f.cor = f.tipo = None
    f.pagina = 1


def _cabecalho_lista(f: FiltrosEstoque, total: int, refresh) -> None:
    with ui.element("div").classes("estoque-toolbar"):
        with ui.element("div").classes("estoque-toolbar-esq"):
            ui.html(
                f'<h1 class="estoque-heading">TODOS OS CARROS DO ESTOQUE</h1>'
                f'<span class="estoque-count">{total} veículo(s)</span>'
            )
            with ui.element("div").classes("estoque-acoes"):
                ui.button("Imprimir lista", on_click=lambda: ui.run_javascript(
                    "window.print()"
                )).props("flat dense no-caps").classes("estoque-acao-btn")
                ui.button("Compartilhar", on_click=lambda: ui.run_javascript(
                    "navigator.clipboard.writeText(window.location.href)"
                )).props("flat dense no-caps").classes("estoque-acao-btn")
                loja = config_como_dict()
                wa = loja.get("whatsapp", "").replace("(", "").replace(")", "").replace(" ", "")
                ui.link(
                    "Orçamento",
                    f"https://wa.me/55{wa}?text=Olá, gostaria de um orçamento",
                ).classes("estoque-acao-btn").props("target=_blank")

        opts = {k: v for k, v in ORDENACOES.items()}
        sel = ui.select(
            opts,
            value=f.ordenar,
            label="Ordenar",
        ).props("dense outlined").classes("estoque-ordenar")

        def mudar_ordem(e):
            f.ordenar = sel.value
            f.pagina = 1
            refresh()

        sel.on("update:model-value", mudar_ordem)


def _card_lista(v: Veiculo, loja: dict) -> None:
    contato = bloco_empresa_html(loja).replace("<br>", " · ").replace("<strong>", "").replace("</strong>", "")
    info = v.info_extra or "Consulte condições com nossa equipe"
    badge = v.badge or "PRONTA ENTREGA"

    with ui.element("div").classes("estoque-card"):
        with ui.element("div").classes("estoque-card-foto").on(
            "click", lambda: ui.navigate.to(site_url(f"/veiculo/{v.id}"))
        ):
            ui.image(v.imagem).props("no-spinner")
        with ui.element("div").classes("estoque-card-corpo"):
            ui.html(
                f'<h3 class="estoque-card-titulo">'
                f'<a href="{site_url("/veiculo/" + str(v.id))}">{v.ano} {v.marca} {v.modelo}</a></h3>'
            )
            ui.html(f'<div class="estoque-card-preco">{formatar_preco(v.preco)}</div>')
            ui.html(
                f'<div class="estoque-card-specs">'
                f"<span>📅 {v.ano}</span>"
                f"<span>🛣 {formatar_km(v.km)}</span>"
                f"<span>⛽ {v.combustivel}</span>"
                f"<span>⚙ {v.cambio}</span>"
                f"</div>"
            )
            ui.html(f'<p class="estoque-card-info">{info}</p>')
        with ui.element("div").classes("estoque-card-lateral"):
            ui.html(f'<span class="estoque-badge">{badge}</span>')
            ui.button(
                "VER DETALHES",
                on_click=lambda: ui.navigate.to(site_url(f"/veiculo/{v.id}")),
            ).classes("btn btn-contorno estoque-btn-detalhes").props("no-caps flat dense")
            ui.button(
                "TENHO INTERESSE",
                on_click=lambda: dialog_interesse(v),
            ).classes("btn btn-preto estoque-btn-interesse").props("no-caps unelevated")
            ui.html(f'<p class="estoque-card-loja">{contato}</p>')


def _paginacao(f: FiltrosEstoque, pagina: int, total_paginas: int, refresh) -> None:
    if total_paginas <= 1:
        return
    with ui.element("div").classes("estoque-paginacao"):
        for p in range(1, total_paginas + 1):
            cls = "ativo" if p == pagina else ""
            ui.button(
                str(p),
                on_click=lambda pg=p: (setattr(f, "pagina", pg), refresh()),
            ).props("flat dense").classes(f"pag-btn {cls}")
