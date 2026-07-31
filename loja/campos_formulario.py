"""Campos padronizados dos formulários públicos do site."""

from nicegui import ui

_PROPS_BASE = "outlined dense no-error-icon hide-bottom-space"


def input_texto(label: str, *, placeholder: str = "", value: str = "", classes: str = ""):
    """Texto livre — exibe em maiúsculas; normaliza ao sair do campo."""
    campo = ui.input(
        label, placeholder=placeholder, value=value or "",
    ).props(_PROPS_BASE).classes(f"campo-maiusculas {classes}".strip())
    _blur_maiusculas(campo)
    return campo


def input_email(label: str, *, placeholder: str = "", value: str = "", classes: str = ""):
    """E-mail — sem conversão para maiúsculas."""
    return ui.input(
        label, placeholder=placeholder, value=value or "",
    ).props(_PROPS_BASE).classes(f"campo-email {classes}".strip())


def input_numero(label: str, *, placeholder: str = "", value: str = "", classes: str = ""):
    """Somente dígitos — filtra caracteres inválidos ao sair do campo."""
    campo = ui.input(
        label, placeholder=placeholder, value=value or "",
    ).props(f"{_PROPS_BASE} inputmode=numeric").classes(
        f"campo-numeros {classes}".strip()
    )
    _blur_numeros(campo)
    return campo


def input_data(label: str, *, placeholder: str = "", value: str = "", classes: str = ""):
    """Data — dígitos e barras; normaliza ao sair do campo."""
    campo = ui.input(
        label, placeholder=placeholder, value=value or "",
    ).props(f"{_PROPS_BASE} inputmode=numeric").classes(
        f"campo-numeros {classes}".strip()
    )
    _blur_data(campo)
    return campo


def textarea_texto(label: str, *, placeholder: str = "", value: str = "", classes: str = ""):
    """Área de texto — maiúsculas ao sair do campo."""
    campo = ui.textarea(
        label, placeholder=placeholder, value=value or "",
    ).props(_PROPS_BASE).classes(f"campo-maiusculas {classes}".strip())
    _blur_maiusculas(campo)
    return campo


def _blur_maiusculas(campo) -> None:
    def aplicar() -> None:
        valor = campo.value
        if not valor:
            return
        upper = str(valor).upper()
        if upper != valor:
            campo.value = upper

    campo.on("blur", aplicar)


def _blur_numeros(campo) -> None:
    def aplicar() -> None:
        valor = campo.value
        if not valor:
            return
        numeros = "".join(c for c in str(valor) if c.isdigit())
        if numeros != str(valor):
            campo.value = numeros

    campo.on("blur", aplicar)


def _blur_data(campo) -> None:
    def aplicar() -> None:
        valor = campo.value
        if not valor:
            return
        limpo = "".join(c for c in str(valor) if c.isdigit() or c == "/")
        if limpo != str(valor):
            campo.value = limpo

    campo.on("blur", aplicar)
