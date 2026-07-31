from datetime import datetime

from nicegui import ui

from loja.admin.layout import ConfirmacaoExclusao, ajuda
from loja.crm_repo import (
    TIPOS_COMPROMISSO,
    excluir_compromisso,
    listar_compromissos_semana,
    salvar_compromisso,
)


def pagina_agenda() -> None:
    cx = ConfirmacaoExclusao()
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Agenda</h2>"
        "<p>Test drives, entregas e lembretes</p></div></div>"
    )
    ajuda("Anote visitas e retornos. O dashboard mostra o que é hoje.")

    @ui.refreshable
    def lista() -> None:
        items = listar_compromissos_semana()
        if not items:
            ui.html('<p class="erp-vazio">Nenhum compromisso nos próximos 7 dias.</p>')
            return
        for c in items:
            with ui.element("div").classes("erp-painel erp-agenda-item"):
                ui.html(
                    f"<strong>{c.data_hora.strftime('%d/%m %H:%M')}</strong> · "
                    f"{c.tipo.replace('_', ' ').title()} — {c.titulo}"
                )
                if c.observacoes:
                    ui.html(f"<p>{c.observacoes}</p>")
                with ui.row():
                    if not c.concluido:
                        ui.button(
                            "Concluir",
                            on_click=lambda cid=c.id: (
                                salvar_compromisso({"concluido": True}, cid),
                                lista.refresh(),
                            ),
                        ).props("flat dense")
                    ui.button(
                        "Excluir",
                        on_click=lambda cid=c.id, tit=c.titulo: cx.pedir(
                            f"o compromisso «{tit}»",
                            lambda c_id=cid: (
                                excluir_compromisso(c_id),
                                lista.refresh(),
                                ui.notify("Compromisso excluído.", type="warning"),
                            ),
                        ),
                    ).props("flat dense color=negative")

    def novo() -> None:
        with ui.dialog() as dlg, ui.card().classes("erp-dialog"):
            ui.label("Novo compromisso").classes("erp-dialog-titulo")
            titulo = ui.input("Título")
            tipo = ui.select(
                {t: t.replace("_", " ").title() for t in TIPOS_COMPROMISSO},
                label="Tipo", value="lembrete",
            )
            data = ui.input(
                "Data e hora (AAAA-MM-DD HH:MM)",
                value=datetime.now().strftime("%Y-%m-%d %H:00"),
            )
            obs = ui.textarea("Observações")

            def salvar():
                if not titulo.value:
                    ui.notify("Informe o título.", type="warning")
                    return
                try:
                    dt = datetime.strptime(data.value.strip(), "%Y-%m-%d %H:%M")
                except ValueError:
                    ui.notify("Data inválida. Use AAAA-MM-DD HH:MM", type="warning")
                    return
                salvar_compromisso({
                    "titulo": titulo.value,
                    "tipo": tipo.value,
                    "data_hora": dt,
                    "observacoes": obs.value or "",
                })
                ui.notify("Agendado!", type="positive")
                dlg.close()
                lista.refresh()

            with ui.row():
                ui.button("Salvar", on_click=salvar).classes("btn btn-preto")
                ui.button("Cancelar", on_click=dlg.close).props("flat")
            dlg.open()

    with ui.element("div").classes("erp-toolbar"):
        ui.button("+ Novo compromisso", on_click=novo).classes("btn btn-preto").props(
            "unelevated no-caps"
        )
    lista()
