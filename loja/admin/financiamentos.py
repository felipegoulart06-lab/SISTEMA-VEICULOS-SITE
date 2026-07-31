from nicegui import ui

from loja.admin.layout import ConfirmacaoExclusao, ajuda, id_do_evento
from loja.crm_repo import (
    LABEL_FINANCIAMENTO,
    STATUS_FINANCIAMENTO,
    dados_financiamento_formatados,
    excluir_financiamento,
    listar_financiamentos,
    obter_financiamento,
    salvar_financiamento_admin,
)
from loja.repositorio import formatar_preco


def pagina_financiamentos_admin() -> None:
    cx = ConfirmacaoExclusao()
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Financiamentos</h2>"
        "<p>Solicitações do site aguardando análise</p></div></div>"
    )
    ajuda(
        "Cada formulário enviado pelo site aparece aqui. "
        "Abra para ver todos os dados e atualize o status da análise."
    )

    @ui.refreshable
    def tabela() -> None:
        items = listar_financiamentos()
        colunas = [
            {"name": "id", "label": "#", "field": "id"},
            {"name": "cliente", "label": "Cliente", "field": "cliente"},
            {"name": "veiculo", "label": "Veículo", "field": "veiculo"},
            {"name": "valor", "label": "Valor", "field": "valor"},
            {"name": "entrada", "label": "Entrada", "field": "entrada"},
            {"name": "status", "label": "Status", "field": "status"},
            {"name": "data", "label": "Data", "field": "data"},
            {"name": "acoes", "label": "Ações", "field": "acoes"},
        ]
        linhas = [{
            "id": f.id,
            "cliente": f.nome,
            "veiculo": f"{f.veiculo_marca} {f.veiculo_modelo}".strip() or "—",
            "valor": formatar_preco(f.valor_veiculo),
            "entrada": formatar_preco(f.valor_entrada),
            "status": LABEL_FINANCIAMENTO.get(f.status, f.status).upper(),
            "data": f.criado_em.strftime("%d/%m/%Y"),
            "acoes": f.id,
        } for f in items]

        tbl = ui.table(
            columns=colunas, rows=linhas, row_key="id", pagination=12,
        ).classes("erp-tabela").props("flat bordered dense")
        tbl.add_slot("body-cell-acoes", """
            <q-td :props="props">
                <q-btn flat dense size="sm" icon="visibility" color="primary"
                    @click="$parent.$emit('abrir', props.row.id)" />
                <q-btn flat dense size="sm" icon="delete" color="negative"
                    @click.stop.prevent="$parent.$emit('ask_delete', props.row.id)" />
            </q-td>
        """)

        def on_excluir(e):
            fid = id_do_evento(e)
            fin = obter_financiamento(fid)
            nome = fin.nome if fin else f"#{fid}"
            cx.pedir(
                f"a solicitação de «{nome}»",
                lambda f_id=fid: (
                    excluir_financiamento(f_id),
                    ui.notify("Excluída.", type="warning"),
                    tabela.refresh(),
                ),
            )

        tbl.on("abrir", lambda e: abrir(id_do_evento(e)))
        tbl.on("ask_delete", on_excluir)

    def abrir(fin_id: int) -> None:
        fin = obter_financiamento(fin_id)
        if not fin:
            return
        texto = dados_financiamento_formatados(fin)

        with ui.dialog() as dlg, ui.card().classes("erp-dialog erp-dialog-wide"):
            ui.label(f"Financiamento — {fin.nome}").classes("erp-dialog-titulo")
            with ui.element("div").classes("erp-form-body"):
                status = ui.select(
                    {s: LABEL_FINANCIAMENTO[s] for s in STATUS_FINANCIAMENTO},
                    label="Status da análise",
                    value=fin.status if fin.status in STATUS_FINANCIAMENTO else "novo",
                ).props("outlined dense")
                obs = ui.textarea(
                    "Observações internas",
                    value=fin.observacoes_interna or "",
                ).props("outlined dense").classes("erp-form-full")
                ui.label("Dados completos do formulário").classes("erp-secao-titulo")
                dados = ui.textarea(
                    value=texto,
                ).props("outlined readonly").classes("erp-form-full")
                dados.props('rows=18')

            def salvar():
                salvar_financiamento_admin({
                    "status": status.value,
                    "observacoes_interna": obs.value or "",
                }, fin_id)
                ui.notify("Atualizado!", type="positive")
                dlg.close()
                tabela.refresh()

            with ui.row().classes("erp-dialog-botoes"):
                ui.button("Fechar", on_click=dlg.close).props("flat no-caps")
                ui.button("Salvar", on_click=salvar).classes("btn btn-preto").props(
                    "unelevated no-caps"
                )
            dlg.open()

    tabela()
