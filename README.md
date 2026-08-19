# SISTEMA DE VEÍCULOS + SITE

ERP white-label + site público para lojas de veículos (NiceGUI + FastAPI + SQLAlchemy).

Repositório: [felipegoulart06-lab/SISTEMA-VEICULOS-SITE](https://github.com/felipegoulart06-lab/SISTEMA-VEICULOS-SITE)

## Stack

- Python 3.12
- NiceGUI + FastAPI
- Site público em HTML/Jinja2 (rápido, sem WebSocket)
- SQLAlchemy + PostgreSQL (Supabase) ou SQLite local

## Deploy (produção)

| Hospedagem | Guia | Observação |
|------------|------|------------|
| **Easypanel / VPS** | [DEPLOY-EASYPANEL.md](DEPLOY-EASYPANEL.md) | Recomendado |
| **Render** | [render.yaml](render.yaml) + painel Render | Docker |
| **Railway** | Dockerfile na raiz | Docker |
| **Vercel** | [DEPLOY-VERCEL.md](DEPLOY-VERCEL.md) | Só proxy — app roda em servidor Docker |

Resumo: App com **Dockerfile**, porta **8080**, volume em `/app/dados`, variáveis do `.env.example`.

## Setup local

```bash
git clone https://github.com/felipegoulart06-lab/SISTEMA-VEICULOS-SITE.git
cd SISTEMA-VEICULOS-SITE
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

App em `http://localhost:8080`.

## Acessos

| Painel | URL | Login |
|--------|-----|--------|
| Master | `/master/login` | `MASTER_EMAIL` / `MASTER_SENHA` |
| ERP loja | subdomínio ou `/admin/login` | e-mail da empresa |
| Site | domínio próprio ou `/loja/{slug}/` | público |

No **Painel Master → Guia de implantação** há o passo a passo para cadastrar empresas e configurar domínios do ERP e do site.

## Variáveis importantes

Veja `.env.example`. Em produção use PostgreSQL via Supabase (`SUPABASE_DB_*` ou `DATABASE_URL`).

Desenvolvimento rápido com SQLite: `USE_LOCAL_SQLITE=1`

## Estrutura

- `main.py` — rotas e bootstrap
- `loja/` — site HTML, ERP, master, DB, auth
- `templates/site/` — templates Jinja2 do site público
- `dados/` — storage local (não versionado)
