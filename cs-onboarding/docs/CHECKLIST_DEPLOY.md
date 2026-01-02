# ✅ Checklist Rápido - Deploy em Produção

## 🎯 6 Passos Essenciais Antes do Deploy

### 1. ⚙️ Configurar URIs no Google Cloud Console

**Onde:** https://console.cloud.google.com/ → APIs & Services → Credentials → OAuth 2.0 Client ID

**Adicionar estas URIs:**
```
Produção:
https://seu-dominio.com/auth/google/callback
https://seu-dominio.com/agenda/callback

Desenvolvimento (se ainda não tiver):
http://localhost:5000/auth/google/callback
http://localhost:5000/agenda/callback
```

**Tempo:** 5 minutos

---

### 2. 📝 Atualizar .env de Produção

**No servidor de produção, editar `.env`:**

```bash
# Atualizar esta linha:
GOOGLE_REDIRECT_URI=https://seu-dominio.com/auth/google/callback

# Verificar se estas estão corretas:
GOOGLE_CLIENT_ID=seu-client-id
GOOGLE_CLIENT_SECRET=seu-client-secret
```

**Tempo:** 2 minutos

---

### 3. 🗄️ Executar Migrações no Banco de Produção

**Via SSH no servidor:**

```bash
# Conectar ao servidor
ssh usuario@seu-servidor

# Ir para o diretório
cd /caminho/para/cs-onboarding

# Executar migrações
python apply_google_tokens_migration.py
python apply_risc_migration.py
```

**OU via SQL direto:**

```bash
psql -U usuario -d nome_do_banco -f migrations/create_google_tokens_table.sql
psql -U usuario -d nome_do_banco -f migrations/create_risc_events_table.sql
```

**Tempo:** 5 minutos

---

### 4. 📦 Instalar Dependências

**No servidor:**

```bash
# Ativar ambiente virtual (se usar)
source venv/bin/activate

# Instalar novas dependências
pip install PyJWT==2.8.0 cryptography==42.0.5

# OU instalar tudo
pip install -r requirements.txt
```

**Tempo:** 3 minutos

---

### 5. 🔄 Reiniciar Servidor

**Escolha o comando apropriado:**

```bash
# Gunicorn
sudo systemctl restart gunicorn

# Systemd
sudo systemctl restart csapp

# PM2
pm2 restart csapp

# Docker
docker-compose restart
```

**Tempo:** 1 minuto

---

### 6. ✅ Testar Login e Agenda

**Testes básicos:**

1. **Testar Login:**
   - Acesse `https://seu-dominio.com/login`
   - Clique em "Entrar com Google"
   - Verifique que solicita apenas: email, profile
   - Confirme que login funciona

2. **Testar Agenda:**
   - Acesse `https://seu-dominio.com/agenda`
   - Clique em "Conectar Google Calendar"
   - Verifique que solicita apenas: calendar
   - Confirme que eventos aparecem

3. **Verificar Banco:**
   ```sql
   SELECT usuario, scopes FROM google_tokens;
   ```
   Deve mostrar: `openid email profile https://www.googleapis.com/auth/calendar`

**Tempo:** 10 minutos

---

## 📋 Checklist Resumido

```
[ ] 1. URIs configuradas no Google Cloud Console
[ ] 2. .env atualizado (GOOGLE_REDIRECT_URI)
[ ] 3. Migrações executadas (2 tabelas criadas)
[ ] 4. Dependências instaladas (PyJWT + cryptography)
[ ] 5. Servidor reiniciado
[ ] 6. Login e Agenda testados
```

**Tempo total:** ~25 minutos

---

## 🆘 Troubleshooting Rápido

| Erro | Solução |
|------|---------|
| `redirect_uri_mismatch` | Verificar URIs no Google Cloud Console |
| `no such table: google_tokens` | Executar migrações |
| `ModuleNotFoundError: jwt` | Instalar dependências |
| `Token inválido` | Verificar GOOGLE_CLIENT_ID no .env |

---

## 📚 Documentação Completa

Para mais detalhes, consulte:
- `docs/PENDENCIAS_IMPLEMENTACAO.md` - Checklist completo
- `docs/GOOGLE_OAUTH_INCREMENTAL.md` - Guia técnico OAuth
- `docs/RISC_PROTECAO_ENTRE_CONTAS.md` - Guia técnico RISC

---

**Status Atual:** ✅ Funcionando em desenvolvimento  
**Próximo Passo:** Seguir os 6 passos acima para produção  
**Prioridade:** Fazer antes do próximo deploy
