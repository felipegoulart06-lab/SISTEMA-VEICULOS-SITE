from nicegui import ui

from loja.admin.layout import ConfirmacaoExclusao, ajuda, id_do_evento
from loja.crm_repo import (
    TIPOS_DOCUMENTO,
    excluir_documento,
    listar_documentos,
    obter_documento,
    salvar_documento,
    template_documento,
)
from loja.repositorio import config_como_dict


def pagina_documentos() -> None:
    cx = ConfirmacaoExclusao()
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Documentos</h2>"
        "<p>Recibo, contrato, procuração e entrega</p></div></div>"
    )
    ajuda("Gere o documento, revise e imprima / salve em PDF pelo navegador.")

    @ui.refreshable
    def tabela() -> None:
        docs = listar_documentos()
        colunas = [
            {"name": "id", "label": "#", "field": "id"},
            {"name": "tipo", "label": "Tipo", "field": "tipo"},
            {"name": "titulo", "label": "Título", "field": "titulo"},
            {"name": "cliente", "label": "Cliente", "field": "cliente"},
            {"name": "data", "label": "Data", "field": "data"},
            {"name": "acoes", "label": "Ações", "field": "acoes"},
        ]
        linhas = [{
            "id": d.id,
            "tipo": d.tipo.upper(),
            "titulo": d.titulo,
            "cliente": d.cliente_nome or "—",
            "data": d.criado_em.strftime("%d/%m/%Y"),
            "acoes": d.id,
        } for d in docs]
        tbl = ui.table(
            columns=colunas, rows=linhas, row_key="id", pagination=10
        ).classes("erp-tabela").props("flat bordered dense")
        tbl.add_slot("body-cell-acoes", """
            <q-td :props="props">
                <q-btn flat dense size="sm" icon="print" color="primary"
                    @click="$parent.$emit('ver', props.row.id)" />
                <q-btn flat dense size="sm" icon="delete" color="negative"
                    @click.stop.prevent="$parent.$emit('ask_delete', props.row.id)" />
            </q-td>
        """)
        def on_excluir(e):
            did = id_do_evento(e)
            cx.pedir(
                "este documento",
                lambda d_id=did: (
                    excluir_documento(d_id),
                    ui.notify("Documento excluído.", type="warning"),
                    tabela.refresh(),
                ),
            )

        tbl.on("ver", lambda e: ver(id_do_evento(e)))
        tbl.on("ask_delete", on_excluir)

    def ver(doc_id: int) -> None:
        d = obter_documento(doc_id)
        if not d:
            return
        with ui.dialog() as dlg, ui.card().classes("erp-dialog erp-dialog-wide"):
            ui.html(f'<div class="doc-print">{d.conteudo_html}</div>')
            ui.button(
                "Imprimir / PDF",
                on_click=lambda: ui.run_javascript("window.print()"),
            ).classes("btn btn-preto")
            ui.button("Fechar", on_click=dlg.close).props("flat")
            dlg.open()

    def novo() -> None:
        loja = config_como_dict()
        with ui.dialog() as dlg, ui.card().classes("erp-dialog erp-dialog-wide"):
            ui.label("Novo documento").classes("erp-dialog-titulo")
            tipo = ui.select(
                {t: t.title() for t in TIPOS_DOCUMENTO},
                label="Tipo", value="recibo",
            )
            cliente = ui.input("Nome do cliente")
            veiculo = ui.input("Veículo (opcional)")
            valor = ui.input("Valor (opcional)", placeholder="R$ 50.000,00")

            def gerar():
                html = template_documento(
                    tipo.value, loja,
                    cliente=cliente.value or "",
                    veiculo=veiculo.value or "",
                    valor=valor.value or "",
                )
                salvar_documento({
                    "tipo": tipo.value,
                    "titulo": f"{tipo.value.title()} — {cliente.value or 'Cliente'}",
                    "conteudo_html": html,
                    "cliente_nome": cliente.value or "",
                })
                ui.notify("Documento gerado!", type="positive")
                dlg.close()
                tabela.refresh()

            with ui.row():
                ui.button("Gerar", on_click=gerar).classes("btn btn-preto")
                ui.button("Cancelar", on_click=dlg.close).props("flat")
            dlg.open()

    with ui.element("div").classes("erp-toolbar"):
        ui.button("+ Gerar documento", on_click=novo).classes("btn btn-preto").props(
            "unelevated no-caps"
        )
    tabela()
