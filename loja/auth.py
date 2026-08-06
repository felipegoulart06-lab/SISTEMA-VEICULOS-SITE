"""Autenticação — Admin da empresa e Admin Master."""

from nicegui import app, ui

from loja.plataforma import (
    autenticar_conta,
    autenticar_master,
    empresa_pode_acessar,
    obter_conta,
    precisa_trocar_senha,
    trocar_senha_tenant,
)
from loja.roteamento_host import erp_admin_url, erp_login_url, erp_trocar_senha_url
from loja.seguranca import (
    chave_login,
    mensagem_bloqueio_login,
    rate_limit_login,
    secret_totp_master,
    totp_obrigatorio_master,
    verificar_totp,
)
from loja.tenant_ctx import ligar_tenant, limpar_tenant


def logado() -> bool:
    return bool(app.storage.user.get("usuario_id")) and bool(
        app.storage.user.get("conta_slug")
    )


def usuario_nome() -> str:
    return app.storage.user.get("usuario_nome", "Admin")


def conta_slug() -> str | None:
    return app.storage.user.get("conta_slug")


def fazer_logout() -> None:
    app.storage.user.clear()
    limpar_tenant()


def fazer_login(email: str, senha: str) -> bool:
    """Login da empresa: e-mail + senha do administrador único."""
    ok, _ = tentar_login_empresa(email, senha)
    return ok


def tentar_login_empresa(email: str, senha: str) -> tuple[bool, str | None]:
    """Login com rate limit. Retorna (sucesso, mensagem_erro)."""
    import time

    chave = chave_login("empresa", email)
    if rate_limit_login.bloqueado(chave):
        return False, mensagem_bloqueio_login(chave)

    conta = autenticar_conta(email, senha)
    if not conta:
        rate_limit_login.registrar_falha(chave)
        return False, None

    rate_limit_login.limpar(chave)
    for chave_sess in ("master_id", "master_nome", "master_email", "impersonando"):
        app.storage.user.pop(chave_sess, None)
    app.storage.user["usuario_id"] = conta.id
    app.storage.user["usuario_nome"] = conta.nome
    app.storage.user["usuario_email"] = conta.email
    app.storage.user["conta_slug"] = conta.slug
    app.storage.user["conta_id"] = conta.id
    app.storage.user["trocar_senha"] = precisa_trocar_senha(
        conta.slug, conta.email,
    )
    app.storage.user["_acesso_check_em"] = time.time()
    app.storage.user["_acesso_ok"] = True
    ligar_tenant(conta.slug)
    return True, None


def deve_trocar_senha() -> bool:
    return bool(app.storage.user.get("trocar_senha"))


def concluir_troca_senha(nova_senha: str) -> None:
    slug = app.storage.user.get("conta_slug")
    email = app.storage.user.get("usuario_email")
    if not slug or not email:
        raise ValueError("Sessão inválida.")
    ligar_tenant(slug)
    trocar_senha_tenant(slug, email, nova_senha)
    app.storage.user["trocar_senha"] = False


def exigir_login() -> bool:
    """Garante sessão da empresa. Retorna False se redirecionou."""
    if master_logado() and not impersonando():
        ui.navigate.to("/master")
        return False

    if not logado():
        ui.navigate.to(erp_login_url())
        return False

    conta = obter_conta(app.storage.user.get("conta_id") or 0)
    if conta is None:
        fazer_logout()
        ui.navigate.to(erp_login_url())
        return False
    liberado, motivo = empresa_pode_acessar(conta)
    if not liberado and not impersonando():
        fazer_logout()
        ui.notify(motivo, type="negative", timeout=6000)
        ui.navigate.to(erp_login_url())
        return False
    ligar_tenant(conta.slug)
    if deve_trocar_senha():
        ui.navigate.to(erp_trocar_senha_url())
        return False
    return True


def redirecionar_se_logado() -> None:
    if master_logado():
        ui.navigate.to("/master")
        return
    if logado():
        ligar_tenant(app.storage.user.get("conta_slug"))
        ui.navigate.to(erp_admin_url())


def redirecionar_se_master_logado() -> None:
    if master_logado():
        ui.navigate.to("/master")


def master_logado() -> bool:
    return bool(app.storage.user.get("master_id"))


def master_nome() -> str:
    return app.storage.user.get("master_nome", "Master")


def fazer_login_master(email: str, senha: str, codigo_totp: str = "") -> bool:
    ok, _ = tentar_login_master(email, senha, codigo_totp)
    return ok


def tentar_login_master(
    email: str, senha: str, codigo_totp: str = "",
) -> tuple[bool, str | None]:
    chave = chave_login("master", email)
    if rate_limit_login.bloqueado(chave):
        return False, mensagem_bloqueio_login(chave)

    user = autenticar_master(email, senha)
    if not user:
        rate_limit_login.registrar_falha(chave)
        return False, None

    secret = getattr(user, "totp_secret", None)
    if totp_obrigatorio_master(secret):
        if not verificar_totp(secret_totp_master(secret), codigo_totp):
            rate_limit_login.registrar_falha(chave)
            return False, "Código 2FA inválido ou ausente."

    rate_limit_login.limpar(chave)
    app.storage.user.clear()
    limpar_tenant()
    app.storage.user["master_id"] = user.id
    app.storage.user["master_nome"] = user.nome
    app.storage.user["master_email"] = user.email
    return True, None


def fazer_logout_master() -> None:
    app.storage.user.clear()
    limpar_tenant()


def exigir_master() -> bool:
    if logado() and not master_logado():
        fazer_logout()
    if not master_logado():
        ui.navigate.to("/master/login")
        return False
    limpar_tenant()
    return True


def entrar_como_conta(conta_id: int) -> bool:
    """Master acessa o ERP da loja sem perder a sessão Master."""
    if not master_logado():
        return False
    conta = obter_conta(conta_id)
    if conta is None:
        return False
    app.storage.user["usuario_id"] = conta.id
    app.storage.user["usuario_nome"] = conta.nome
    app.storage.user["usuario_email"] = conta.email
    app.storage.user["conta_slug"] = conta.slug
    app.storage.user["conta_id"] = conta.id
    app.storage.user["impersonando"] = True
    app.storage.user["trocar_senha"] = False
    ligar_tenant(conta.slug)
    return True


def impersonando() -> bool:
    return bool(app.storage.user.get("impersonando"))


def sair_da_loja() -> None:
    for chave in (
        "usuario_id", "usuario_nome", "usuario_email",
        "conta_slug", "conta_id", "impersonando", "trocar_senha",
    ):
        app.storage.user.pop(chave, None)
    limpar_tenant()
