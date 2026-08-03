# Deploy no Easypanel (GitHub)

Guia para publicar o **sigma-sistema** como App no [Easypanel](https://easypanel.io), usando o repositório GitHub e Supabase como banco.

Repositório: `goulartfelipe618-beep/sigma-sistema`

---

## Pré-requisitos

1. **VPS** com Easypanel instalado
2. **Conta GitHub** com acesso ao repositório
3. **Supabase** configurado (Postgres + credenciais `SUPABASE_DB_*`)
4. **Domínio** apontando para o IP do VPS (ex.: `plataforma.com.br`)

---

## Passo 1 — Criar o App no Easypanel

1. Abra seu **Project** no Easypanel
2. **+ Service** → **App**
3. Nome sugerido: `sigma-sistema`

---

## Passo 2 — Conectar o GitHub

Aba **Source**:

| Campo | Valor |
|-------|--------|
| Source | GitHub |
| Owner / Repo | `goulartfelipe618-beep/sigma-sistema` |
| Branch | `main` |
| Build Path | `/` |

Ative **Auto Deploy** para redeploy automático a cada push.

---

## Passo 3 — Build (Dockerfile)

Aba **Build**:

| Campo | Valor |
|-------|--------|
| Build method | **Dockerfile** |
| Dockerfile path | `Dockerfile` |

O repositório já inclui o `Dockerfile` na raiz.

---

## Passo 4 — Porta do container

Aba **Domains** ou configuração do serviço:

| Campo | Valor |
|-------|--------|
| **Target port** (porta interna) | `8080` |

A variável `PORT=8080` também pode ser definida no Environment (o app lê `PORT` automaticamente).

Health check: `GET /health` → `{"status":"ok"}`

---

## Passo 5 — Volume persistente (uploads)

Imagens e arquivos ficam em `dados/storage/`. Sem volume, uploads somem ao redeploy.

Aba **Storage** → **Add mount**:

| Campo | Valor |
|-------|--------|
| Mount path (container) | `/app/dados` |
| Volume | criar novo, ex. `sigma-dados` |

---

## Passo 6 — Variáveis de ambiente

Aba **Environment** — cole e ajuste (nunca commite senhas reais):

```env
AMBIENTE=production
PORT=8080

SECRET_KEY=GERE_UMA_CHAVE_COM_32_CARACTERES_OU_MAIS

MASTER_EMAIL=seu-email-master@dominio.com
MASTER_SENHA=SENHA_FORTE_AQUI

SUPABASE_URL=https://SEU_PROJECT.supabase.co
SUPABASE_PROJECT_ID=SEU_PROJECT_REF
SUPABASE_ANON_KEY=sua-chave-anon

SUPABASE_DB_USER=postgres.SEU_PROJECT_REF
SUPABASE_DB_PASSWORD=SENHA_DO_BANCO
SUPABASE_DB_HOST=aws-0-sa-east-1.pooler.supabase.com
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
```

### Gerar SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Credenciais Supabase

No painel Supabase → **Project Settings** → **Database**:

- **Connection string** (Session pooler, porta 5432)
- Use o usuário `postgres` ou role dedicado (`erp_app`)
- **Não** defina `USE_LOCAL_SQLITE=1` em produção

Opcional — URL única em vez de variáveis separadas:

```env
DATABASE_URL=postgresql+psycopg://USER:SENHA@HOST:5432/postgres?sslmode=require
```

---

## Passo 7 — Domínios

### Domínio principal (Master + dev paths)

Aba **Domains** → adicionar:

| Domínio | Uso |
|---------|-----|
| `painel.seudominio.com.br` | Login Master `/master/login` |
| ou `seudominio.com.br` | Landing / Master |

Easypanel gera HTTPS automaticamente (Let's Encrypt).

### Subdomínios ERP (wildcard)

Cada loja acessa o ERP em `{slug}.plataforma.com.br`.

1. No **DNS** do domínio, crie:
   - `A` → IP do VPS (`@` ou subdomínio base)
   - `A` ou `CNAME` → `*.plataforma.seudominio.com.br` → IP do VPS
2. No Easypanel, adicione domínio wildcard se suportado, ou adicione cada subdomínio manualmente
3. No painel Master → **Domínios**, configure o subdomínio de cada empresa

### Site público (domínio próprio da loja)

Cada loja pode ter `dominio_site` (ex. `www.rodavia.com.br`):

1. DNS do cliente: `A` ou `CNAME` → IP do VPS
2. Easypanel: adicionar o domínio no App
3. Master → empresa → **Domínio do site**

---

## Passo 8 — Deploy

1. Clique **Deploy**
2. Acompanhe os logs de build
3. Quando subir, teste:
   - `https://SEU-DOMINIO/health` → `ok`
   - `https://SEU-DOMINIO/master/login`

---

## Checklist pós-deploy

- [ ] `/health` responde 200
- [ ] Login Master funciona
- [ ] Login ERP (`/admin/login`) funciona
- [ ] Supabase conectado (empresas e veículos aparecem)
- [ ] Upload de imagem persiste após redeploy (volume montado)
- [ ] `SECRET_KEY` forte definida
- [ ] Senhas demo alteradas (`MASTER_SENHA`, contas das lojas)
- [ ] 2FA Master opcional (`MASTER_TOTP_SECRET`)

---

## Redeploy automático

Com **Auto Deploy** ativo, cada `git push` na branch `main` dispara novo build.

Deploy manual: botão **Deploy** no painel do serviço.

---

## Solução de problemas

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| App não inicia | `SECRET_KEY` fraca em produção | Defina `SECRET_KEY` com 32+ chars |
| Erro de banco | Credenciais Supabase | Revise `SUPABASE_DB_*` ou `DATABASE_URL` |
| Site vazio, ERP ok | Tenant/schema Supabase | Rode migração ou sync no servidor |
| Upload some | Sem volume | Monte `/app/dados` |
| WebSocket / tela branca | Proxy | Confirme target port 8080 e HTTPS no Easypanel |
| 502 Bad Gateway | Container ainda iniciando | Aguarde health check; veja logs |

### Ver logs

Easypanel → serviço `sigma-sistema` → **Logs**

### Testar build local (opcional)

```bash
docker build -t sigma-sistema .
docker run --rm -p 8080:8080 --env-file .env sigma-sistema
```

---

## Arquitetura resumida

```
Internet
    │
    ▼
Easypanel (HTTPS + proxy)
    │
    ▼
Container sigma-sistema :8080
    ├── /master/login     → Admin Master
    ├── /admin/login      → ERP empresas
    ├── {slug}.dominio    → ERP por subdomínio
    ├── www.loja.com.br   → Site público
    └── /app/dados        → volume (uploads)
            │
            ▼
        Supabase Postgres (schemas tenant_*)
```

Veja também `SECURITY.md` e `.env.example`.
