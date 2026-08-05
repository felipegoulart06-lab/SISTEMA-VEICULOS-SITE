"""Site público em HTML estático (Jinja2) — sem WebSocket NiceGUI."""

from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from loja.config import MENU
from loja.crm_repo import listar_depoimentos
from loja.institucional import obter_institucional
from loja.pagina_conteudo import obter_pagina
from loja.pagina_contato import ASSUNTOS
from loja.pagina_estoque import ORDENACOES
from loja.plataforma import obter_conta_por_slug
from loja.repositorio import (
    FiltrosEstoque,
    ITENS_POR_PAGINA,
    Veiculo,
    config_como_dict,
    facetas_estoque,
    filtrar_estoque,
    filtrar_veiculos,
    formatar_km,
    formatar_preco,
    incrementar_visualizacoes,
    listar_marcas,
    obter_veiculo_publico,
    salvar_lead,
    veiculo_destaque,
)
from loja.tenant_ctx import ligar_tenant, site_url
from loja.whitelabel import bloco_empresa_html, html_favicon, titulo_aba_site

HOME_LIMITE_VEICULOS = 18
_BANNER_PADRAO = (
    "https://images.unsplash.com/photo-1555215695-3004980ad54e?w=1400&q=80"
)
_FOTO_PADRAO = (
    "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=800&q=80"
)

_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _logo_html(loja: dict) -> str:
    logo = html.escape(loja.get("logo_texto") or loja.get("nome") or "Loja")
    if loja.get("slogan"):
        return f'{logo} <span>{html.escape(loja["slogan"])}</span>'
    return logo


def _social_links(loja: dict) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    fb = (loja.get("facebook") or "").strip()
    ig = (loja.get("instagram") or "").strip()
    email = (loja.get("email") or "").strip()
    if fb and fb not in {"#", "http://", "https://"}:
        links.append(("Facebook", fb))
    if ig and ig not in {"#", "http://", "https://"}:
        links.append(("Instagram", ig))
    if email:
        links.append(("E-mail", f"mailto:{email}"))
    return links


def _wa_link(loja: dict, texto: str = "") -> str:
    num = (
        (loja.get("whatsapp") or "")
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "")
        .replace("-", "")
    )
    if not num:
        return ""
    from urllib.parse import quote

    msg = quote(texto or "Olá! Gostaria de falar com a loja.")
    return f"https://wa.me/55{num}?text={msg}"


def _serializar_veiculo(v: Veiculo) -> dict:
    return {
        "id": v.id,
        "marca": v.marca,
        "modelo": v.modelo,
        "ano": v.ano,
        "km_fmt": formatar_km(v.km),
        "combustivel": v.combustivel,
        "cambio": v.cambio,
        "cor": v.cor,
        "preco_fmt": formatar_preco(v.preco),
        "imagem": (v.imagem or "").strip() or _FOTO_PADRAO,
        "imagem_destaque": (v.imagem_destaque or "").strip() or "",
        "descricao": v.descricao or "",
    }


def _fotos_galeria(v) -> list[str]:
    urls: list[str] = []
    if v.imagem and v.imagem.strip():
        urls.append(v.imagem.strip())
    extras = (getattr(v, "fotos_url", None) or "").replace(",", "\n")
    for linha in extras.split("\n"):
        u = linha.strip()
        if u and u not in urls:
            urls.append(u)
    return urls or [_FOTO_PADRAO]


def _ctx_base(slug: str, rota_ativa: str = "") -> dict:
    loja = config_como_dict()
    cor = loja.get("cor_primaria") or "#c0392b"

    def url(path: str = "/") -> str:
        return site_url(path, slug)

    return {
        "slug": slug,
        "loja": loja,
        "menu": MENU,
        "rota_ativa": rota_ativa,
        "cor": cor,
        "logo_html": _logo_html(loja),
        "social_links": _social_links(loja),
        "bloco_empresa": bloco_empresa_html(loja),
        "favicon_html": html_favicon(loja),
        "wa_link": _wa_link(loja),
        "url": url,
        "ano": datetime.now().year,
        "busca_cabecalho": "",
    }


def _render(template: str, **ctx) -> HTMLResponse:
    html_out = _env.get_template(template).render(**ctx)
    return HTMLResponse(html_out)


def _filtros_da_query(request: Request) -> FiltrosEstoque:
    qp = request.query_params
    ano_raw = qp.get("ano")
    ano = int(ano_raw) if ano_raw and ano_raw.isdigit() else None
    pagina_raw = qp.get("pagina") or "1"
    pagina = int(pagina_raw) if pagina_raw.isdigit() else 1
    return FiltrosEstoque(
        marca=qp.get("marca") or None,
        ano=ano,
        combustivel=qp.get("combustivel") or None,
        cor=qp.get("cor") or None,
        tipo=qp.get("tipo") or None,
        busca=qp.get("busca") or "",
        ordenar=qp.get("ordenar") or "recente",
        pagina=max(1, pagina),
    )


def _facetas_grupos(f: FiltrosEstoque, facets: dict) -> list[dict]:
    grupos = [
        ("tipo", "TIPO", facets.get("tipo", [])),
        ("marca", "MARCA", facets.get("marca", [])),
        ("ano", "ANO", facets.get("ano", [])),
        ("combustivel", "COMBUSTÍVEL", facets.get("combustivel", [])),
        ("cor", "COR", facets.get("cor", [])),
    ]
    resultado = []
    for campo, titulo, itens in grupos:
        if not itens:
            continue
        ativo = getattr(f, campo)
        if campo == "ano":
            itens = [(str(k), v) for k, v in itens]
            if ativo is not None:
                ativo = str(ativo)
        resultado.append({
            "campo": campo,
            "titulo": titulo,
            "itens": itens,
            "ativo": str(ativo) if ativo is not None else None,
        })
    return resultado


def _pagina_url(slug: str, f: FiltrosEstoque, pagina: int) -> str:
    params: dict[str, str | int] = {"pagina": pagina}
    for campo in ("marca", "combustivel", "cor", "tipo", "busca", "ordenar"):
        val = getattr(f, campo)
        if val:
            params[campo] = val
    if f.ano:
        params["ano"] = f.ano
    qs = urlencode(params)
    return site_url(f"/estoque?{qs}" if qs else "/estoque", slug)


def _render_home(slug: str, request: Request) -> HTMLResponse:
    marca = request.query_params.get("marca") or None
    veiculos_raw = filtrar_veiculos(marca=marca, limite=HOME_LIMITE_VEICULOS)
    destaque = veiculo_destaque(veiculos_raw)
    grade = [
        _serializar_veiculo(v)
        for v in veiculos_raw
        if not destaque or v.id != destaque.id
    ]
    destaque_d = _serializar_veiculo(destaque) if destaque else None
    depoimentos = [
        {"nome": d.nome, "texto": d.texto, "nota": d.nota or 5}
        for d in listar_depoimentos(apenas_ativos=True)[:6]
    ]
    loja = config_como_dict()
    ctx = _ctx_base(slug, "/")
    ctx.update({
        "titulo_pagina": titulo_aba_site(loja),
        "seo_descricao": loja.get("seo_descricao") or "",
        "banner_url": loja.get("banner_url") or _BANNER_PADRAO,
        "marcas": listar_marcas(),
        "marca_atual": marca,
        "destaque": destaque_d,
        "veiculos": grade,
        "depoimentos": depoimentos,
    })
    return _render("site/home.html", **ctx)


def _render_estoque(slug: str, request: Request) -> HTMLResponse:
    f = _filtros_da_query(request)
    veiculos, total = filtrar_estoque(f)
    facets = facetas_estoque()
    total_paginas = max(1, (total + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)
    loja = config_como_dict()
    hidden: dict[str, str | int] = {}
    for campo in ("marca", "combustivel", "cor", "tipo", "busca"):
        val = getattr(f, campo)
        if val:
            hidden[campo] = val
    if f.ano:
        hidden["ano"] = f.ano
    ctx = _ctx_base(slug, "/estoque")
    ctx.update({
        "titulo_pagina": titulo_aba_site(loja, "Estoque"),
        "seo_descricao": loja.get("seo_descricao") or "",
        "busca_cabecalho": f.busca,
        "veiculos": [_serializar_veiculo(v) for v in veiculos],
        "total": total,
        "filtros": f,
        "filtros_hidden": hidden,
        "facetas_grupos": _facetas_grupos(f, facets),
        "ordenacoes": ORDENACOES,
        "total_paginas": total_paginas,
        "pagina_url": lambda p: _pagina_url(slug, f, p),
    })
    return _render("site/estoque.html", **ctx)


def _render_veiculo(slug: str, veiculo_id: int, request: Request | None = None) -> Response:
    v = obter_veiculo_publico(veiculo_id)
    if v is None:
        loja = config_como_dict()
        ctx = _ctx_base(slug, "/estoque")
        ctx.update({
            "titulo_pagina": titulo_aba_site(loja, "Veículo não encontrado"),
            "titulo": "Veículo não encontrado",
            "conteudo": (
                '<p>Este veículo não está disponível.</p>'
                f'<p><a href="{html.escape(site_url("/estoque", slug))}" '
                'class="btn btn-preto">Ver estoque</a></p>'
            ),
        })
        return _render("site/conteudo.html", **ctx)

    incrementar_visualizacoes(veiculo_id)
    loja = config_como_dict()
    titulo = f"{v.marca} {v.modelo} {v.ano}"
    veiculo = {
        "id": v.id,
        "marca": v.marca,
        "modelo": v.modelo,
        "ano": v.ano,
        "km_fmt": formatar_km(v.km),
        "combustivel": v.combustivel,
        "cambio": v.cambio,
        "cor": v.cor or "",
        "placa": getattr(v, "placa", "") or "",
        "preco_fmt": formatar_preco(v.preco),
        "descricao": v.descricao or "",
    }
    ctx = _ctx_base(slug, "/estoque")
    qp = request.query_params if request else {}
    ctx.update({
        "titulo_pagina": titulo_aba_site(loja, titulo),
        "veiculo": veiculo,
        "fotos": _fotos_galeria(v),
        "wa_link": _wa_link(
            loja,
            f"Olá! Tenho interesse no {titulo} — {formatar_preco(v.preco)}",
        ),
        "mensagem": (
            "Interesse registrado! Em breve entraremos em contato."
            if qp.get("ok") else ""
        ),
        "erro": (
            "Preencha nome e telefone."
            if qp.get("erro") else ""
        ),
    })
    return _render("site/veiculo.html", **ctx)


def _render_empresa(slug: str) -> HTMLResponse:
    loja = config_como_dict()
    ctx = _ctx_base(slug, "/empresa")
    ctx.update({
        "titulo_pagina": titulo_aba_site(loja, "Empresa"),
        "institucional": obter_institucional(),
    })
    return _render("site/empresa.html", **ctx)


def _render_conteudo(slug: str, pagina_slug: str, rota: str) -> HTMLResponse:
    pagina = obter_pagina(pagina_slug)
    loja = config_como_dict()
    if pagina is None:
        titulo = "Página não encontrada"
        conteudo = (
            "<p>Este conteúdo ainda não foi publicado.</p>"
        )
    else:
        titulo = pagina.titulo
        conteudo = pagina.conteudo_html or (
            '<p class="pagina-vazia">Conteúdo ainda não preenchido. '
            "Edite esta página no ERP em Site → Páginas.</p>"
        )
    ctx = _ctx_base(slug, rota)
    ctx.update({
        "titulo_pagina": titulo_aba_site(loja, titulo),
        "seo_descricao": getattr(pagina, "seo_descricao", "") or "",
        "titulo": titulo,
        "conteudo": conteudo,
    })
    return _render("site/conteudo.html", **ctx)


def _render_contato(
    slug: str,
    *,
    mensagem: str = "",
    erro: str = "",
    form: dict | None = None,
) -> HTMLResponse:
    loja = config_como_dict()
    ctx = _ctx_base(slug, "/contato")
    ctx.update({
        "titulo_pagina": titulo_aba_site(loja, "Contato"),
        "assuntos": list(ASSUNTOS.values()),
        "mensagem": mensagem,
        "erro": erro,
        "form": form or {},
    })
    return _render("site/contato.html", **ctx)


async def _processar_contato(slug: str, request: Request) -> Response:
    form = await _ler_formulario(request)
    nome = (form.get("nome") or "").strip()
    telefone = (form.get("telefone") or "").strip()
    email = (form.get("email") or "").strip()
    assunto = (form.get("assunto") or "").strip()
    mensagem_txt = (form.get("mensagem") or "").strip()

    if not nome or not telefone or not mensagem_txt:
        return _render_contato(
            slug,
            erro="Preencha nome, telefone e mensagem.",
            form=form,
        )

    rotulo = assunto or "Contato"
    salvar_lead({
        "nome": nome,
        "telefone": telefone,
        "email": email,
        "origem": "contato",
        "status": "novo",
        "observacoes": f"[{rotulo}] {mensagem_txt}",
    })
    return _render_contato(
        slug,
        mensagem="Mensagem enviada! Em breve nossa equipe entrará em contato.",
    )


async def _processar_interesse(slug: str, request: Request) -> Response:
    form = await _ler_formulario(request)
    nome = (form.get("nome") or "").strip()
    telefone = (form.get("telefone") or "").strip()
    email = (form.get("email") or "").strip()
    mensagem_txt = (form.get("mensagem") or "").strip()
    veiculo_id_raw = form.get("veiculo_id") or "0"
    veiculo_id = int(veiculo_id_raw) if veiculo_id_raw.isdigit() else 0

    if not nome or not telefone:
        if veiculo_id:
            return RedirectResponse(
                site_url(f"/veiculo/{veiculo_id}?erro=1", slug),
                status_code=303,
            )
        return RedirectResponse(site_url("/contato", slug), status_code=303)

    v = obter_veiculo_publico(veiculo_id) if veiculo_id else None
    titulo_v = (
        f"{v.marca} {v.modelo} {v.ano}" if v else f"ID {veiculo_id}"
    )
    salvar_lead({
        "nome": nome,
        "telefone": telefone,
        "email": email,
        "origem": "site",
        "status": "novo",
        "observacoes": (
            f"Interesse em: {titulo_v}"
            + (f"\n{mensagem_txt}" if mensagem_txt else "")
        ),
    })
    if veiculo_id:
        return RedirectResponse(
            site_url(f"/veiculo/{veiculo_id}?ok=1", slug),
            status_code=303,
        )
    return RedirectResponse(site_url("/contato", slug), status_code=303)


async def _ler_formulario(request: Request) -> dict[str, str]:
    try:
        form = await request.form()
        return {k: str(v) for k, v in form.items()}
    except Exception:
        return {}


def _normalizar_path(path: str) -> str:
    path = "/" + path.strip("/")
    return "/" if path == "/" else path.rstrip("/") or "/"


async def tentar_responder_html(
    slug: str,
    path: str,
    request: Request,
) -> Response | None:
    """Renderiza HTML do site público ou None para passar ao NiceGUI."""
    conta = obter_conta_por_slug(slug)
    if conta is None or not conta.ativa:
        return HTMLResponse(
            "<h1>Loja não encontrada</h1>"
            "<p>Esta conta não existe ou está inativa.</p>",
            status_code=404,
        )

    ligar_tenant(slug)
    path = _normalizar_path(path)
    method = request.method.upper()

    if method == "POST":
        if path == "/contato":
            return await _processar_contato(slug, request)
        if path == "/interesse":
            return await _processar_interesse(slug, request)
        return None

    if method != "GET":
        return None

    if path == "/":
        return _render_home(slug, request)
    if path == "/estoque":
        return _render_estoque(slug, request)
    if path == "/empresa":
        return _render_empresa(slug)
    if path == "/contato":
        return _render_contato(slug)
    if path == "/privacidade":
        return _render_conteudo(slug, "privacidade", "/privacidade")
    if path == "/lgpd":
        return _render_conteudo(slug, "lgpd", "/lgpd")

    m = re.fullmatch(r"/veiculo/(\d+)", path)
    if m:
        return _render_veiculo(slug, int(m.group(1)), request)

    return None
