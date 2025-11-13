#!/bin/bash
# scripts/restore_database.sh
# Script para restaurar backup do banco de dados PostgreSQL

# ========================================
# CONFIGURAÇÃO
# ========================================

# Diretório de backups
BACKUP_DIR="${BACKUP_DIR:-./backups}"

# URL do banco de dados
DATABASE_URL="${DATABASE_URL}"

# ========================================
# VALIDAÇÕES
# ========================================

# Verifica se DATABASE_URL está definido
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERRO: DATABASE_URL não está definido"
    exit 1
fi

# Verifica se arquivo de backup foi fornecido
if [ -z "$1" ]; then
    echo "❌ ERRO: Arquivo de backup não especificado"
    echo ""
    echo "Uso: $0 <arquivo_backup>"
    echo ""
    echo "Backups disponíveis:"
    ls -lh "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null || echo "  Nenhum backup encontrado"
    exit 1
fi

BACKUP_FILE="$1"

# Verifica se arquivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ ERRO: Arquivo não encontrado: $BACKUP_FILE"
    exit 1
fi

# ========================================
# CONFIRMAÇÃO
# ========================================

echo "⚠️  ATENÇÃO: Esta operação irá SUBSTITUIR todos os dados do banco!"
echo ""
echo "📄 Arquivo: $BACKUP_FILE"
echo "🗄️  Banco: $DATABASE_URL"
echo ""
read -p "Tem certeza que deseja continuar? (digite 'SIM' para confirmar): " CONFIRM

if [ "$CONFIRM" != "SIM" ]; then
    echo "❌ Operação cancelada"
    exit 0
fi

# ========================================
# BACKUP DE SEGURANÇA
# ========================================

echo "🔄 Criando backup de segurança antes da restauração..."
SAFETY_BACKUP="$BACKUP_DIR/safety_backup_$(date +%Y%m%d_%H%M%S).sql.gz"

if pg_dump "$DATABASE_URL" | gzip > "$SAFETY_BACKUP"; then
    echo "✅ Backup de segurança criado: $SAFETY_BACKUP"
else
    echo "⚠️  Falha ao criar backup de segurança"
    read -p "Continuar mesmo assim? (digite 'SIM'): " FORCE
    if [ "$FORCE" != "SIM" ]; then
        exit 1
    fi
fi

# ========================================
# RESTAURAÇÃO
# ========================================

echo "🔄 Restaurando banco de dados..."

# Descomprime e restaura
if gunzip -c "$BACKUP_FILE" | psql "$DATABASE_URL"; then
    echo "✅ Banco de dados restaurado com sucesso!"
else
    echo "❌ ERRO: Falha na restauração"
    echo "⚠️  Backup de segurança disponível em: $SAFETY_BACKUP"
    exit 1
fi

echo "✅ Restauração concluída!"

