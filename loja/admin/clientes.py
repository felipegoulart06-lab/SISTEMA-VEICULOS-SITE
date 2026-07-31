from nicegui import ui

from loja.admin.layout import ConfirmacaoExclusao, ajuda, id_do_evento
from loja.crm_repo import excluir_cliente, listar_clientes, obter_cliente, salvar_cliente


def pagina_clientes() -> None:
    cx = ConfirmacaoExclusao()
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Clientes</h2>"
        "<p>Pessoa física e jurídica</p></div></div>"
    )
    ajuda("Guarde quem comprou ou vendeu com você. Facilita o próximo contato.")

    @ui.refreshable
    def tabela() -> None:
        clientes = listar_clientes()
        colunas = [
            {"name": "id", "label": "#", "field": "id"},
            {"name": "tipo", "label": "Tipo", "field": "tipo"},
            {"name": "nome", "label": "Nome", "field": "nome"},
            {"name": "doc", "label": "CPF/CNPJ", "field": "doc"},
            {"name": "telefone", "label": "Telefone", "field": "telefone"},
            {"name": "cidade", "label": "Cidade", "field": "cidade"},
            {"name": "acoes", "label": "Ações", "field": "acoes"},
        ]
        linhas = [{
            "id": c.id,
            "tipo": c.tipo,
            "nome": c.nome,
            "doc": c.documento or "—",
            "telefone": c.telefone or "—",
            "cidade": c.cidade or "—",
            "acoes": c.id,
        } for c in clientes]

        tbl = ui.table(
            columns=colunas, rows=linhas, row_key="id", pagination=10
        ).classes("erp-tabela").props("flat bordered dense")
        tbl.add_slot("body-cell-acoes", """
            <q-td :props="props">
                <q-btn flat dense size="sm" icon="edit" color="primary"
                    @click="$parent.$emit('editar', props.row.id)" />
                <q-btn flat dense size="sm" icon="delete" color="negative"
                    @click.stop.prevent="$parent.$emit('ask_delete', props.row.id)" />
            </q-td>
        """)
        def on_excluir(e):
            cid = id_do_evento(e)
            nome = next((c.nome for c in clientes if c.id == cid), f"#{cid}")
            cx.pedir(
                f"o cliente «{nome}»",
                lambda c=cid: (
                    excluir_cliente(c),
                    ui.notify("Cliente excluído.", type="warning"),
                    tabela.refresh(),
                ),
            )

        tbl.on("editar", lambda e: abrir(id_do_evento(e)))
        tbl.on("ask_delete", on_excluir)

    def abrir(cliente_id: int | None = None) -> None:
        c = obter_cliente(cliente_id) if cliente_id else None
        with ui.dialog() as dlg, ui.card().classes("erp-dialog erp-dialog-wide"):
            ui.label("Editar cliente" if c else "Novo cliente").classes("erp-dialog-titulo")
            with ui.element("div").classes("erp-form-body"):
                with ui.element("div").classes("erp-form-grid"):
                    tipo = ui.select(
                        {"PF": "Pessoa Física", "PJ": "Pessoa Jurídica"},
                        label="Tipo", value=c.tipo if c else "PF",
                    ).props("outlined dense")
                    documento = ui.input(
                        "CPF / CNPJ", value=c.documento if c else "",
                    ).props("outlined dense")
                    nome = ui.input(
                        "Nome / Razão social", value=c.nome if c else "",
                    ).props("outlined dense").classes("erp-form-full")
                    telefone = ui.input(
                        "Telefone", value=c.telefone if c else "",
                    ).props("outlined dense")
                    email = ui.input(
                        "E-mail", value=c.email if c else "",
                    ).props("outlined dense")
                    endereco = ui.input(
                        "Endereço", value=c.endereco if c else "",
                    ).props("outlined dense").classes("erp-form-full")
                    cidade = ui.input(
                        "Cidade", value=c.cidade if c else "",
                    ).props("outlined dense")
                    obs = ui.textarea(
                        "Observações", value=c.observacoes if c else "",
                    ).props("outlined dense").classes("erp-form-full")
                    docs = ui.textarea(
                        "Documentos / anotações",
                        value=c.documentos_texto if c else "",
                    ).props("outlined dense").classes("erp-form-full")

            def salvar():
                if not nome.value:
                    ui.notify("Informe o nome.", type="warning")
                    return
                salvar_cliente({
                    "tipo": tipo.value,
                    "nome": nome.value.strip(),
                    "documento": documento.value or "",
                    "telefone": telefone.value or "",
                    "email": email.value or "",
                    "endereco": endereco.value or "",
                    "cidade": cidade.value or "",
                    "observacoes": obs.value or "",
                    "documentos_texto": docs.value or "",
                }, cliente_id)
                ui.notify("Cliente salvo!", type="positive")
                dlg.close()
                tabela.refresh()

            with ui.row().classes("erp-dialog-botoes"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
                ui.button("Salvar", on_click=salvar).classes("btn btn-preto").props(
                    "unelevated no-caps"
                )
            dlg.open()

    with ui.element("div").classes("erp-toolbar"):
        ui.button("+ Novo cliente", on_click=lambda: abrir()).classes(
            "btn btn-preto"
        ).props("unelevated no-caps")
    tabela()
