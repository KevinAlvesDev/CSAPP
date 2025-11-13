# 🔐 GUIA DE SEGURANÇA - CREDENCIAIS EXPOSTAS

## ⚠️ AÇÃO IMEDIATA NECESSÁRIA

Se você identificou que credenciais foram expostas no repositório Git, siga este guia **IMEDIATAMENTE**.

---

## 🚨 PASSO 1: REVOGAR TODAS AS CREDENCIAIS EXPOSTAS

### 1.1 Google OAuth

**Credenciais expostas:**
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

**Como revogar:**

1. Acesse: https://console.cloud.google.com/
2. Selecione seu projeto
3. Vá em: **APIs & Services** → **Credentials**
4. Encontre o OAuth 2.0 Client ID usado
5. Clique em **DELETE** (ícone de lixeira)
6. Crie um novo OAuth 2.0 Client ID:
   - Application type: **Web application**
   - Authorized redirect URIs:
     - `http://127.0.0.1:5000/agenda/callback` (dev)
     - `https://seu-app.up.railway.app/agenda/callback` (prod)
7. Copie o novo **Client ID** e **Client Secret**
8. Atualize no arquivo `.env` (NÃO commite!)

---

### 1.2 Cloudflare R2

**Credenciais expostas:**
- `CLOUDFLARE_ACCESS_KEY_ID`
- `CLOUDFLARE_SECRET_ACCESS_KEY`

**Como revogar:**

1. Acesse: https://dash.cloudflare.com/
2. Vá em: **R2** → **Manage R2 API Tokens**
3. Encontre o token exposto
4. Clique em **Revoke** ou **Delete**
5. Crie um novo API Token:
   - Permissions: **Object Read & Write**
   - Bucket: Selecione seu bucket
6. Copie o novo **Access Key ID** e **Secret Access Key**
7. Atualize no arquivo `.env` (NÃO commite!)

---

### 1.3 SendGrid

**Credenciais expostas:**
- `SENDGRID_API_KEY`

**Como revogar:**

1. Acesse: https://app.sendgrid.com/
2. Vá em: **Settings** → **API Keys**
3. Encontre a API Key exposta
4. Clique em **Delete**
5. Crie uma nova API Key:
   - Name: `CSAPP Production`
   - Permissions: **Full Access** ou **Mail Send** (mínimo)
6. Copie a nova API Key (só aparece uma vez!)
7. Atualize no arquivo `.env` (NÃO commite!)

---

### 1.4 SMTP Gmail

**Credenciais expostas:**
- `SMTP_PASSWORD` (App Password)

**Como revogar:**

1. Acesse: https://myaccount.google.com/apppasswords
2. Encontre a senha de app usada
3. Clique em **Revoke** ou **Remove**
4. Crie uma nova App Password:
   - App: **Mail**
   - Device: **CSAPP**
5. Copie a nova senha (16 caracteres)
6. Atualize no arquivo `.env` (NÃO commite!)

---

### 1.5 Flask Secret Key

**Credencial exposta:**
- `FLASK_SECRET_KEY`

**Como gerar nova:**

```bash
# Execute no terminal
python -c "import secrets; print(secrets.token_hex(32))"
```

Copie o resultado (64 caracteres) e atualize no `.env`.

---

## 🗑️ PASSO 2: REMOVER .env DO HISTÓRICO DO GIT

### Opção A: Usando BFG Repo-Cleaner (Recomendado)

```bash
# 1. Instalar BFG
# Download: https://rtyley.github.io/bfg-repo-cleaner/

# 2. Fazer backup do repositório
git clone --mirror https://github.com/KevinAlvesDev/CSAPP.git csapp-backup.git

# 3. Remover arquivo .env do histórico
java -jar bfg.jar --delete-files .env csapp-backup.git

# 4. Limpar o repositório
cd csapp-backup.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. Forçar push (CUIDADO!)
git push --force
```

### Opção B: Usando git filter-branch

```bash
# ATENÇÃO: Isso reescreve TODO o histórico do Git!

# 1. Fazer backup
git clone https://github.com/KevinAlvesDev/CSAPP.git csapp-backup

# 2. Remover .env do histórico
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# 3. Limpar referências
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 4. Forçar push (CUIDADO!)
git push origin --force --all
git push origin --force --tags
```

### ⚠️ IMPORTANTE APÓS REESCREVER HISTÓRICO

Todos os colaboradores precisam:

```bash
# Deletar clone local
rm -rf CSAPP

# Clonar novamente
git clone https://github.com/KevinAlvesDev/CSAPP.git
```

---

## ✅ PASSO 3: VERIFICAR SEGURANÇA

### 3.1 Verificar .gitignore

```bash
# Verificar se .env está no .gitignore
cat .gitignore | grep ".env"
```

Deve aparecer:
```
.env
*.env
```

### 3.2 Verificar que .env não está no Git

```bash
# Não deve retornar nada
git ls-files | grep ".env"
```

### 3.3 Testar com novas credenciais

```bash
# Rodar aplicação localmente
python run.py

# Testar:
# - Login
# - Upload de imagem (R2)
# - Envio de e-mail (SMTP/SendGrid)
# - Google Calendar (se aplicável)
```

---

## 📋 CHECKLIST DE SEGURANÇA

- [ ] Revogadas credenciais do Google OAuth
- [ ] Revogadas credenciais do Cloudflare R2
- [ ] Revogada API Key do SendGrid
- [ ] Revogada senha de app do Gmail
- [ ] Gerada nova FLASK_SECRET_KEY
- [ ] Atualizado arquivo .env local
- [ ] Removido .env do histórico do Git
- [ ] Verificado .gitignore
- [ ] Testada aplicação com novas credenciais
- [ ] Atualizado .env em produção (Railway)
- [ ] Notificados colaboradores sobre reescrita do histórico

---

## 🔒 BOAS PRÁTICAS PARA O FUTURO

1. **NUNCA** commite arquivos `.env`
2. **SEMPRE** use `.env.example` com valores fictícios
3. **SEMPRE** adicione `.env` ao `.gitignore`
4. **Use** gerenciadores de secrets (Railway Secrets, AWS Secrets Manager, etc.)
5. **Rotacione** credenciais periodicamente (a cada 90 dias)
6. **Use** diferentes credenciais para dev/staging/prod
7. **Habilite** 2FA em todas as contas (Google, Cloudflare, SendGrid)
8. **Monitore** acessos suspeitos nos dashboards dos serviços

---

## 📞 CONTATOS DE EMERGÊNCIA

- **Google Cloud Support:** https://cloud.google.com/support
- **Cloudflare Support:** https://dash.cloudflare.com/?to=/:account/support
- **SendGrid Support:** https://support.sendgrid.com/

---

**Última atualização:** 2025-01-13

