"""Navegação SPA do site público — menus trocam painéis sem reload."""

from __future__ import annotations

import time
from collections.abc import Callable

from nicegui import app, ui

from loja.componentes import (
    banner,
    barra_lateral_site,
    barra_social,
    cabecalho,
    card_destaque,
    card_veiculo,
    injetar_tema,
    rodape,
    secao_sobre,
    sidebar_marcas,
)
from loja.config import MENU
from loja.crm_repo import listar_depoimentos, obter_popup_ativo
from loja.pagina_avaliacao import montar_formulario_avaliacao
from loja.pagina_contato import montar_pagina_contato
from loja.pagina_empresa import montar_pagina_empresa
from loja.pagina_estoque import montar_pagina_estoque
from loja.pagina_financiamento import montar_formulario_financiamento
from loja.plataforma import obter_conta_por_slug, empresa_pode_acessar
from loja.repositorio import (
    FiltrosEstoque,
    config_como_dict,
    filtrar_veiculos,
    veiculo_destaque,
)
from loja.tenant_ctx import ligar_tenant, resolver_link_site, site_url
from loja.whitelabel import html_favicon, titulo_aba_site

CSS_SITE = "/static/estilo.css?v=23"
TTL_PAINEL = 600.0
MAX_PAINEIS_SITE = 2
HOME_LIMITE_VEICULOS = 18

SPLASH_SITE = """
<style>
#sigma-splash{position:fixed;inset:0;z-index:99999;background:#fff;display:flex;
flex-direction:column;align-items:center;justify-content:center;gap:12px;
font-family:system-ui,Segoe UI,sans-serif;color:#555}
#sigma-splash .sigma-spin{width:36px;height:36px;border:3px solid #e5e7eb;
border-top-color:#c0392b;border-radius:50%;animation:sigma-spin .8s linear infinite}
@keyframes sigma-spin{to{transform:rotate(360deg)}}
</style>
<script>
(function(){
  function splash(){
    if(document.getElementById('sigma-splash')) return;
    var d=document.createElement('div'); d.id='sigma-splash';
    d.innerHTML='<div class="sigma-spin"></div><p>Carregando loja…</p>';
    (document.body||document.documentElement).appendChild(d);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',splash);
  else splash();
  new MutationObserver(function(){
    if(document.querySelector('.site-root,.cabecalho-principal,.barra-social'))
      document.getElementById('sigma-splash')?.remove();
  }).observe(document.documentElement,{childList:true,subtree:true});
})();
</script>
"""

# NiceGUI 3.x usa CSS layers — override precisa estar em @layer overrides
CSS_LAYOUT_FIX = """
<style>
@layer overrides {
  .nicegui-content,
  .nicegui-column,
  .nicegui-sub-pages {
    align-items: stretch !important;
    gap: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    max-width: none !important;
  }
  .site-root,
  .nicegui-content > .site-root,
  .barra-social,
  .cabecalho-principal,
  .rodape,
  .site-spa-host,
  .site-spa-painel {
    width: 100% !important;
    max-width: none !important;
    align-self: stretch !important;
    box-sizing: border-box !important;
  }
  .site-spa-painel > * {
    align-self: center !important;
    box-sizing: border-box !important;
  }
  .corpo-site,
  .banner,
  .secao-sobre,
  .secao-depoimentos,
  .barra-social .conteudo,
  .cabecalho-principal .conteudo,
  .rodape .conteudo,
  .corpo-estoque-wrap,
  .corpo-institucional-wrap,
  .corpo-financiamento-wrap,
  .corpo-avaliacao-wrap,
  .corpo-detalhe-wrap {
    width: 100% !important;
    max-width: 1200px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    box-sizing: border-box !important;
  }
  /* Botões flutuantes NÃO podem herdar stretch/width:100% */
  .site-redes-fixas,
  .site-btn-avaliacao,
  .site-btn-atendimento,
  .site-chat-panel,
  .site-root > .site-redes-fixas,
  .site-root > .site-btn-avaliacao,
  .site-root > .q-btn.site-btn-atendimento {
    width: auto !important;
    max-width: none !important;
    min-width: 0 !important;
    height: auto !important;
    align-self: auto !important;
    flex: 0 0 auto !important;
  }
  .site-btn-atendimento {
    width: 48px !important;
    max-width: 48px !important;
    height: 48px !important;
  }
  .site-btn-avaliacao {
    width: auto !important;
    max-width: max-content !important;
    white-space: nowrap !important;
  }
}
</style>
"""

ROTAS_SITE = {
    "/",
    "/estoque",
    "/financiamento",
    "/empresa",
    "/contato",
    "/avaliacao",
}


def normalizar_rota_site(path: str | None) -> str:
    path = "/" + (path or "").strip("/")
    if path in ("", "/"):
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    # remove prefixo /loja/{slug} se vier completo
    partes = path.strip("/").split("/")
    if len(partes) >= 2 and partes[0] == "loja":
        resto = "/" + "/".join(partes[2:]) if len(partes) > 2 else "/"
        path = resto if resto != "/" else "/"
    if path in ROTAS_SITE:
        return path
    return "/"


def _filtros_home() -> dict:
    try:
        dados = app.storage.client.get("filtros_home")
        if isinstance(dados, dict):
            return dados
        dados = {"marca": None, "busca": ""}
        app.storage.client["filtros_home"] = dados
        return dados
    except Exception:
        return {"marca": None, "busca": ""}


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


def _head_site(titulo: str, descricao: str = "", cfg: dict | None = None) -> None:
    ui.add_head_html(SPLASH_SITE)
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    ui.add_head_html(f'<link rel="stylesheet" href="{CSS_SITE}">')
    ui.add_head_html(CSS_LAYOUT_FIX)
    ui.add_head_html(
        '<link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">'
    )
    injetar_tema()
    ui.page_title(titulo)
    if cfg:
        fav = html_favicon(cfg)
        if fav:
            ui.add_head_html(fav)
    if descricao:
        ui.add_head_html(f'<meta name="description" content="{descricao}">')


def montar_site_spa(
    slug: str,
    rota_inicial: str = "/",
    financ_kwargs: dict | None = None,
) -> bool:
    conta = obter_conta_por_slug(slug)
    if conta is None:
        return False
    liberado, _ = empresa_pode_acessar(conta)
    if not liberado:
        return False
    ligar_tenant(conta.slug)

    cfg = config_como_dict()
    estado = {"rota": normalizar_rota_site(rota_inicial)}
    host_ref: dict = {"el": None}
    paineis: dict[str, dict] = {}
    nav_refs: dict[str, object] = {}
    carregando_ref: dict = {"el": None}
    estoque_ui: dict = {}
    financ_ctx = dict(financ_kwargs or {})

    _head_site(
        titulo_aba_site(cfg),
        cfg.get("seo_descricao") or "",
        cfg=cfg,
    )

    def _url_abs(destino: str) -> str:
        return site_url(destino if destino != "/" else "/")

    def _marcar_ativo(destino: str) -> None:
        for href, el in nav_refs.items():
            if el is None:
                continue
            if href == destino:
                el.classes(add="ativo")
            else:
                el.classes(remove="ativo")

    def _esconder_todos() -> None:
        for p in paineis.values():
            el = p.get("el")
            if el is not None:
                el.set_visibility(False)
        if carregando_ref["el"] is not None:
            carregando_ref["el"].set_visibility(False)

    def _mostrar_carregando() -> None:
        _esconder_todos()
        el = carregando_ref["el"]
        if el is not None:
            el.set_visibility(True)

    def _montar_home() -> None:
        popup = obter_popup_ativo()
        if popup:
            link_popup = resolver_link_site(popup.link or "", slug)
            with ui.dialog() as dlg_pop, ui.card().classes("popup-site"):
                ui.label(popup.titulo or "Novidade").classes("text-h6")
                ui.markdown(popup.texto or "")
                if popup.link:
                    ui.button(
                        "Ver mais",
                        on_click=lambda destino=link_popup: ui.navigate.to(destino),
                    ).classes("btn btn-preto")
                ui.button("Fechar", on_click=dlg_pop.close).props("flat")
                dlg_pop.open()

        banner()

        @ui.refreshable
        def listagem() -> None:
            filtros = _filtros_home()
            veiculos = filtrar_veiculos(
                filtros.get("marca"), filtros.get("busca") or "",
                limite=HOME_LIMITE_VEICULOS,
            )
            destaque = veiculo_destaque(veiculos)
            grade = [v for v in veiculos if destaque and v.id != destaque.id]
            sidebar_marcas(filtros.get("marca"), selecionar_marca)
            with ui.element("main"):
                if destaque:
                    card_destaque(destaque)
                with ui.element("div").classes("grade-veiculos"):
                    if not grade:
                        ui.html(
                            '<p class="sem-resultado">Nenhum veículo encontrado.</p>'
                        )
                    else:
                        for v in grade:
                            card_veiculo(v)
                ui.button(
                    "Ver estoque completo",
                    on_click=lambda: ir("/estoque"),
                ).classes("btn-estoque-completo").props("no-caps unelevated")

        def selecionar_marca(marca: str | None) -> None:
            filtros = _filtros_home()
            filtros["marca"] = marca
            listagem.refresh()

        with ui.element("div").classes("corpo-site"):
            listagem()
        deps = listar_depoimentos(apenas_ativos=True)
        if deps:
            with ui.element("section").classes("secao-depoimentos"):
                ui.html("<h2>O que dizem nossos clientes</h2>")
                with ui.element("div").classes("depoimentos-grade"):
                    for d in deps[:6]:
                        ui.html(
                            f'<blockquote class="depoimento-card">'
                            f"<p>“{d.texto}”</p>"
                            f"<footer>{'★' * d.nota} — {d.nome}</footer>"
                            f"</blockquote>"
                        )
        secao_sobre()

    def _montar_estoque() -> None:
        filtros_estoque = _filtros_estoque()

        def refresh() -> None:
            fn = estoque_ui.get("refresh")
            if fn:
                fn()

        estoque_ui["aplicar_busca"] = refresh
        with ui.element("div").classes("corpo-estoque-wrap"):
            montar_pagina_estoque(filtros_estoque, estoque_ui)
        _salvar_filtros_estoque(filtros_estoque)

    def _montar_financiamento() -> None:
        banner()
        with ui.element("div").classes("corpo-financiamento-wrap"):
            montar_formulario_financiamento(**financ_ctx)
            financ_ctx.clear()

    def _montar_empresa() -> None:
        with ui.element("div").classes("corpo-institucional-wrap"):
            montar_pagina_empresa()

    def _montar_contato() -> None:
        with ui.element("div").classes("corpo-institucional-wrap"):
            montar_pagina_contato()

    def _montar_avaliacao() -> None:
        banner()
        with ui.element("div").classes("corpo-avaliacao-wrap"):
            montar_formulario_avaliacao()

    BUILDERS: dict[str, Callable] = {
        "/": _montar_home,
        "/estoque": _montar_estoque,
        "/financiamento": _montar_financiamento,
        "/empresa": _montar_empresa,
        "/contato": _montar_contato,
        "/avaliacao": _montar_avaliacao,
    }

    def _evictar_paineis(destino: str) -> None:
        reservados = {destino, "loading"}
        while len(paineis) > MAX_PAINEIS_SITE:
            candidatos = [
                (k, v) for k, v in paineis.items() if k not in reservados
            ]
            if not candidatos:
                break
            chave, info = min(candidatos, key=lambda x: x[1].get("ts", 0))
            el = info.get("el")
            if el is not None:
                try:
                    el.delete()
                except Exception:
                    pass
            paineis.pop(chave, None)

    def _montar_painel(destino: str, visivel: bool = True) -> None:
        host = host_ref["el"]
        if host is None:
            return
        if destino in paineis:
            try:
                paineis[destino]["el"].delete()
            except Exception:
                pass
            paineis.pop(destino, None)
        with host:
            painel = ui.element("div").classes("site-spa-painel")
            if not visivel:
                painel.set_visibility(False)
            with painel:
                BUILDERS.get(destino, _montar_home)()
            paineis[destino] = {"el": painel, "ts": time.monotonic()}
        _evictar_paineis(destino)

    def _mostrar(destino: str, forcar: bool = False) -> None:
        agora = time.monotonic()
        existente = paineis.get(destino)
        fresco = (
            existente
            and not forcar
            and (agora - existente["ts"]) < TTL_PAINEL
        )
        _esconder_todos()
        if fresco:
            existente["el"].set_visibility(True)
            return
        _montar_painel(destino, visivel=True)

    def ir(href: str, forcar: bool = False) -> None:
        destino = normalizar_rota_site(href)
        mesma = destino == estado["rota"]
        estado["rota"] = destino
        _marcar_ativo(destino)
        url = _url_abs(destino)
        ui.run_javascript(f'history.pushState({{}}, "", "{url}");')
        if mesma and not forcar and destino in paineis:
            return

        agora = time.monotonic()
        existente = paineis.get(destino)
        fresco = (
            existente
            and not forcar
            and (agora - existente["ts"]) < TTL_PAINEL
        )
        if fresco:
            _esconder_todos()
            existente["el"].set_visibility(True)
            return

        # Feedback imediato; monta o painel no próximo tick
        _mostrar_carregando()

        def _depois() -> None:
            if estado["rota"] != destino:
                return
            try:
                _mostrar(destino, forcar=forcar)
            except Exception:
                _mostrar_carregando()

        ui.timer(0.01, _depois, once=True)

    def buscar(texto: str) -> None:
        if estado["rota"] == "/":
            filtros = _filtros_home()
            filtros["busca"] = texto or ""
            antigo = paineis.pop("/", None)
            if antigo and antigo.get("el") is not None:
                try:
                    antigo["el"].delete()
                except Exception:
                    pass
            ir("/", forcar=True)
            return
        filtros = _filtros_estoque()
        filtros.busca = texto or ""
        filtros.pagina = 1
        _salvar_filtros_estoque(filtros)
        if estado["rota"] == "/estoque":
            fn = estoque_ui.get("refresh")
            if fn:
                fn()
            else:
                ir("/estoque", forcar=True)
        else:
            ir("/estoque", forcar=True)

    ui.context.client.site_ir = ir  # type: ignore[attr-defined]

    root = ui.element("div").classes("site-root")
    root.style(
        "width:100%;max-width:100%;display:flex;flex-direction:column;"
        "align-items:stretch;margin:0;padding:0;box-sizing:border-box"
    )
    with root:
        barra_social()
        cabecalho(
            buscar,
            navegar_spa=ir,
            nav_refs=nav_refs,
            rota_ativa=estado["rota"],
        )

        host_ref["el"] = ui.element("div").classes("site-spa-host")
        with host_ref["el"]:
            carregando_ref["el"] = ui.element("div").classes("site-spa-carregando")
            with carregando_ref["el"]:
                ui.html('<p class="site-spa-carregando-txt">Carregando…</p>')

        _marcar_ativo(estado["rota"])
        rodape()

    def _carregar_flutuantes() -> None:
        barra_lateral_site(avaliacao_spa=ir)

    def _carregar_conteudo_inicial() -> None:
        try:
            _mostrar(estado["rota"], forcar=True)
        except Exception:
            if carregando_ref["el"] is not None:
                carregando_ref["el"].set_visibility(True)

    # Shell leve primeiro; conteúdo pesado no próximo tick (menos bloqueio WebSocket)
    _mostrar_carregando()
    ui.timer(0.05, _carregar_conteudo_inicial, once=True)
    ui.timer(0.15, _carregar_flutuantes, once=True)

    return True
