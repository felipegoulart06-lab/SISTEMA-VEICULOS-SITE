"""Editor da página institucional (EMPRESA) no ERP."""

from __future__ import annotations

from nicegui import events, ui

from loja.admin.layout import ajuda
from loja.institucional import (
    ICONES_PILARES,
    metricas_institucionais,
    obter_institucional,
    salvar_institucional,
    salvar_upload_institucional,
)
from loja.repositorio import listar_marcas
from loja.tenant_ctx import site_url


def _navegar_erp(href: str) -> None:
    ir = getattr(ui.context.client, "erp_ir", None)
    if callable(ir):
        ir(href)
    else:
        ui.navigate.to(href)


def pagina_institucional() -> None:
    dados = obter_institucional()
    metricas = metricas_institucionais()
    marcas = listar_marcas()

    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Editar institucional</h2>"
        "<p>Conteúdo da página EMPRESA no site público</p></div></div>"
    )
    ajuda(
        "Títulos, pilares, missão e visão são editáveis. "
        "Métricas, marcas e dados de contato vêm automaticamente do ERP. "
        "Depoimentos ficam em Marketing → Depoimentos. "
        "O bloco final de CTA é padrão para todos os sites."
    )

    with ui.element("div").classes("erp-toolbar"):
        ui.button(
            "← Voltar ao Site",
            on_click=lambda: _navegar_erp("/admin/site"),
        ).props("flat no-caps")
        ui.link("Ver página EMPRESA", site_url("/empresa")).props(
            "target=_blank"
        ).classes("erp-link-externo")

    with ui.element("div").classes("erp-form-page erp-painel"):
        ui.label("Topo da página").classes("erp-secao-titulo")
        titulo = ui.input("Título H1", value=dados.get("titulo", "")).props(
            "outlined dense"
        ).classes("w-full")
        subtitulo = ui.input(
            "Subtítulo", value=dados.get("subtitulo", ""),
        ).props("outlined dense").classes("w-full")
        intro = ui.textarea(
            "Texto introdutório (H3 / parágrafo)",
            value=dados.get("intro", ""),
        ).props("outlined dense").classes("w-full")

        ui.label("Imagem institucional").classes("erp-secao-titulo")
        ui.label(
            "A imagem ocupa a largura total e altura fixa do layout "
            "(object-fit: cover), mesmo com outro tamanho de arquivo."
        ).classes("text-caption text-grey-7")
        imagem_url = {"valor": dados.get("imagem_url", "")}
        preview = ui.image(imagem_url["valor"] or "https://placehold.co/1200x420").classes(
            "erp-preview-institucional"
        )
        url_campo = ui.input(
            "URL da imagem (ou envie um arquivo abaixo)",
            value=imagem_url["valor"],
        ).props("outlined dense").classes("w-full")

        def _atualizar_preview(url: str) -> None:
            imagem_url["valor"] = url
            url_campo.value = url
            preview.set_source(url or "https://placehold.co/1200x420")

        def on_url_change(e) -> None:
            _atualizar_preview((e.value or "").strip())

        url_campo.on("update:model-value", on_url_change)

        async def on_upload(e: events.UploadEventArguments) -> None:
            try:
                raw = e.content.read() if hasattr(e.content, "read") else e.content
                if isinstance(raw, str):
                    raw = raw.encode("utf-8")
                url = salvar_upload_institucional(e.name or "imagem.jpg", raw)
                _atualizar_preview(url)
                ui.notify("Imagem enviada.", type="positive")
            except Exception as err:
                ui.notify(f"Falha no upload: {err}", type="negative")

        ui.upload(
            on_upload=on_upload,
            auto_upload=True,
            label="Enviar imagem",
        ).props("accept=.jpg,.jpeg,.png,.webp,.gif flat bordered").classes(
            "w-full q-mb-md"
        )

        ui.label("Pilares").classes("erp-secao-titulo")
        pilares_titulo = ui.input(
            "Título da seção (H2)",
            value=dados.get("pilares_titulo", "NOSSOS PILARES"),
        ).props("outlined dense").classes("w-full")

        pilares_campos: list[dict] = []
        for i, p in enumerate(dados.get("pilares") or []):
            with ui.element("div").classes("erp-subpainel"):
                ui.label(f"Container {i + 1}").classes("text-weight-bold")
                icone = ui.select(
                    {k: k for k in ICONES_PILARES},
                    label="Ícone",
                    value=p.get("icone") if p.get("icone") in ICONES_PILARES else "star",
                ).props("outlined dense").classes("w-full")
                tit = ui.input(
                    "Título", value=p.get("titulo", ""),
                ).props("outlined dense").classes("w-full")
                txt = ui.textarea(
                    "Texto", value=p.get("texto", ""),
                ).props("outlined dense").classes("w-full")
                pilares_campos.append({"icone": icone, "titulo": tit, "texto": txt})

        ui.label("Métricas (automáticas)").classes("erp-secao-titulo")
        with ui.element("div").classes("erp-metricas-readonly"):
            for valor, rotulo in metricas:
                ui.html(
                    f'<div class="erp-metrica-chip"><strong>{valor}</strong>'
                    f"<span>{rotulo}</span></div>"
                )
        ui.label(
            "Esses números vêm do ERP (clientes, anos desde a criação da "
            "empresa e veículos disponíveis). Não são editáveis aqui."
        ).classes("text-caption text-grey-7")

        ui.label("Missão e Visão").classes("erp-secao-titulo")
        with ui.element("div").classes("erp-form-grid"):
            missao_titulo = ui.input(
                "Container 1 — título",
                value=dados.get("missao_titulo", "Missão"),
            ).props("outlined dense")
            visao_titulo = ui.input(
                "Container 2 — título",
                value=dados.get("visao_titulo", "Visão"),
            ).props("outlined dense")
            missao_texto = ui.textarea(
                "Container 1 — texto",
                value=dados.get("missao_texto", ""),
            ).props("outlined dense").classes("erp-form-full")
            visao_texto = ui.textarea(
                "Container 2 — texto",
                value=dados.get("visao_texto", ""),
            ).props("outlined dense").classes("erp-form-full")

        ui.label("Marcas que trabalhamos (automático)").classes("erp-secao-titulo")
        if marcas:
            ui.html(
                "<p>"
                + " · ".join(marcas)
                + "</p>"
            )
        else:
            ui.label(
                "Nenhuma marca no estoque ainda. Cadastre veículos para listar aqui."
            ).classes("text-caption text-grey-7")

        ui.label("Depoimentos").classes("erp-secao-titulo")
        ui.html(
            '<p class="erp-ajuda">Gerencie em '
            '<a href="/admin/depoimentos">Marketing → Depoimentos</a> '
            "(nome, estrelas, comentário e cidade).</p>"
        )

        ui.label("Dados da empresa e CTA final").classes("erp-secao-titulo")
        ui.label(
            "O bloco de endereço/telefone/WhatsApp/e-mail/horário vem das "
            "Configurações. O CTA final (“Pronto para encontrar seu próximo "
            "carro?”) é padrão e igual para todos os sites."
        ).classes("text-caption text-grey-7")

        def salvar() -> None:
            salvar_institucional({
                "titulo": titulo.value or "",
                "subtitulo": subtitulo.value or "",
                "intro": intro.value or "",
                "imagem_url": imagem_url["valor"] or url_campo.value or "",
                "pilares_titulo": pilares_titulo.value or "NOSSOS PILARES",
                "pilares": [
                    {
                        "icone": c["icone"].value,
                        "titulo": c["titulo"].value or "",
                        "texto": c["texto"].value or "",
                    }
                    for c in pilares_campos
                ],
                "missao_titulo": missao_titulo.value or "Missão",
                "missao_texto": missao_texto.value or "",
                "visao_titulo": visao_titulo.value or "Visão",
                "visao_texto": visao_texto.value or "",
            })
            ui.notify(
                "Institucional salvo! Recarregue a página EMPRESA no site.",
                type="positive",
            )

        ui.button(
            "Salvar alterações", on_click=salvar,
        ).classes("btn btn-preto").props("unelevated no-caps").style(
            "margin-top:16px"
        )
