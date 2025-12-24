# 🔐 Proxy SOCKS5 para Banco OAMD

## 📋 Arquitetura

```
[Servidor Produção] 
    ↓ (via Internet)
[Seu PC - pacto-css.ddns.net:50022] (Proxy SOCKS5)
    ↓ (via Rede Local/VPN)
[Banco OAMD - oamd.pactosolucoes.com.br:5432]
```

**Seu PC funciona como proxy** porque:
- ✅ Tem acesso ao banco OAMD (via IP residencial/VPN)
- ✅ Cria um proxy SOCKS5 na porta 50022
- ✅ Aceita conexões externas do servidor de produção
- ✅ Roteia as consultas para o OAMD e retorna os dados

## 🚀 Como Usar

### 1. Iniciar o Proxy

Execute o script no seu PC:

```batch
INICIAR_TUNEL_OAMD.bat
```

O script irá:
- Criar um túnel SSH local (`localhost` → `localhost`)
- Abrir proxy SOCKS5 na porta **50022**
- Aceitar conexões de **qualquer IP** (`0.0.0.0`)

### 2. Testar Localmente

Em outra janela, teste se o proxy está funcionando:

```batch
TESTAR_CONEXAO_OAMD.bat
```

### 3. Configurar Produção

No servidor de produção, configure o `.env`:

```env
EXTERNAL_DB_URL=postgresql://cs_pacto:pacto@db@oamd.pactosolucoes.com.br:5432/OAMD
EXTERNAL_DB_PROXY_URL=socks5://pacto-css.ddns.net:50022
EXTERNAL_DB_TIMEOUT=10
```

### 4. Manter o Proxy Ativo

**NÃO FECHE** a janela do `INICIAR_TUNEL_OAMD.bat` enquanto a produção precisar acessar o OAMD.

## 🔧 Configurações

### Desenvolvimento Local

```env
EXTERNAL_DB_URL=postgresql://cs_pacto:pacto@db@oamd.pactosolucoes.com.br:5432/OAMD
EXTERNAL_DB_PROXY_URL=socks5://localhost:50022
EXTERNAL_DB_TIMEOUT=10
```

### Produção (Container)

```env
EXTERNAL_DB_URL=postgresql://cs_pacto:pacto@db@oamd.pactosolucoes.com.br:5432/OAMD
EXTERNAL_DB_PROXY_URL=socks5://pacto-css.ddns.net:50022
EXTERNAL_DB_TIMEOUT=10
```

## 🔒 Firewall

Certifique-se de que a porta **50022** está aberta:

### Windows Firewall

```powershell
# Verificar se a regra existe
Get-NetFirewallRule -DisplayName "SOCKS5 Proxy OAMD"

# Criar regra (se não existir)
New-NetFirewallRule -DisplayName "SOCKS5 Proxy OAMD" -Direction Inbound -LocalPort 50022 -Protocol TCP -Action Allow
```

### Roteador

Configure **Port Forwarding**:
- Porta Externa: **50022**
- Porta Interna: **50022**
- Protocolo: **TCP**
- IP Destino: IP do seu PC na rede local

## 🔍 Troubleshooting

### Erro: "Connection refused"

**Causa:** O proxy não está rodando

**Solução:** Execute `INICIAR_TUNEL_OAMD.bat`

### Erro: "Connection timeout"

**Possíveis causas:**
1. Firewall bloqueando a porta 50022
2. Roteador sem port forwarding configurado
3. DDNS não está apontando para o IP correto

**Solução:**
```powershell
# Verificar se a porta está aberta
netstat -an | findstr :50022

# Testar de fora da rede
# Use um serviço como https://www.yougetsignal.com/tools/open-ports/
```

### Erro: "Can't connect to OAMD database"

**Causa:** Seu PC não tem acesso ao OAMD

**Solução:** Verifique se você consegue acessar o OAMD diretamente do seu PC (VPN ativa?)

## 📝 Notas Técnicas

### Por que SSH localhost → localhost?

O comando `ssh -D 0.0.0.0:50022 -N usuario@localhost` cria um **Dynamic Port Forwarding** (proxy SOCKS5) sem precisar de um servidor remoto. É uma forma de criar um proxy local que aceita conexões externas.

### Alternativas

Se não quiser usar SSH, você pode usar ferramentas dedicadas:
- **Dante** (SOCKS5 server)
- **3proxy**
- **Shadowsocks**

Mas o SSH é mais simples porque já vem instalado com o Git.

## 🔐 Segurança

- ⚠️ A porta 50022 está **exposta na internet**
- ⚠️ Qualquer um que souber seu IP pode tentar usar o proxy
- ✅ Considere usar autenticação no proxy (SSH com chave pública)
- ✅ Ou use uma VPN ao invés de expor a porta
