# Deploy e domínios — Vercel vs servidor Docker

Repositório: [felipegoulart06-lab/SISTEMA-VEICULOS-SITE](https://github.com/felipegoulart06-lab/SISTEMA-VEICULOS-SITE)

---

## Importante: o que a Vercel **não** faz neste projeto

Esta aplicação é **Python + NiceGUI + WebSocket + FastAPI long-running**. A Vercel é **serverless** e **não executa** este stack como app completa.

| Componente | Vercel serverless | Servidor Docker (recomendado) |
|------------|-------------------|-------------------------------|
| Site público (HTML) | Parcial | Sim |
| ERP NiceGUI (WebSocket) | **Não** | Sim |
| Painel Master | **Não** | Sim |
| Uploads persistentes | **Não** | Sim (volume `/app/dados`) |
| Multi-domínio por `Host` | Limitado | Sim |

**Recomendação:** hospede a aplicação inteira em **Easypanel**, **Railway**, **Render** ou **Fly.io** usando o `Dockerfile` da raiz.

Guia Easypanel: **[DEPLOY-EASYPANEL.md](DEPLOY-EASYPANEL.md)**

---

## Opção A — Hospedagem correta (recomendada)

### Easypanel / VPS

1. Conecte o GitHub `felipegoulart06-lab/SISTEMA-VEICULOS-SITE`
2. Build: **Dockerfile**, porta **8080**
3. Volume: `/app/dados`
4. Variáveis: copie de `.env.example` (Supabase, `SECRET_KEY`, Master, etc.)
5. Adicione **todos os domínios** das empresas na aba Domains do App

### Render (alternativa)

1. New → **Web Service** → conecte o repositório
2. Runtime: **Docker**
3. Health check: `/health`
4. Use o arquivo `render.yaml` como referência
5. Configure env vars no painel Render
6. Custom Domains: adicione site + ERP de cada loja

### Railway (alternativa)

1. New Project → Deploy from GitHub
2. Detecta `Dockerfile` automaticamente
3. Variables: mesmas do `.env.example`
4. Settings → Networking → Custom Domain para cada hostname

---

## Opção B — Vercel apenas como proxy (avançado)

Use a Vercel **somente** se quiser SSL/domínios na borda apontando para um **backend já publicado** (Railway/Render/Easypanel).

1. Publique o backend primeiro (Opção A) e anote a URL, ex.:  
   `https://sigma-sistema.up.railway.app`
2. Edite `vercel.json` e substitua `BACKEND_URL` pela URL real
3. Importe o repositório na Vercel
4. Adicione os domínios customizados (site e ERP) no projeto Vercel
5. DNS: CNAME dos domínios → `cname.vercel-dns.com` (ou conforme painel Vercel)

**Limitações do proxy Vercel:**

- WebSocket do ERP NiceGUI pode **falhar** ou ser instável
- Prefira apontar DNS **direto** para o servidor Docker (Easypanel/Railway/Render)

Se o ERP não abrir via Vercel, remova o proxy e use DNS A/CNAME direto para o backend.

---

## Fluxo de domínios (todas as hospedagens)

A ordem correta está no **Painel Master → Guia de implantação** (`/master/guia`).

Resumo:

1. **Deploy** da app + `/health` OK
2. **Configurações** → domínio base (ex.: `plataforma.com.br`)
3. **Empresas** → criar loja
4. **Domínios** → subdomínio ERP + domínio site (+ domínio ERP opcional)
5. **DNS** → A/CNAME para o servidor
6. **Hospedagem** → registrar cada hostname no painel (Easypanel Domains, Render Custom Domains, etc.)
7. **Testar** ERP (`/login`) e site (`/`)

O sistema identifica a empresa pelo cabeçalho HTTP `Host`. Todos os domínios devem chegar na **mesma instância** da aplicação.

---

## Variáveis de ambiente (produção)

```env
AMBIENTE=production
PORT=8080
SECRET_KEY=chave-forte-com-32-caracteres-ou-mais
MASTER_EMAIL=...
MASTER_SENHA=...
SUPABASE_DB_HOST=...
SUPABASE_DB_USER=...
SUPABASE_DB_PASSWORD=...
SUPABASE_DB_NAME=postgres
SUPABASE_DB_PORT=5432
```

Opcional: `DATABASE_URL=postgresql+psycopg://...?sslmode=require`

---

## Checklist pós-deploy

- [ ] `GET /health` → `{"status":"ok"}`
- [ ] `/master/login` acessível
- [ ] Subdomínio ERP abre login
- [ ] Domínio do site mostra estoque
- [ ] SSL ativo (HTTPS)
- [ ] Upload de imagens persiste após redeploy (volume montado)
- [ ] Empresa suspensa no Master bloqueia ERP e site
