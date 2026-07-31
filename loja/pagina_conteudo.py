"""Renderização das páginas institucionais do site (privacidade, LGPD...)."""

from sqlalchemy import select

from nicegui import ui

from loja.database import get_session
from loja.models import PaginaSite


def obter_pagina(slug: str) -> PaginaSite | None:
    with get_session() as db:
        p = db.scalar(
            select(PaginaSite).where(
                PaginaSite.slug == slug, PaginaSite.publicada.is_(True),
            )
        )
        if p:
            db.expunge(p)
        return p


def listar_paginas_menu() -> list[PaginaSite]:
    with get_session() as db:
        itens = db.scalars(
            select(PaginaSite)
            .where(PaginaSite.publicada.is_(True), PaginaSite.no_menu.is_(True))
            .order_by(PaginaSite.ordem)
        ).all()
        for i in itens:
            db.expunge(i)
        return list(itens)


def montar_pagina_conteudo(slug: str) -> None:
    pagina = obter_pagina(slug)
    with ui.element("article").classes("pagina-conteudo"):
        if pagina is None:
            ui.html("<h1>Página não encontrada</h1>")
            ui.html("<p>Este conteúdo ainda não foi publicado.</p>")
            return
        ui.html(f"<h1>{pagina.titulo}</h1>")
        if pagina.conteudo_html:
            ui.html(pagina.conteudo_html)
        else:
            ui.html(
                '<p class="pagina-vazia">Conteúdo ainda não preenchido. '
                "Edite esta página no ERP em Site → Páginas.</p>"
            )
