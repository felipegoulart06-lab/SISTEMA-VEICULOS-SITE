"""Conteúdo da página institucional (EMPRESA) do site público."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from loja.auth import conta_slug
from loja.provisionamento import (
    ler_config,
    pasta_storage,
    salvar_config,
)
from loja.repositorio import config_como_dict
from loja.tenant_ctx import get_tenant_slug

CHAVE = "site.institucional"
GRUPO = "site"

ICONES_PILARES = [
    "verified_user",
    "handshake",
    "directions_car",
    "security",
    "thumb_up",
    "support_agent",
    "star",
    "favorite",
    "build",
    "payments",
    "speed",
    "emoji_events",
    "storefront",
    "workspace_premium",
    "local_shipping",
]


def _pilares_padrao() -> list[dict]:
    return [
        {
            "icone": "verified_user",
            "titulo": "Ética e transparência",
            "texto": (
                "Negociamos com clareza em cada etapa — "
                "do primeiro contato à entrega do veículo."
            ),
        },
        {
            "icone": "handshake",
            "titulo": "Compromisso com você",
            "texto": (
                "Buscamos a melhor solução de compra, troca ou "
                "financiamento para o seu perfil."
            ),
        },
        {
            "icone": "directions_car",
            "titulo": "Veículos selecionados",
            "texto": (
                "Estoque revisado, documentação em dia e opções "
                "para diferentes bolsos e estilos."
            ),
        },
    ]


def padrao_institucional(loja: dict | None = None) -> dict:
    loja = loja or {}
    nome = loja.get("nome") or "Nossa loja"
    cidade = loja.get("cidade") or "nossa região"
    return {
        "titulo": f"CONHEÇA A {nome.upper()}",
        "subtitulo": "Tradição, confiança e o carro certo para você",
        "intro": loja.get("sobre") or (
            f"A {nome} atua há mais de 15 anos no mercado automotivo de "
            f"{cidade} e região. Trabalhamos com veículos seminovos "
            "selecionados, com procedência garantida e opções de financiamento."
        ),
        "imagem_url": loja.get("banner_url") or "",
        "pilares_titulo": "NOSSOS PILARES",
        "pilares": _pilares_padrao(),
        "missao_titulo": "Missão",
        "missao_texto": (
            f"Oferecer veículos seminovos com qualidade, segurança e "
            f"atendimento acolhedor, tornando a {nome} referência em {cidade}."
        ),
        "visao_titulo": "Visão",
        "visao_texto": (
            "Ser a loja multimarcas mais lembrada pela confiança, "
            "pelo pós-venda e pela experiência simples de comprar um carro."
        ),
    }


def obter_institucional() -> dict:
    from loja.cache_local import get_institucional_cache, set_institucional_cache
    from loja.tenant_ctx import get_tenant_slug

    slug = get_tenant_slug() or ""
    cached = get_institucional_cache(slug)
    if cached is not None:
        return cached

    loja = config_como_dict()
    base = padrao_institucional(loja)
    salvo = ler_config(CHAVE, {})
    if not salvo:
        if slug:
            set_institucional_cache(slug, base)
        return base
    dados = {**base, **{k: v for k, v in salvo.items() if v not in (None, "")}}
    pilares = salvo.get("pilares")
    if isinstance(pilares, list) and len(pilares) >= 3:
        normalizados = []
        padrao = _pilares_padrao()
        for i in range(3):
            p = pilares[i] if i < len(pilares) else {}
            base_p = padrao[i]
            normalizados.append({
                "icone": (p.get("icone") or base_p["icone"]).strip(),
                "titulo": (p.get("titulo") or base_p["titulo"]).strip(),
                "texto": (p.get("texto") or base_p["texto"]).strip(),
            })
        dados["pilares"] = normalizados
    else:
        dados["pilares"] = _pilares_padrao()
    if slug:
        set_institucional_cache(slug, dados)
    return dados


def salvar_institucional(dados: dict) -> None:
    from loja.cache_local import invalidar_config
    from loja.tenant_ctx import get_tenant_slug

    pilares = dados.get("pilares") or _pilares_padrao()
    while len(pilares) < 3:
        pilares.append(_pilares_padrao()[len(pilares)])
    payload = {
        "titulo": (dados.get("titulo") or "").strip(),
        "subtitulo": (dados.get("subtitulo") or "").strip(),
        "intro": (dados.get("intro") or "").strip(),
        "imagem_url": (dados.get("imagem_url") or "").strip(),
        "pilares_titulo": (dados.get("pilares_titulo") or "NOSSOS PILARES").strip(),
        "pilares": [
            {
                "icone": (p.get("icone") or "star").strip(),
                "titulo": (p.get("titulo") or "").strip(),
                "texto": (p.get("texto") or "").strip(),
            }
            for p in pilares[:3]
        ],
        "missao_titulo": (dados.get("missao_titulo") or "Missão").strip(),
        "missao_texto": (dados.get("missao_texto") or "").strip(),
        "visao_titulo": (dados.get("visao_titulo") or "Visão").strip(),
        "visao_texto": (dados.get("visao_texto") or "").strip(),
    }
    salvar_config(CHAVE, payload, grupo=GRUPO)
    invalidar_config(get_tenant_slug())


def metricas_institucionais() -> list[tuple[str, str]]:
    """Métricas automáticas: clientes, anos no mercado, veículos em estoque."""
    from sqlalchemy import func, select

    from loja.cache_local import get_metricas_cache, set_metricas_cache
    from loja.database import get_session
    from loja.models import Cliente, VeiculoDB
    from loja.plataforma import obter_conta_por_slug
    from loja.tenant_ctx import get_tenant_slug

    slug = get_tenant_slug() or conta_slug() or ""
    cached = get_metricas_cache(slug)
    if cached is not None:
        return [(a, b) for a, b in cached]

    with get_session() as db:
        clientes = db.scalar(select(func.count()).select_from(Cliente)) or 0
        veiculos = db.scalar(
            select(func.count()).select_from(VeiculoDB).where(
                VeiculoDB.status == "disponivel",
                VeiculoDB.publicado.is_(True),
            )
        ) or 0

    anos = 1
    if slug:
        conta = obter_conta_por_slug(slug)
        criado = getattr(conta, "criado_em", None) if conta else None
        if criado is not None:
            if getattr(criado, "tzinfo", None) is not None:
                criado = criado.replace(tzinfo=None)
            delta = datetime.now() - criado
            anos = max(1, int(delta.days / 365.25) or 1)

    resultado = [
        (f"{clientes}+" if clientes else "0", "Clientes satisfeitos"),
        (f"{anos}+", "Anos no mercado"),
        (f"{veiculos}+" if veiculos else "0", "Veículos em estoque"),
    ]
    if slug:
        set_metricas_cache(slug, resultado)
    return resultado


def salvar_upload_institucional(nome_arquivo: str, conteudo: bytes) -> str:
    """Salva upload e devolve URL pública /media/{slug}/uploads/..."""
    slug = get_tenant_slug() or conta_slug()
    if not slug:
        raise RuntimeError("Empresa não identificada para upload.")
    ext = Path(nome_arquivo or "imagem.jpg").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    pasta = pasta_storage(slug) / "uploads"
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"institucional_{uuid.uuid4().hex[:12]}{ext}"
    destino = pasta / nome
    destino.write_bytes(conteudo)
    return f"/media/{slug}/uploads/{nome}"
