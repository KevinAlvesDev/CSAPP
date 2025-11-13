#!/bin/bash
# scripts/backup_database.sh
# Script para backup automático do banco de dados PostgreSQL

# ========================================
# CONFIGURAÇÃO
# ========================================

# Diretório de backups (ajuste conforme necessário)
BACKUP_DIR="${BACKUP_DIR:-./backups}"

# Número de dias para manter backups (padrão: 30 dias)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Nome do arquivo de backup (com timestamp)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="backup_${TIMESTAMP}.sql.gz"

# URL do banco de dados (deve estar em .env ou variável de ambiente)
DATABASE_URL="${DATABASE_URL}"

# ========================================
# VALIDAÇÕES
# ========================================

# Verifica se DATABASE_URL está definido
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERRO: DATABASE_URL não está definido"
    echo "Configure a variável de ambiente DATABASE_URL"
    exit 1
fi

# Cria diretório de backups se não existir
mkdir -p "$BACKUP_DIR"

# ========================================
# BACKUP
# ========================================

echo "🔄 Iniciando backup do banco de dados..."
echo "📁 Diretório: $BACKUP_DIR"
echo "📄 Arquivo: $BACKUP_FILE"

# Executa pg_dump e comprime com gzip
if pg_dump "$DATABASE_URL" | gzip > "$BACKUP_DIR/$BACKUP_FILE"; then
    echo "✅ Backup criado com sucesso: $BACKUP_DIR/$BACKUP_FILE"
    
    # Mostra tamanho do arquivo
    SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
    echo "📊 Tamanho: $SIZE"
else
    echo "❌ ERRO: Falha ao criar backup"
    exit 1
fi

# ========================================
# LIMPEZA DE BACKUPS ANTIGOS
# ========================================

echo "🧹 Removendo backups com mais de $RETENTION_DAYS dias..."

# Remove backups antigos
find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete

# Conta backups restantes
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f | wc -l)
echo "📦 Backups mantidos: $BACKUP_COUNT"

# ========================================
# UPLOAD PARA CLOUDFLARE R2 (OPCIONAL)
# ========================================

# Descomente as linhas abaixo para fazer upload automático para R2
# Requer AWS CLI configurado com credenciais do R2

# if [ -n "$CLOUDFLARE_ENDPOINT_URL" ] && [ -n "$CLOUDFLARE_BUCKET_NAME" ]; then
#     echo "☁️  Fazendo upload para Cloudflare R2..."
#     
#     aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" \
#         "s3://$CLOUDFLARE_BUCKET_NAME/backups/$BACKUP_FILE" \
#         --endpoint-url "$CLOUDFLARE_ENDPOINT_URL"
#     
#     if [ $? -eq 0 ]; then
#         echo "✅ Upload para R2 concluído"
#     else
#         echo "⚠️  Falha no upload para R2 (backup local mantido)"
#     fi
# fi

echo "✅ Backup concluído!"

