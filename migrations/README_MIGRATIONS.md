# Database Migrations com Alembic

Este diretório contém as migrations do banco de dados usando Alembic.

## 📋 Comandos Principais

### Criar uma nova migration

```bash
python -m alembic revision -m "descrição da mudança"
```

Exemplo:
```bash
python -m alembic revision -m "adicionar coluna email_verificado"
```

### Aplicar migrations (upgrade)

```bash
# Aplicar todas as migrations pendentes
python -m alembic upgrade head

# Aplicar até uma revisão específica
python -m alembic upgrade <revision_id>

# Aplicar próxima migration
python -m alembic upgrade +1
```

### Reverter migrations (downgrade)

```bash
# Reverter última migration
python -m alembic downgrade -1

# Reverter até uma revisão específica
python -m alembic downgrade <revision_id>

# Reverter todas
python -m alembic downgrade base
```

### Ver histórico de migrations

```bash
# Ver histórico completo
python -m alembic history

# Ver status atual
python -m alembic current

# Ver migrations pendentes
python -m alembic history --verbose
```

## 📝 Como Criar uma Migration

1. **Criar o arquivo de migration:**
   ```bash
   python -m alembic revision -m "adicionar_tabela_notificacoes"
   ```

2. **Editar o arquivo gerado** em `migrations/versions/`:
   ```python
   def upgrade() -> None:
       # Código SQL para aplicar a mudança
       op.execute("""
           CREATE TABLE notificacoes (
               id SERIAL PRIMARY KEY,
               usuario_email VARCHAR(255) NOT NULL,
               mensagem TEXT,
               lida BOOLEAN DEFAULT FALSE,
               data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )
       """)

   def downgrade() -> None:
       # Código SQL para reverter a mudança
       op.execute("DROP TABLE notificacoes")
   ```

3. **Aplicar a migration:**
   ```bash
   python -m alembic upgrade head
   ```

## 🔄 Workflow Recomendado

### Desenvolvimento Local (SQLite)
```bash
# 1. Criar migration
python -m alembic revision -m "minha_mudanca"

# 2. Editar o arquivo gerado

# 3. Testar localmente
python -m alembic upgrade head

# 4. Se der erro, reverter
python -m alembic downgrade -1
```

### Produção (PostgreSQL)
```bash
# 1. Fazer backup do banco
# 2. Aplicar migrations
python -m alembic upgrade head

# 3. Verificar se funcionou
python -m alembic current
```

## ⚠️ Boas Práticas

1. **Sempre teste localmente** antes de aplicar em produção
2. **Faça backup** antes de aplicar migrations em produção
3. **Migrations devem ser idempotentes** (podem ser executadas múltiplas vezes)
4. **Nunca edite migrations já aplicadas** em produção
5. **Use transações** quando possível
6. **Documente mudanças complexas** nos comentários da migration

## 🚨 Troubleshooting

### Migration falhou no meio
```bash
# Marcar como resolvida manualmente
python -m alembic stamp head

# Ou reverter
python -m alembic downgrade -1
```

### Banco fora de sincronia
```bash
# Ver estado atual
python -m alembic current

# Forçar para uma revisão específica (cuidado!)
python -m alembic stamp <revision_id>
```

## 📚 Exemplos de Migrations Comuns

### Adicionar coluna
```python
def upgrade():
    op.execute("ALTER TABLE perfil_usuario ADD COLUMN telefone VARCHAR(20)")

def downgrade():
    op.execute("ALTER TABLE perfil_usuario DROP COLUMN telefone")
```

### Criar índice
```python
def upgrade():
    op.execute("CREATE INDEX idx_implantacoes_status ON implantacoes(status)")

def downgrade():
    op.execute("DROP INDEX idx_implantacoes_status")
```

### Adicionar constraint
```python
def upgrade():
    op.execute("""
        ALTER TABLE tarefas 
        ADD CONSTRAINT fk_tarefa_implantacao 
        FOREIGN KEY (implantacao_id) REFERENCES implantacoes(id)
    """)

def downgrade():
    op.execute("ALTER TABLE tarefas DROP CONSTRAINT fk_tarefa_implantacao")
```

