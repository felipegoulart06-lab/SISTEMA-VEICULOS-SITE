from nicegui import ui

from loja.admin.layout import ConfirmacaoExclusao, ajuda, id_do_evento
from loja.crm_repo import (
    STATUS_PROPOSTA,
    excluir_proposta,
    listar_clientes,
    listar_propostas,
    obter_proposta,
    salvar_proposta,
)
from loja.repositorio import (
    config_como_dict,
    formatar_preco,
    listar_veiculos_opcoes,
    obter_veiculo,
)


def pagina_propostas() -> None:
    cx = ConfirmacaoExclusao()
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Propostas</h2>"
        "<p>Crie, acompanhe e imprima</p></div></div>"
    )
    ajuda("Monte a proposta, envie (imprimir/PDF do navegador) e marque como aprovada.")

    @ui.refreshable
    def tabela() -> None:
        props = listar_propostas()
        veiculos = listar_veiculos_opcoes()
        colunas = [
            {"name": "id", "label": "#", "field": "id"},
            {"name": "cliente", "label": "Cliente", "field": "cliente"},
            {"name": "veiculo", "label": "Veículo", "field": "veiculo"},
            {"name": "valor", "label": "Valor", "field": "valor"},
            {"name": "status", "label": "Status", "field": "status"},
            {"name": "acoes", "label": "Ações", "field": "acoes"},
        ]
        linhas = [{
            "id": p.id,
            "cliente": p.cliente_nome or "—",
            "veiculo": veiculos.get(p.veiculo_id, "—"),
            "valor": formatar_preco(p.valor),
            "status": p.status.upper(),
            "acoes": p.id,
        } for p in props]
        tbl = ui.table(
            columns=colunas, rows=linhas, row_key="id", pagination=10
        ).classes("erp-tabela").props("flat bordered dense")
        tbl.add_slot("body-cell-acoes", """
            <q-td :props="props">
                <q-btn flat dense size="sm" icon="print" color="primary"
                    @click="$parent.$emit('imprimir', props.row.id)" />
                <q-btn flat dense size="sm" icon="edit" color="primary"
                    @click="$parent.$emit('editar', props.row.id)" />
                <q-btn flat dense size="sm" icon="delete" color="negative"
                    @click.stop.prevent="$parent.$emit('ask_delete', props.row.id)" />
            </q-td>
        """)
        def on_excluir(e):
            pid = id_do_evento(e)
            props = listar_propostas()
            p = next((x for x in props if x.id == pid), None)
            rotulo = (
                f"a proposta de «{p.cliente_nome}»"
                if p and p.cliente_nome else "esta proposta"
            )
            cx.pedir(
                rotulo,
                lambda p_id=pid: (
                    excluir_proposta(p_id),
                    ui.notify("Excluída.", type="warning"),
                    tabela.refresh(),
                ),
            )

        tbl.on("imprimir", lambda e: imprimir(id_do_evento(e)))
        tbl.on("editar", lambda e: abrir(id_do_evento(e)))
        tbl.on("ask_delete", on_excluir)

    def imprimir(proposta_id: int) -> None:
        p = obter_proposta(proposta_id)
        if not p:
            return
        loja = config_como_dict()
        veiculo = "—"
        if p.veiculo_id:
            v = obter_veiculo(p.veiculo_id)
            if v:
                veiculo = f"{v.marca} {v.modelo} {v.ano}"
        html = f"""
        <div class="doc-print">
            <h2>PROPOSTA COMERCIAL</h2>
            <p><strong>{loja['nome']}</strong><br>{loja.get('endereco','')} · {loja.get('telefone','')}</p>
            <hr>
            <p>Cliente: <strong>{p.cliente_nome}</strong></p>
            <p>Veículo: <strong>{veiculo}</strong></p>
            <p>Valor proposto: <strong>{formatar_preco(p.valor)}</strong></p>
            <div>{p.texto or ''}</div>
            <p style="margin-top:40px">Data: ____/____/________ &nbsp;&nbsp; Assinatura: _______________</p>
        </div>
        """
        with ui.dialog() as dlg, ui.card().classes("erp-dialog erp-dialog-wide"):
            ui.html(html)
            ui.button(
                "Imprimir / Salvar PDF",
                on_click=lambda: ui.run_javascript("window.print()"),
            ).classes("btn btn-preto")
            ui.button("Fechar", on_click=dlg.close).props("flat")
            dlg.open()

    def abrir(proposta_id: int | None = None) -> None:
        p = obter_proposta(proposta_id) if proposta_id else None
        clientes = {c.id: c.nome for c in listar_clientes()}
        clientes_opts = {None: "— Digite o nome abaixo —", **clientes}
        veiculos = {None: "— Nenhum —", **listar_veiculos_opcoes()}

        with ui.dialog() as dlg, ui.card().classes("erp-dialog erp-dialog-wide"):
            ui.label("Editar proposta" if p else "Nova proposta").classes(
                "erp-dialog-titulo"
            )
            with ui.element("div").classes("erp-form-body"):
                with ui.element("div").classes("erp-form-grid"):
                    cliente_sel = ui.select(
                        clientes_opts, label="Cliente cadastrado",
                        value=p.cliente_id if p else None,
                    ).props("outlined dense")
                    veiculo = ui.select(
                        veiculos, label="Veículo", value=p.veiculo_id if p else None,
                    ).props("outlined dense")
                    cliente_nome = ui.input(
                        "Nome do cliente", value=p.cliente_nome if p else "",
                    ).props("outlined dense").classes("erp-form-full")
                    valor = ui.number(
                        "Valor", value=p.valor if p else 0, format="%.2f",
                    ).props("outlined dense")
                    status = ui.select(
                        {s: s.upper() for s in STATUS_PROPOSTA},
                        label="Status", value=p.status if p else "rascunho",
                    ).props("outlined dense")
                    texto = ui.textarea(
                        "Texto da proposta",
                        value=p.texto if p else (
                            "Condições de pagamento, entrada e parcelas a combinar.\n"
                            "Validade desta proposta: 7 dias."
                        ),
                    ).props("outlined dense").classes("erp-form-full")

            def salvar():
                nome = cliente_nome.value or ""
                if cliente_sel.value and not nome:
                    nome = clientes.get(cliente_sel.value, "")
                if not nome:
                    ui.notify("Informe o cliente.", type="warning")
                    return
                salvar_proposta({
                    "cliente_id": cliente_sel.value,
                    "cliente_nome": nome,
                    "veiculo_id": veiculo.value,
                    "valor": float(valor.value or 0),
                    "status": status.value,
                    "texto": texto.value or "",
                }, proposta_id)
                ui.notify("Proposta salva!", type="positive")
                dlg.close()
                tabela.refresh()

            with ui.row().classes("erp-dialog-botoes"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
                ui.button("Salvar", on_click=salvar).classes("btn btn-preto").props(
                    "unelevated no-caps"
                )
            dlg.open()

    with ui.element("div").classes("erp-toolbar"):
        ui.button("+ Nova proposta", on_click=lambda: abrir()).classes(
            "btn btn-preto"
        ).props("unelevated no-caps")
    tabela()
