"""Utilitários de segurança — rate limit, headers, uploads e 2FA."""

from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict
from pathlib import Path
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware

SECRET_KEY_PADRAO = "sigma-erp-secret-change-in-production"
TENTATIVAS_LOGIN_MAX = 5
JANELA_LOGIN_SEG = 900  # 15 minutos
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def em_producao() -> bool:
    ambiente = os.getenv("AMBIENTE", os.getenv("ENV", "")).lower()
    return ambiente in {"prod", "production"} or os.getenv("PRODUCTION", "").lower() in {
        "1",
        "true",
        "yes",
    }


def mostrar_credenciais_demo() -> bool:
    return not em_producao()


def validar_ambiente() -> None:
    """Falha em produção se SECRET_KEY estiver ausente ou fraca."""
    chave = os.getenv("SECRET_KEY", SECRET_KEY_PADRAO)
    if em_producao():
        if not chave or chave == SECRET_KEY_PADRAO or len(chave) < 32:
            raise RuntimeError(
                "SECRET_KEY ausente ou fraca em produção. "
                "Defina SECRET_KEY com pelo menos 32 caracteres aleatórios."
            )
    elif chave == SECRET_KEY_PADRAO:
        print(
            "[seguranca] AVISO: SECRET_KEY padrão em uso — altere antes de produção."
        )


def ip_cliente() -> str:
    try:
        from nicegui import context

        req = context.client.request
        if req is None:
            return "desconhecido"
        encaminhado = req.headers.get("x-forwarded-for")
        if encaminhado:
            return encaminhado.split(",")[0].strip()
        if req.client:
            return req.client.host or "desconhecido"
    except Exception:
        pass
    return "desconhecido"


class _RateLimitLogin:
    def __init__(self) -> None:
        self._falhas: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def bloqueado(self, chave: str) -> bool:
        with self._lock:
            agora = time.time()
            recentes = [
                t for t in self._falhas[chave] if agora - t < JANELA_LOGIN_SEG
            ]
            self._falhas[chave] = recentes
            return len(recentes) >= TENTATIVAS_LOGIN_MAX

    def registrar_falha(self, chave: str) -> None:
        with self._lock:
            self._falhas[chave].append(time.time())

    def limpar(self, chave: str) -> None:
        with self._lock:
            self._falhas.pop(chave, None)

    def segundos_restantes(self, chave: str) -> int:
        with self._lock:
            if not self._falhas.get(chave):
                return 0
            mais_antiga = min(self._falhas[chave])
            restante = JANELA_LOGIN_SEG - (time.time() - mais_antiga)
            return max(0, int(restante))


rate_limit_login = _RateLimitLogin()


def chave_login(tipo: str, email: str) -> str:
    return f"{tipo}:{ip_cliente()}:{email.strip().lower()}"


def mensagem_bloqueio_login(chave: str) -> str:
    restante = rate_limit_login.segundos_restantes(chave)
    minutos = max(1, (restante + 59) // 60)
    return f"Muitas tentativas de login. Aguarde cerca de {minutos} min."


def _extensao_por_magic(conteudo: bytes) -> set[str] | None:
    if conteudo.startswith(b"\xff\xd8\xff"):
        return {".jpg", ".jpeg"}
    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return {".png"}
    if conteudo[:6] in (b"GIF87a", b"GIF89a"):
        return {".gif"}
    if len(conteudo) >= 12 and conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return {".webp"}
    return None


def validar_upload_imagem(nome_arquivo: str, conteudo: bytes) -> str:
    """Valida tamanho, extensão e assinatura. Retorna extensão segura."""
    if not conteudo:
        raise ValueError("Arquivo vazio.")
    if len(conteudo) > MAX_UPLOAD_BYTES:
        raise ValueError("Arquivo muito grande (máximo 5 MB).")

    ext = Path(nome_arquivo or "imagem.jpg").suffix.lower()
    if ext not in EXTENSOES_IMAGEM:
        ext = ".jpg"

    magic_ext = _extensao_por_magic(conteudo)
    if magic_ext is None:
        raise ValueError("Formato de imagem não permitido.")
    if ext not in magic_ext:
        ext = sorted(magic_ext)[0]
    return ext


def nome_upload_seguro(prefixo: str, extensao: str) -> str:
    ext = extensao if extensao in EXTENSOES_IMAGEM else ".jpg"
    return f"{prefixo}_{uuid.uuid4().hex[:12]}{ext}"


def verificar_totp(secret: str | None, codigo: str | None) -> bool:
    if not secret or not codigo:
        return False
    try:
        import pyotp
    except ImportError:
        raise RuntimeError("pyotp não instalado — necessário para 2FA Master.")
    totp = pyotp.TOTP(secret.strip())
    return totp.verify(str(codigo).strip().replace(" ", ""), valid_window=1)


def totp_obrigatorio_master(totp_secret_usuario: str | None) -> bool:
    if totp_secret_usuario:
        return True
    return bool(os.getenv("MASTER_TOTP_SECRET", "").strip())


def secret_totp_master(totp_secret_usuario: str | None) -> str | None:
    if totp_secret_usuario:
        return totp_secret_usuario.strip()
    env = os.getenv("MASTER_TOTP_SECRET", "").strip()
    return env or None


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob: https:; "
            "connect-src 'self' ws: wss:;"
        )
        if em_producao():
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response
