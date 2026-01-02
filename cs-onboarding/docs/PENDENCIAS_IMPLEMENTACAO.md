# ✅ Checklist de Pendências - OAuth Incremental e RISC

## 📅 Data: 2026-01-02

---

## 🎯 RESUMO EXECUTIVO

Foram implementadas duas funcionalidades de segurança avançadas:
1. **Autorização Incremental do Google OAuth 2.0**
2. **RISC (Proteção entre Contas)**

Ambas estão **100% funcionais em desenvolvimento**, mas precisam de **configurações no Google Cloud Console** para funcionar em produção.

---

# 🔵 PRIORIDADE ALTA - Fazer Antes de Deploy em Produção

## 1. Configurar URIs de Redirecionamento no Google Cloud Console

### **O que fazer:**
Adicionar as URIs de callback da agenda no Google Cloud Console.

### **Onde:**
1. Acesse: https://console.cloud.google.com/
2. Selecione seu projeto
3. Vá em: **APIs & Services** > **Credentials**
4. Clique no seu **OAuth 2.0 Client ID**
5. Em **Authorized redirect URIs**, adicione:

#### **Para Desenvolvimento:**
```
http://localhost:5000/auth/google/callback
http://localhost:5000/agenda/callback
```

#### **Para Produção:**
```
https://seu-dominio.com/auth/google/callback
https://seu-dominio.com/agenda/callback
```

### **Por que é importante:**
Sem isso, o login e a conexão com Google Calendar vão dar erro `redirect_uri_mismatch`.

### **Status:** 🔴 PENDENTE
### **Tempo estimado:** 5 minutos

---

## 2. Atualizar Variável GOOGLE_REDIRECT_URI no .env de Produção

### **O que fazer:**
Atualizar o arquivo `.env` do servidor de produção com a URI correta.

### **Onde:**
No servidor de produção, edite o arquivo `.env`:

```bash
# Desenvolvimento (já está correto)
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback

# Produção (ATUALIZAR)
GOOGLE_REDIRECT_URI=https://seu-dominio.com/auth/google/callback
```

### **Por que é importante:**
O sistema usa essa variável para gerar a URL de callback. Se estiver errada, o OAuth não funciona.

### **Status:** 🔴 PENDENTE
### **Tempo estimado:** 2 minutos

---

## 3. Executar Migrações no Banco de Produção

### **O que fazer:**
Executar os scripts de migração para criar as tabelas no banco de produção.

### **Como fazer:**

#### **Opção A: Via SSH no servidor**
```bash
# Conectar ao servidor
ssh usuario@seu-servidor

# Ir para o diretório do projeto
cd /caminho/para/cs-onboarding

# Executar migrações
python apply_google_tokens_migration.py
python apply_risc_migration.py
```

#### **Opção B: Manualmente via SQL**
Se preferir, pode executar os arquivos SQL diretamente no banco:

```bash
# Conectar ao PostgreSQL
psql -U usuario -d nome_do_banco

# Executar migrações
\i migrations/create_google_tokens_table.sql
\i migrations/create_risc_events_table.sql
```

### **Tabelas que serão criadas:**
- `google_tokens` - Armazena tokens OAuth do Google
- `risc_events` - Armazena logs de eventos de segurança

### **Por que é importante:**
Sem essas tabelas, o sistema vai dar erro ao tentar salvar tokens ou processar eventos RISC.

### **Status:** 🔴 PENDENTE
### **Tempo estimado:** 5 minutos

---

## 4. Instalar Dependências no Servidor de Produção

### **O que fazer:**
Instalar as novas bibliotecas Python no servidor.

### **Como fazer:**

```bash
# Conectar ao servidor
ssh usuario@seu-servidor

# Ir para o diretório do projeto
cd /caminho/para/cs-onboarding

# Ativar ambiente virtual (se usar)
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### **Novas dependências:**
- `PyJWT==2.8.0` - Para validar tokens RISC
- `cryptography==42.0.5` - Necessário para PyJWT

### **Por que é importante:**
Sem essas bibliotecas, o endpoint RISC vai dar erro `ModuleNotFoundError`.

### **Status:** 🔴 PENDENTE
### **Tempo estimado:** 3 minutos

---

## 5. Reiniciar Servidor de Produção

### **O que fazer:**
Reiniciar o servidor para aplicar as mudanças.

### **Como fazer:**

#### **Se usar Gunicorn:**
```bash
sudo systemctl restart gunicorn
```

#### **Se usar systemd:**
```bash
sudo systemctl restart csapp
```

#### **Se usar PM2:**
```bash
pm2 restart csapp
```

#### **Se usar Docker:**
```bash
docker-compose restart
```

### **Por que é importante:**
As mudanças no código só entram em vigor após reiniciar o servidor.

### **Status:** 🔴 PENDENTE
### **Tempo estimado:** 1 minuto

---

# 🟡 PRIORIDADE MÉDIA - Fazer Quando Possível

## 6. Registrar Endpoint RISC no Google Cloud Console

### **O que fazer:**
Registrar o endpoint `/risc/events` para começar a receber eventos de segurança.

### **Como fazer:**
Siga o guia completo em: `docs/RISC_REGISTRO_GOOGLE.md`

**Resumo:**
1. Gerar token de autorização com escopo `https://www.googleapis.com/auth/risc`
2. Chamar API de configuração do Google
3. Registrar URL: `https://seu-dominio.com/risc/events`
4. Testar com evento de verificação

### **Por que é importante:**
Sem isso, você não vai receber eventos de segurança do Google (contas hackeadas, tokens revogados, etc).

### **Impacto se não fizer:**
- Sistema funciona normalmente
- Mas não terá proteção proativa contra contas comprometidas

### **Status:** 🟡 PENDENTE (opcional, mas recomendado)
### **Tempo estimado:** 15-20 minutos

---

## 7. Configurar HTTPS no Servidor (se ainda não tiver)

### **O que fazer:**
Garantir que o servidor está usando HTTPS (SSL/TLS).

### **Por que é importante:**
- Google OAuth **exige HTTPS** em produção
- RISC **exige HTTPS** para receber eventos
- Segurança geral do sistema

### **Como fazer:**

#### **Opção A: Usar Certbot (Let's Encrypt - Grátis)**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com
```

#### **Opção B: Usar Cloudflare (Grátis)**
1. Adicionar domínio no Cloudflare
2. Ativar SSL/TLS (Full ou Full Strict)
3. Cloudflare gerencia certificado automaticamente

#### **Opção C: Certificado Próprio**
Comprar certificado SSL e configurar no servidor.

### **Status:** 🟡 VERIFICAR (pode já estar configurado)
### **Tempo estimado:** 30 minutos (se não tiver)

---

# 🟢 PRIORIDADE BAIXA - Melhorias Futuras

## 8. Testar Fluxo Completo em Produção

### **O que fazer:**
Após deploy, testar:

1. **Login com Google:**
   - Verificar que solicita apenas escopos básicos
   - Confirmar que login funciona

2. **Conexão com Calendar:**
   - Acessar `/agenda`
   - Clicar em "Conectar Google Calendar"
   - Verificar que solicita apenas escopo de calendar
   - Confirmar que eventos aparecem

3. **Verificar Tokens no Banco:**
   ```sql
   SELECT usuario, scopes FROM google_tokens;
   ```
   - Deve mostrar escopos combinados

4. **Verificar Endpoint RISC:**
   ```bash
   curl https://seu-dominio.com/risc/status
   ```
   - Deve retornar status "ok"

### **Status:** 🟢 FAZER APÓS DEPLOY
### **Tempo estimado:** 10 minutos

---

## 9. Configurar Monitoramento de Eventos RISC

### **O que fazer:**
Criar alertas para eventos críticos.

### **Sugestões:**

#### **A. Criar query para eventos críticos:**
```sql
-- Ver eventos de hijacking (contas hackeadas)
SELECT * FROM risc_events 
WHERE event_payload LIKE '%hijacking%'
ORDER BY received_at DESC;
```

#### **B. Configurar alerta por email:**
Criar script que verifica eventos críticos a cada hora e envia email se houver.

#### **C. Dashboard de monitoramento:**
Adicionar página no admin para visualizar eventos RISC.

### **Status:** 🟢 MELHORIA FUTURA
### **Tempo estimado:** 2-3 horas

---

## 10. Adicionar Mais Escopos (Opcional)

### **O que fazer:**
Se quiser integrar com Google Drive ou outros serviços, adicionar suporte.

### **Como fazer:**
Seguir o mesmo padrão da agenda:

1. Adicionar escopo em `config.py`
2. Criar rota de conexão
3. Criar callback
4. Usar autorização incremental

### **Exemplo para Drive:**
```python
GOOGLE_OAUTH_SCOPES_DRIVE = 'https://www.googleapis.com/auth/drive.file'
```

### **Status:** 🟢 OPCIONAL
### **Tempo estimado:** 1-2 horas por escopo

---

# 📊 RESUMO DE PENDÊNCIAS

## Por Prioridade:

### 🔴 **ALTA - Fazer ANTES de deploy:**
1. ✅ Configurar URIs no Google Cloud Console (5 min)
2. ✅ Atualizar GOOGLE_REDIRECT_URI no .env (2 min)
3. ✅ Executar migrações no banco (5 min)
4. ✅ Instalar dependências (3 min)
5. ✅ Reiniciar servidor (1 min)

**Total:** ~15 minutos

### 🟡 **MÉDIA - Fazer quando possível:**
6. ⏳ Registrar endpoint RISC (20 min)
7. ⏳ Configurar HTTPS se necessário (30 min)

**Total:** ~50 minutos

### 🟢 **BAIXA - Melhorias futuras:**
8. ⏳ Testar em produção (10 min)
9. ⏳ Configurar monitoramento (2-3 horas)
10. ⏳ Adicionar mais escopos (opcional)

---

# 🎯 PRÓXIMOS PASSOS RECOMENDADOS

## Hoje (antes de dormir):
- [ ] Nada urgente! Tudo está funcionando em desenvolvimento

## Amanhã (antes do deploy):
1. [ ] Configurar URIs no Google Cloud Console
2. [ ] Atualizar .env de produção
3. [ ] Executar migrações no banco de produção
4. [ ] Instalar dependências
5. [ ] Reiniciar servidor
6. [ ] Testar login e agenda

## Próxima semana:
- [ ] Registrar endpoint RISC
- [ ] Configurar monitoramento
- [ ] Documentar para equipe

---

# 📚 DOCUMENTAÇÃO DE REFERÊNCIA

Todos os guias estão em `/docs`:

1. **OAuth Incremental:**
   - `GOOGLE_OAUTH_INCREMENTAL.md` - Guia técnico completo
   - `IMPLEMENTACAO_OAUTH_RESUMO.md` - Resumo executivo
   - `TESTE_OAUTH_INCREMENTAL.md` - Como testar

2. **RISC:**
   - `RISC_PROTECAO_ENTRE_CONTAS.md` - Guia técnico completo
   - `RISC_REGISTRO_GOOGLE.md` - Como registrar no Google

---

# ✅ CHECKLIST RÁPIDO

Antes de fazer deploy em produção:

```
[ ] URIs configuradas no Google Cloud Console
[ ] .env atualizado com GOOGLE_REDIRECT_URI correto
[ ] Migrações executadas (google_tokens e risc_events)
[ ] Dependências instaladas (PyJWT e cryptography)
[ ] Servidor reiniciado
[ ] HTTPS configurado
[ ] Testado login com Google
[ ] Testado conexão com Calendar
[ ] Endpoint RISC acessível
```

Depois do deploy (quando possível):

```
[ ] Endpoint RISC registrado no Google
[ ] Monitoramento configurado
[ ] Equipe treinada
[ ] Documentação interna atualizada
```

---

# 🆘 SE ALGO DER ERRADO

## Erro: "redirect_uri_mismatch"
**Solução:** Verificar URIs no Google Cloud Console

## Erro: "no such table: google_tokens"
**Solução:** Executar `python apply_google_tokens_migration.py`

## Erro: "ModuleNotFoundError: No module named 'jwt'"
**Solução:** Instalar dependências: `pip install -r requirements.txt`

## Erro: "Token inválido"
**Solução:** Verificar que GOOGLE_CLIENT_ID está correto no .env

## Dúvidas?
Consulte a documentação em `/docs` ou os comentários no código.

---

**Última atualização:** 2026-01-02 02:09  
**Status:** Implementação completa em desenvolvimento ✅  
**Próximo passo:** Configurar para produção 🚀
