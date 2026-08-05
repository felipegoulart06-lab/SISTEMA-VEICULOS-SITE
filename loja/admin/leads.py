from nicegui import ui

from loja.admin.layout import ConfirmacaoExclusao, ajuda
from loja.crm_repo import (
    LABEL_LEAD,
    STATUS_LEAD,
    adicionar_lead_atividade,
    listar_lead_atividades,
    listar_lead_tarefas,
    mover_lead_status,
    salvar_lead_tarefa,
)
from loja.repositorio import (
    ORIGENS,
    excluir_lead,
    listar_campanhas,
    listar_leads,
    listar_veiculos_opcoes,
    salvar_lead,
)


def pagina_leads() -> None:
    cx = ConfirmacaoExclusao()
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Leads (CRM)</h2>"
        "<p>Pipeline visual do interesse até a venda</p></div></div>"
    )
    ajuda(
        "Arraste o lead pelo funil: Novo → Contato → Negociação → Financiamento → Fechado. "
        "Clique no card para ver histórico e tarefas."
    )

    @ui.refreshable
    def kanban() -> None:
        leads = listar_leads()
        veiculos = listar_veiculos_opcoes()
        por_status: dict[str, list] = {s: [] for s in STATUS_LEAD}
        for l in leads:
            st = l.status if l.status in por_status else "novo"
            # legado
            if l.status == "contatado":
                st = "contato"
            elif l.status in ("visita", "proposta"):
                st = "negociacao"
            elif l.status == "fechou":
                st = "fechado"
            por_status[st].append(l)

        with ui.element("div").classes("kanban"):
            for status in STATUS_LEAD:
                with ui.element("div").classes("kanban-col"):
                    ui.html(
                        f'<div class="kanban-col-titulo">'
                        f"{LABEL_LEAD[status]} "
                        f'<span>({len(por_status[status])})</span></div>'
                    )
                    for l in por_status[status]:
                        idx = STATUS_LEAD.index(status)
                        veiculo = veiculos.get(l.veiculo_id, "")
                        with ui.element("div").classes("kanban-card"):
                            ui.html(f"<strong>{l.nome}</strong>")
                            ui.html(f'<p class="kanban-meta">{l.telefone}</p>')
                            if veiculo:
                                ui.html(f'<p class="kanban-meta">{veiculo}</p>')
                            if getattr(l, "vendedor", ""):
                                ui.html(
                                    f'<p class="kanban-meta">Vendedor: {l.vendedor}</p>'
                                )
                            with ui.row().classes("kanban-acoes"):
                                if idx > 0:
                                    ui.button(
                                        icon="chevron_left",
                                        on_click=lambda lid=l.id, i=idx: (
                                            mover_lead_status(lid, STATUS_LEAD[i - 1]),
                                            kanban.refresh(),
                                        ),
                                    ).props("flat dense size=sm")
                                ui.button(
                                    icon="open_in_new",
                                    on_click=lambda lid=l.id: abrir_detalhe(lid),
                                ).props("flat dense size=sm")
                                if idx < len(STATUS_LEAD) - 1 and status != "perdido":
                                    ui.button(
                                        icon="chevron_right",
                                        on_click=lambda lid=l.id, i=idx: (
                                            mover_lead_status(lid, STATUS_LEAD[i + 1]),
                                            kanban.refresh(),
                                        ),
                                    ).props("flat dense size=sm")
                                if status != "perdido":
                                    ui.button(
                                        icon="close",
                                        on_click=lambda lid=l.id: (
                                            mover_lead_status(lid, "perdido"),
                                            kanban.refresh(),
                                        ),
                                    ).props("flat dense size=sm color=negative")

    def abrir_detalhe(lead_id: int) -> None:
        from loja.database import get_session
        from loja.models import Lead

        with get_session() as db:
            lead = db.get(Lead, lead_id)
            if lead:
                db.expunge(lead)
        if not lead:
            return

        with ui.dialog() as dlg, ui.card().classes("erp-dialog erp-dialog-wide"):
            ui.label(f"Lead — {lead.nome}").classes("erp-dialog-titulo")
            with ui.element("div").classes("erp-form-body"):
                with ui.element("div").classes("erp-form-grid"):
                    nome = ui.input("Nome", value=lead.nome).props("outlined dense")
                    telefone = ui.input(
                        "Telefone", value=lead.telefone,
                    ).props("outlined dense")
                    email = ui.input(
                        "E-mail", value=lead.email or "",
                    ).props("outlined dense")
                    vendedor = ui.input(
                        "Vendedor responsável", value=lead.vendedor or "",
                    ).props("outlined dense")
                    origem = ui.select(
                        ORIGENS, label="Origem", value=lead.origem or "site",
                    ).props("outlined dense")
                    status = ui.select(
                        {s: LABEL_LEAD[s] for s in STATUS_LEAD},
                        label="Status",
                        value=lead.status if lead.status in STATUS_LEAD else "novo",
                    ).props("outlined dense")
                    obs = ui.textarea(
                        "Observações", value=lead.observacoes or "",
                    ).props("outlined dense").classes("erp-form-full")

                ui.label("Histórico").classes("erp-secao-titulo")
                for a in listar_lead_atividades(lead_id):
                    ui.html(
                        f'<p class="erp-hist">{a.criado_em.strftime("%d/%m %H:%M")} — {a.texto}</p>'
                    )
                nova_hist = ui.input("Adicionar nota no histórico").props(
                    "outlined dense"
                ).classes("erp-form-full")

                ui.label("Tarefas / lembretes").classes("erp-secao-titulo")
                for t in listar_lead_tarefas(lead_id):
                    check = "✓" if t.concluida else "○"
                    ui.html(f"<p>{check} {t.titulo}</p>")
                nova_tarefa = ui.input("Nova tarefa").props(
                    "outlined dense"
                ).classes("erp-form-full")

            def salvar():
                salvar_lead({
                    "nome": nome.value,
                    "telefone": telefone.value,
                    "email": email.value or "",
                    "vendedor": vendedor.value or "",
                    "origem": origem.value,
                    "status": status.value,
                    "observacoes": obs.value or "",
                }, lead_id)
                if nova_hist.value:
                    adicionar_lead_atividade(lead_id, nova_hist.value)
                if nova_tarefa.value:
                    salvar_lead_tarefa({
                        "lead_id": lead_id,
                        "titulo": nova_tarefa.value,
                    })
                ui.notify("Lead atualizado!", type="positive")
                dlg.close()
                kanban.refresh()

            with ui.row().classes("erp-dialog-botoes"):
                ui.button("Fechar", on_click=dlg.close).props("flat no-caps")
                ui.button(
                    "Excluir",
                    on_click=lambda l_id=lead_id, l_nome=lead.nome: cx.pedir(
                        f"o lead «{l_nome}»",
                        lambda: (
                            excluir_lead(l_id),
                            dlg.close(),
                            kanban.refresh(),
                            ui.notify("Lead excluído.", type="warning"),
                        ),
                    ),
                ).props("flat color=negative no-caps")
                ui.button("Salvar", on_click=salvar).classes("btn btn-preto").props(
                    "unelevated no-caps"
                )
            dlg.open()

    def novo_lead() -> None:
        veiculos_opts = {None: "— Nenhum —"}
        veiculos_opts.update(listar_veiculos_opcoes())
        campanhas_opts = {None: "— Nenhuma —"}
        for c in listar_campanhas():
            campanhas_opts[c.id] = c.nome

        with ui.dialog() as dlg, ui.card().classes("erp-dialog erp-dialog-wide"):
            ui.label("Novo lead").classes("erp-dialog-titulo")
            with ui.element("div").classes("erp-form-body"):
                with ui.element("div").classes("erp-form-grid"):
                    nome = ui.input("Nome").props("outlined dense")
                    telefone = ui.input("Telefone").props("outlined dense")
                    email = ui.input("E-mail").props("outlined dense")
                    vendedor = ui.input("Vendedor").props("outlined dense")
                    origem = ui.select(
                        ORIGENS, label="Origem", value="balcao",
                    ).props("outlined dense")
                    veiculo = ui.select(
                        veiculos_opts, label="Veículo de interesse", value=None,
                    ).props("outlined dense")
                    campanha = ui.select(
                        campanhas_opts, label="Campanha", value=None,
                    ).props("outlined dense")
                    obs = ui.textarea("Observações").props(
                        "outlined dense"
                    ).classes("erp-form-full")

            def salvar():
                if not nome.value or not telefone.value:
                    ui.notify("Preencha nome e telefone.", type="warning")
                    return
                salvar_lead({
                    "nome": nome.value.strip(),
                    "telefone": telefone.value.strip(),
                    "email": email.value or "",
                    "vendedor": vendedor.value or "",
                    "origem": origem.value,
                    "veiculo_id": veiculo.value,
                    "campanha_id": campanha.value,
                    "observacoes": obs.value or "",
                    "status": "novo",
                })
                ui.notify("Lead criado!", type="positive")
                dlg.close()
                kanban.refresh()

            with ui.row().classes("erp-dialog-botoes"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
                ui.button("Criar", on_click=salvar).classes("btn btn-preto").props(
                    "unelevated no-caps"
                )
            dlg.open()

    with ui.element("div").classes("erp-toolbar"):
        ui.button("+ Novo lead", on_click=novo_lead).classes("btn btn-preto").props(
            "unelevated no-caps"
        )
    kanban()
