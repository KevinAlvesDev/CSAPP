# 📝 Notas de Deploy - CSAPP

## 🔧 Dependências Específicas por Ambiente

### **python-magic vs python-magic-bin**

O projeto usa validação de arquivos com `python-magic`. A instalação varia por sistema operacional:

#### **Windows (Desenvolvimento)**
```bash
pip install python-magic-bin
```
- Inclui a biblioteca `libmagic` compilada para Windows
- Não requer instalação adicional de bibliotecas do sistema

#### **Linux/macOS (Produção)**
```bash
# Instalar libmagic do sistema primeiro
# Ubuntu/Debian:
sudo apt-get install libmagic1

# CentOS/RHEL:
sudo yum install file-libs

# macOS:
brew install libmagic

# Depois instalar o pacote Python
pip install python-magic
```

### **requirements.txt**

O arquivo `requirements.txt` usa `python-magic==0.4.27` que funciona em produção (Linux).

Para desenvolvimento local no Windows, você pode precisar instalar manualmente:
```bash
pip install python-magic-bin
```

O código em `backend/project/file_validation.py` funciona com ambas as versões.

---

## 🐳 Deploy com Docker

Se estiver usando Docker, adicione ao `Dockerfile`:

```dockerfile
# Instalar libmagic
RUN apt-get update && apt-get install -y libmagic1 && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
RUN pip install -r requirements.txt
```

---

## 🚀 Deploy em Plataformas Cloud

### **Render**
- ✅ `python-magic` funciona nativamente
- ✅ `libmagic1` já está instalado no ambiente

### **Heroku**
Adicione ao `Aptfile`:
```
libmagic1
```

### **Railway**
- ✅ `python-magic` funciona nativamente
- ✅ `libmagic1` já está instalado no ambiente

### **Fly.io**
Adicione ao `Dockerfile`:
```dockerfile
RUN apt-get update && apt-get install -y libmagic1
```

---

## 📦 Outras Dependências Importantes

### **PostgreSQL (Produção)**
```bash
# Configurar DATABASE_URL no .env
DATABASE_URL=postgresql://user:password@host:5432/database
```

### **Redis (Cache - Opcional)**
```bash
# Configurar REDIS_URL no .env
REDIS_URL=redis://localhost:6379/0

# Se não configurado, usa SimpleCache (memória)
```

### **Alembic (Migrations)**
```bash
# Executar migrations após deploy
python -m alembic upgrade head
```

---

## ✅ Checklist de Deploy

Antes de fazer deploy em produção:

- [ ] ✅ Configurar variáveis de ambiente (`.env`)
- [ ] ✅ Configurar `DATABASE_URL` (PostgreSQL)
- [ ] ✅ Configurar `SECRET_KEY` (chave secreta única)
- [ ] ✅ Configurar `REDIS_URL` (opcional, para cache)
- [ ] ✅ Configurar credenciais de email (SMTP ou SendGrid)
- [ ] ✅ Configurar Auth0 ou OAuth Google (se usar)
- [ ] ✅ Configurar Cloudflare R2 (para uploads)
- [ ] ✅ Executar migrations: `python -m alembic upgrade head`
- [ ] ✅ Definir `FLASK_DEBUG=False`
- [ ] ✅ Configurar `SENTRY_DSN` (opcional, para monitoramento)
- [ ] ✅ Testar health checks: `/health`, `/health/ready`, `/health/live`

---

## 🔒 Segurança

### **Variáveis de Ambiente Obrigatórias**
```bash
SECRET_KEY=sua-chave-secreta-muito-forte-aqui
DATABASE_URL=postgresql://...
ADMIN_EMAIL=admin@example.com
```

### **Variáveis Opcionais mas Recomendadas**
```bash
SENTRY_DSN=https://...
REDIS_URL=redis://...
CORS_ALLOWED_ORIGINS=https://app.example.com
```

---

## 📊 Monitoramento

### **Health Checks**
- `GET /health` - Status geral
- `GET /health/ready` - Pronto para receber tráfego
- `GET /health/live` - Aplicação está viva

### **Logs**
- Logs são salvos em `logs/app.log` e `logs/errors.log`
- Configure `SENTRY_DSN` para monitoramento de erros em produção

### **APM (Performance)**
- Métricas disponíveis em `/api/v1/metrics` (requer autenticação)
- Monitora queries lentas, cache hits/misses, tempo de resposta

---

## 🐛 Troubleshooting

### **Erro: "No module named 'magic'"**
```bash
# Linux/macOS
sudo apt-get install libmagic1
pip install python-magic

# Windows
pip install python-magic-bin
```

### **Erro: "libmagic.so.1: cannot open shared object file"**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install libmagic1

# CentOS/RHEL
sudo yum install file-libs
```

### **Erro: "No matching distribution found for python-magic-bin"**
- Isso acontece em Linux/macOS
- Use `python-magic` ao invés de `python-magic-bin`
- O `requirements.txt` já está configurado corretamente

---

## 📚 Documentação Adicional

- **Guia Rápido:** `GUIA_RAPIDO.md`
- **Melhorias Implementadas:** `MELHORIAS_IMPLEMENTADAS.md` e `MELHORIAS_ROUND_2_IMPLEMENTADAS.md`
- **Testes:** `GUIA_EXECUCAO_TESTES.md`
- **Migrations:** `migrations/README_MIGRATIONS.md`
- **Novas Funcionalidades:** `GUIA_NOVAS_FUNCIONALIDADES.md`

---

**🎉 Projeto pronto para produção!** 🚀

