from nicegui import ui

from loja.admin.layout import ConfirmacaoExclusao, ajuda
from loja.crm_repo import (
    excluir_popup,
    listar_popups,
    salvar_popup,
)
from loja.repositorio import (
    ORIGENS,
    listar_campanhas,
    listar_todos_veiculos,
    salvar_campanha,
    salvar_veiculo,
)


def pagina_marketing() -> None:
    cx = ConfirmacaoExclusao()
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Marketing</h2>"
        "<p>Campanhas, pop-up e destaques</p></div></div>"
    )
    ajuda("Organize de onde veio o cliente e destaque carros no site.")

    with ui.tabs().classes("w-full") as tabs:
        t1 = ui.tab("Campanhas")
        t2 = ui.tab("Pop-up")
        t3 = ui.tab("Destaques")

    with ui.tab_panels(tabs, value=t1).classes("w-full"):
        with ui.tab_panel(t1):
            _campanhas()
        with ui.tab_panel(t2):
            _popups()
        with ui.tab_panel(t3):
            _destaques()


def _campanhas() -> None:
    @ui.refreshable
    def lista():
        for c in listar_campanhas():
            status = "Ativa" if c.ativa else "Pausada"
            with ui.row().classes("w-full items-center justify-between erp-resumo-item"):
                ui.label(f"{c.nome} · {c.origem} · {status}")
                ui.button(
                    "Alternar",
                    on_click=lambda cid=c.id, a=c.ativa: (
                        salvar_campanha({"ativa": not a}, cid),
                        lista.refresh(),
                    ),
                ).props("flat dense")

    def nova():
        with ui.dialog() as dlg, ui.card().classes("erp-dialog"):
            ui.label("Nova campanha").classes("erp-dialog-titulo")
            nome = ui.input("Nome")
            origem = ui.select(ORIGENS, label="Canal", value="instagram")

            def salvar():
                if not nome.value:
                    return
                salvar_campanha({"nome": nome.value, "origem": origem.value, "ativa": True})
                ui.notify("Campanha criada!", type="positive")
                dlg.close()
                lista.refresh()

            ui.button("Salvar", on_click=salvar).classes("btn btn-preto")
            dlg.open()

    ui.button("+ Campanha", on_click=nova).classes("btn btn-preto").props("unelevated no-caps")
    lista()


def _popups() -> None:
    @ui.refreshable
    def lista():
        for p in listar_popups():
            with ui.element("div").classes("erp-painel"):
                ui.html(
                    f"<strong>{p.titulo or 'Sem título'}</strong> — "
                    f"{'ATIVO' if p.ativo else 'inativo'}"
                )
                ui.html(f"<p>{p.texto}</p>")
                with ui.row():
                    ui.button(
                        "Ativar" if not p.ativo else "Desativar",
                        on_click=lambda pid=p.id, a=p.ativo: (
                            salvar_popup({"ativo": not a}, pid),
                            lista.refresh(),
                        ),
                    ).props("flat dense")
                    ui.button(
                        "Excluir",
                        on_click=lambda pid=p.id, tit=p.titulo: cx.pedir(
                            f"o pop-up «{tit or 'sem título'}»",
                            lambda p_id=pid: (
                                excluir_popup(p_id),
                                lista.refresh(),
                                ui.notify("Pop-up excluído.", type="warning"),
                            ),
                        ),
                    ).props("flat dense color=negative")

    def novo():
        with ui.dialog() as dlg, ui.card().classes("erp-dialog"):
            ui.label("Novo pop-up").classes("erp-dialog-titulo")
            titulo = ui.input("Título")
            texto = ui.textarea("Texto")
            link = ui.input("Link", value="/estoque")
            ativo = ui.checkbox("Ativar agora", value=False)

            def salvar():
                salvar_popup({
                    "titulo": titulo.value or "",
                    "texto": texto.value or "",
                    "link": link.value or "",
                    "ativo": ativo.value,
                })
                dlg.close()
                lista.refresh()

            ui.button("Salvar", on_click=salvar).classes("btn btn-preto")
            dlg.open()

    ui.button("+ Pop-up", on_click=novo).classes("btn btn-preto").props("unelevated no-caps")
    lista()


def _destaques() -> None:
    ui.label(
        "Marque um veículo como destaque na home. "
        "Use a imagem de destaque 720×480 no cadastro do veículo."
    )

    @ui.refreshable
    def lista():
        for v in listar_todos_veiculos():
            if v.status != "disponivel":
                continue
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(f"{v.marca} {v.modelo} {'★' if v.destaque else ''}")
                ui.button(
                    "Remover destaque" if v.destaque else "Destacar",
                    on_click=lambda vid=v.id, d=v.destaque: (
                        salvar_veiculo({"destaque": not d}, vid),
                        lista.refresh(),
                    ),
                ).props("flat dense")

    lista()
