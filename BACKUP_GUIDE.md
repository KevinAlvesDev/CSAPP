# 📦 GUIA DE BACKUP E RESTAURAÇÃO

## 📋 VISÃO GERAL

Este guia descreve como fazer backup e restaurar o banco de dados PostgreSQL do CSAPP.

**Importante:** Backups regulares são essenciais para:
- Recuperação de desastres
- Proteção contra perda de dados
- Migração entre ambientes
- Testes de restauração

---

## 🔧 CONFIGURAÇÃO INICIAL

### 1. Tornar scripts executáveis

```bash
chmod +x scripts/backup_database.sh
chmod +x scripts/restore_database.sh
```

### 2. Configurar variáveis de ambiente

```bash
# .env ou variáveis de ambiente
DATABASE_URL=postgresql://user:password@host:5432/database
BACKUP_DIR=./backups  # Opcional (padrão: ./backups)
RETENTION_DAYS=30     # Opcional (padrão: 30 dias)
```

---

## 💾 BACKUP MANUAL

### Criar backup único

```bash
# Backup simples
./scripts/backup_database.sh

# Backup com diretório customizado
BACKUP_DIR=/mnt/backups ./scripts/backup_database.sh
```

**Resultado:**
- Arquivo: `backups/backup_YYYYMMDD_HHMMSS.sql.gz`
- Comprimido com gzip (economiza ~90% de espaço)
- Backups antigos (>30 dias) são removidos automaticamente

---

## ⏰ BACKUP AUTOMÁTICO (CRON)

### Configurar backup diário

```bash
# Editar crontab
crontab -e

# Adicionar linha (backup diário às 2h da manhã)
0 2 * * * cd /path/to/CSAPP && ./scripts/backup_database.sh >> logs/backup.log 2>&1
```

### Exemplos de agendamento

```bash
# Diário às 2h
0 2 * * * ./scripts/backup_database.sh

# A cada 6 horas
0 */6 * * * ./scripts/backup_database.sh

# Semanal (domingo às 3h)
0 3 * * 0 ./scripts/backup_database.sh

# Mensal (dia 1 às 4h)
0 4 1 * * ./scripts/backup_database.sh
```

---

## 🔄 RESTAURAÇÃO

### Listar backups disponíveis

```bash
ls -lh backups/backup_*.sql.gz
```

### Restaurar backup

```bash
# Restaurar backup específico
./scripts/restore_database.sh backups/backup_20250113_020000.sql.gz
```

**Atenção:**
- ⚠️ Operação DESTRUTIVA (substitui todos os dados)
- ✅ Cria backup de segurança antes de restaurar
- ✅ Requer confirmação manual (digite 'SIM')

---

## ☁️ BACKUP PARA CLOUDFLARE R2 (OPCIONAL)

### 1. Instalar AWS CLI

```bash
# Ubuntu/Debian
sudo apt install awscli

# macOS
brew install awscli

# Windows
# Download: https://aws.amazon.com/cli/
```

### 2. Configurar credenciais R2

```bash
aws configure

# Preencha:
AWS Access Key ID: <CLOUDFLARE_ACCESS_KEY_ID>
AWS Secret Access Key: <CLOUDFLARE_SECRET_ACCESS_KEY>
Default region name: auto
Default output format: json
```

### 3. Habilitar upload automático

Edite `scripts/backup_database.sh` e descomente as linhas:

```bash
if [ -n "$CLOUDFLARE_ENDPOINT_URL" ] && [ -n "$CLOUDFLARE_BUCKET_NAME" ]; then
    echo "☁️  Fazendo upload para Cloudflare R2..."
    
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" \
        "s3://$CLOUDFLARE_BUCKET_NAME/backups/$BACKUP_FILE" \
        --endpoint-url "$CLOUDFLARE_ENDPOINT_URL"
    
    if [ $? -eq 0 ]; then
        echo "✅ Upload para R2 concluído"
    else
        echo "⚠️  Falha no upload para R2 (backup local mantido)"
    fi
fi
```

### 4. Configurar variáveis

```bash
# .env
CLOUDFLARE_ENDPOINT_URL=https://3cd0bca0fc94af4472d8c6d68cd061ab.r2.cloudflarestorage.com
CLOUDFLARE_BUCKET_NAME=seu-bucket
```

---

## 🧪 TESTAR BACKUP/RESTAURAÇÃO

### Teste completo

```bash
# 1. Criar backup
./scripts/backup_database.sh

# 2. Verificar arquivo criado
ls -lh backups/backup_*.sql.gz

# 3. Testar restauração (em ambiente de teste!)
# ATENÇÃO: Só faça isso em ambiente de desenvolvimento/teste!
./scripts/restore_database.sh backups/backup_YYYYMMDD_HHMMSS.sql.gz
```

---

## 📊 MONITORAMENTO

### Verificar tamanho dos backups

```bash
du -sh backups/
```

### Verificar backups recentes

```bash
ls -lht backups/ | head -10
```

### Verificar logs de backup (se usando cron)

```bash
tail -f logs/backup.log
```

---

## ⚠️ BOAS PRÁTICAS

### ✅ Fazer:
- Testar restauração regularmente (mensal)
- Manter backups em múltiplos locais (local + R2)
- Monitorar espaço em disco
- Documentar procedimentos de recuperação
- Automatizar backups (cron)

### ❌ Não fazer:
- Confiar apenas em backups locais
- Nunca testar restauração
- Ignorar falhas de backup
- Manter backups indefinidamente (custo)

---

## 🚨 RECUPERAÇÃO DE DESASTRES

### Cenário 1: Banco corrompido

```bash
# 1. Identificar último backup válido
ls -lht backups/

# 2. Restaurar
./scripts/restore_database.sh backups/backup_YYYYMMDD_HHMMSS.sql.gz

# 3. Verificar integridade
psql $DATABASE_URL -c "SELECT COUNT(*) FROM implantacoes;"
```

### Cenário 2: Perda total do servidor

```bash
# 1. Provisionar novo servidor
# 2. Instalar PostgreSQL
# 3. Criar banco de dados vazio
# 4. Baixar backup do R2 (se configurado)
aws s3 cp s3://bucket/backups/backup_YYYYMMDD_HHMMSS.sql.gz . \
    --endpoint-url $CLOUDFLARE_ENDPOINT_URL

# 5. Restaurar
./scripts/restore_database.sh backup_YYYYMMDD_HHMMSS.sql.gz
```

---

## 📝 CHECKLIST DE BACKUP

- [ ] Scripts configurados e executáveis
- [ ] Variáveis de ambiente definidas
- [ ] Backup manual testado
- [ ] Cron configurado (se aplicável)
- [ ] Upload para R2 configurado (opcional)
- [ ] Restauração testada em ambiente de teste
- [ ] Monitoramento de espaço em disco
- [ ] Documentação atualizada

---

**Última atualização:** 2025-01-13

