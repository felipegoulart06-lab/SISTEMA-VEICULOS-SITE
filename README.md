# SIGMA — Sistema de Veículos + Site

ERP white-label + site público para lojas de veículos (NiceGUI + SQLAlchemy).

## Stack

- Python 3.11+
- NiceGUI
- SQLAlchemy + PostgreSQL (Supabase) ou SQLite local
- Passlib (senhas)

## Setup no servidor

```bash
git clone https://github.com/goulartfelipe618-beep/sigma-sistema.git
cd sigma-sistema
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edite .env com as credenciais reais (Supabase, SECRET_KEY, etc.)
python main.py
```

App em `http://localhost:8080` (ou a porta configurada).

## Acessos padrão (troque em produção)

| Painel | URL | Login |
|--------|-----|--------|
| Master | `/master/login` | `MASTER_EMAIL` / `MASTER_SENHA` no `.env` |
| ERP loja | `/admin/login` | usuário da conta |
| Site | `/loja/{slug}/` | público |

## Variáveis importantes

Veja `.env.example`. Em produção use PostgreSQL via Supabase (`SUPABASE_DB_*` ou `DATABASE_URL`).

Para desenvolvimento local rápido (SQLite):

```env
USE_LOCAL_SQLITE=1
```

## Estrutura

- `main.py` — rotas e bootstrap
- `loja/` — site, ERP, master, DB, auth
- `dados/` — storage local (não versionado)
- `migrar_para_supabase.py` — migração SQLite → Postgres
