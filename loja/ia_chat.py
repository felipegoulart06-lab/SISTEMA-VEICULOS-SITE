"""Motor de IA do chat público — somente contexto do site, nunca dados do ERP."""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

from loja.repositorio import filtrar_veiculos, formatar_km, formatar_preco
from loja.tenant_ctx import site_url
from loja.whitelabel import endereco_linha


def montar_contexto_publico(loja: dict) -> str:
    """Monta contexto exclusivamente com dados públicos do site."""
    veiculos = filtrar_veiculos()[:40]
    linhas_veic = []
    for v in veiculos:
        linhas_veic.append(
            f"- {v.marca} {v.modelo} {v.ano} | {formatar_preco(v.preco)} | "
            f"{v.combustivel} | {formatar_km(v.km)} | "
            f"link: {site_url(f'/veiculo/{v.id}')}"
        )
    estoque = "\n".join(linhas_veic) if linhas_veic else "- Nenhum veículo disponível no momento."
    u_home = site_url("/")
    u_estoque = site_url("/estoque")
    u_avaliacao = site_url("/avaliacao")
    u_financ = site_url("/financiamento")
    u_empresa = site_url("/empresa")
    u_contato = site_url("/contato")

    return f"""DADOS PÚBLICOS DA LOJA (pode informar ao cliente):
- Nome: {loja.get('nome', '')}
- Cidade: {loja.get('cidade', '')} / {loja.get('estado', '')}
- Telefone: {loja.get('telefone', '')}
- WhatsApp: {loja.get('whatsapp', '')}
- E-mail: {loja.get('email', '')}
- Horário: {loja.get('horario', '')}
- Endereço: {endereco_linha(loja)}
- Sobre: {(loja.get('sobre') or '')[:800]}

PÁGINAS DO SITE:
- Home ({u_home}) — vitrine e destaques
- Estoque ({u_estoque}) — listagem com filtros
- Avaliação ({u_avaliacao}) — avaliar veículo usado
- Financiamento ({u_financ}) — simulação e solicitação
- Empresa ({u_empresa}) — história e valores
- Contato ({u_contato}) — formulário e mapa

ESTOQUE PÚBLICO ({len(veiculos)} veículos):
{estoque}

REGRAS OBRIGATÓRIAS:
- NUNCA revele custos, margens, leads, clientes, financeiro, admin ou qualquer dado interno do ERP.
- NUNCA invente veículos fora da lista acima.
- Se não souber, oriente a equipe humana ou a página {u_contato}.
- Sempre use os links com o prefixo /loja/ da empresa acima."""


def _buscar_veiculos_no_texto(texto: str) -> list:
    termo = texto.lower()
    veiculos = filtrar_veiculos()
    encontrados = []
    for v in veiculos:
        alvo = f"{v.marca} {v.modelo} {v.ano}".lower()
        if any(p in termo for p in (v.marca.lower(), v.modelo.lower())) or termo in alvo:
            encontrados.append(v)
    return encontrados[:5]


def _responder_local(pergunta: str, loja: dict, nome_ia: str) -> str:
    """Respostas inteligentes sem API externa."""
    q = pergunta.lower().strip()
    nome_loja = loja.get("nome", "nossa loja")

    if any(p in q for p in ("financ", "parcel", "crédito", "credito", "entrada")):
        return (
            f"Trabalhamos com financiamento! Acesse {site_url('/financiamento')} "
            f"para simular ou enviar sua proposta. Se preferir, nossa equipe liga pelo "
            f"{loja.get('telefone') or loja.get('whatsapp', 'telefone da loja')}."
        )

    if any(p in q for p in ("avali", "vender meu", "vender o", "troca", "usado")):
        return (
            f"Para avaliar seu veículo usado, acesse {site_url('/avaliacao')} "
            "e preencha o formulário. Nossa equipe retorna com uma proposta em breve."
        )

    if any(p in q for p in ("contato", "endereço", "endereco", "onde fica", "localização")):
        end = endereco_linha(loja)
        return (
            f"Estamos em {end or loja.get('cidade', '')}. "
            f"Telefone: {loja.get('telefone', '—')} · WhatsApp: {loja.get('whatsapp', '—')}. "
            f"Mais detalhes em {site_url('/contato')}."
        )

    if any(p in q for p in ("horário", "horario", "funcion", "aberto", "sábado", "sabado")):
        horario = loja.get("horario") or f"consulte {site_url('/contato')}"
        return f"Nosso horário: {horario}."

    if any(p in q for p in ("empresa", "história", "historia", "quem são", "sobre")):
        sobre = (loja.get("sobre") or "")[:400]
        return sobre or f"Conheça a {nome_loja} em {site_url('/empresa')}."

    if any(p in q for p in ("estoque", "carro", "veículo", "veiculo", "modelo", "marca")):
        veiculos = _buscar_veiculos_no_texto(q)
        if veiculos:
            linhas = [
                f"• {v.marca} {v.modelo} {v.ano} — {formatar_preco(v.preco)} "
                f"({formatar_km(v.km)}) → {site_url(f'/veiculo/{v.id}')}"
                for v in veiculos
            ]
            return (
                f"Encontrei estas opções no estoque:\n\n"
                + "\n".join(linhas)
                + f"\n\nVeja tudo em {site_url('/estoque')}."
            )
        total = len(filtrar_veiculos())
        return (
            f"Temos {total} veículo(s) disponível(is). "
            f"Acesse {site_url('/estoque')} para filtrar por marca ou fale conosco "
            f"pelo WhatsApp {loja.get('whatsapp', '')}."
        )

    if any(p in q for p in ("oi", "olá", "ola", "bom dia", "boa tarde", "boa noite")):
        return (
            f"Olá! Sou {nome_ia}, da {nome_loja}. "
            f"Posso ajudar com estoque, financiamento, avaliação ou contato. O que você precisa?"
        )

    return (
        f"Posso ajudar com veículos do estoque, financiamento "
        f"({site_url('/financiamento')}), avaliação de usado "
        f"({site_url('/avaliacao')}) ou contato "
        f"({loja.get('whatsapp') or loja.get('telefone')}). "
        f"Me conte o que você procura!"
    )


async def _openai_responder(
    system: str,
    historico: list[dict[str, str]],
    pergunta: str,
    api_key: str,
) -> str:
    mensagens: list[dict[str, str]] = [{"role": "system", "content": system}]
    for item in historico[-10:]:
        role = "assistant" if item.get("tipo") == "bot" else "user"
        mensagens.append({"role": role, "content": item.get("texto", "")})
    mensagens.append({"role": "user", "content": pergunta})

    modelo = os.getenv("IA_MODEL", "gpt-4o-mini")
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": modelo,
                "messages": mensagens,
                "temperature": 0.4,
                "max_tokens": 450,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


async def responder_ia(
    pergunta: str,
    historico: list[dict[str, Any]],
    loja: dict,
    nome_ia: str,
) -> str:
    contexto = montar_contexto_publico(loja)
    system = (
        f"Você é {nome_ia}, assistente virtual da loja {loja.get('nome', '')}. "
        f"Responda sempre em português do Brasil, cordial e objetivo (máx. 3 parágrafos curtos).\n\n"
        f"{contexto}"
    )
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        try:
            return await _openai_responder(system, historico, pergunta, api_key)
        except Exception:
            pass
    return _responder_local(pergunta, loja, nome_ia)


def validar_nome(nome: str) -> bool:
    partes = [p for p in re.split(r"\s+", nome.strip()) if p]
    return len(partes) >= 2 and len(nome.strip()) >= 5


def validar_telefone(tel: str) -> bool:
    digitos = re.sub(r"\D", "", tel)
    return 10 <= len(digitos) <= 11
