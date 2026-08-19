# Deploy 100% na Vercel

Repositório: [felipegoulart06-lab/SISTEMA-VEICULOS-SITE](https://github.com/felipegoulart06-lab/SISTEMA-VEICULOS-SITE)

A aplicação completa (site HTML + ERP NiceGUI + Painel Master) roda na **Vercel** como **FastAPI Function** com suporte a **WebSocket** (Fluid Compute).

---

## Pré-requisitos

1. Conta [Vercel](https://vercel.com) (Plano Pro recomendado — WebSockets + `maxDuration` 800s)
2. Projeto **Supabase** (Postgres + Storage)
3. Domínios das lojas (site + ERP)

---

## Passo 1 — Supabase Storage (uploads de imagens)

Na Vercel o disco é efêmero. Imagens vão para o **Supabase Storage**.

1. Supabase → **Storage** → **New bucket**
2. Nome: `media`
3. Marque como **Public bucket**
4. Policies: permitir leitura pública; escrita via service role (backend)

No Supabase → **Settings → API**, copie a **service_role key** (nunca exponha no frontend).

---

## Passo 2 — Importar na Vercel

1. [vercel.com/new](https://vercel.com/new) → Import Git Repository
2. Repo: `felipegoulart06-lab/SISTEMA-VEICULOS-SITE`
3. Framework Preset: detecta **FastAPI** automaticamente (`main.py` → `app`)
4. Root Directory: `/`

---

## Passo 3 — Variáveis de ambiente (Vercel → Settings → Environment Variables)

| Variável | Obrigatório | Exemplo |
|----------|-------------|---------|
| `AMBIENTE` | Sim | `production` |
| `SECRET_KEY` | Sim | chave com 32+ caracteres |
| `MASTER_EMAIL` | Sim | `master@plataforma.com` |
| `MASTER_SENHA` | Sim | senha forte |
| `SUPABASE_DB_HOST` | Sim | `aws-0-....pooler.supabase.com` |
| `SUPABASE_DB_USER` | Sim | `erp_app....` |
| `SUPABASE_DB_PASSWORD` | Sim | senha do role |
| `SUPABASE_DB_NAME` | Sim | `postgres` |
| `SUPABASE_DB_PORT` | Sim | `5432` |
| `SUPABASE_URL` | Sim | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Sim | service role (uploads) |
| `SUPABASE_STORAGE_BUCKET` | Não | `media` (padrão) |
| `NICEGUI_REDIS_URL` | Recomendado | Upstash Redis (sessões multi-instância) |

Opcional: `DATABASE_URL=postgresql+psycopg://...?sslmode=require`

**Não** defina `USE_LOCAL_SQLITE` em produção.

---

## Passo 4 — Deploy

Clique **Deploy**. A Vercel:

- Instala `requirements.txt`
- Executa `scripts/vercel_build.py` (copia CSS para `public/static`)
- Publica `main.py` como Function FastAPI + WebSocket (NiceGUI)

Teste: `https://SEU-PROJETO.vercel.app/health` → `{"status":"ok"}`

---

## Passo 5 — Domínios customizados

Para **cada** hostname (site da loja, subdomínio ERP, domínio base):

1. Vercel → Project → **Settings → Domains** → Add
2. DNS no registrador:
   - **CNAME** `@` ou `www` → `cname.vercel-dns.com` (conforme painel Vercel)
   - **CNAME** `admin` ou `*.plataforma` → Vercel
3. No **Painel Master → Domínios**, cadastre os mesmos hostnames
4. Aguarde SSL automático (Let's Encrypt)

O roteamento por empresa usa o cabeçalho `Host` — todos os domínios apontam para **o mesmo projeto Vercel**.

Ordem completa: **Master → Guia de implantação** (`/master/guia`).

---

## Passo 6 — Redis (recomendado em produção)

Com múltiplas instâncias Vercel, sessões NiceGUI precisam de storage compartilhado:

1. Vercel Marketplace → **Upstash Redis**
2. Copie a URL → `NICEGUI_REDIS_URL`
3. Redeploy

Sem Redis, usuários podem perder sessão ao alternar instâncias (cold start).

---

## Arquivos de configuração

| Arquivo | Função |
|---------|--------|
| `main.py` | App FastAPI/NiceGUI exportado como `app` |
| `vercel.json` | `maxDuration: 800` para conexões WebSocket |
| `pyproject.toml` | Entrypoint `main:app` + build script |
| `loja/vercel.py` | Detecta `VERCEL=1` |
| `loja/storage_remoto.py` | Uploads → Supabase Storage |

---

## Desenvolvimento local (sem Vercel)

```bash
python main.py
```

Comportamento Docker/Easypanel inalterado (`ui.run()` + disco local em `dados/storage`).

Simular Vercel localmente:

```bash
vercel dev
```

---

## Limitações conhecidas

- **Cold start**: primeira requisição pode levar 5–15 s (Postgres no Supabase + NiceGUI)
- **WebSocket**: exige Fluid Compute (padrão em projetos novos) e Plano Pro para duração longa
- **Uploads antigos** em `/media/` local não migram automaticamente — reenvie imagens ou migre para o bucket `media`
- **Região Supabase**: prefira `sa-east-1` (São Paulo) para latência no Brasil

---

## Checklist pós-deploy

- [ ] `/health` OK
- [ ] `/master/login` abre
- [ ] Subdomínio ERP abre `/login`
- [ ] Domínio do site mostra estoque (HTML)
- [ ] Upload de imagem institucional salva no Supabase Storage
- [ ] Domínios customizados com SSL
- [ ] `NICEGUI_REDIS_URL` configurado (produção)
