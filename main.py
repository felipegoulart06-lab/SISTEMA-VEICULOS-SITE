import os
from pathlib import Path

from nicegui import app, ui

from loja.admin.login import pagina_login
from loja.admin.trocar_senha import pagina_trocar_senha
from loja.admin.master import pagina_master_login
from loja.admin.spa_erp import montar_erp_spa, normalizar_rota_erp
from loja.admin.spa_master import montar_master_spa, normalizar_rota_master
from loja.componentes import (
    barra_social,
    cabecalho,
    encerrar_pagina_site,
    injetar_tema,
)
from loja.database import init_db
from loja.pagina_conteudo import montar_pagina_conteudo, obter_pagina
from loja.pagina_detalhe import montar_pagina_detalhe
from loja.plataforma import listar_contas, obter_conta_por_slug
from loja.repositorio import (
    FiltrosEstoque,
    config_como_dict,
    obter_veiculo_publico,
)
from loja.spa_site import montar_site_spa
from loja.tenant_ctx import ligar_tenant, site_url

STATIC = Path(__file__).resolve().parent / "loja" / "static"
STORAGE = Path(__file__).resolve().parent / "dados" / "storage"
STORAGE.mkdir(parents=True, exist_ok=True)
app.add_static_files("/static", STATIC)
app.add_static_files("/media", STORAGE)

init_db()

CSS_SITE = "/static/estilo.css?v=19"


def ativar_loja(slug: str) -> bool:
    conta = obter_conta_por_slug(slug)
    if conta is None or not conta.ativa:
        return False
    ligar_tenant(conta.slug)
    return True


def _head_site(titulo: str, descricao: str = "") -> None:
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    ui.add_head_html(f'<link rel="stylesheet" href="{CSS_SITE}">')
    ui.add_head_html(
        '<link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">'
    )
    injetar_tema()
    ui.add_head_html(f"<title>{titulo}</title>")
    if descricao:
        ui.add_head_html(f'<meta name="description" content="{descricao}">')


def _filtros_estoque() -> FiltrosEstoque:
    try:
        dados = app.storage.client.get("filtros_estoque")
        if isinstance(dados, dict):
            return FiltrosEstoque(
                marca=dados.get("marca"),
                ano=dados.get("ano"),
                combustivel=dados.get("combustivel"),
                cor=dados.get("cor"),
                tipo=dados.get("tipo"),
                busca=dados.get("busca") or "",
                ordenar=dados.get("ordenar") or "recente",
                pagina=int(dados.get("pagina") or 1),
            )
    except Exception:
        pass
    return FiltrosEstoque()


def _salvar_filtros_estoque(filtros: FiltrosEstoque) -> None:
    try:
        app.storage.client["filtros_estoque"] = {
            "marca": filtros.marca,
            "ano": filtros.ano,
            "combustivel": filtros.combustivel,
            "cor": filtros.cor,
            "tipo": filtros.tipo,
            "busca": filtros.busca,
            "ordenar": filtros.ordenar,
            "pagina": filtros.pagina,
        }
    except Exception:
        pass


# ---- Plataforma / landing ----

@ui.page("/")
def pagina_plataforma() -> None:
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    ui.add_head_html('<link rel="stylesheet" href="/static/admin.css?v=20">')
    ui.add_head_html(
        "<style>body{margin:0;font-family:Inter,Segoe UI,sans-serif;background:#eef1f6}"
        ".plat{max-width:960px;margin:0 auto;padding:48px 20px}"
        ".plat h1{font-size:32px;margin:0 0 8px}.plat p{color:#6b7280}"
        ".plat-acoes{display:flex;gap:12px;flex-wrap:wrap;margin:28px 0}"
        ".plat-card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;"
        "padding:18px;margin-top:12px}.plat-card a{color:#1e3a5f;font-weight:700}"
        "</style>"
    )
    contas = listar_contas(apenas_ativas=True)
    with ui.element("div").classes("plat"):
        ui.html("<h1>Plataforma White Label</h1>")
        ui.html(
            "<p>ERP + Site para lojas de veículos. "
            "Cada conta possui ambiente isolado.</p>"
        )
        with ui.element("div").classes("plat-acoes"):
            ui.button(
                "Admin Master",
                on_click=lambda: ui.navigate.to("/master/login"),
            ).props("unelevated no-caps").style("background:#1e3a5f;color:#fff")
            ui.button(
                "Login da loja",
                on_click=lambda: ui.navigate.to("/admin/login"),
            ).props("outline no-caps")
        ui.html("<h3 style='margin-top:32px'>Lojas ativas</h3>")
        if not contas:
            ui.html("<p>Nenhuma conta ativa. Crie uma no painel Master.</p>")
        else:
            for c in contas:
                with ui.element("div").classes("plat-card"):
                    ui.html(
                        f"<strong>{c.nome}</strong><br>"
                        f'<a href="/loja/{c.slug}/" target="_blank">'
                        f"Abrir site /loja/{c.slug}/</a>"
                    )


def _loja_nao_encontrada() -> None:
    ui.html("<h1>Loja não encontrada</h1>")
    ui.html("<p>Esta conta não existe ou está inativa.</p>")
    ui.link("Voltar à plataforma", "/")


# ---- Site público por conta: /loja/{slug}/... (SPA nos menus) ----

@ui.page("/loja/{slug}/")
@ui.page("/loja/{slug}")
def pagina_inicial_loja(slug: str) -> None:
    if not montar_site_spa(slug, "/"):
        _loja_nao_encontrada()


@ui.page("/loja/{slug}/estoque")
def pagina_estoque_loja(slug: str) -> None:
    if not montar_site_spa(slug, "/estoque"):
        _loja_nao_encontrada()


@ui.page("/loja/{slug}/veiculo/{veiculo_id}")
def pagina_veiculo_loja(slug: str, veiculo_id: int) -> None:
    if not ativar_loja(slug):
        _loja_nao_encontrada()
        return
    cfg = config_como_dict()
    v = obter_veiculo_publico(veiculo_id)
    if v is None:
        _head_site(f"{cfg['nome']} — Veículo não encontrado")
        barra_social()
        cabecalho(lambda _: None)
        with ui.element("div").classes("pagina-detalhe-erro"):
            ui.html("<h1>Veículo não encontrado</h1>")
            ui.link("Ver estoque", site_url("/estoque")).classes("btn btn-preto")
        encerrar_pagina_site()
        return

    _head_site(f"{v.marca} {v.modelo} {v.ano} — {cfg['nome']}")

    def buscar_detalhe(texto: str) -> None:
        filtros = _filtros_estoque()
        filtros.busca = texto
        filtros.pagina = 1
        _salvar_filtros_estoque(filtros)
        ui.navigate.to(site_url("/estoque"))

    barra_social()
    cabecalho(buscar_detalhe)
    with ui.element("div").classes("corpo-detalhe-wrap"):
        montar_pagina_detalhe(veiculo_id)
    encerrar_pagina_site()


@ui.page("/loja/{slug}/financiamento")
def pagina_financiamento_loja(
    slug: str,
    marca: str = "",
    modelo: str = "",
    ano: str = "",
    cor: str = "",
    valor: float = 0,
    veiculo_id: int = 0,
) -> None:
    kwargs = {}
    if marca or modelo or ano or cor or valor or veiculo_id:
        kwargs = {
            "marca": marca,
            "modelo": modelo,
            "ano": ano,
            "cor": cor,
            "valor": valor,
            "veiculo_id": veiculo_id,
        }
    if not montar_site_spa(slug, "/financiamento", financ_kwargs=kwargs):
        _loja_nao_encontrada()


@ui.page("/loja/{slug}/empresa")
def pagina_empresa_loja(slug: str) -> None:
    if not montar_site_spa(slug, "/empresa"):
        _loja_nao_encontrada()


@ui.page("/loja/{slug}/contato")
def pagina_contato_loja(slug: str) -> None:
    if not montar_site_spa(slug, "/contato"):
        _loja_nao_encontrada()


@ui.page("/loja/{slug}/privacidade")
def pagina_privacidade_loja(slug: str) -> None:
    _pagina_conteudo_loja(slug, "privacidade")


@ui.page("/loja/{slug}/lgpd")
def pagina_lgpd_loja(slug: str) -> None:
    _pagina_conteudo_loja(slug, "lgpd")


def _pagina_conteudo_loja(slug: str, pagina_slug: str) -> None:
    if not ativar_loja(slug):
        _loja_nao_encontrada()
        return
    cfg = config_como_dict()
    pagina = obter_pagina(pagina_slug)
    titulo = pagina.titulo if pagina else "Página"
    _head_site(
        f"{cfg['nome']} — {titulo}",
        pagina.seo_descricao if pagina else "",
    )
    barra_social()
    cabecalho(lambda _: None)
    with ui.element("div").classes("corpo-institucional-wrap"):
        montar_pagina_conteudo(pagina_slug)
    encerrar_pagina_site()


@ui.page("/loja/{slug}/avaliacao")
def pagina_avaliacao_loja(slug: str) -> None:
    if not montar_site_spa(slug, "/avaliacao"):
        _loja_nao_encontrada()


# Compatibilidade: rotas antigas → loja demo sigma
@ui.page("/estoque")
def _legado_estoque() -> None:
    ui.navigate.to("/loja/sigma/estoque")


@ui.page("/avaliacao")
def _legado_avaliacao() -> None:
    ui.navigate.to("/loja/sigma/avaliacao")


@ui.page("/financiamento")
def _legado_financiamento() -> None:
    ui.navigate.to("/loja/sigma/financiamento")


@ui.page("/empresa")
def _legado_empresa() -> None:
    ui.navigate.to("/loja/sigma/empresa")


@ui.page("/contato")
def _legado_contato() -> None:
    ui.navigate.to("/loja/sigma/contato")


@ui.page("/veiculo/{veiculo_id}")
def _legado_veiculo(veiculo_id: int) -> None:
    ui.navigate.to(f"/loja/sigma/veiculo/{veiculo_id}")


# ---- Admin Master (SPA: menu troca conteúdo sem reload) ----

@ui.page("/master/login")
def rota_master_login() -> None:
    pagina_master_login()


@ui.page("/master")
@ui.page("/master/{resto:path}")
def rota_master_spa(resto: str = "") -> None:
    if resto == "login":
        pagina_master_login()
        return
    rota = normalizar_rota_master("/master" if not resto else f"/master/{resto}")
    montar_master_spa(rota)


# ---- ERP da loja (SPA: menu troca conteúdo sem reload) ----

@ui.page("/admin/login")
def rota_login() -> None:
    pagina_login()


@ui.page("/admin/trocar-senha")
def rota_trocar_senha() -> None:
    pagina_trocar_senha()


@ui.page("/admin")
@ui.page("/admin/{resto:path}")
def rota_erp_spa(resto: str = "") -> None:
    if resto in ("login", "trocar-senha"):
        if resto == "login":
            pagina_login()
        else:
            pagina_trocar_senha()
        return
    rota = normalizar_rota_erp("/admin" if not resto else f"/admin/{resto}")
    montar_erp_spa(rota)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Plataforma White Label — Gestão Veículos",
        favicon="🚗",
        reload=False,
        port=8080,
        storage_secret=os.getenv(
            "SECRET_KEY", "sigma-erp-secret-change-in-production",
        ),
    )
