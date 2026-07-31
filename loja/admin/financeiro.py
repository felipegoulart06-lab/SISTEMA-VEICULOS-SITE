from datetime import datetime

from nicegui import ui

from loja.admin.layout import ConfirmacaoExclusao, ajuda, id_do_evento
from loja.crm_repo import (
    CATEGORIAS_FINANCEIRO,
    excluir_lancamento,
    listar_lancamentos,
    lucro_por_veiculo,
    resumo_financeiro,
    salvar_lancamento,
)
from loja.repositorio import formatar_preco, listar_todos_veiculos


def pagina_financeiro() -> None:
    cx = ConfirmacaoExclusao()
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Financeiro</h2>"
        "<p>Entradas, saídas e lucro por veículo</p></div></div>"
    )
    ajuda("Lance o que entra e o que sai. Assim você sabe se o mês fechou no azul.")

    @ui.refreshable
    def topo() -> None:
        r = resumo_financeiro()
        with ui.element("div").classes("erp-cards"):
            _mini("Entradas (mês)", formatar_preco(r["entradas_mes"]), "verde")
            _mini("Saídas (mês)", formatar_preco(r["saidas_mes"]), "vermelho")
            _mini("Fluxo do mês", formatar_preco(r["fluxo_mes"]), "azul")
            _mini("A receber", formatar_preco(r["a_receber"]), "amarelo")
            _mini("A pagar", formatar_preco(r["a_pagar"]), "amarelo")

    def _mini(titulo, valor, cor):
        ui.html(
            f'<div class="erp-stat erp-stat-{cor}">'
            f'<div class="erp-stat-body">'
            f'<span class="erp-stat-label">{titulo}</span>'
            f'<strong class="erp-stat-valor" style="font-size:20px">{valor}</strong>'
            f"</div></div>"
        )

    @ui.refreshable
    def tabela() -> None:
        rows = listar_lancamentos()
        colunas = [
            {"name": "id", "label": "#", "field": "id"},
            {"name": "tipo", "label": "Tipo", "field": "tipo"},
            {"name": "cat", "label": "Categoria", "field": "cat"},
            {"name": "desc", "label": "Descrição", "field": "desc"},
            {"name": "valor", "label": "Valor", "field": "valor"},
            {"name": "pago", "label": "Pago", "field": "pago"},
            {"name": "acoes", "label": "Ações", "field": "acoes"},
        ]
        linhas = [{
            "id": l.id,
            "tipo": l.tipo.upper(),
            "cat": l.categoria,
            "desc": l.descricao,
            "valor": formatar_preco(l.valor),
            "pago": "Sim" if l.pago else "Não",
            "acoes": l.id,
        } for l in rows]
        tbl = ui.table(
            columns=colunas, rows=linhas, row_key="id", pagination=12
        ).classes("erp-tabela").props("flat bordered dense")
        tbl.add_slot("body-cell-acoes", """
            <q-td :props="props">
                <q-btn flat dense size="sm" icon="delete" color="negative"
                    @click.stop.prevent="$parent.$emit('ask_delete', props.row.id)" />
            </q-td>
        """)
        def on_excluir(e):
            lid = id_do_evento(e)
            cx.pedir(
                "este lançamento financeiro",
                lambda l_id=lid: (
                    excluir_lancamento(l_id),
                    ui.notify("Excluído.", type="warning"),
                    tabela.refresh(),
                    topo.refresh(),
                    lucros.refresh(),
                ),
            )

        tbl.on("ask_delete", on_excluir)

    @ui.refreshable
    def lucros() -> None:
        ui.html('<h3 class="erp-secao-titulo">Lucro por veículo vendido</h3>')
        dados = lucro_por_veiculo()
        if not dados:
            ui.html('<p class="erp-vazio">Nenhum veículo marcado como vendido.</p>')
            return
        for d in dados:
            ui.html(
                f'<div class="erp-resumo-item">'
                f"<span>{d['veiculo']}</span>"
                f'<strong class="erp-num">{formatar_preco(d["lucro"])}</strong></div>'
            )

    def novo() -> None:
        veiculos = {None: "— Nenhum —"}
        for v in listar_todos_veiculos():
            veiculos[v.id] = f"{v.marca} {v.modelo}"
        with ui.dialog() as dlg, ui.card().classes("erp-dialog erp-dialog-wide"):
            ui.label("Novo lançamento").classes("erp-dialog-titulo")
            with ui.element("div").classes("erp-form-body"):
                with ui.element("div").classes("erp-form-grid"):
                    tipo = ui.select(
                        {"entrada": "Entrada", "saida": "Saída"},
                        label="Tipo", value="entrada",
                    ).props("outlined dense")
                    cat = ui.select(
                        CATEGORIAS_FINANCEIRO, label="Categoria", value="geral",
                    ).props("outlined dense")
                    desc = ui.input("Descrição").props(
                        "outlined dense"
                    ).classes("erp-form-full")
                    valor = ui.number(
                        "Valor", value=0, format="%.2f",
                    ).props("outlined dense")
                    comissao = ui.number(
                        "Comissão %", value=0, format="%.1f",
                    ).props("outlined dense")
                    veiculo = ui.select(
                        veiculos, label="Veículo vinculado", value=None,
                    ).props("outlined dense")
                    pago = ui.checkbox("Já pago / recebido", value=True)

            def salvar():
                if not desc.value:
                    ui.notify("Informe a descrição.", type="warning")
                    return
                salvar_lancamento({
                    "tipo": tipo.value,
                    "categoria": cat.value,
                    "descricao": desc.value,
                    "valor": float(valor.value or 0),
                    "comissao_pct": float(comissao.value or 0),
                    "veiculo_id": veiculo.value,
                    "pago": pago.value,
                    "vencimento": datetime.now(),
                })
                ui.notify("Lançamento salvo!", type="positive")
                dlg.close()
                tabela.refresh()
                topo.refresh()

            with ui.row().classes("erp-dialog-botoes"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
                ui.button("Salvar", on_click=salvar).classes("btn btn-preto").props(
                    "unelevated no-caps"
                )
            dlg.open()

    topo()
    with ui.element("div").classes("erp-toolbar"):
        ui.button("+ Novo lançamento", on_click=novo).classes("btn btn-preto").props(
            "unelevated no-caps"
        )
    tabela()
    lucros()
