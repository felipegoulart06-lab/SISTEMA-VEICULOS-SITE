import os
from pathlib import Path

from nicegui import app, ui
from starlette.middleware.base import BaseHTTPMiddleware

from loja.admin.login import pagina_login
from loja.admin.trocar_senha import pagina_trocar_senha
from loja.admin.master import pagina_master_login
from loja.admin.spa_erp import montar_erp_spa, normalizar_rota_erp
from loja.admin.spa_master import montar_master_spa, normalizar_rota_master
from loja.auth import logado
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
from loja.roteamento_host import (
    get_contexto_host,
    resolver_contexto_host,
    set_contexto_host,
)
from loja.seguranca import SecurityHeadersMiddleware, validar_ambiente
from loja.spa_site import CSS_LAYOUT_FIX, montar_site_spa
from loja.tenant_ctx import ligar_tenant, site_url

STATIC = Path(__file__).resolve().parent / "loja" / "static"
STORAGE = Path(__file__).resolve().parent / "dados" / "storage"
STORAGE.mkdir(parents=True, exist_ok=True)
app.add_static_files("/static", STATIC)
app.add_static_files("/media", STORAGE)


class HostContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        set_contexto_host(
            resolver_contexto_host(request.headers.get("host", ""))
        )
        return await call_next(request)


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(HostContextMiddleware)

validar_ambiente()


def _log_startup() -> None:
    from loja.db_config import database_url, usando_postgres

    ambiente = os.getenv("AMBIENTE") or os.getenv("ENV") or "(nao definido)"
    port = os.getenv("PORT", "8080")
    chave = os.getenv("SECRET_KEY", "")
    chave_ok = bool(chave) and chave != "sigma-erp-secret-change-in-production" and len(chave) >= 32
    postgres = usando_postgres()
    print(
        f"[startup] AMBIENTE={ambiente} PORT={port} "
        f"postgres={postgres} SECRET_KEY={'ok' if chave_ok else 'AUSENTE/FRACA'}"
    )
    if postgres:
        url = database_url()
        host = url.split("@")[-1].split("/")[0] if "@" in url else "?"
        print(f"[startup] DB conectando em {host}")
    else:
        print(
            "[startup] AVISO: SQLite local — defina DATABASE_URL ou SUPABASE_DB_* "
            "no Easypanel e redeploy"
        )


_log_startup()
init_db()

CSS_SITE = "/static/estilo.css?v=22"


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


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
    ui.add_head_html(CSS_LAYOUT_FIX)
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


# ---- Plataforma / landing (somente localhost — sem domínio próprio) ----

@ui.page("/")
def pagina_raiz() -> None:
    ctx = get_contexto_host()
    if ctx.modo == "erp" and ctx.slug:
        ligar_tenant(ctx.slug)
        if logado():
            ui.navigate.to("/admin")
        else:
            pagina_login()
        return
    if ctx.modo == "site" and ctx.slug:
        if not montar_site_spa(ctx.slug, "/"):
            _loja_nao_encontrada()
        return
    _pagina_plataforma_local()


def _pagina_plataforma_local() -> None:
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    ui.add_head_html('<link rel="stylesheet" href="/static/admin.css?v=20">')
    ui.add_head_html(
        "<style>body{margin:0;font-family:Inter,Segoe UI,sans-serif;background:#eef1f6}"
        ".plat{max-width:960px;margin:0 auto;padding:48px 20px}"
        ".plat h1{font-size:32px;margin:0 0 8px}.plat p{color:#6b7280}"
        ".plat-acoes{display:flex;gap:16px;flex-wrap:wrap;margin:28px 0}"
        ".plat-login-box{flex:1;min-width:240px;background:#fff;border:1px solid #e5e7eb;"
        "border-radius:14px;padding:20px}.plat-login-box p{margin:6px 0 14px;color:#6b7280;font-size:14px}"
        ".plat-btn-master{background:#1e3a5f!important;color:#fff!important;width:100%}"
        ".plat-btn-empresa{background:#c0392b!important;color:#fff!important;width:100%}"
        ".plat-card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;"
        "padding:18px;margin-top:12px}.plat-card a{color:#1e3a5f;font-weight:700}"
        "</style>"
    )
    contas = listar_contas(apenas_ativas=True)
    with ui.element("div").classes("plat"):
        ui.html("<h1>Plataforma White Label</h1>")
        ui.html(
            "<p>Painel Master em ambiente local. "
            "Cada loja acessa o ERP pelo <strong>subdomínio</strong> "
            "cadastrado no Master; o site público fica no domínio próprio da loja.</p>"
        )
        with ui.element("div").classes("plat-acoes"):
            with ui.element("div").classes("plat-login-box plat-login-master"):
                ui.html("<strong>Painel Master</strong>")
                ui.html("<p>Gestão da plataforma (somente local/dev)</p>")
                ui.button(
                    "Login Master",
                    on_click=lambda: ui.navigate.to("/master/login"),
                ).props("unelevated no-caps").classes("plat-btn-master")
        ui.html("<h3 style='margin-top:32px'>Lojas ativas</h3>")
        if not contas:
            ui.html("<p>Nenhuma conta ativa. Crie uma no painel Master.</p>")
        else:
            for c in contas:
                sub = c.subdominio or "—"
                site = c.dominio_site or f"/loja/{c.slug}/ (dev)"
                with ui.element("div").classes("plat-card"):
                    ui.html(
                        f"<strong>{c.nome}</strong><br>"
                        f"ERP: <code>{sub}</code><br>"
                        f"Site: <code>{site}</code>"
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


# ---- Login ERP no subdomínio da empresa ----

@ui.page("/login")
def rota_login_subdominio() -> None:
    ctx = get_contexto_host()
    if ctx.modo == "erp" and ctx.slug:
        ligar_tenant(ctx.slug)
        pagina_login()
        return
    ui.navigate.to("/admin/login")


@ui.page("/trocar-senha")
def rota_trocar_senha_subdominio() -> None:
    ctx = get_contexto_host()
    if ctx.modo == "erp":
        pagina_trocar_senha()
        return
    ui.navigate.to("/admin/trocar-senha")


def _montar_site_host(slug: str, rota: str, **kwargs) -> bool:
    financ = kwargs if kwargs else None
    if not montar_site_spa(slug, rota, financ_kwargs=financ):
        _loja_nao_encontrada()
        return False
    return True


def _site_por_host(rota: str, **kwargs) -> bool:
    ctx = get_contexto_host()
    if ctx.modo == "site" and ctx.slug:
        return _montar_site_host(ctx.slug, rota, **kwargs)
    return False


# ---- Site no domínio próprio da loja (rotas na raiz) ----

@ui.page("/estoque")
def rota_estoque_host() -> None:
    if not _site_por_host("/estoque"):
        ui.navigate.to("/loja/sigma/estoque")


@ui.page("/avaliacao")
def rota_avaliacao_host() -> None:
    if not _site_por_host("/avaliacao"):
        ui.navigate.to("/loja/sigma/avaliacao")


@ui.page("/financiamento")
def rota_financiamento_host(
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
    if not _site_por_host("/financiamento", **kwargs):
        ui.navigate.to("/loja/sigma/financiamento")


@ui.page("/empresa")
def rota_empresa_host() -> None:
    if not _site_por_host("/empresa"):
        ui.navigate.to("/loja/sigma/empresa")


@ui.page("/contato")
def rota_contato_host() -> None:
    if not _site_por_host("/contato"):
        ui.navigate.to("/loja/sigma/contato")


@ui.page("/privacidade")
def rota_privacidade_host() -> None:
    ctx = get_contexto_host()
    if ctx.modo == "site" and ctx.slug:
        _pagina_conteudo_loja(ctx.slug, "privacidade")
        return
    ui.navigate.to("/loja/sigma/privacidade")


@ui.page("/lgpd")
def rota_lgpd_host() -> None:
    ctx = get_contexto_host()
    if ctx.modo == "site" and ctx.slug:
        _pagina_conteudo_loja(ctx.slug, "lgpd")
        return
    ui.navigate.to("/loja/sigma/lgpd")


@ui.page("/veiculo/{veiculo_id}")
def rota_veiculo_host(veiculo_id: int) -> None:
    ctx = get_contexto_host()
    if ctx.modo != "site" or not ctx.slug:
        ui.navigate.to(f"/loja/sigma/veiculo/{veiculo_id}")
        return
    if not ativar_loja(ctx.slug):
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


# Compatibilidade local: /loja/{slug}/...

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
    port = int(os.getenv("PORT", "8080"))
    ui.run(
        title="Plataforma White Label — Gestão Veículos",
        favicon="🚗",
        reload=False,
        host="0.0.0.0",
        port=port,
        show_welcome_message=False,
        uvicorn_logging_level="info",
        storage_secret=os.getenv(
            "SECRET_KEY", "sigma-erp-secret-change-in-production",
        ),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
