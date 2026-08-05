from nicegui import ui

from loja.admin.layout import ajuda
from loja.repositorio import config_como_dict, salvar_config
from loja.tenant_ctx import site_url


def _navegar_erp(href: str) -> None:
    """Navega no ERP sem reload quando o SPA estiver ativo."""
    ir = getattr(ui.context.client, "erp_ir", None)
    if callable(ir):
        ir(href)
    else:
        ui.navigate.to(href)


def pagina_site() -> None:
    cfg = config_como_dict()
    ui.html(
        '<div class="erp-page-header"><div>'
        "<h2>Site público</h2>"
        "<p>Logo, banner, cores e rodapé</p></div></div>"
    )
    ajuda(
        "O que você mudar aqui aparece no site do cliente. "
        "Menus do site são fixos (Home, Estoque, Financiamento…). "
        "O conteúdo da página EMPRESA fica em Editar institucional."
    )

    with ui.element("div").classes("erp-toolbar"):
        ui.button(
            "EDITAR INSTITUCIONAL ›",
            on_click=lambda: _navegar_erp("/admin/site/institucional"),
        ).classes("btn btn-preto").props("unelevated no-caps")
        ui.link("Abrir site", site_url("/")).props("target=_blank")

    with ui.element("div").classes("erp-form-page erp-painel"):
        with ui.element("div").classes("erp-form-grid"):
            logo = ui.input(
                "Logo (texto)", value=cfg.get("logo_texto", ""),
            ).props("outlined dense")
            slogan = ui.input(
                "Slogan", value=cfg.get("slogan", ""),
            ).props("outlined dense")
            banner = ui.input(
                "URL do banner", value=cfg.get("banner_url", ""),
            ).props("outlined dense").classes("erp-form-full")
            cor = ui.input(
                "Cor primária", value=cfg.get("cor_primaria", "#c0392b"),
            ).props("outlined dense type=color")
            facebook = ui.input(
                "Facebook", value=cfg.get("facebook", ""),
            ).props("outlined dense")
            instagram = ui.input(
                "Instagram", value=cfg.get("instagram", ""),
            ).props("outlined dense")
            seo_titulo = ui.input(
                "Título da aba do site",
                value=cfg.get("seo_titulo", ""),
                placeholder="Ex: Rodavia Multimarcas",
            ).props("outlined dense").classes("erp-form-full")
            dominio = ui.input(
                "Domínio (informativo)",
                value=cfg.get("dominio", ""),
                placeholder="www.minhaloja.com.br",
            ).props("outlined dense").classes("erp-form-full")
            sobre = ui.textarea(
                "Texto sobre a empresa (rodapé/home)",
                value=cfg.get("sobre", ""),
            ).props("outlined dense").classes("erp-form-full")
            seo_desc = ui.textarea(
                "SEO — descrição", value=cfg.get("seo_descricao", ""),
            ).props("outlined dense").classes("erp-form-full")

        ui.html(
            '<p class="erp-ajuda">Favicon da loja: configure em '
            "<strong>Configurações → Identidade do sistema</strong>.</p>"
        )

        def salvar():
            salvar_config({
                "logo_texto": logo.value or "",
                "slogan": slogan.value or "",
                "banner_url": banner.value or "",
                "cor_primaria": cor.value or "#c0392b",
                "facebook": facebook.value or "",
                "instagram": instagram.value or "",
                "sobre": sobre.value or "",
                "seo_titulo": seo_titulo.value or "",
                "seo_descricao": seo_desc.value or "",
                "dominio": dominio.value or "",
            })
            ui.notify(
                "Site atualizado! Recarregue a página pública.", type="positive",
            )

        ui.button(
            "Salvar alterações", on_click=salvar,
        ).classes("btn btn-preto").props("unelevated no-caps").style(
            "margin-top:16px"
        )
