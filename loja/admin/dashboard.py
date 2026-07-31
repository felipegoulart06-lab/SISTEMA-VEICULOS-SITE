from nicegui import ui

from loja.admin.layout import ajuda
from loja.repositorio import formatar_preco, metricas_dashboard


CORES_ORIGEM = {
    "site": "#c0392b",
    "google": "#4285f4",
    "instagram": "#e1306c",
    "facebook": "#1877f2",
    "olx": "#6e0ad6",
    "indicacao": "#10b981",
    "balcao": "#f59e0b",
}


def pagina_dashboard() -> None:
    m = metricas_dashboard()

    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Visão geral</h2>"
        "<p>Números do dia a dia da sua loja</p>"
        "</div></div>"
    )
    ajuda("Acompanhe vendas, leads e compromissos. Tudo em um só lugar.")

    with ui.element("div").classes("erp-cards"):
        _card("Faturamento do mês", formatar_preco(m["faturamento_mes"]), "attach_money", "verde")
        _card("Lucro estimado", formatar_preco(m["lucro_estimado"]), "trending_up", "azul")
        _card("Disponíveis", str(m["disponiveis"]), "directions_car", "azul")
        _card("Vendidos", str(m["vendidos"]), "check_circle", "verde")
        _card("Leads novos", str(m["leads_novos"]), "person_add", "vermelho")
        _card("Em negociação", str(m["leads_negociacao"]), "handshake", "amarelo")
        _card("Avaliações", str(m["avaliacoes_novas"]), "request_quote", "vermelho")
        _card("Reservados", str(m["reservados"]), "schedule", "amarelo")

    with ui.element("div").classes("erp-linha-dupla"):
        with ui.element("div").classes("erp-painel"):
            ui.html(
                '<div class="erp-painel-titulo-row">'
                '<span class="material-icons erp-painel-ico">visibility</span>'
                "<span>Anúncios mais visualizados</span></div>"
            )
            if not m["top_anuncios"]:
                ui.html('<p class="erp-vazio">Nenhum anúncio ainda.</p>')
            else:
                for item in m["top_anuncios"]:
                    ui.html(
                        f'<div class="erp-resumo-item">'
                        f"<span>{item['nome']}</span>"
                        f'<strong class="erp-num">{item["views"]} views</strong></div>'
                    )

        with ui.element("div").classes("erp-painel"):
            ui.html(
                '<div class="erp-painel-titulo-row">'
                '<span class="material-icons erp-painel-ico">event</span>'
                "<span>Agenda do dia</span></div>"
            )
            if not m["agenda_dia"]:
                ui.html('<p class="erp-vazio">Nenhum compromisso hoje.</p>')
            else:
                for c in m["agenda_dia"]:
                    ui.html(
                        f'<div class="erp-resumo-item">'
                        f"<span>{c['hora']} · {c['titulo']}</span>"
                        f'<strong class="erp-num">{c["tipo"]}</strong></div>'
                    )

    with ui.element("div").classes("erp-linha-dupla"):
        with ui.element("div").classes("erp-painel"):
            ui.html(
                '<div class="erp-painel-titulo-row">'
                '<span class="material-icons erp-painel-ico">pie_chart</span>'
                "<span>Leads por origem</span></div>"
            )
            if not m["por_origem"]:
                ui.html('<p class="erp-vazio">Nenhum lead ainda.</p>')
            else:
                total = sum(x[1] for x in m["por_origem"])
                for origem, qtd in m["por_origem"]:
                    pct = int(qtd / max(total, 1) * 100)
                    cor = CORES_ORIGEM.get(origem.lower(), "#c0392b")
                    ui.html(
                        f'<div class="erp-barra-origem">'
                        f'<div class="erp-barra-label">'
                        f"<span>{origem.upper()}</span>"
                        f'<span class="erp-barra-qtd">{qtd} · {pct}%</span></div>'
                        f'<div class="erp-barra-track">'
                        f'<div class="erp-barra-fill" style="width:{pct}%;'
                        f"background:{cor}\"></div></div></div>"
                    )

        with ui.element("div").classes("erp-painel"):
            ui.html(
                '<div class="erp-painel-titulo-row">'
                '<span class="material-icons erp-painel-ico">history</span>'
                "<span>Últimas atividades</span></div>"
            )
            if not m.get("atividades"):
                ui.html('<p class="erp-vazio">Sem atividades recentes.</p>')
            else:
                for a in m["atividades"]:
                    ui.html(
                        f'<div class="erp-resumo-item">'
                        f"<span>{a['texto']}</span>"
                        f'<strong class="erp-num">{a["quando"]}</strong></div>'
                    )


def _card(titulo: str, valor: str, icone: str, cor: str) -> None:
    ui.html(
        f'<div class="erp-stat erp-stat-{cor}">'
        f'<div class="erp-stat-ico"><span class="material-icons">{icone}</span></div>'
        f'<div class="erp-stat-body">'
        f'<span class="erp-stat-label">{titulo}</span>'
        f'<strong class="erp-stat-valor">{valor}</strong></div></div>'
    )
