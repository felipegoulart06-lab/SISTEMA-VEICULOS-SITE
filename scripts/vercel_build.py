"""Prepara assets estáticos para CDN da Vercel."""

from __future__ import annotations

import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PUBLIC = RAIZ / "public"
STATIC_SRC = RAIZ / "loja" / "static"


def main() -> None:
    dest = PUBLIC / "static"
    if dest.exists():
        shutil.rmtree(dest)
    if STATIC_SRC.exists():
        shutil.copytree(STATIC_SRC, dest)
    print(f"[vercel build] static copiado para {dest}")


if __name__ == "__main__":
    main()
