# Como Registrar o Endpoint RISC no Google

## 📋 Pré-requisitos

- ✅ Endpoint `/risc/events` implementado e funcionando
- ✅ HTTPS configurado (obrigatório em produção)
- ✅ Google Cloud Project criado
- ✅ OAuth 2.0 Client ID configurado

---

## 🚀 Passo a Passo

### **1. Gerar Token de Autorização**

Você precisa de um token OAuth com o escopo `https://www.googleapis.com/auth/risc`.

#### **Opção A: Usando Python**

```python
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Carregar credenciais de service account
credentials = service_account.Credentials.from_service_account_file(
    'path/to/service-account-key.json',
    scopes=['https://www.googleapis.com/auth/risc']
)

# Obter token
credentials.refresh(Request())
access_token = credentials.token

print(f"Access Token: {access_token}")
```

#### **Opção B: Usando gcloud CLI**

```bash
gcloud auth application-default print-access-token
```

---

### **2. Registrar Endpoint**

Use a API de configuração RISC para registrar seu endpoint.

#### **Request**

```bash
curl -X POST https://risc.googleapis.com/v1beta/stream:update \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "delivery": {
      "delivery_method": "https://schemas.openid.net/secevent/risc/delivery-method/push",
      "url": "https://seu-dominio.com/risc/events"
    },
    "events_requested": [
      "https://schemas.openid.net/secevent/risc/event-type/sessions-revoked",
      "https://schemas.openid.net/secevent/oauth/event-type/tokens-revoked",
      "https://schemas.openid.net/secevent/oauth/event-type/token-revoked",
      "https://schemas.openid.net/secevent/risc/event-type/account-disabled",
      "https://schemas.openid.net/secevent/risc/event-type/account-enabled",
      "https://schemas.openid.net/secevent/risc/event-type/account-credential-change-required"
    ]
  }'
```

#### **Response Esperada**

```json
{
  "name": "stream/YOUR_STREAM_ID",
  "delivery": {
    "delivery_method": "https://schemas.openid.net/secevent/risc/delivery-method/push",
    "url": "https://seu-dominio.com/risc/events"
  },
  "events_requested": [...]
}
```

---

### **3. Verificar Configuração**

```bash
curl -X GET https://risc.googleapis.com/v1beta/stream \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### **4. Testar Endpoint**

O Google pode enviar um evento de verificação para testar seu endpoint.

```bash
curl -X POST https://risc.googleapis.com/v1beta/stream:verify \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Você deve receber um evento do tipo `verification` no seu endpoint.

---

## 🔧 Desenvolvimento Local

Para testar localmente, você pode usar **ngrok** para expor seu servidor local:

### **1. Instalar ngrok**

```bash
# Windows
choco install ngrok

# Mac
brew install ngrok

# Linux
snap install ngrok
```

### **2. Expor Servidor Local**

```bash
ngrok http 5000
```

Isso vai gerar uma URL pública como:
```
https://abc123.ngrok.io
```

### **3. Registrar URL do ngrok**

Use a URL do ngrok como endpoint:
```
https://abc123.ngrok.io/risc/events
```

**⚠️ Atenção:** URLs do ngrok mudam a cada execução. Use apenas para testes!

---

## 📊 Monitorar Eventos

### **Ver Configuração Atual**

```bash
curl https://risc.googleapis.com/v1beta/stream \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### **Atualizar Configuração**

```bash
curl -X POST https://risc.googleapis.com/v1beta/stream:update \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "delivery": {
      "delivery_method": "https://schemas.openid.net/secevent/risc/delivery-method/push",
      "url": "https://novo-dominio.com/risc/events"
    }
  }'
```

### **Desabilitar RISC**

```bash
curl -X DELETE https://risc.googleapis.com/v1beta/stream \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## ⚠️ Troubleshooting

### **Erro: "Invalid URL"**
- ✅ Certifique-se que a URL usa HTTPS
- ✅ Verifique se o endpoint está acessível publicamente
- ✅ Teste com `curl https://seu-dominio.com/risc/status`

### **Erro: "Unauthorized"**
- ✅ Verifique se o token de acesso é válido
- ✅ Confirme que tem o escopo `https://www.googleapis.com/auth/risc`
- ✅ Gere um novo token se necessário

### **Não Recebe Eventos**
- ✅ Verifique se a configuração está ativa
- ✅ Teste com evento de verificação
- ✅ Verifique logs do servidor
- ✅ Confirme que o endpoint retorna 202

---

## 📚 Referências

- [RISC API Reference](https://developers.google.com/identity/protocols/risc/reference)
- [RISC Configuration Guide](https://developers.google.com/identity/protocols/risc/configuration)
- [OpenID RISC Specification](https://openid.net/specs/openid-risc-profile-specification-1_0.html)

---

## ✅ Checklist

- [ ] Gerar token de autorização
- [ ] Registrar endpoint no Google
- [ ] Verificar configuração
- [ ] Testar com evento de verificação
- [ ] Monitorar logs
- [ ] Documentar URL do endpoint
- [ ] Configurar alertas para eventos críticos

---

## 🎯 Próximos Passos

Após registrar o endpoint:

1. **Monitorar Logs:** Verificar se eventos estão chegando
2. **Testar Fluxo:** Revogar permissões manualmente e verificar
3. **Configurar Alertas:** Para eventos críticos (hijacking)
4. **Documentar:** Anotar configuração para referência futura

**Status:** Pronto para registro! 🚀
