# 🔌 Guia de Configuração do Proxy OAMD

## Problema

O banco de dados OAMD só aceita conexões de IPs autorizados. Quando a aplicação roda em produção (servidor diferente), não consegue acessar o banco diretamente.

## Solução: Proxy Service

Um micro-serviço que roda em um servidor com IP autorizado (sua casa) e funciona como intermediário entre a aplicação e o banco OAMD.

```
[App em Produção] → HTTP → [Proxy na sua casa] → PostgreSQL → [Banco OAMD]
```

## Configuração

### 1. No Servidor com Acesso ao Banco (Sua Casa)

#### Passo 1: Instalar dependências
```bash
cd cs-onboarding
pip install -r proxy_requirements.txt
```

#### Passo 2: Configurar variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto (ou edite o existente):

```env
# Token de segurança (gere um aleatório)
PROXY_API_TOKEN=seu-token-super-secreto-aqui-mude-isso-12345
```

#### Passo 3: Iniciar o proxy
```bash
python oamd_proxy_service.py
```

O proxy estará rodando em: `http://localhost:5001`

#### Passo 4: Expor para internet (Escolha uma opção)

**Opção A: ngrok (Mais fácil - Desenvolvimento)**
```bash
# Instalar ngrok: https://ngrok.com/download
ngrok http 5001
```

Você receberá uma URL pública como: `https://abc123.ngrok.io`

**Opção B: Configurar roteador (Produção)**
1. Configurar port forwarding no roteador: `5001 → IP_DO_SEU_PC:5001`
2. Usar um serviço de DNS dinâmico (ex: No-IP, DynDNS)
3. Configurar SSL/HTTPS (recomendado)

**Opção C: Servidor VPS**
1. Contratar um VPS pequeno (ex: DigitalOcean, AWS, Heroku)
2. Fazer deploy do proxy lá
3. Configurar firewall para aceitar apenas do IP da aplicação principal

### 2. Na Aplicação Principal (Produção)

Edite o arquivo `.env`:

```env
# Configuração do Proxy OAMD
OAMD_PROXY_URL=https://abc123.ngrok.io  # URL do proxy
OAMD_PROXY_TOKEN=seu-token-super-secreto-aqui-mude-isso-12345  # Mesmo token

# Remover ou comentar a conexão direta
# EXTERNAL_DB_URL=postgresql://...
```

## Como Funciona

1. **Aplicação tenta conexão direta** ao banco OAMD
2. **Se falhar** (erro de conexão, timeout, etc)
3. **Automaticamente tenta via proxy HTTP**
4. **Proxy consulta o banco** (tem IP autorizado)
5. **Retorna dados via HTTP** para a aplicação

## Testando

### Teste 1: Health Check do Proxy
```bash
curl http://localhost:5001/health
```

Resposta esperada:
```json
{"status": "ok", "database": "connected"}
```

### Teste 2: Consulta de Empresa
```bash
curl "http://localhost:5001/api/consultar_empresa?id_favorecido=11273" \
  -H "X-API-Token: seu-token-aqui"
```

### Teste 3: Da Aplicação Principal
```bash
# Com o proxy rodando
curl "http://localhost:5000/api/consultar_empresa?id_favorecido=11273"
```

## Segurança

✅ **Token de autenticação** - Apenas requisições com token válido são aceitas
✅ **CORS configurado** - Aceita apenas origens permitidas
✅ **Rate limiting** - Previne abuso (adicionar se necessário)
✅ **HTTPS recomendado** - Use ngrok ou configure SSL

## Monitoramento

Os logs do proxy mostrarão:
- ✅ Consultas bem-sucedidas
- ❌ Erros de conexão
- ⚠️ Tentativas sem token
- 📊 Performance

## Vantagens

1. ✅ **Sem alteração no firewall** do banco OAMD
2. ✅ **Fallback automático** - Se conexão direta funcionar, usa ela
3. ✅ **Cache possível** - Pode adicionar cache no proxy
4. ✅ **Logs centralizados** - Monitora todas as consultas
5. ✅ **Escalável** - Pode rodar em múltiplos servidores

## Desvantagens

1. ⚠️ **Latência adicional** - Mais um hop na rede
2. ⚠️ **Ponto único de falha** - Se proxy cair, consultas falham
3. ⚠️ **Manutenção** - Precisa manter o proxy rodando

## Alternativas

### Alternativa 1: VPN
- Aplicação conecta via VPN à rede com acesso ao banco
- Mais seguro, mas mais complexo de configurar

### Alternativa 2: SSH Tunnel
- Criar túnel SSH do servidor de produção para sua casa
- Mais técnico, requer configuração de SSH

### Alternativa 3: Liberar IP no Firewall
- Solicitar liberação do IP do servidor de produção
- Mais simples, mas requer acesso ao firewall do banco

## Produção

Para produção, recomendo:

1. **Deploy do proxy em VPS** (não deixar rodando no PC de casa)
2. **Configurar HTTPS** com certificado válido
3. **Adicionar cache Redis** para reduzir consultas ao banco
4. **Monitoramento** com Sentry ou similar
5. **Backup** - Ter 2 instâncias do proxy em servidores diferentes

## Comandos Úteis

```bash
# Iniciar proxy em background (Linux/Mac)
nohup python oamd_proxy_service.py > proxy.log 2>&1 &

# Iniciar proxy em background (Windows)
start /B python oamd_proxy_service.py

# Ver logs
tail -f proxy.log

# Parar proxy
# Linux/Mac: kill $(lsof -t -i:5001)
# Windows: netstat -ano | findstr :5001 e depois taskkill /PID <PID>
```

## Suporte

Se tiver problemas:
1. Verificar logs do proxy
2. Testar health check
3. Verificar firewall local
4. Confirmar token está correto
5. Testar conexão direta ao banco do proxy

---

**Criado em**: 2024-12-12
**Versão**: 1.0
