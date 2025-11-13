# 🚀 Guia Rápido - CSAPP Melhorado

## 📋 Checklist de Configuração

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente
```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar com suas configurações
# Mínimo necessário:
# - SECRET_KEY (gere uma chave aleatória)
# - DATABASE_URL (ou deixe vazio para SQLite)
# - ADMIN_EMAIL
```

### 3. Gerar SECRET_KEY
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Inicializar Banco de Dados

**SQLite (Desenvolvimento):**
```bash
# Deixe DATABASE_URL vazio no .env
# O banco será criado automaticamente em backend/dashboard_simples.db
python run.py
```

**PostgreSQL (Produção):**
```bash
# Configure DATABASE_URL no .env
# Exemplo: postgresql://user:pass@host:5432/dbname

# Aplicar migrations
python -m alembic upgrade head
```

### 5. Executar Aplicação
```bash
python run.py
```

---

## 🔍 Endpoints Importantes

### Aplicação
- **Dashboard:** `http://localhost:5000/`
- **Login:** `http://localhost:5000/login`

### Monitoramento
- **Health Check:** `http://localhost:5000/health`
- **Readiness:** `http://localhost:5000/health/ready`
- **Liveness:** `http://localhost:5000/health/live`

### Documentação
- **API Docs (Swagger):** `http://localhost:5000/api/docs`
- **OpenAPI Spec:** `http://localhost:5000/api/docs/spec`

---

## 🛠️ Comandos Úteis

### Migrations
```bash
# Criar nova migration
python -m alembic revision -m "descricao_da_mudanca"

# Aplicar todas as migrations
python -m alembic upgrade head

# Reverter última migration
python -m alembic downgrade -1

# Ver histórico
python -m alembic history

# Ver status atual
python -m alembic current
```

### Cache
```python
# Limpar cache de usuário
from backend.project.cache_config import clear_user_cache
clear_user_cache('user@example.com')

# Limpar cache de implantação
from backend.project.cache_config import clear_implantacao_cache
clear_implantacao_cache(123)

# Limpar todo o cache
from backend.project.cache_config import clear_all_cache
clear_all_cache()
```

### Logs
```bash
# Ver logs em tempo real
tail -f logs/app.log

# Ver apenas erros
tail -f logs/app.log | grep ERROR

# Ver logs de um módulo específico
tail -f logs/app.log | grep "database"
```

---

## 🔐 Configurações de Segurança

### Produção (Obrigatório)
```bash
# .env
FLASK_DEBUG=False
SECRET_KEY=<chave-aleatoria-forte>
DATABASE_URL=postgresql://...
```

### Headers de Segurança
Já configurados automaticamente:
- ✅ Content Security Policy (CSP)
- ✅ HSTS (apenas em produção)
- ✅ X-Frame-Options
- ✅ X-Content-Type-Options
- ✅ X-XSS-Protection

### Upload de Arquivos
Limites configurados:
- **Tamanho máximo:** 10 MB
- **Tipos permitidos:** Imagens, PDFs, Documentos Office
- **Validação:** MIME type real (não apenas extensão)

---

## 📊 Monitoramento

### Health Checks
```bash
# Verificar saúde da aplicação
curl http://localhost:5000/health

# Resposta esperada (200 OK):
{
  "status": "healthy",
  "checks": {
    "database": {"status": "up", "response_time_ms": 12.5},
    "r2_storage": {"status": "up"}
  }
}
```

### Sentry (Opcional)
```bash
# Configurar no .env
SENTRY_DSN=https://...@sentry.io/...

# Erros serão enviados automaticamente
```

---

## 🚀 Deploy

### Railway / Heroku
```bash
# Configurar variáveis de ambiente no painel
DATABASE_URL=<fornecido-automaticamente>
SECRET_KEY=<gerar-nova>
REDIS_URL=<se-disponivel>

# Aplicar migrations após deploy
python -m alembic upgrade head
```

### Docker (Futuro)
```bash
# Build
docker build -t csapp .

# Run
docker run -p 5000:5000 --env-file .env csapp
```

---

## 🐛 Troubleshooting

### Erro: "Connection pool not initialized"
**Solução:** Reinicie a aplicação. O pool é inicializado no startup.

### Erro: "Migration failed"
**Solução:**
```bash
# Ver estado atual
python -m alembic current

# Forçar para head (cuidado!)
python -m alembic stamp head
```

### Cache não funciona
**Solução:**
- Verifique se `REDIS_URL` está configurado (produção)
- Em desenvolvimento, usa SimpleCache (memória)
- Reinicie a aplicação

### Upload de arquivo rejeitado
**Solução:**
- Verifique o tamanho (max 10MB)
- Verifique o tipo (deve estar na whitelist)
- Verifique os logs para detalhes

---

## 📚 Documentação Adicional

- **Migrations:** `migrations/README_MIGRATIONS.md`
- **Melhorias:** `MELHORIAS_IMPLEMENTADAS.md`
- **API:** `http://localhost:5000/api/docs`

---

## 🆘 Suporte

Em caso de problemas:
1. Verifique os logs em `logs/app.log`
2. Consulte a documentação
3. Verifique o health check: `/health`
4. Entre em contato com o suporte

---

**Última atualização:** 2025-01-13  
**Versão:** 1.0.0

