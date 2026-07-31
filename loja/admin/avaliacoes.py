from nicegui import ui

from loja.admin.layout import ConfirmacaoExclusao, ajuda, id_do_evento
from loja.crm_repo import salvar_avaliacao_completa
from loja.repositorio import (
    STATUS_AVALIACAO,
    excluir_avaliacao,
    formatar_preco,
    listar_avaliacoes,
    salvar_avaliacao_status,
)


def pagina_avaliacoes_admin() -> None:
    cx = ConfirmacaoExclusao()
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Avaliação de usados</h2>"
        "<p>Pedidos do site + margem estimada</p></div></div>"
    )
    ajuda(
        "Esse módulo vende: registre FIPE, valor sugerido e valor pago para ver a margem."
    )

    @ui.refreshable
    def tabela() -> None:
        aval = listar_avaliacoes()
        colunas = [
            {"name": "id", "label": "#", "field": "id"},
            {"name": "cliente", "label": "Cliente", "field": "cliente"},
            {"name": "veiculo", "label": "Veículo", "field": "veiculo"},
            {"name": "sugerido", "label": "Sugerido", "field": "sugerido"},
            {"name": "margem", "label": "Margem", "field": "margem"},
            {"name": "status", "label": "Status", "field": "status"},
            {"name": "acoes", "label": "Ações", "field": "acoes"},
        ]
        linhas = []
        for a in aval:
            linhas.append({
                "id": a.id,
                "cliente": a.nome,
                "veiculo": f"{a.marca} {a.modelo} {a.ano}",
                "sugerido": formatar_preco(getattr(a, "valor_sugerido", 0) or 0),
                "margem": formatar_preco(getattr(a, "margem", 0) or 0),
                "status": a.status.upper(),
                "acoes": a.id,
            })

        tbl = ui.table(
            columns=colunas, rows=linhas, row_key="id", pagination=10
        ).classes("erp-tabela").props("flat bordered dense")
        tbl.add_slot("body-cell-acoes", """
            <q-td :props="props">
                <q-btn flat dense size="sm" icon="edit" color="primary"
                    @click="$parent.$emit('abrir', props.row.id)" />
                <q-btn flat dense size="sm" icon="delete" color="negative"
                    @click.stop.prevent="$parent.$emit('ask_delete', props.row.id)" />
            </q-td>
        """)
        def on_excluir(e):
            aid = id_do_evento(e)
            item = next((a for a in aval if a.id == aid), None)
            rotulo = (
                f"a avaliação de «{item.nome}» ({item.marca} {item.modelo})"
                if item else "esta avaliação"
            )
            cx.pedir(
                rotulo,
                lambda a_id=aid: (
                    excluir_avaliacao(a_id),
                    ui.notify("Excluída.", type="warning"),
                    tabela.refresh(),
                ),
            )

        tbl.on("abrir", lambda e: abrir(id_do_evento(e)))
        tbl.on("ask_delete", on_excluir)

    def abrir(avaliacao_id: int) -> None:
        from loja.database import get_session
        from loja.models import Avaliacao

        with get_session() as db:
            a = db.get(Avaliacao, avaliacao_id)
            if a:
                db.expunge(a)
        if not a:
            return

        with ui.dialog() as dlg, ui.card().classes("erp-dialog erp-dialog-wide"):
            ui.label("Avaliação de usado").classes("erp-dialog-titulo")
            with ui.element("div").classes("erp-form-body"):
                ui.html(
                    f"<p><strong>{a.nome}</strong> · {a.telefone}<br>"
                    f"{a.marca} {a.modelo} {a.ano} · {a.km} km · {a.cor}<br>"
                    f"Intenção: {a.intencao} · Interesse: {a.veiculo_interesse or '—'}</p>"
                )
                with ui.element("div").classes("erp-form-grid"):
                    fipe = ui.number(
                        "Valor FIPE", value=a.valor_fipe or 0, format="%.2f",
                    ).props("outlined dense")
                    sugerido = ui.number(
                        "Valor sugerido (compra)",
                        value=a.valor_sugerido or 0,
                        format="%.2f",
                    ).props("outlined dense")
                    pago = ui.number(
                        "Valor pago", value=a.valor_pago or 0, format="%.2f",
                    ).props("outlined dense")
                    status = ui.select(
                        {s: s.upper() for s in STATUS_AVALIACAO},
                        label="Status", value=a.status,
                    ).props("outlined dense")
                    fotos = ui.input(
                        "URLs das fotos (uma por linha)", value=a.fotos_url or "",
                    ).props("outlined dense").classes("erp-form-full")
                    obs = ui.textarea(
                        "Observações internas", value=a.obs_interna or "",
                    ).props("outlined dense").classes("erp-form-full")

            def salvar():
                sug = float(sugerido.value or 0)
                pag = float(pago.value or 0)
                salvar_avaliacao_completa(avaliacao_id, {
                    "fotos_url": fotos.value or "",
                    "valor_fipe": float(fipe.value or 0),
                    "valor_sugerido": sug,
                    "valor_pago": pag,
                    "margem": sug - pag if pag else 0,
                    "obs_interna": obs.value or "",
                    "status": status.value,
                })
                salvar_avaliacao_status(avaliacao_id, status.value)
                ui.notify("Avaliação salva!", type="positive")
                dlg.close()
                tabela.refresh()

            with ui.row().classes("erp-dialog-botoes"):
                ui.button("Fechar", on_click=dlg.close).props("flat no-caps")
                ui.button("Salvar", on_click=salvar).classes("btn btn-preto").props(
                    "unelevated no-caps"
                )
            dlg.open()

    tabela()
