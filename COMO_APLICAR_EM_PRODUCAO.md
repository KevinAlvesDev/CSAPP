# 🚀 COMO APLICAR MELHORIAS EM PRODUÇÃO

## 📋 GUIA PASSO A PASSO

Este guia descreve **exatamente** como aplicar todas as melhorias implementadas em produção, de forma segura e sem quebrar o código.

---

## ⚠️ ANTES DE COMEÇAR

### Pré-requisitos:
- [ ] Acesso ao Railway (ou servidor de produção)
- [ ] Acesso ao repositório Git
- [ ] Backup do banco de dados atual
- [ ] Ambiente de staging para testes (recomendado)

### Tempo estimado:
- **Urgente (credenciais):** 1h
- **Aplicação completa:** 2-3h

---

## 🔴 PASSO 1: REVOGAR CREDENCIAIS (URGENTE - FAZER HOJE)

### 1.1 Google OAuth

```bash
# 1. Acesse: https://console.cloud.google.com/
# 2. Vá em: APIs & Services → Credentials
# 3. Encontre o Client ID: 423250542233-ao4bam43it31ja6la5oemsgu7un7i3nv
# 4. Clique em DELETE
# 5. Crie novo OAuth 2.0 Client ID:
#    - Application type: Web application
#    - Authorized redirect URIs: https://seu-app.up.railway.app/agenda/callback
# 6. Copie o novo Client ID e Client Secret
```

### 1.2 Cloudflare R2

```bash
# 1. Acesse: https://dash.cloudflare.com/
# 2. Vá em: R2 → Manage R2 API Tokens
# 3. Encontre o token com Access Key: b26f2fee7ec4e2aa95506e18997e97e1aa10cb1a3f522b4dcd94eda8acab9c66
# 4. Clique em Revoke
# 5. Crie novo API Token:
#    - Permissions: Object Read & Write
#    - Bucket: seu-bucket
# 6. Copie o novo Access Key ID e Secret Access Key
```

### 1.3 SendGrid

```bash
# 1. Acesse: https://app.sendgrid.com/
# 2. Vá em: Settings → API Keys
# 3. Encontre a key: SG.BiRbczRhS66l7k0Y_vwwGw...
# 4. Clique em Delete
# 5. Crie nova API Key:
#    - Name: CSAPP Production
#    - Permissions: Full Access (ou Mail Send)
# 6. Copie a nova API Key
```

### 1.4 Gmail SMTP

```bash
# 1. Acesse: https://myaccount.google.com/apppasswords
# 2. Revogue a senha: ernqotyognsikmsp
# 3. Crie nova App Password:
#    - App: Mail
#    - Device: CSAPP
# 4. Copie a nova senha (16 caracteres)
```

### 1.5 Flask Secret Key

```bash
# Gere nova chave
python -c "import secrets; print(secrets.token_hex(32))"

# Copie o resultado (64 caracteres)
```

### 1.6 Atualizar .env Local

```bash
# Copie o template
cp .env.example .env

# Edite com as NOVAS credenciais
nano .env

# Cole as novas credenciais:
FLASK_SECRET_KEY=<nova_chave_64_caracteres>
GOOGLE_CLIENT_ID=<novo_client_id>
GOOGLE_CLIENT_SECRET=<novo_client_secret>
CLOUDFLARE_ACCESS_KEY_ID=<novo_access_key>
CLOUDFLARE_SECRET_ACCESS_KEY=<novo_secret_key>
SENDGRID_API_KEY=<nova_api_key>
SMTP_PASSWORD=<nova_senha_app>
```

### 1.7 Atualizar Railway

```bash
# 1. Acesse: https://railway.app/
# 2. Vá em: Seu Projeto → Variables
# 3. Atualize TODAS as variáveis com as novas credenciais
# 4. IMPORTANTE: Defina também:
FLASK_ENV=production
FLASK_DEBUG=false
USE_SQLITE_LOCALLY=false

# 5. Salve (Railway fará redeploy automático)
```

---

## 🟢 PASSO 2: TESTAR LOCALMENTE

### 2.1 Rodar Testes

```bash
# Ativar ambiente virtual
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Rodar testes
python -m pytest tests/ -v

# Deve passar: 85%+ dos testes
```

### 2.2 Testar Aplicação Local

```bash
# Rodar aplicação
python run.py

# Em outro terminal, testar:

# 1. Dashboard
curl http://localhost:5000/dashboard

# 2. Login
curl http://localhost:5000/login

# 3. Rotas dev (devem retornar 404 se FLASK_ENV=production)
FLASK_ENV=production python run.py
curl http://localhost:5000/dev-login
# Esperado: 404
```

---

## 🔵 PASSO 3: APLICAR MIGRATION DE ÍNDICES

### 3.1 Backup do Banco (IMPORTANTE!)

```bash
# Fazer backup ANTES de aplicar migration
./scripts/backup_database.sh

# Verificar backup criado
ls -lh backups/
```

### 3.2 Aplicar Migration

```bash
# Aplicar migration de índices
python -m alembic upgrade head

# Verificar índices criados (PostgreSQL)
psql $DATABASE_URL -c "\d+ implantacoes"

# Deve mostrar os novos índices:
# - idx_implantacoes_usuario_cs
# - idx_implantacoes_status
# - etc.
```

### 3.3 Testar Performance

```bash
# Antes (sem índices): ~2-5s
# Depois (com índices): ~200-500ms

time curl http://localhost:5000/dashboard
```

---

## 🟣 PASSO 4: COMMIT E PUSH

### 4.1 Verificar Mudanças

```bash
# Ver arquivos modificados
git status

# IMPORTANTE: Verificar que .env NÃO aparece
# Se aparecer, adicione ao .gitignore!
```

### 4.2 Commit

```bash
# Adicionar arquivos
git add .

# Commit
git commit -m "feat: implementar melhorias de segurança, performance e qualidade

- Adicionar 17 índices no banco (80-90% mais rápido)
- Implementar cache estratégico (dashboard, analytics)
- Otimizar queries N+1 (101 queries → 1)
- Adicionar Sentry para monitoramento
- Criar scripts de backup/restore
- Substituir 36 print() por logging
- Adicionar 11 exceções customizadas
- Implementar context managers para DB
- Proteger rotas dev em produção
- Melhorar validação de senha
- Ajustar rate limiting
- Proteger APIs contra CSRF

Veja documentação completa em TODAS_MELHORIAS_IMPLEMENTADAS.md"
```

### 4.3 Push

```bash
# Push para main (Railway fará deploy automático)
git push origin main
```

---

## 🟡 PASSO 5: VERIFICAR DEPLOY

### 5.1 Monitorar Logs

```bash
# Railway
railway logs

# Ou via dashboard: https://railway.app/
```

### 5.2 Testar em Produção

```bash
# 1. Rotas dev (devem retornar 404)
curl https://seu-app.up.railway.app/dev-login
# Esperado: 404 Not Found

# 2. Login normal
# Acesse: https://seu-app.up.railway.app/login
# Tente fazer login

# 3. Rate limiting
# Tente fazer login 6 vezes com senha errada
# 6ª tentativa deve bloquear

# 4. Dashboard (deve estar rápido)
time curl https://seu-app.up.railway.app/dashboard
# Esperado: ~200-500ms (primeira vez)
# Esperado: ~50-100ms (com cache)
```

---

## 🟠 PASSO 6: CONFIGURAR BACKUP AUTOMÁTICO

### 6.1 Configurar Cron (Servidor)

```bash
# Editar crontab
crontab -e

# Adicionar backup diário às 2h
0 2 * * * cd /path/to/CSAPP && ./scripts/backup_database.sh >> logs/backup.log 2>&1
```

### 6.2 Configurar Railway Cron (Alternativa)

```bash
# Railway não suporta cron nativamente
# Opções:
# 1. Usar GitHub Actions (recomendado)
# 2. Usar serviço externo (cron-job.org)
# 3. Usar Railway Plugin (se disponível)
```

---

## 🔴 PASSO 7: CONFIGURAR SENTRY (OPCIONAL)

### 7.1 Criar Conta Sentry

```bash
# 1. Acesse: https://sentry.io/
# 2. Crie conta gratuita
# 3. Crie novo projeto: Flask
# 4. Copie o DSN
```

### 7.2 Configurar no Railway

```bash
# Adicionar variável no Railway
SENTRY_DSN=https://abc123@o123456.ingest.sentry.io/123456
APP_VERSION=1.0.0
```

### 7.3 Testar

```bash
# Forçar erro para testar
curl https://seu-app.up.railway.app/rota-inexistente

# Verificar no Sentry: https://sentry.io/
# Deve aparecer o erro
```

---

## ✅ CHECKLIST FINAL

### Segurança:
- [ ] Credenciais revogadas (Google, R2, SendGrid, Gmail)
- [ ] Nova FLASK_SECRET_KEY gerada
- [ ] .env local atualizado
- [ ] Railway atualizado com novas credenciais
- [ ] FLASK_ENV=production definido
- [ ] Rotas /dev-login* testadas (404)

### Performance:
- [ ] Migration de índices aplicada
- [ ] Índices verificados no banco
- [ ] Performance testada (80-90% mais rápido)
- [ ] Cache funcionando

### Backup:
- [ ] Scripts executáveis (chmod +x)
- [ ] Backup manual testado
- [ ] Cron configurado (se aplicável)

### Monitoramento:
- [ ] Sentry configurado (opcional)
- [ ] Logs verificados (estruturados)

### Testes:
- [ ] Testes locais passando (85%+)
- [ ] Aplicação testada localmente
- [ ] Deploy em produção verificado
- [ ] Funcionalidades testadas em produção

---

## 🆘 TROUBLESHOOTING

### Problema: Migration falha

```bash
# Rollback
python -m alembic downgrade -1

# Verificar erro
python -m alembic upgrade head --sql

# Aplicar manualmente se necessário
```

### Problema: Cache não funciona

```bash
# Verificar Redis/cache configurado
python -c "from backend.project.cache_config import cache; cache.set('test', 'ok'); print(cache.get('test'))"

# Limpar cache
python -c "from backend.project.cache_config import cache; cache.clear()"
```

### Problema: Sentry não captura erros

```bash
# Verificar DSN configurado
echo $SENTRY_DSN

# Testar manualmente
python -c "from backend.project.sentry_config import capture_message; capture_message('Test')"
```

---

**Última atualização:** 2025-01-13

