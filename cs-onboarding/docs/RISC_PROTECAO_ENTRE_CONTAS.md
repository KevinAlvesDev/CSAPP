# RISC - Proteção entre Contas (Cross-Account Protection)

## 📋 Visão Geral

O RISC (Risk and Incident Sharing and Coordination) é um sistema do Google que notifica seu aplicativo sobre eventos de segurança relacionados às contas dos usuários, permitindo proteção proativa e automática.

## 🎯 O que foi Implementado

### **Componentes**

1. **Serviço RISC** (`backend/project/domain/risc_service.py`)
   - Validação de tokens JWT do Google
   - Processamento de eventos de segurança
   - Ações automáticas de proteção

2. **Endpoint** (`/risc/events`)
   - Recebe eventos do Google via POST
   - Valida e processa eventos
   - Retorna 202 Accepted (padrão RISC)

3. **Tabela de Logs** (`risc_events`)
   - Armazena todos os eventos para auditoria
   - Índices para queries rápidas

---

## 🔐 Eventos de Segurança Suportados

### 1. **Sessions Revoked** (`sessions-revoked`)
**O que é:** Google revogou todas as sessões do usuário

**Ação Automática:**
- ✅ Encerrar todas as sessões no CS Onboarding
- ✅ Revogar tokens OAuth armazenados

**Quando acontece:**
- Usuário fez logout de todos os dispositivos no Google
- Google detectou atividade suspeita

---

### 2. **Tokens Revoked** (`tokens-revoked`)
**O que é:** Todos os tokens OAuth foram revogados

**Ação Automática:**
- ✅ Excluir todos os tokens OAuth armazenados

**Quando acontece:**
- Usuário revogou acesso em myaccount.google.com
- Google detectou uso indevido de tokens

---

### 3. **Token Revoked** (`token-revoked`)
**O que é:** Token específico foi revogado

**Ação Automática:**
- ✅ Excluir o refresh_token correspondente

**Quando acontece:**
- Token específico foi comprometido
- Usuário revogou permissão específica

---

### 4. **Account Disabled** (`account-disabled`) ⚠️ CRÍTICO
**O que é:** Conta do Google foi desabilitada

**Motivos Possíveis:**

#### **`reason: hijacking`** 🚨 ALERTA MÁXIMO
- **Significado:** Conta foi HACKEADA
- **Ação Automática:**
  - ✅ Encerrar TODAS as sessões imediatamente
  - ✅ Revogar TODOS os tokens
  - ✅ Log crítico de segurança

#### **`reason: bulk-account`**
- **Significado:** Conta suspeita de spam/automação
- **Ação Automática:**
  - ✅ Log de aviso
  - ⚠️ Análise manual recomendada

#### **Sem motivo**
- **Significado:** Conta desabilitada por outro motivo
- **Ação Automática:**
  - ✅ Log de aviso

---

### 5. **Account Enabled** (`account-enabled`)
**O que é:** Conta foi reativada

**Ação Automática:**
- ✅ Log informativo

---

### 6. **Credential Change Required** (`account-credential-change-required`)
**O que é:** Usuário precisa trocar senha

**Ação Automática:**
- ✅ Log de aviso
- 💡 Pode enviar notificação ao usuário

---

### 7. **Verification** (`verification`)
**O que é:** Evento de teste do Google

**Ação Automática:**
- ✅ Responder com sucesso

---

## 🚀 Como Funciona

### **Fluxo Completo**

```
1. EVENTO DE SEGURANÇA OCORRE
   ├─> Usuário é hackeado
   ├─> Usuário revoga permissões
   └─> Google detecta atividade suspeita

2. GOOGLE ENVIA NOTIFICAÇÃO
   ├─> POST para /risc/events
   ├─> Token JWT no campo 'SET'
   └─> Assinado com chaves do Google

3. SEU APP RECEBE E VALIDA
   ├─> Valida assinatura JWT
   ├─> Verifica issuer (Google)
   └─> Verifica audience (seu Client ID)

4. SEU APP PROCESSA EVENTO
   ├─> Identifica tipo de evento
   ├─> Executa ação apropriada
   └─> Registra no banco (auditoria)

5. SEU APP RESPONDE
   └─> 202 Accepted (evento processado)
```

---

## 📊 Exemplo de Token de Evento

```json
{
  "iss": "https://accounts.google.com/",
  "aud": "seu-client-id.apps.googleusercontent.com",
  "iat": 1735786800,
  "jti": "unique-event-id-12345",
  "events": {
    "https://schemas.openid.net/secevent/risc/event-type/account-disabled": {
      "subject": {
        "subject_type": "iss-sub",
        "iss": "https://accounts.google.com/",
        "sub": "google-user-id-67890"
      },
      "reason": "hijacking"
    }
  }
}
```

---

## 🔧 Configuração

### **1. Endpoint Público**

O endpoint `/risc/events` precisa estar acessível publicamente via HTTPS.

**URL de Produção:**
```
https://seu-dominio.com/risc/events
```

**URL de Desenvolvimento (para testes):**
```
http://localhost:5000/risc/events
```

### **2. Registrar no Google Cloud Console**

Você precisa registrar seu endpoint no Google usando a API de configuração RISC.

**Documentação oficial:**
https://developers.google.com/identity/protocols/risc

**Passos:**
1. Gerar token de autorização
2. Chamar API de configuração
3. Testar configuração

---

## 🧪 Como Testar

### **1. Verificar Status do Endpoint**

```bash
curl http://localhost:5000/risc/status
```

**Resposta esperada:**
```json
{
  "status": "ok",
  "message": "RISC endpoint is operational",
  "endpoint": "/risc/events"
}
```

### **2. Simular Evento (Desenvolvimento)**

Você pode criar um token JWT de teste e enviar para o endpoint.

**Nota:** Em produção, apenas o Google pode enviar eventos válidos.

---

## 📈 Monitoramento

### **Ver Eventos Recebidos**

```sql
SELECT 
    event_type,
    user_id,
    action_taken,
    received_at
FROM risc_events
ORDER BY received_at DESC
LIMIT 10;
```

### **Contar Eventos por Tipo**

```sql
SELECT 
    event_type,
    COUNT(*) as total
FROM risc_events
GROUP BY event_type
ORDER BY total DESC;
```

### **Ver Eventos Críticos (Hijacking)**

```sql
SELECT *
FROM risc_events
WHERE event_payload LIKE '%hijacking%'
ORDER BY received_at DESC;
```

---

## ⚠️ Importante

### **Segurança**

1. **Validação de Tokens:** Sempre valide a assinatura JWT
2. **HTTPS Obrigatório:** Em produção, use apenas HTTPS
3. **Logs de Auditoria:** Todos os eventos são registrados
4. **Ações Irreversíveis:** Revogar sessões é permanente

### **Performance**

1. **Processamento Assíncrono:** Eventos são processados rapidamente
2. **Índices no Banco:** Queries otimizadas
3. **Cache de Chaves:** Chaves públicas do Google são cacheadas

### **Manutenção**

1. **Monitorar Logs:** Verificar eventos regularmente
2. **Limpar Logs Antigos:** Opcional, para economizar espaço
3. **Testar Periodicamente:** Usar endpoint de verificação

---

## 🎯 Benefícios

### **Para Segurança**
- ✅ Proteção automática contra contas comprometidas
- ✅ Resposta rápida a incidentes
- ✅ Redução de risco de acesso não autorizado

### **Para Compliance**
- ✅ Demonstra responsabilidade com dados
- ✅ Facilita auditorias
- ✅ Alinhado com boas práticas

### **Para Usuários**
- ✅ Proteção invisível e automática
- ✅ Maior confiança no sistema
- ✅ Menos preocupação com segurança

---

## 📚 Referências

- [Google RISC Documentation](https://developers.google.com/identity/protocols/risc)
- [OpenID RISC Specification](https://openid.net/specs/openid-risc-profile-specification-1_0.html)
- [Security Event Token (SET)](https://tools.ietf.org/html/rfc8417)

---

## ✅ Checklist de Implementação

- [x] Criar serviço RISC
- [x] Criar endpoint `/risc/events`
- [x] Criar tabela `risc_events`
- [x] Validar tokens JWT
- [x] Processar eventos de segurança
- [x] Registrar eventos para auditoria
- [x] Adicionar ao requirements.txt
- [x] Documentar implementação
- [ ] Registrar endpoint no Google Cloud Console (manual)
- [ ] Testar em produção

---

## 🎉 Status

**✅ IMPLEMENTAÇÃO COMPLETA E FUNCIONAL!**

O sistema RISC está pronto para receber e processar eventos de segurança do Google.

**Próximo passo:** Registrar o endpoint no Google Cloud Console para começar a receber eventos reais.
