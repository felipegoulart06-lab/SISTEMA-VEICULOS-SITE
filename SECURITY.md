# Política de Segurança — Plataforma White Label

Este documento define regras permanentes para desenvolvimento e operação do sistema.

## Ambiente de produção

Defina no `.env` ou no painel do servidor:

```env
AMBIENTE=production
SECRET_KEY=<string aleatória com 32+ caracteres>
MASTER_EMAIL=...
MASTER_SENHA=...
# Opcional — 2FA global para todos os logins Master:
MASTER_TOTP_SECRET=<base32 do Google Authenticator>
```

Sem `SECRET_KEY` forte, a aplicação **não inicia** em produção.

## Autenticação

| Área | Regra |
|------|--------|
| Master | `/master/login` — sessão isolada, 2FA TOTP opcional |
| Empresas | `/admin/login` ou subdomínio ERP — uma tela para todas |
| Senhas | PBKDF2-SHA256 via passlib — nunca texto puro no banco |
| Rate limit | 5 tentativas / 15 min por IP + e-mail (login Master e ERP) |
| Demo | Credenciais demo só aparecem fora de produção |

### Ativar 2FA Master

1. Instale um app TOTP (Google Authenticator, Authy).
2. Gere um secret: `python -c "import pyotp; print(pyotp.random_base32())"`.
3. Configure `MASTER_TOTP_SECRET` no ambiente **ou** grave em `admin_master.totp_secret`.
4. Escaneie o QR: `otpauth://totp/Plataforma:master@email?secret=SEU_SECRET&issuer=Plataforma`.

## Isolamento multi-tenant

- Cada empresa tem schema/banco tenant próprio.
- Sempre usar `ligar_tenant(slug)` antes de queries no ERP.
- Master usa banco `plataforma` — nunca misturar sessões Master/empresa sem impersonação explícita.

## Uploads

Implementado em `loja/seguranca.py`:

- Whitelist: JPG, PNG, WebP, GIF
- Máximo 5 MB
- Validação por magic bytes (não confiar só na extensão)
- Nome de arquivo UUID — nunca usar nome original do usuário

## Headers HTTP

Middleware `SecurityHeadersMiddleware` aplica:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Referrer-Policy`, `Permissions-Policy`
- `Content-Security-Policy` (compatível com NiceGUI)
- `Strict-Transport-Security` em produção (HTTPS)

## Domínios

- ERP: subdomínio (`{slug}.plataforma.com.br`)
- Site: domínio próprio da loja (`dominio_site`)
- Resolução via `Host` header — não expor rotas internas em URLs públicas

## O que nunca fazer

1. Commitar `.env`, senhas ou tokens Supabase
2. Desabilitar rate limit ou headers “temporariamente”
3. Servir uploads fora de `/media/{slug}/`
4. Usar SQL concatenado — sempre SQLAlchemy/parâmetros
5. Exibir credenciais demo em produção
6. Compartilhar `SECRET_KEY` entre ambientes

## Checklist antes de deploy

- [ ] `AMBIENTE=production`
- [ ] `SECRET_KEY` com 32+ caracteres aleatórios
- [ ] Senhas Master e empresas alteradas
- [ ] 2FA Master ativo (`MASTER_TOTP_SECRET` ou coluna `totp_secret`)
- [ ] HTTPS terminado no proxy (nginx/Caddy/Cloudflare)
- [ ] Backups Supabase configurados
- [ ] Logs de plataforma monitorados

## Reportar vulnerabilidades

Contato privado com o administrador do repositório — não abrir issue pública com detalhes exploráveis.
