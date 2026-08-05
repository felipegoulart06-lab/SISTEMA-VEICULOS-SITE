from nicegui import ui

from loja.admin.layout import ConfirmacaoExclusao, ajuda, id_do_evento
from loja.crm_repo import (
    excluir_custo_veiculo,
    listar_custos_veiculo,
    salvar_custo_veiculo,
)
from loja.repositorio import (
    CAMBIOS,
    COMBUSTIVEIS,
    LIMITE_LISTAGEM_ERP,
    STATUS_VEICULO,
    excluir_veiculo,
    formatar_preco,
    listar_veiculos_resumo,
    obter_veiculo,
    salvar_veiculo,
)


def pagina_veiculos() -> None:
    cx = ConfirmacaoExclusao()
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Estoque de veículos</h2>"
        "<p>Cadastre, publique e controle custos</p></div></div>"
    )
    ajuda("Cadastre aqui o carro que entrou no estoque. Use Publicar para aparecer no site.")

    @ui.refreshable
    def tabela() -> None:
        veiculos = listar_veiculos_resumo()
        if len(veiculos) >= LIMITE_LISTAGEM_ERP:
            ui.html(
                f'<p class="erp-ajuda">Exibindo os {LIMITE_LISTAGEM_ERP} veículos '
                "mais recentes. Use filtros ou exportação se precisar de mais.</p>"
            )
        colunas = [
            {"name": "id", "label": "#", "field": "id"},
            {"name": "veiculo", "label": "Veículo", "field": "veiculo"},
            {"name": "placa", "label": "Placa", "field": "placa"},
            {"name": "ano", "label": "Ano", "field": "ano"},
            {"name": "preco", "label": "Preço", "field": "preco"},
            {"name": "status", "label": "Status", "field": "status"},
            {"name": "pub", "label": "Site", "field": "pub"},
            {"name": "acoes", "label": "Ações", "field": "acoes"},
        ]
        linhas = []
        for v in veiculos:
            linhas.append({
                "id": v.id,
                "veiculo": f"{v.marca} {v.modelo}",
                "placa": getattr(v, "placa", "") or "—",
                "ano": v.ano,
                "preco": formatar_preco(v.preco),
                "status": v.status.upper(),
                "pub": "Sim" if getattr(v, "publicado", True) else "Não",
                "acoes": v.id,
            })

        tbl = ui.table(
            columns=colunas, rows=linhas, row_key="id", pagination=25
        ).classes("erp-tabela").props("flat bordered dense")

        tbl.add_slot("body-cell-acoes", """
            <q-td :props="props">
                <q-btn flat dense size="sm" icon="edit" color="primary"
                    @click="$parent.$emit('editar', props.row.id)" />
                <q-btn flat dense size="sm" icon="attach_money" color="secondary"
                    @click="$parent.$emit('custos', props.row.id)" />
                <q-btn flat dense size="sm" icon="delete" color="negative"
                    @click.stop.prevent="$parent.$emit('ask_delete', props.row.id)" />
            </q-td>
        """)
        def on_excluir(e):
            vid = id_do_evento(e)
            v = obter_veiculo(vid)
            rotulo = (
                f"o veículo «{v.marca} {v.modelo}»"
                if v else "este veículo"
            )
            cx.pedir(
                rotulo,
                lambda v_id=vid: (
                    excluir_veiculo(v_id),
                    ui.notify("Veículo excluído.", type="warning"),
                    tabela.refresh(),
                ),
            )

        tbl.on("editar", lambda e: abrir_formulario(id_do_evento(e)))
        tbl.on("custos", lambda e: abrir_custos(id_do_evento(e)))
        tbl.on("ask_delete", on_excluir)

    def abrir_custos(veiculo_id: int) -> None:
        v = obter_veiculo(veiculo_id)
        with ui.dialog() as dlg, ui.card().classes("erp-dialog"):
            ui.label(f"Custos — {v.marca} {v.modelo}" if v else "Custos").classes(
                "erp-dialog-titulo"
            )

            @ui.refreshable
            def lista_custos():
                for c in listar_custos_veiculo(veiculo_id):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label(f"{c.descricao} — {formatar_preco(c.valor)}")
                        ui.button(
                            icon="delete",
                            on_click=lambda cid=c.id, desc=c.descricao: cx.pedir(
                                f"o custo «{desc}»",
                                lambda c_id=cid: (
                                    excluir_custo_veiculo(c_id),
                                    lista_custos.refresh(),
                                ),
                            ),
                        ).props("flat dense color=negative")

            lista_custos()
            desc = ui.input("Descrição (ex.: funilaria)").classes("w-full")
            valor = ui.number("Valor", value=0, format="%.2f")

            def add():
                if not desc.value:
                    ui.notify("Informe a descrição.", type="warning")
                    return
                salvar_custo_veiculo({
                    "veiculo_id": veiculo_id,
                    "descricao": desc.value,
                    "valor": float(valor.value or 0),
                })
                lista_custos.refresh()
                ui.notify("Custo adicionado.", type="positive")

            with ui.row():
                ui.button("Adicionar", on_click=add).props("btn btn-preto")
                ui.button("Fechar", on_click=dlg.close).props("flat")
            dlg.open()

    def abrir_formulario(veiculo_id: int | None = None) -> None:
        v = obter_veiculo(veiculo_id) if veiculo_id else None
        titulo = "Editar veículo" if v else "Novo veículo"

        with ui.dialog() as dlg, ui.card().classes("erp-dialog erp-dialog-wide"):
            ui.label(titulo).classes("erp-dialog-titulo")
            with ui.element("div").classes("erp-form-body"):
                with ui.element("div").classes("erp-form-grid"):
                    marca = ui.input("Marca", value=v.marca if v else "").props(
                        "outlined dense"
                    )
                    modelo = ui.input("Modelo", value=v.modelo if v else "").props(
                        "outlined dense"
                    )
                with ui.element("div").classes("erp-form-row-3"):
                    ano = ui.number(
                        "Ano", value=v.ano if v else 2024, format="%.0f",
                    ).props("outlined dense")
                    km = ui.number(
                        "KM", value=v.km if v else 0, format="%.0f",
                    ).props("outlined dense")
                    views = ui.number(
                        "Visualizações",
                        value=getattr(v, "visualizacoes", 0) if v else 0,
                        format="%.0f",
                    ).props("outlined dense")
                with ui.element("div").classes("erp-form-grid"):
                    combustivel = ui.select(
                        COMBUSTIVEIS, label="Combustível",
                        value=v.combustivel if v else "FLEX",
                    ).props("outlined dense")
                    cambio = ui.select(
                        CAMBIOS, label="Câmbio",
                        value=v.cambio if v else "MANUAL",
                    ).props("outlined dense")
                with ui.element("div").classes("erp-form-row-3"):
                    preco = ui.number(
                        "Preço venda", value=v.preco if v else 0, format="%.2f",
                    ).props("outlined dense")
                    custo = ui.number(
                        "Custo compra", value=v.custo if v else 0, format="%.2f",
                    ).props("outlined dense")
                    fipe = ui.number(
                        "FIPE (manual)",
                        value=getattr(v, "fipe", 0) if v else 0,
                        format="%.2f",
                    ).props("outlined dense")
                with ui.element("div").classes("erp-form-row-3"):
                    placa = ui.input(
                        "Placa", value=getattr(v, "placa", "") if v else "",
                    ).props("outlined dense")
                    chassi = ui.input(
                        "Chassi", value=getattr(v, "chassi", "") if v else "",
                    ).props("outlined dense")
                    renavam = ui.input(
                        "Renavam", value=getattr(v, "renavam", "") if v else "",
                    ).props("outlined dense")
                with ui.element("div").classes("erp-form-grid"):
                    cor = ui.input("Cor", value=v.cor if v else "BRANCO").props(
                        "outlined dense"
                    )
                    tipo = ui.input(
                        "Tipo", value=v.tipo if v else "AUTOMÓVEL",
                    ).props("outlined dense")
                    badge = ui.input(
                        "Etiqueta/badge", value=v.badge if v else "PRONTA ENTREGA",
                    ).props("outlined dense")
                    status = ui.select(
                        {s: s.upper() for s in STATUS_VEICULO},
                        label="Status", value=v.status if v else "disponivel",
                    ).props("outlined dense")
                    etiquetas = ui.input(
                        "Etiquetas (separadas por vírgula)",
                        value=getattr(v, "etiquetas", "") if v else "",
                    ).props("outlined dense").classes("erp-form-full")
                    imagem = ui.input(
                        "URL da foto principal", value=v.imagem if v else "",
                    ).props("outlined dense").classes("erp-form-full")
                    imagem_destaque = ui.input(
                        "URL da imagem de destaque (720×480 px)",
                        value=getattr(v, "imagem_destaque", "") if v else "",
                    ).props("outlined dense").classes("erp-form-full")
                    ui.label(
                        "Usada na home quando o veículo for destaque. "
                        "Recomendado: 720px de largura × 480px de altura."
                    ).classes("text-caption text-grey-7 q-mb-sm")
                    videos = ui.input(
                        "URL do vídeo",
                        value=getattr(v, "videos_url", "") if v else "",
                    ).props("outlined dense").classes("erp-form-full")
                    opcionais = ui.textarea(
                        "Opcionais",
                        value=getattr(v, "opcionais", "") if v else "",
                    ).props("outlined dense").classes("erp-form-full")
                    historico = ui.textarea(
                        "Histórico do veículo",
                        value=getattr(v, "historico_texto", "") if v else "",
                    ).props("outlined dense").classes("erp-form-full")
                    descricao = ui.textarea(
                        "Descrição no site", value=v.descricao if v else "",
                    ).props("outlined dense").classes("erp-form-full")
                with ui.element("div").classes("erp-form-checks"):
                    destaque = ui.checkbox(
                        "Veículo destaque na home (imagem 720×480)",
                        value=v.destaque if v else False,
                    )
                    publicado = ui.checkbox(
                        "Publicar no site",
                        value=getattr(v, "publicado", True) if v else True,
                    )

            def salvar():
                if not marca.value or not modelo.value:
                    ui.notify("Informe marca e modelo.", type="warning")
                    return
                salvar_veiculo({
                    "marca": marca.value.upper().strip(),
                    "modelo": modelo.value.upper().strip(),
                    "ano": int(ano.value or 0),
                    "km": int(km.value or 0),
                    "combustivel": combustivel.value,
                    "cambio": cambio.value,
                    "preco": float(preco.value or 0),
                    "custo": float(custo.value or 0),
                    "fipe": float(fipe.value or 0),
                    "placa": (placa.value or "").upper(),
                    "chassi": chassi.value or "",
                    "renavam": renavam.value or "",
                    "cor": (cor.value or "BRANCO").upper(),
                    "tipo": (tipo.value or "AUTOMÓVEL").upper(),
                    "badge": badge.value or "",
                    "etiquetas": etiquetas.value or "",
                    "imagem": imagem.value or "",
                    "imagem_destaque": imagem_destaque.value or "",
                    "videos_url": videos.value or "",
                    "opcionais": opcionais.value or "",
                    "historico_texto": historico.value or "",
                    "descricao": descricao.value or "",
                    "status": status.value,
                    "destaque": destaque.value,
                    "publicado": publicado.value,
                    "visualizacoes": int(views.value or 0),
                }, veiculo_id)
                ui.notify("Veículo salvo!", type="positive")
                dlg.close()
                tabela.refresh()

            with ui.row().classes("erp-dialog-botoes"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
                ui.button("Salvar", on_click=salvar).classes("btn btn-preto").props(
                    "unelevated no-caps"
                )
            dlg.open()

    with ui.element("div").classes("erp-toolbar"):
        ui.button("+ Novo veículo", on_click=lambda: abrir_formulario()).classes(
            "btn btn-preto"
        ).props("unelevated no-caps")
    tabela()
