from nicegui import ui

from loja.admin.layout import ConfirmacaoExclusao, ajuda
from loja.crm_repo import (
    excluir_depoimento,
    listar_depoimentos,
    salvar_depoimento,
)


def pagina_depoimentos() -> None:
    cx = ConfirmacaoExclusao()
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Depoimentos</h2>"
        "<p>Avaliações dos seus clientes na página EMPRESA</p></div></div>"
    )
    ajuda(
        "Preencha nome, cidade, estrelas e comentário. "
        "Só os publicados aparecem no site."
    )

    @ui.refreshable
    def lista() -> None:
        for d in listar_depoimentos():
            with ui.element("div").classes("erp-painel"):
                estrelas = "★" * (d.nota or 5)
                cidade = (getattr(d, "cidade", None) or "").strip()
                cidade_html = f" · {cidade}" if cidade else ""
                ui.html(
                    f"<strong>{d.nome}</strong>{cidade_html} {estrelas} "
                    f"({'no site' if d.ativo else 'oculto'})"
                )
                ui.html(f"<p>{d.texto}</p>")
                with ui.row():
                    ui.button(
                        "Editar",
                        on_click=lambda did=d.id: abrir_form(did),
                    ).props("flat dense")
                    ui.button(
                        "Ocultar" if d.ativo else "Publicar",
                        on_click=lambda did=d.id, a=d.ativo: (
                            salvar_depoimento({"ativo": not a}, did),
                            lista.refresh(),
                        ),
                    ).props("flat dense")
                    ui.button(
                        "Excluir",
                        on_click=lambda did=d.id, nom=d.nome: cx.pedir(
                            f"o depoimento de «{nom}»",
                            lambda d_id=did: (
                                excluir_depoimento(d_id),
                                lista.refresh(),
                                ui.notify("Depoimento excluído.", type="warning"),
                            ),
                        ),
                    ).props("flat dense color=negative")

    def abrir_form(depoimento_id: int | None = None) -> None:
        atual = None
        if depoimento_id:
            atual = next(
                (d for d in listar_depoimentos() if d.id == depoimento_id),
                None,
            )
        with ui.dialog() as dlg, ui.card().classes("erp-dialog"):
            ui.label(
                "Editar depoimento" if atual else "Novo depoimento"
            ).classes("erp-dialog-titulo")
            nome = ui.input(
                "Nome completo", value=atual.nome if atual else "",
            ).props("outlined dense").classes("w-full")
            cidade = ui.input(
                "Cidade",
                value=getattr(atual, "cidade", "") if atual else "",
            ).props("outlined dense").classes("w-full")
            texto = ui.textarea(
                "Comentário", value=atual.texto if atual else "",
            ).props("outlined dense").classes("w-full")
            nota = ui.number(
                "Estrelas (1-5)",
                value=atual.nota if atual else 5,
                format="%.0f",
                min=1,
                max=5,
            ).props("outlined dense")
            ativo = ui.checkbox(
                "Publicar no site",
                value=atual.ativo if atual else True,
            )

            def salvar():
                if not nome.value or not texto.value:
                    ui.notify("Preencha nome e comentário.", type="warning")
                    return
                salvar_depoimento({
                    "nome": nome.value.strip(),
                    "cidade": (cidade.value or "").strip(),
                    "texto": texto.value.strip(),
                    "nota": int(nota.value or 5),
                    "ativo": ativo.value,
                }, depoimento_id)
                dlg.close()
                lista.refresh()
                ui.notify("Depoimento salvo.", type="positive")

            with ui.row().classes("erp-dialog-botoes"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
                ui.button("Salvar", on_click=salvar).classes("btn btn-preto").props(
                    "unelevated no-caps"
                )
            dlg.open()

    with ui.element("div").classes("erp-toolbar"):
        ui.button(
            "+ Depoimento", on_click=lambda: abrir_form(None),
        ).classes("btn btn-preto").props("unelevated no-caps")
    lista()
