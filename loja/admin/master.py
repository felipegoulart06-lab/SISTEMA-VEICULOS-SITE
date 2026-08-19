"""Painel do Administrador Master — MVP.

Telas: Dashboard, Empresas, Planos, Domínios, Logs e Configurações.
"""

from datetime import datetime, timedelta

from nicegui import ui

from loja.auth import (
    exigir_master,
    fazer_logout_master,
    master_logado,
    master_nome,
    tentar_login_master,
)
from loja.seguranca import mostrar_credenciais_demo
from loja.provisionamento import gerar_token_longo
from loja.tempo import naive
from loja.plataforma import (
    DIAS_PARA_EXCLUSAO,
    LOG_LABEL,
    STATUS_CONTA,
    STATUS_CRIACAO,
    STATUS_LABEL,
    TIPOS_LOG,
    alterar_status_conta,
    atualizar_conta,
    atualizar_dominios,
    criar_conta,
    data_liberacao_exclusao,
    dias_restantes_exclusao,
    estatisticas_plataforma,
    excluir_conta,
    excluir_plano,
    gerar_dominios_empresa,
    listar_contas,
    listar_logs,
    listar_planos,
    obter_conta,
    obter_config_plataforma,
    obter_plano,
    pode_excluir_conta,
    regenerar_token,
    renovar_licenca,
    salvar_config_plataforma,
    salvar_plano,
    slugify,
    ultimas_contas,
)

MENU_MASTER = [
    ("Dashboard", "/master", "dashboard"),
    ("Empresas", "/master/empresas", "storefront"),
    ("Planos", "/master/planos", "credit_card"),
    ("Domínios", "/master/dominios", "language"),
    ("Guia de implantação", "/master/guia", "menu_book"),
    ("Logs", "/master/logs", "receipt_long"),
    ("Configurações", "/master/configuracoes", "settings"),
]

TOM_STATUS = {
    "ativa": "ok",
    "teste": "info",
    "suspensa": "erro",
    "cancelada": "neutro",
}


def _moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data(valor) -> str:
    return valor.strftime("%d/%m/%Y") if valor else "—"


def _data_hora(valor) -> str:
    return valor.strftime("%d/%m/%Y %H:%M") if valor else "—"


def _pill(texto: str, tom: str) -> str:
    return f'<span class="mst-pill mst-pill-{tom}">{texto}</span>'


def _pill_status(status: str) -> str:
    return _pill(STATUS_LABEL.get(status, status), TOM_STATUS.get(status, "neutro"))


def _pill_licenca(vencimento) -> str:
    from loja.tempo import agora, naive

    venc = naive(vencimento)
    if not venc:
        return _pill("sem prazo", "neutro")
    dias = (venc - agora()).days
    if dias < 0:
        return _pill(f"vencida em {_data(venc)}", "erro")
    if dias <= 7:
        return _pill(f"vence em {dias}d", "alerta")
    return _pill(_data(venc), "ok")


def _css_master() -> None:
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    ui.add_head_html(
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2'
        '?family=Inter:wght@400;500;600;700;800&display=swap">'
    )
    ui.add_head_html(
        '<link rel="stylesheet" href="https://fonts.googleapis.com/icon'
        '?family=Material+Icons">'
    )
    ui.add_head_html('<link rel="stylesheet" href="/static/admin.css?v=28">')
    ui.add_head_html(
        "<style>:root { --erp-accent: #1e3a5f; --erp-accent-hover: #16304f; "
        "--erp-accent-soft: rgba(30,58,95,0.12); }</style>"
    )


def layout_master(pagina_atual: str, conteudo_fn) -> None:
    if not exigir_master():
        return
    _css_master()
    cfg = obter_config_plataforma()
    sidebar_ref = {"el": None}
    backdrop_ref = {"el": None}
    aberto = {"v": False}

    def _aplicar_menu(ligado: bool) -> None:
        sb = sidebar_ref["el"]
        bd = backdrop_ref["el"]
        if sb is None:
            return
        if ligado:
            sb.classes(add="aberto")
            if bd is not None:
                bd.classes(add="aberto")
        else:
            sb.classes(remove="aberto")
            if bd is not None:
                bd.classes(remove="aberto")

    def toggle_sidebar() -> None:
        aberto["v"] = not aberto["v"]
        _aplicar_menu(aberto["v"])

    def fechar_sidebar() -> None:
        aberto["v"] = False
        _aplicar_menu(False)

    titulo = next(
        (t for t, href, _ in MENU_MASTER if href == pagina_atual), "Painel",
    )

    with ui.element("div").classes("erp-app"):
        backdrop_ref["el"] = ui.element("div").classes(
            "erp-sidebar-backdrop"
        ).on("click", fechar_sidebar)
        sidebar_ref["el"] = ui.element("aside").classes("erp-sidebar")
        with sidebar_ref["el"]:
            with ui.element("div").classes("erp-sidebar-topo"):
                ui.html(
                    f'<div class="erp-logo-text">{cfg.nome_plataforma}</div>'
                )
                ui.html('<p class="erp-loja-nome">Administrador Master</p>')

            with ui.element("nav").classes("erp-nav"):
                for item_titulo, href, icone in MENU_MASTER:
                    ativo = "ativo" if pagina_atual == href else ""
                    ui.html(
                        f'<a href="{href}" class="erp-nav-item {ativo}">'
                        f'<span class="material-icons erp-nav-ico">{icone}</span>'
                        f"<span>{item_titulo}</span></a>"
                    )

            with ui.element("div").classes("erp-sidebar-rodape"):
                ui.html(f'<span class="mst-versao">v{cfg.versao}</span>')
                ui.button(
                    "Sair do Master",
                    on_click=lambda: (
                        fazer_logout_master(), ui.navigate.to("/master/login"),
                    ),
                ).props("flat no-caps").classes("erp-btn-sair")

        with ui.element("div").classes("erp-main"):
            with ui.element("header").classes("erp-topbar"):
                with ui.element("div").classes("erp-topbar-esq"):
                    ui.button("☰", on_click=toggle_sidebar).classes(
                        "erp-menu-mobile"
                    ).props("flat dense")
                    ui.html(
                        f'<div class="erp-topbar-titulos"><h1>{titulo}</h1>'
                        f"<span>Controle da plataforma</span></div>"
                    )
                with ui.element("div").classes("erp-topbar-dir"):
                    with ui.element("div").classes("erp-user-pill"):
                        with ui.element("div").classes("erp-user-info"):
                            ui.label(master_nome()).classes("erp-usuario-nome")
                            ui.label("Master").classes("erp-usuario-cargo")
                        with ui.element("div").classes("erp-avatar"):
                            ui.label(master_nome()[0].upper())

            with ui.element("div").classes("erp-conteudo"):
                conteudo_fn()


def pagina_master_login() -> None:
    """Login exclusivo do Administrador Master."""
    _css_master()
    if master_logado():
        ui.navigate.to("/master")
        return

    ui.add_head_html(
        "<style>:root { --erp-accent: #1e3a5f; --erp-accent-hover: #16304f; }</style>"
    )

    with ui.element("div").classes("erp-login-page erp-login-master"):
        with ui.element("div").classes("erp-login-brand"):
            ui.html('<div class="erp-login-brand-logo">PLATAFORMA</div>')
            ui.html('<p class="erp-login-brand-loja">Administrador Master</p>')
            ui.html(
                '<ul class="erp-login-features">'
                "<li>Criar e gerenciar empresas</li>"
                "<li>Planos, licença e status</li>"
                "<li>Domínios e logs da plataforma</li>"
                "</ul>"
            )
            ui.html(
                '<p class="erp-login-brand-copy">'
                "Acesso restrito — não use esta tela para entrar nas lojas"
                "</p>"
            )

        with ui.element("div").classes("erp-login-form-side"):
            with ui.element("div").classes("erp-login-card"):
                ui.html(
                    '<div class="erp-login-card-topo"><h1>Login Master</h1>'
                    "<p>Acesso exclusivo do administrador da plataforma</p>"
                    "</div>"
                )
                email = ui.input("E-mail Master").props(
                    "outlined dense hide-bottom-space autofocus"
                ).classes("erp-login-field")
                senha = ui.input(
                    "Senha",
                    password=True,
                    password_toggle_button=True,
                ).props("outlined dense hide-bottom-space").classes("erp-login-field")
                codigo_totp = ui.input("Código 2FA (se ativo)").props(
                    "outlined dense hide-bottom-space maxlength=8"
                ).classes("erp-login-field")

                def entrar() -> None:
                    ok, erro = tentar_login_master(
                        email.value or "",
                        senha.value or "",
                        codigo_totp.value or "",
                    )
                    if ok:
                        ui.notify("Login Master realizado!", type="positive")
                        ui.navigate.to("/master")
                    else:
                        ui.notify(
                            erro or "E-mail ou senha incorretos.",
                            type="negative",
                        )

                senha.on("keydown.enter", entrar)
                codigo_totp.on("keydown.enter", entrar)
                ui.button("Entrar como Master", on_click=entrar).classes(
                    "erp-login-btn"
                ).props("unelevated no-caps")
                if mostrar_credenciais_demo():
                    with ui.element("div").classes("erp-login-rodape-card"):
                        ui.html(
                            '<span class="erp-login-badge">Master</span>'
                            "<code>master@plataforma.com</code>"
                            '<span class="erp-login-sep">·</span>'
                            "<code>master123</code>"
                        )


# ------------------------------------------------------------ Dashboard

def pagina_master_dashboard() -> None:
    stats = estatisticas_plataforma()
    ui.html(
        '<div class="erp-page-header"><div><h2>Dashboard</h2>'
        "<p>Visão geral das empresas</p></div>"
        '<div><a href="/master/guia" class="mst-link-guia">'
        '<span class="material-icons">menu_book</span> Guia de implantação'
        "</a></div></div>"
    )

    cartoes = [
        ("Total de empresas", stats["total"], "storefront"),
        ("Empresas ativas", stats["ativas"], "check_circle"),
        ("Empresas em teste", stats["teste"], "science"),
        ("Empresas suspensas", stats["suspensas"], "block"),
    ]
    with ui.element("div").classes("mst-kpis"):
        for rotulo, valor, icone in cartoes:
            with ui.element("div").classes("mst-kpi"):
                ui.html(
                    f'<span class="material-icons mst-kpi-ico">{icone}</span>'
                    f'<div><div class="mst-kpi-valor">{valor}</div>'
                    f'<div class="mst-kpi-rotulo">{rotulo}</div></div>'
                )

    with ui.element("div").classes("erp-painel").style("margin-top:16px"):
        ui.html(
            '<div class="erp-painel-titulo-row">'
            '<span class="material-icons erp-painel-ico">history</span>'
            "<span>Últimas empresas criadas</span></div>"
        )
        contas = ultimas_contas()
        if not contas:
            ui.html(
                '<p class="erp-ajuda">Nenhuma empresa cadastrada. '
                "Crie a primeira em Empresas.</p>"
            )
        for c in contas:
            with ui.element("div").classes("mst-linha"):
                ui.html(
                    f"<div><strong>{c.nome}</strong> {_pill_status(c.status)}"
                    f'<div class="mst-sub">{c.subdominio or c.slug} · criada em '
                    f"{_data(c.criado_em)}</div></div>"
                )


# ------------------------------------------------------------- Empresas

def pagina_master_empresas() -> None:
    ui.html(
        '<div class="erp-page-header"><div><h2>Empresas</h2>'
        "<p>Cada empresa possui ERP e site isolados</p></div></div>"
    )

    @ui.refreshable
    def lista() -> None:
        contas = listar_contas()
        planos = {p.id: p.nome for p in listar_planos()}
        if not contas:
            ui.html('<p class="erp-ajuda">Nenhuma empresa criada ainda.</p>')
            return
        with ui.element("div").classes("mst-tabela-wrap"):
            ui.html(
                '<div class="mst-tabela-head mst-head-emp">'
                "<span>Empresa</span><span>Plano</span><span>Status</span>"
                "<span>Criada em</span><span>Licença até</span>"
                "<span>Ações</span></div>"
            )
            for c in contas:
                inicial = (c.nome or "?")[0].upper()
                with ui.element("div").classes("mst-tabela-row mst-head-emp"):
                    ui.html(
                        f'<span class="mst-empresa">'
                        f'<span class="mst-logo" style="background:{c.tema_cor}">'
                        f"{inicial}</span>"
                        f"<span><strong>{c.nome}</strong>"
                        f'<span class="mst-sub">{c.email}</span></span></span>'
                    )
                    ui.html(f"<span>{planos.get(c.plano_id, '—')}</span>")
                    ui.html(f"<span>{_pill_status(c.status)}</span>")
                    ui.html(f"<span>{_data(c.criado_em)}</span>")
                    ui.html(f"<span>{_pill_licenca(c.vencimento_em)}</span>")
                    with ui.element("span").classes("mst-acoes"):
                        ui.button(
                            "Editar",
                            on_click=lambda cid=c.id: _dialog_editar(
                                cid, lista.refresh
                            ),
                        ).props("flat dense no-caps").classes("mst-btn-mini")
                        rotulo = (
                            "Reativar" if c.status == "suspensa" else "Desativar"
                        )
                        ui.button(
                            rotulo,
                            on_click=lambda cid=c.id, st=c.status, n=c.nome: _confirmar_alternar(
                                cid, st, n, lista.refresh
                            ),
                        ).props("flat dense no-caps").classes("mst-btn-mini")
                        _acoes_exclusao(c, lista.refresh)

    with ui.element("div").classes("erp-toolbar"):
        ui.button(
            "Criar empresa", on_click=lambda: _dialog_criar(lista.refresh),
        ).classes("erp-btn-primario").props("unelevated no-caps")

    lista()


def _confirmar_alternar(
    conta_id: int, status_atual: str, nome: str, refresh,
) -> None:
    desativar = status_atual != "suspensa"
    if desativar:
        titulo = f"Desativar a empresa {nome}?"
        texto = (
            "O ERP e o site ficarão bloqueados imediatamente. "
            f"A exclusão só poderá ser feita após {DIAS_PARA_EXCLUSAO} dias."
        )
        rotulo_acao = "Desativar"
        cor = "warning"
    else:
        titulo = f"Reativar a empresa {nome}?"
        texto = "A empresa voltará a acessar ERP e site público."
        rotulo_acao = "Reativar"
        cor = "primary"

    with ui.dialog() as dlg, ui.card().classes("erp-dialog"):
        ui.label(titulo).classes("text-weight-bold")
        ui.label(texto)
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")

            def confirmar() -> None:
                dlg.close()
                _alternar(conta_id, status_atual, refresh)

            ui.button(rotulo_acao, on_click=confirmar).props(
                f"unelevated no-caps color={cor}"
            )
    dlg.open()


def _alternar(conta_id: int, status_atual: str, refresh) -> None:
    novo = "ativa" if status_atual == "suspensa" else "suspensa"
    alterar_status_conta(conta_id, novo)
    if novo == "suspensa":
        ui.notify(
            f"Empresa desativada. Conta bloqueada. "
            f"Exclusão liberada em {DIAS_PARA_EXCLUSAO} dias.",
            type="warning",
            timeout=7000,
        )
    else:
        ui.notify("Empresa reativada.", type="positive")
    refresh()


def _acoes_exclusao(conta, refresh) -> None:
    """Excluir só após 31 dias desativada; enquanto isso mostra a contagem."""
    dias = dias_restantes_exclusao(conta)
    if dias is None:
        ui.html(
            '<span class="mst-exclusao-bloqueada" title="'
            f'Desative a empresa e aguarde {DIAS_PARA_EXCLUSAO} dias">'
            "Excluir</span>"
        )
        return
    if dias > 0:
        liberacao = data_liberacao_exclusao(conta)
        data_txt = liberacao.strftime("%d/%m/%Y") if liberacao else ""
        ui.html(
            f'<span class="mst-contagem-exclusao" title="Liberada em {data_txt}">'
            f"Exclusão em <strong>{dias}</strong> dia"
            f'{"s" if dias != 1 else ""}</span>'
        )
        return
    ui.button(
        "Excluir",
        on_click=lambda cid=conta.id, n=conta.nome: _dialog_excluir(
            cid, n, refresh
        ),
    ).props("flat dense no-caps").classes("mst-btn-mini mst-btn-perigo")


def _dialog_excluir(conta_id: int, nome: str, refresh) -> None:
    conta = obter_conta(conta_id)
    if conta is None or not pode_excluir_conta(conta):
        ui.notify(
            "Exclusão ainda não liberada. Aguarde 31 dias após desativar.",
            type="warning",
        )
        return
    with ui.dialog() as dlg, ui.card().classes("erp-dialog"):
        ui.label(f"Excluir a empresa {nome}?").classes("text-weight-bold")
        ui.label(
            "O ERP, o site e todos os dados serão apagados definitivamente."
        )
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")

            def confirmar() -> None:
                try:
                    excluir_conta(conta_id)
                except ValueError as exc:
                    ui.notify(str(exc), type="warning")
                    return
                dlg.close()
                ui.notify("Empresa excluída.", type="positive")
                refresh()

            ui.button("Excluir", on_click=confirmar).props(
                "unelevated no-caps color=negative"
            )
    dlg.open()


def _abrir_paleta_cor(campo_cor, preview_el) -> None:
    """Abre seletor de cor em diálogo próprio (evita bug dentro do modal principal)."""
    inicial = (campo_cor.value or "#c0392b").strip()
    if not inicial.startswith("#"):
        inicial = "#c0392b"
    estado = {"cor": inicial}

    with ui.dialog() as paleta, ui.card().classes("erp-dialog mst-paleta-cor"):
        ui.html("<h3 class='erp-dialog-titulo'>Escolher cor do tema</h3>")
        qcolor = ui.element("q-color").props(
            f'model-value="{inicial}" no-header no-footer'
        )
        qcolor.on("change", lambda e: estado.update(cor=e.args or estado["cor"]))

        def aplicar() -> None:
            campo_cor.set_value(estado["cor"])
            preview_el.style(f"background-color: {estado['cor']}")
            paleta.close()

        with ui.row().classes("w-full justify-end gap-2 erp-dialog-botoes"):
            ui.button("Cancelar", on_click=paleta.close).props("flat no-caps")
            ui.button("Aplicar", on_click=aplicar).classes(
                "erp-btn-primario"
            ).props("unelevated no-caps")
    paleta.open()


def _dialog_criar(refresh) -> None:
    planos = listar_planos(apenas_ativos=True)
    opcoes = {p.id: p.nome for p in planos}
    cfg = obter_config_plataforma()
    dominio_base = cfg.dominio_base or "plataforma.com.br"

    with ui.dialog() as dlg, ui.card().classes("erp-dialog mst-dialog"):
        with ui.column().classes("w-full erp-form-stack mst-form-criar"):
            ui.html("<h3>Criar empresa</h3>")
            ui.html(
                '<p class="erp-ajuda">Cria banco isolado, ERP vazio, site público limpo '
                "(sem veículos nem conteúdo) e domínios exclusivos para esta empresa. "
                "A senha temporária é obrigatória.</p>"
            )
            nome = ui.input("Nome da empresa").classes("erp-input-full")
            email = ui.input("E-mail do administrador (login)").classes("erp-input-full")
            sub = ui.input(
                "Identificador", placeholder="minha-loja",
            ).classes("erp-input-full")
            plano = ui.select(
                opcoes, label="Plano",
                value=planos[0].id if planos else None,
            ).classes("erp-input-full")
            status = ui.select(
                STATUS_CRIACAO,
                label="Status inicial",
                value="ativa",
            ).classes("erp-input-full")
            dias = ui.number("Dias de licença", value=30, format="%.0f").classes(
                "erp-input-full"
            )

            @ui.refreshable
            def preview_dominios() -> None:
                slug_prev = slugify(sub.value or nome.value or "minha-loja")
                doms = gerar_dominios_empresa(slug_prev, dominio_base)
                ui.html(
                    '<div class="mst-dominios-preview erp-ajuda">'
                    "<strong>Acesso configurado automaticamente</strong><br>"
                    f"ERP (subdomínio): <code>{doms['subdominio']}</code><br>"
                    "Site: configure o domínio próprio depois em Domínios<br>"
                    f"Dev local site: <code>/loja/{slug_prev}/</code>"
                    "</div>"
                )

            preview_dominios()
            sub.on("update:model-value", lambda _: preview_dominios.refresh())
            nome.on("update:model-value", lambda _: preview_dominios.refresh())

            ui.label("Cor do tema").classes("mst-field-label")
            with ui.row().classes("w-full items-center gap-3 mst-cor-tema-row"):
                preview_cor = ui.element("div").classes("mst-cor-preview")
                preview_cor.style("background-color: #c0392b")
                cor = ui.input(
                    value="#c0392b",
                    placeholder="#c0392b",
                ).classes("erp-input-full flex-grow")
                ui.button(
                    icon="palette",
                    on_click=lambda: _abrir_paleta_cor(cor, preview_cor),
                ).props("outline round dense").classes("mst-btn-paleta")

                def _atualizar_preview_cor() -> None:
                    val = (cor.value or "").strip()
                    if len(val) == 7 and val.startswith("#"):
                        try:
                            int(val[1:], 16)
                        except ValueError:
                            return
                        preview_cor.style(f"background-color: {val}")

                cor.on("update:model-value", lambda _: _atualizar_preview_cor())

            ui.label("Senha temporária *").classes("mst-field-label")
            with ui.row().classes("w-full items-center gap-2 mst-senha-row"):
                senha = ui.input(
                    "Senha temporária",
                    password=True,
                    password_toggle_button=True,
                    placeholder="Obrigatória — mín. 8 caracteres",
                ).classes("erp-input-full flex-grow")
                ui.button(
                    "Gerar token (25)",
                    on_click=lambda: senha.set_value(gerar_token_longo(25)),
                ).props("outline no-caps dense").classes("mst-btn-gerar-token")

            estado: dict = {"relatorio": None}

            @ui.refreshable
            def sucesso() -> None:
                relatorio = estado.get("relatorio")
                if relatorio is None:
                    return
                linhas = "".join(
                    f'<li class="mst-etapa-{"ok" if e.ok else "erro"}">{e.titulo}'
                    + (f' <span class="mst-sub">{e.detalhe}</span>' if e.detalhe else "")
                    + "</li>"
                    for e in relatorio.etapas
                )
                ui.html(
                    f'<div class="mst-sucesso"><strong>Empresa criada!</strong><br>'
                    f"ERP: acesse <code>{estado['subdominio']}</code> no navegador<br>"
                    f"Site (dev): <a href='/loja/{estado['slug']}/' target='_blank'>"
                    f"/loja/{estado['slug']}/</a><br>"
                    f"Domínio do site: "
                    f"<code>{estado['dominio_site'] or 'configurar em Domínios'}</code><br>"
                    f"Login (e-mail): <code>{estado['email']}</code><br>"
                    f"Senha temporária: <code>{estado['senha']}</code><br>"
                    f"<span>O administrador precisará trocar a senha no primeiro "
                    f"acesso.</span>"
                    f'<ul class="mst-etapas">{linhas}</ul></div>'
                )

            def criar() -> None:
                if not nome.value or not email.value:
                    ui.notify("Preencha nome e e-mail.", type="warning")
                    return
                senha_val = (senha.value or "").strip()
                if len(senha_val) < 8:
                    ui.notify(
                        "Informe a senha temporária (mínimo 8 caracteres) "
                        "ou gere um token de 25 dígitos.",
                        type="warning",
                    )
                    return
                try:
                    conta, senha_gerada, relatorio = criar_conta(
                        nome=nome.value,
                        email=email.value,
                        slug=sub.value or None,
                        token=senha_val,
                        plano_id=plano.value,
                        status=status.value,
                        dias_licenca=int(dias.value or 30),
                        tema_cor=cor.value or "#c0392b",
                    )
                except ValueError as err:
                    ui.notify(str(err), type="negative")
                    return
                except Exception as err:
                    ui.notify(f"Erro ao criar empresa: {err}", type="negative")
                    return
                estado.update({
                    "relatorio": relatorio,
                    "slug": conta.slug,
                    "senha": senha_gerada,
                    "email": conta.email,
                    "subdominio": conta.subdominio,
                    "dominio_site": conta.dominio_site,
                    "dominio_erp": conta.dominio_erp,
                })
                ui.notify("Empresa criada!", type="positive")
                sucesso.refresh()
                refresh()

            sucesso()
            with ui.row().classes("w-full justify-end gap-2 erp-dialog-botoes"):
                ui.button("Fechar", on_click=dlg.close).props("flat no-caps")
                ui.button("Criar empresa", on_click=criar).classes(
                    "erp-btn-primario"
                ).props("unelevated no-caps")
    dlg.open()


def _dialog_editar(conta_id: int, refresh) -> None:
    conta = obter_conta(conta_id)
    if conta is None:
        return
    opcoes = {p.id: p.nome for p in listar_planos()}

    with ui.dialog() as dlg, ui.card().classes("erp-dialog mst-dialog"):
        ui.html(f"<h3>Editar {conta.nome}</h3>")
        nome = ui.input("Nome", value=conta.nome).classes("erp-input-full")
        plano = ui.select(
            opcoes, label="Plano", value=conta.plano_id,
        ).classes("erp-input-full")
        status = ui.select(
            {s: STATUS_LABEL[s] for s in STATUS_CONTA},
            label="Status", value=conta.status,
        ).classes("erp-input-full")
        vencimento = ui.input(
            "Licença até",
            value=(naive(conta.vencimento_em) or datetime.now()).strftime("%Y-%m-%d"),
        ).props("type=date").classes("erp-input-full")
        cor = ui.input("Cor do tema", value=conta.tema_cor).classes(
            "erp-input-full"
        )
        logo = ui.input("Logo (URL)", value=conta.logo_url).classes(
            "erp-input-full"
        )
        favicon = ui.input("Favicon (URL)", value=conta.favicon_url).classes(
            "erp-input-full"
        )
        obs = ui.textarea("Observações", value=conta.observacoes).classes(
            "erp-input-full"
        )
        ui.html(
            '<p class="erp-ajuda">Os domínios são editados na tela Domínios.</p>'
        )

        def salvar() -> None:
            try:
                venc = datetime.strptime(vencimento.value, "%Y-%m-%d")
            except (TypeError, ValueError):
                venc = conta.vencimento_em
            atualizar_conta(conta_id, {
                "nome": nome.value.strip() or conta.nome,
                "plano_id": plano.value,
                "status": status.value,
                "vencimento_em": venc,
                "tema_cor": cor.value.strip() or "#c0392b",
                "logo_url": logo.value.strip(),
                "favicon_url": favicon.value.strip(),
                "observacoes": obs.value or "",
            })
            dlg.close()
            ui.notify("Empresa atualizada.", type="positive")
            refresh()

        def nova_senha() -> None:
            token = regenerar_token(conta_id)
            ui.notify(
                f"Nova senha temporária: {token}", type="positive",
                timeout=0, close_button="Fechar",
            )

        def renovar() -> None:
            novo = renovar_licenca(conta_id, 30)
            if novo:
                vencimento.value = novo.strftime("%Y-%m-%d")
                ui.notify(
                    f"Licença renovada até {novo:%d/%m/%Y}.", type="positive",
                )
                refresh()

        with ui.row().classes("w-full justify-between gap-2 mt-3"):
            with ui.row().classes("gap-2"):
                ui.button("Renovar 30 dias", on_click=renovar).props(
                    "flat no-caps"
                )
                ui.button("Nova senha", on_click=nova_senha).props(
                    "flat no-caps"
                )
            with ui.row().classes("gap-2"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
                ui.button("Salvar", on_click=salvar).classes(
                    "erp-btn-primario"
                ).props("unelevated no-caps")
    dlg.open()


# --------------------------------------------------------------- Planos

def pagina_master_planos() -> None:
    ui.html(
        '<div class="erp-page-header"><div><h2>Planos</h2>'
        "<p>Nesta versão a plataforma opera com o plano Starter</p>"
        "</div></div>"
    )

    @ui.refreshable
    def grade() -> None:
        planos = listar_planos()
        contas = listar_contas()
        with ui.element("div").classes("mst-planos"):
            for p in planos:
                em_uso = sum(1 for c in contas if c.plano_id == p.id)
                with ui.element("div").classes("mst-plano"):
                    ui.html(
                        f'<div class="mst-plano-topo"><h3>{p.nome}</h3>'
                        f'<div class="mst-plano-preco">{_moeda(p.preco_mensal)}'
                        f"<span>/mês</span></div>"
                        f'<div class="mst-sub">{p.descricao or "—"}</div></div>'
                        f'<ul class="mst-plano-lista">'
                        f"<li>Veículos: <strong>"
                        f"{'Ilimitado' if not p.limite_veiculos else p.limite_veiculos}"
                        f"</strong></li>"
                        f"<li>Licença: <strong>{p.dias_licenca} dias</strong></li>"
                        f"<li>Empresas usando: <strong>{em_uso}</strong></li>"
                        f"<li>Situação: <strong>"
                        f"{'Ativo' if p.ativo else 'Inativo'}</strong></li>"
                        f"</ul>"
                    )
                    with ui.row().classes("gap-2 w-full"):
                        ui.button(
                            "Editar",
                            on_click=lambda pid=p.id: _dialog_plano(
                                grade.refresh, pid
                            ),
                        ).props("flat dense no-caps").classes("mst-btn-mini")
                        ui.button(
                            "Excluir",
                            on_click=lambda pid=p.id: _excluir_plano(
                                pid, grade.refresh
                            ),
                        ).props("flat dense no-caps").classes(
                            "mst-btn-mini mst-btn-perigo"
                        )

    with ui.element("div").classes("erp-toolbar"):
        ui.button(
            "Novo plano", on_click=lambda: _dialog_plano(grade.refresh),
        ).classes("erp-btn-primario").props("unelevated no-caps")

    grade()


def _excluir_plano(plano_id: int, refresh) -> None:
    try:
        excluir_plano(plano_id)
    except ValueError as err:
        ui.notify(str(err), type="negative")
        return
    ui.notify("Plano excluído.", type="positive")
    refresh()


def _dialog_plano(refresh, plano_id: int | None = None) -> None:
    p = obter_plano(plano_id) if plano_id else None
    with ui.dialog() as dlg, ui.card().classes("erp-dialog mst-dialog"):
        ui.html(f"<h3>{'Editar' if p else 'Novo'} plano</h3>")
        nome = ui.input("Nome", value=p.nome if p else "").classes(
            "erp-input-full"
        )
        descricao = ui.input(
            "Descrição", value=p.descricao if p else "",
        ).classes("erp-input-full")
        preco = ui.number(
            "Preço mensal", value=p.preco_mensal if p else 0, format="%.2f",
        ).classes("erp-input-full")
        veiculos = ui.number(
            "Limite de veículos (0 = ilimitado)",
            value=p.limite_veiculos if p else 50, format="%.0f",
        ).classes("erp-input-full")
        dias = ui.number(
            "Dias de licença", value=p.dias_licenca if p else 30, format="%.0f",
        ).classes("erp-input-full")
        ativo = ui.switch("Plano ativo", value=p.ativo if p else True)

        def salvar() -> None:
            if not nome.value:
                ui.notify("Informe o nome do plano.", type="warning")
                return
            salvar_plano({
                "nome": nome.value.strip(),
                "descricao": descricao.value or "",
                "preco_mensal": float(preco.value or 0),
                "limite_veiculos": int(veiculos.value or 0),
                "dias_licenca": int(dias.value or 30),
                "ativo": ativo.value,
            }, plano_id)
            dlg.close()
            ui.notify("Plano salvo.", type="positive")
            refresh()

        with ui.row().classes("w-full justify-end gap-2 mt-3"):
            ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
            ui.button("Salvar", on_click=salvar).classes(
                "erp-btn-primario"
            ).props("unelevated no-caps")
    dlg.open()


# ------------------------------------------------------------- Domínios

def pagina_master_dominios() -> None:
    ui.html(
        '<div class="erp-page-header"><div><h2>Domínios</h2>'
        "<p>Somente o Administrador Master pode editar domínios</p>"
        "</div>"
        '<div><a href="/master/guia" class="mst-link-guia">'
        '<span class="material-icons">menu_book</span> Ver passo a passo completo'
        "</a></div></div>"
    )
    ui.html(
        '<div class="mst-nota">O ERP de cada loja abre no <strong>subdomínio</strong> '
        "ou no <strong>domínio ERP</strong> cadastrado aqui. O site público fica no "
        "<strong>domínio próprio</strong> da empresa. DNS e SSL são configurados no "
        "provedor e na hospedagem (Easypanel, Railway, Render, etc.). "
        'Consulte <a href="/master/guia">Guia de implantação</a> para a ordem correta '
        "dos passos.</div>"
    )

    @ui.refreshable
    def lista() -> None:
        contas = listar_contas()
        if not contas:
            ui.html('<p class="erp-ajuda">Nenhuma empresa cadastrada.</p>')
            return
        with ui.element("div").classes("mst-tabela-wrap"):
            ui.html(
                '<div class="mst-tabela-head mst-head-dom">'
                "<span>Empresa</span><span>Subdomínio (ERP)</span>"
                "<span>Domínio ERP</span><span>Domínio do site</span>"
                "<span>Ações</span></div>"
            )
            for c in contas:
                with ui.element("div").classes("mst-tabela-row mst-head-dom"):
                    ui.html(f"<span><strong>{c.nome}</strong></span>")
                    ui.html(f"<span>{c.subdominio or '—'}</span>")
                    erp_dom = c.dominio_erp if c.dominio_erp and c.dominio_erp != c.subdominio else "—"
                    ui.html(f"<span>{erp_dom}</span>")
                    ui.html(f"<span>{c.dominio_site or '—'}</span>")
                    with ui.element("span").classes("mst-acoes"):
                        ui.button(
                            "Editar domínios",
                            on_click=lambda cid=c.id: _dialog_dominios(
                                cid, lista.refresh
                            ),
                        ).props("flat dense no-caps").classes("mst-btn-mini")
                        site_url = (
                            f"https://{c.dominio_site}/"
                            if c.dominio_site
                            else f"/loja/{c.slug}/"
                        )
                        ui.button(
                            "Abrir site",
                            on_click=lambda u=site_url: ui.navigate.to(
                                u, new_tab=True,
                            ),
                        ).props("flat dense no-caps").classes("mst-btn-mini")

    lista()


def _dialog_dominios(conta_id: int, refresh) -> None:
    conta = obter_conta(conta_id)
    if conta is None:
        return
    with ui.dialog() as dlg, ui.card().classes("erp-dialog mst-dialog"):
        ui.html(f"<h3>Domínios de {conta.nome}</h3>")
        ui.html(
            '<p class="erp-ajuda">Subdomínio na plataforma (ex.: '
            "<code>loja.dominio-base</code>) ou domínio ERP próprio "
            "(ex.: <code>admin.loja.com.br</code>). O site público usa o "
            "domínio próprio abaixo. Veja o "
            '<a href="/master/guia" target="_blank">Guia de implantação</a>.</p>'
        )
        sub = ui.input(
            "Subdomínio (ERP na plataforma)", value=conta.subdominio,
            placeholder="minha-loja.plataforma.com.br",
        ).classes("erp-input-full")
        erp = ui.input(
            "Domínio ERP (opcional)", value=conta.dominio_erp or conta.subdominio,
            placeholder="admin.minha-loja.com.br",
        ).classes("erp-input-full")
        site = ui.input(
            "Domínio do site", value=conta.dominio_site,
            placeholder="www.minha-loja.com.br",
        ).classes("erp-input-full")

        def salvar() -> None:
            atualizar_dominios(
                conta_id,
                sub.value or "",
                site.value or "",
                erp.value or sub.value or "",
            )
            dlg.close()
            ui.notify("Domínios atualizados.", type="positive")
            refresh()

        with ui.row().classes("w-full justify-end gap-2 mt-3"):
            ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
            ui.button("Salvar", on_click=salvar).classes(
                "erp-btn-primario"
            ).props("unelevated no-caps")
    dlg.open()


# -------------------------------------------------------- Guia de implantação

def pagina_master_guia() -> None:
    cfg = obter_config_plataforma()
    base = cfg.dominio_base or "plataforma.com.br"
    ui.html(
        '<div class="erp-page-header"><div><h2>Guia de implantação</h2>'
        "<p>Como cadastrar empresas, domínios do site e do ERP</p></div></div>"
    )
    ui.html(
        '<div class="mst-nota mst-nota-alerta">'
        "<strong>Hospedagem:</strong> esta aplicação (ERP + Master + sites) roda em "
        "servidor com <strong>Docker</strong> (Easypanel, Railway, Render, Fly.io ou VPS). "
        "A <strong>Vercel</strong> não executa Python/NiceGUI com WebSocket — use-a apenas "
        "como proxy de DNS (opcional) ou hospede tudo no servidor. "
        "Detalhes em <code>DEPLOY-VERCEL.md</code> no repositório."
        "</div>"
    )

    passos = [
        (
            "1",
            "Publicar a aplicação no servidor",
            (
                "<p>Conecte o repositório "
                "<code>felipegoulart06-lab/SISTEMA-VEICULOS-SITE</code> "
                "na sua hospedagem:</p>"
                "<ul>"
                "<li><strong>Easypanel</strong> — App com Dockerfile, porta "
                "<code>8080</code>, volume em <code>/app/dados</code> "
                "(veja <code>DEPLOY-EASYPANEL.md</code>)</li>"
                "<li><strong>Railway / Render</strong> — deploy via Dockerfile "
                "(veja <code>render.yaml</code>)</li>"
                "</ul>"
                "<p>Configure as variáveis de ambiente do <code>.env.example</code>: "
                "<code>SECRET_KEY</code>, <code>MASTER_EMAIL</code>, "
                "<code>MASTER_SENHA</code>, credenciais <code>SUPABASE_DB_*</code>, "
                "<code>AMBIENTE=production</code>, <code>PORT=8080</code>.</p>"
                "<p>Teste: <code>GET https://SEU-SERVIDOR/health</code> deve retornar "
                "<code>{\"status\":\"ok\"}</code>.</p>"
            ),
        ),
        (
            "2",
            "Definir o domínio base da plataforma",
            (
                f"<p>Em <strong>Configurações</strong>, defina "
                f"<strong>Domínio base dos subdomínios</strong> como "
                f"<code>{base}</code> (ou o domínio que você controla, "
                "ex.: <code>minhaplataforma.com.br</code>).</p>"
                "<p>Novas empresas recebem ERP em "
                f"<code>identificador.{base}</code> automaticamente.</p>"
                "<p>No DNS do domínio base, crie um registro curinga "
                f"<code>*. {base}</code> apontando para o IP do servidor "
                "(tipo A) ou CNAME para o host da hospedagem.</p>"
            ),
        ),
        (
            "3",
            "Criar a empresa de veículos",
            (
                "<p>Menu <strong>Empresas</strong> → <strong>Criar empresa</strong>:</p>"
                "<ol>"
                "<li>Nome da empresa e e-mail do administrador (login do ERP)</li>"
                "<li>Identificador (slug) — ex.: <code>rodavia</code></li>"
                "<li>Plano, status e dias de licença</li>"
                "<li>Cor do tema e senha temporária (mín. 8 caracteres)</li>"
                "</ol>"
                "<p>O sistema cria automaticamente: schema isolado no banco, ERP vazio, "
                "site público limpo e subdomínio ERP padrão.</p>"
                "<p><strong>Anote</strong> e-mail, senha temporária e subdomínio exibidos "
                "após a criação — o admin precisará trocar a senha no primeiro acesso.</p>"
            ),
        ),
        (
            "4",
            "Cadastrar domínios no Master",
            (
                "<p>Menu <strong>Domínios</strong> → <strong>Editar domínios</strong> "
                "da empresa:</p>"
                "<table class=\"mst-guia-tabela\">"
                "<thead><tr><th>Campo</th><th>Exemplo</th><th>Uso</th></tr></thead>"
                "<tbody>"
                f"<tr><td>Subdomínio (ERP)</td><td><code>rodavia.{base}</code></td>"
                "<td>ERP na plataforma — login em <code>/login</code></td></tr>"
                "<tr><td>Domínio ERP (opcional)</td>"
                "<td><code>admin.rodavia.com.br</code></td>"
                "<td>ERP com domínio próprio da loja (substitui ou complementa "
                "o subdomínio)</td></tr>"
                "<tr><td>Domínio do site</td>"
                "<td><code>www.rodavia.com.br</code> ou <code>rodavia.com.br</code></td>"
                "<td>Site público de veículos (HTML rápido, sem WebSocket)</td></tr>"
                "</tbody></table>"
                "<p>Salvar aqui <strong>não configura DNS</strong> — apenas informa ao "
                "sistema qual host pertence a qual empresa.</p>"
            ),
        ),
        (
            "5",
            "Configurar DNS (Registro.br, Cloudflare, etc.)",
            (
                "<p>No painel do registrador, crie os registros apontando para o "
                "<strong>mesmo servidor</strong> onde a aplicação está publicada:</p>"
                "<table class=\"mst-guia-tabela\">"
                "<thead><tr><th>Host</th><th>Tipo</th><th>Destino</th></tr></thead>"
                "<tbody>"
                f"<tr><td><code>*. {base}</code></td><td>A ou CNAME</td>"
                "<td>IP ou hostname do servidor</td></tr>"
                "<tr><td><code>rodavia.com.br</code></td><td>A ou CNAME</td>"
                "<td>IP ou hostname do servidor</td></tr>"
                "<tr><td><code>www</code></td><td>CNAME</td>"
                "<td><code>rodavia.com.br</code> (opcional)</td></tr>"
                "<tr><td><code>admin</code></td><td>A ou CNAME</td>"
                "<td>IP ou hostname (se usar domínio ERP próprio)</td></tr>"
                "</tbody></table>"
                "<p>Propagação: de minutos a 48 h. Use "
                "<code>https://dnschecker.org</code> para verificar.</p>"
            ),
        ),
        (
            "6",
            "Registrar domínios na hospedagem",
            (
                "<p>Cada hostname que recebe tráfego HTTP/HTTPS precisa estar "
                "cadastrado no painel do servidor:</p>"
                "<ul>"
                "<li><strong>Easypanel</strong> — no App, aba Domains: adicione "
                "cada domínio (site, ERP, subdomínios). Target port: "
                "<code>8080</code>. SSL automático.</li>"
                "<li><strong>Railway / Render</strong> — Settings → Custom Domains: "
                "adicione site e ERP; siga as instruções de CNAME.</li>"
                "<li><strong>Vercel (opcional)</strong> — só como proxy reverso "
                "para o backend (sem ERP NiceGUI direto). Veja "
                "<code>DEPLOY-VERCEL.md</code>.</li>"
                "</ul>"
                "<p class=\"mst-guia-aviso\">Todos os domínios devem apontar para "
                "<strong>uma única instância</strong> da aplicação — o roteamento "
                "por empresa é feito pelo cabeçalho <code>Host</code>.</p>"
            ),
        ),
        (
            "7",
            "Testar acesso",
            (
                "<ul class=\"mst-guia-checklist\">"
                f"<li>ERP subdomínio: <code>https://empresa.{base}/login</code></li>"
                "<li>ERP domínio próprio: <code>https://admin.loja.com.br/login</code></li>"
                "<li>Site: <code>https://www.loja.com.br/</code> (estoque, contato)</li>"
                "<li>Desenvolvimento local: <code>/loja/{slug}/</code> e "
                "<code>/admin/login</code></li>"
                "<li>Master: <code>/master/login</code> (localhost ou domínio admin "
                "da plataforma)</li>"
                "</ul>"
                "<p>Empresa <strong>suspensa</strong> no Master bloqueia ERP e site "
                "imediatamente (página de conta indisponível).</p>"
            ),
        ),
        (
            "8",
            "Ordem correta (checklist)",
            (
                "<ol class=\"mst-guia-ordem\">"
                "<li>Deploy da aplicação + variáveis + <code>/health</code> OK</li>"
                "<li>Domínio base em Configurações + DNS curinga <code>*</code></li>"
                "<li>Criar empresa em Empresas</li>"
                "<li>Editar domínios em Domínios (site + ERP)</li>"
                "<li>DNS dos domínios da loja (A/CNAME)</li>"
                "<li>Adicionar domínios no Easypanel/Railway/Render</li>"
                "<li>Aguardar SSL e testar login ERP + site público</li>"
                "<li>Entregar credenciais ao cliente (e-mail + senha temp.)</li>"
                "</ol>"
            ),
        ),
    ]

    with ui.element("div").classes("mst-guia"):
        for num, titulo, html in passos:
            with ui.element("section").classes("mst-guia-passo"):
                ui.html(
                    f'<div class="mst-guia-num">{num}</div>'
                    f"<div class=\"mst-guia-corpo\">"
                    f"<h3>{titulo}</h3>{html}</div>"
                )

    contas = listar_contas()
    if contas:
        linhas = "".join(
            f"<tr><td>{c.nome}</td><td><code>{c.subdominio or '—'}</code></td>"
            f"<td><code>{c.dominio_erp or '—'}</code></td>"
            f"<td><code>{c.dominio_site or '—'}</code></td>"
            f"<td>{_pill_status(c.status)}</td></tr>"
            for c in contas
        )
        ui.html(
            '<section class="mst-guia-painel">'
            "<h3>Empresas cadastradas — referência rápida</h3>"
            '<table class="mst-guia-tabela">'
            "<thead><tr><th>Empresa</th><th>Subdomínio ERP</th>"
            "<th>Domínio ERP</th><th>Site</th><th>Status</th></tr></thead>"
            f"<tbody>{linhas}</tbody></table></section>"
        )


# ----------------------------------------------------------------- Logs

def pagina_master_logs() -> None:
    ui.html(
        '<div class="erp-page-header"><div><h2>Logs</h2>'
        "<p>Eventos de ciclo de vida das empresas</p></div></div>"
    )
    hoje = datetime.now()
    filtro = {
        "tipo": None,
        "desde": (hoje - timedelta(days=30)).strftime("%Y-%m-%d"),
        "ate": hoje.strftime("%Y-%m-%d"),
    }

    @ui.refreshable
    def lista() -> None:
        try:
            desde = datetime.strptime(filtro["desde"], "%Y-%m-%d")
            ate = datetime.strptime(filtro["ate"], "%Y-%m-%d") + timedelta(days=1)
        except (TypeError, ValueError):
            desde, ate = None, None
        logs = listar_logs(filtro["tipo"], desde, ate, limite=150)
        if not logs:
            ui.html('<p class="erp-ajuda">Nenhum log no período.</p>')
            return
        if len(logs) >= 150:
            ui.html(
                '<p class="erp-ajuda">Exibindo os 150 eventos mais recentes do período.</p>'
            )
        with ui.element("div").classes("mst-tabela-wrap"):
            ui.html(
                '<div class="mst-tabela-head mst-head-log">'
                "<span>Evento</span><span>Descrição</span>"
                "<span>Empresa</span><span>Data</span></div>"
            )
            for log in logs:
                tom = "erro" if "exclu" in log.tipo or "susp" in log.tipo else "info"
                ui.html(
                    f'<div class="mst-tabela-row mst-head-log">'
                    f"<span>{_pill(LOG_LABEL.get(log.tipo, log.tipo), tom)}</span>"
                    f"<span>{log.mensagem}</span>"
                    f"<span>{log.conta_nome or '—'}</span>"
                    f"<span>{_data_hora(log.criado_em)}</span></div>"
                )

    with ui.element("div").classes("erp-toolbar"):
        ui.select(
            {None: "Todos", **{t: LOG_LABEL[t] for t in TIPOS_LOG}},
            label="Evento", value=None,
            on_change=lambda e: (
                filtro.update({"tipo": e.value}), lista.refresh(),
            ),
        ).style("min-width:190px")
        ui.input(
            "De", value=filtro["desde"],
            on_change=lambda e: (
                filtro.update({"desde": e.value}), lista.refresh(),
            ),
        ).props("type=date dense outlined")
        ui.input(
            "Até", value=filtro["ate"],
            on_change=lambda e: (
                filtro.update({"ate": e.value}), lista.refresh(),
            ),
        ).props("type=date dense outlined")

    lista()


# --------------------------------------------------------- Configurações

def pagina_master_config() -> None:
    cfg = obter_config_plataforma()
    ui.html(
        '<div class="erp-page-header"><div><h2>Configurações</h2>'
        "<p>Identidade da plataforma</p></div></div>"
    )

    with ui.element("div").classes("erp-painel"):
        ui.html(
            '<div class="erp-painel-titulo-row">'
            '<span class="material-icons erp-painel-ico">palette</span>'
            "<span>Plataforma</span></div>"
        )
        nome = ui.input(
            "Nome da plataforma", value=cfg.nome_plataforma,
        ).classes("erp-input-full")
        logo = ui.input("Logo (URL)", value=cfg.logo_url).classes(
            "erp-input-full"
        )
        cor = ui.input("Cor primária", value=cfg.cor_primaria).classes(
            "erp-input-full"
        )
        base = ui.input(
            "Domínio base dos subdomínios", value=cfg.dominio_base,
        ).classes("erp-input-full")
        ui.html(
            '<p class="erp-ajuda">Subdomínio ERP das novas empresas: '
            "<code>identificador.dominio-base</code> "
            "(ex.: sigma.plataforma.com.br). A plataforma não possui domínio "
            "próprio; o Master acessa via localhost.</p>"
        )

        def salvar() -> None:
            salvar_config_plataforma({
                "nome_plataforma": nome.value.strip() or "Plataforma White Label",
                "logo_url": logo.value.strip(),
                "cor_primaria": cor.value.strip() or "#1e3a5f",
                "dominio_base": base.value.strip() or "plataforma.com.br",
            })
            ui.notify("Configurações salvas.", type="positive")

        ui.button("Salvar", on_click=salvar).classes(
            "erp-btn-primario"
        ).props("unelevated no-caps").style("margin-top:12px")

    with ui.element("div").classes("erp-painel").style("margin-top:16px"):
        ui.html(
            '<div class="erp-painel-titulo-row">'
            '<span class="material-icons erp-painel-ico">info</span>'
            "<span>Sobre esta versão</span></div>"
        )
        ui.html(
            f"<p>Versão <strong>{cfg.versao}</strong> — MVP.</p>"
            '<p class="erp-ajuda">Escopo: empresas, planos, licença, domínios '
            "e logs. Cobrança automática, backups agendados, monitoramento e "
            "integrações ficam para as próximas versões.</p>"
        )
