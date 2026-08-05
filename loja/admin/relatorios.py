import csv
import io

from nicegui import ui

from loja.admin.layout import ajuda
from loja.crm_repo import (
    listar_lancamentos,
    lucro_por_veiculo,
    relatorio_leads,
    relatorio_vendas,
    resumo_financeiro,
)
from loja.repositorio import formatar_preco, listar_veiculos_resumo


def pagina_relatorios() -> None:
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Relatórios</h2>"
        "<p>Vendas, leads, financeiro e estoque</p></div></div>"
    )
    ajuda("Veja os números e baixe CSV para abrir no Excel.")

    with ui.tabs().classes("w-full") as tabs:
        t1 = ui.tab("Vendas")
        t2 = ui.tab("Leads")
        t3 = ui.tab("Financeiro")
        t4 = ui.tab("Veículos")

    with ui.tab_panels(tabs, value=t1).classes("w-full"):
        with ui.tab_panel(t1):
            vendas = relatorio_vendas()
            if not vendas:
                ui.html('<p class="erp-vazio">Nenhuma venda registrada.</p>')
            else:
                for v in vendas:
                    ui.html(
                        f'<div class="erp-resumo-item">'
                        f"<span>{v['data']} · {v['veiculo']}</span>"
                        f'<strong>{formatar_preco(v["lucro"])} lucro</strong></div>'
                    )
                ui.button(
                    "Exportar CSV",
                    on_click=lambda: _download_csv(
                        "vendas.csv",
                        ["data", "veiculo", "preco", "custo", "lucro"],
                        vendas,
                    ),
                ).props("flat")

            ui.html('<h3 class="erp-secao-titulo">Lucro por veículo</h3>')
            for d in lucro_por_veiculo():
                ui.html(
                    f'<div class="erp-resumo-item"><span>{d["veiculo"]}</span>'
                    f'<strong>{formatar_preco(d["lucro"])}</strong></div>'
                )

        with ui.tab_panel(t2):
            leads = relatorio_leads()
            for l in leads[:50]:
                ui.html(
                    f'<div class="erp-resumo-item">'
                    f"<span>{l['data']} · {l['nome']} · {l['origem']}</span>"
                    f"<strong>{l['status']}</strong></div>"
                )
            ui.button(
                "Exportar CSV",
                on_click=lambda: _download_csv(
                    "leads.csv",
                    ["data", "nome", "telefone", "origem", "status", "vendedor"],
                    leads,
                ),
            ).props("flat")

        with ui.tab_panel(t3):
            r = resumo_financeiro()
            ui.html(
                f"<p>Entradas mês: <strong>{formatar_preco(r['entradas_mes'])}</strong><br>"
                f"Saídas mês: <strong>{formatar_preco(r['saidas_mes'])}</strong><br>"
                f"Fluxo: <strong>{formatar_preco(r['fluxo_mes'])}</strong></p>"
            )
            lanc = [
                {
                    "tipo": x.tipo,
                    "categoria": x.categoria,
                    "descricao": x.descricao,
                    "valor": x.valor,
                    "pago": "sim" if x.pago else "nao",
                }
                for x in listar_lancamentos()
            ]
            ui.button(
                "Exportar CSV",
                on_click=lambda: _download_csv(
                    "financeiro.csv",
                    ["tipo", "categoria", "descricao", "valor", "pago"],
                    lanc,
                ),
            ).props("flat")

        with ui.tab_panel(t4):
            for v in listar_veiculos_resumo()[:200]:
                ui.html(
                    f'<div class="erp-resumo-item">'
                    f"<span>{v.marca} {v.modelo} {v.ano}</span>"
                    f"<strong>{v.status}</strong></div>"
                )


def _download_csv(nome: str, campos: list[str], rows: list[dict]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=campos, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in campos})
    ui.download(buf.getvalue().encode("utf-8-sig"), nome)
