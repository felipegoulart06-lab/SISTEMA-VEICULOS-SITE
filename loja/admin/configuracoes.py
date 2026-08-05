from nicegui import ui

from loja.repositorio import obter_config, salvar_config


def pagina_configuracoes() -> None:
    cfg = obter_config()

    ui.html(
        '<div class="erp-page-header">'
        "<div><h2>White label</h2>"
        "<p>Personalize o sistema e os dados da empresa exibidos no site</p></div></div>"
    )

    with ui.element("div").classes("erp-config-stack"):
        with ui.element("div").classes("erp-painel"):
            ui.html(
                '<div class="erp-painel-titulo-row">'
                '<span class="material-icons erp-painel-ico">palette</span>'
                "<span>Identidade do sistema (ERP)</span></div>"
            )
            nome_sistema = ui.input(
                "Título da aba do ERP",
                value=cfg.nome_sistema,
                placeholder="Ex: Rodavia ERP, AutoGestão",
            ).classes("erp-input-full")
            favicon = ui.input(
                "Favicon (URL da imagem)",
                value=getattr(cfg, "favicon_url", "") or "",
                placeholder="https://minhaloja.com.br/favicon.ico",
            ).classes("erp-input-full")
            cor = ui.input(
                "Cor primária (hex)", value=cfg.cor_primaria
            ).classes("erp-input-full")
            ui.label(
                "O título e o favicon aparecem na aba do navegador ao usar o ERP. "
                "No site público, o favicon é o mesmo; o título do site fica em Site."
            ).classes("erp-ajuda")

        with ui.element("div").classes("erp-config-grid"):
            with ui.element("div").classes("erp-painel"):
                ui.html(
                    '<div class="erp-painel-titulo-row">'
                    '<span class="material-icons erp-painel-ico">store</span>'
                    "<span>Dados da empresa</span></div>"
                )
                nome = ui.input("Nome fantasia", value=cfg.nome).classes("erp-input-full")
                razao = ui.input("Razão social", value=cfg.razao_social).classes(
                    "erp-input-full"
                )
                cnpj = ui.input("CNPJ", value=cfg.cnpj).classes("erp-input-full")
                logo = ui.input(
                    "Texto do logo (site)", value=cfg.logo_texto,
                    placeholder="Ex: SIGMA — deixe vazio para usar o nome fantasia",
                ).classes("erp-input-full")
                slogan = ui.input(
                    "Slogan (abaixo do logo no site)", value=cfg.slogan,
                    placeholder="Ex: Multimarcas",
                ).classes("erp-input-full")

            with ui.element("div").classes("erp-painel"):
                ui.html(
                    '<div class="erp-painel-titulo-row">'
                    '<span class="material-icons erp-painel-ico">location_on</span>'
                    "<span>Endereço e contato</span></div>"
                )
                endereco = ui.input("Logradouro / número", value=cfg.endereco).classes(
                    "erp-input-full"
                )
                bairro = ui.input("Bairro", value=cfg.bairro).classes("erp-input-full")
                with ui.row().classes("erp-row-form w-full"):
                    cidade = ui.input("Cidade", value=cfg.cidade)
                    estado = ui.input("UF", value=cfg.estado).props("maxlength=2")
                    cep = ui.input("CEP", value=cfg.cep)
                telefone = ui.input("Telefone", value=cfg.telefone).classes(
                    "erp-input-full"
                )
                whatsapp = ui.input("WhatsApp", value=cfg.whatsapp).classes(
                    "erp-input-full"
                )
                email = ui.input("E-mail", value=cfg.email).classes("erp-input-full")
                horario = ui.input("Horário de funcionamento", value=cfg.horario).classes(
                    "erp-input-full"
                )

        with ui.element("div").classes("erp-config-grid"):
            with ui.element("div").classes("erp-painel"):
                ui.html(
                    '<div class="erp-painel-titulo-row">'
                    '<span class="material-icons erp-painel-ico">share</span>'
                    "<span>Redes sociais</span></div>"
                )
                facebook = ui.input("Facebook (URL)", value=cfg.facebook).classes(
                    "erp-input-full"
                )
                instagram = ui.input("Instagram (URL)", value=cfg.instagram).classes(
                    "erp-input-full"
                )

            with ui.element("div").classes("erp-painel"):
                ui.html(
                    '<div class="erp-painel-titulo-row">'
                    '<span class="material-icons erp-painel-ico">language</span>'
                    "<span>Site público</span></div>"
                )
                banner = ui.input("URL do banner", value=cfg.banner_url).classes(
                    "erp-input-full"
                )
                sobre = ui.textarea("Texto sobre a loja", value=cfg.sobre).classes(
                    "erp-input-full"
                )
                ui.label(
                    "CNPJ, endereço e contatos aparecem no rodapé e cards do site."
                ).classes("erp-ajuda")

        with ui.element("div").classes("erp-painel"):
            ui.html(
                '<div class="erp-painel-titulo-row">'
                '<span class="material-icons erp-painel-ico">support_agent</span>'
                "<span>Atendimento online (chat do site)</span></div>"
            )
            nome_ia = ui.input(
                "Nome da IA no chat",
                value=getattr(cfg, "nome_ia", "") or "Assistente Virtual",
                placeholder="Ex: Luna, Sofia, Assistente Virtual",
            ).classes("erp-input-full")
            ia_ativa = ui.switch(
                "Ativar IA no chat do site",
                value=bool(getattr(cfg, "ia_ativa", False)),
            )
            ui.label(
                "Com a IA desligada, o chat abre a Central de Atendimento "
                "com telefone, WhatsApp e formulário. "
                "Com a IA ligada, o visitante conversa antes de tirar dúvidas "
                "sobre estoque e páginas do site."
            ).classes("erp-ajuda")
            ui.label(
                "A IA só usa dados públicos (estoque, contato, páginas). "
                "Nunca expõe informações internas do ERP."
            ).classes("erp-ajuda")

    def salvar() -> None:
        salvar_config({
            "nome_sistema": nome_sistema.value.strip() or "Gestão Veículos",
            "favicon_url": favicon.value.strip(),
            "cor_primaria": cor.value.strip() or "#c0392b",
            "nome": nome.value.strip(),
            "razao_social": razao.value.strip(),
            "cnpj": cnpj.value.strip(),
            "logo_texto": logo.value.strip(),
            "slogan": slogan.value.strip(),
            "endereco": endereco.value.strip(),
            "bairro": bairro.value.strip(),
            "cidade": cidade.value.strip(),
            "estado": estado.value.strip().upper()[:2],
            "cep": cep.value.strip(),
            "telefone": telefone.value.strip(),
            "whatsapp": whatsapp.value.strip(),
            "email": email.value.strip(),
            "horario": horario.value.strip(),
            "facebook": facebook.value.strip(),
            "instagram": instagram.value.strip(),
            "banner_url": banner.value.strip(),
            "sobre": sobre.value or "",
            "nome_ia": nome_ia.value.strip() or "Assistente Virtual",
            "ia_ativa": ia_ativa.value,
        })
        ui.notify(
            "Configurações salvas! Recarregue o site e o ERP para ver as mudanças.",
            type="positive",
        )

    with ui.element("div").classes("erp-toolbar"):
        ui.button("Salvar configurações", on_click=salvar).classes(
            "erp-btn-primario"
        ).props("unelevated no-caps")

    with ui.element("div").classes("erp-painel").style("margin-top:24px"):
        ui.html(
            '<div class="erp-painel-titulo-row">'
            '<span class="material-icons erp-painel-ico">extension</span>'
            "<span>Integrações (próximas etapas)</span></div>"
        )
        ui.html(
            "<p>WhatsApp (link já funciona pelo número cadastrado), "
            "e-mail SMTP automático e domínio próprio "
            "ficam para a próxima evolução do produto.</p>"
            "<p>Marketplaces (Webmotors, OLX, etc.) ficarão em "
            "<strong>Integrações</strong> — em breve.</p>"
        )
        ui.link("Personalizar aparência do site →", "/admin/site")
