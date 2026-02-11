# Migrations Guide

## Configuração

As migrations são gerenciadas com **Alembic** e seguem o padrão de versionamento incremental.

### Estrutura

```
migrations/
├── alembic.ini          # Configuração do Alembic
├── env.py               # Script de execução
├── README.md            # Este arquivo
├── versions/            # Migrations versionadas (Alembic)
│   ├── 001_consolidated_base.py
│   └── 002_add_performance_indexes.py
├── *.sql                # Scripts SQL legados (referência)
└── COMANDOS_PRODUCAO.sql
```

## Comandos

### Criar nova migration

```bash
# Gerar migration vazia
alembic revision -m "descricao_da_migration"

# Gerar migration com autogenerate (requer modelos SQLAlchemy)
alembic revision --autogenerate -m "descricao_da_migration"
```

### Aplicar migrations

```bash
# Aplicar todas as migrations pendentes
alembic upgrade head

# Aplicar uma migration específica
alembic upgrade 001_consolidated_base

# Verificar migration atual
alembic current

# Ver histórico
alembic history
```

### Reverter migrations

```bash
# Reverter última migration
alembic downgrade -1

# Reverter para uma revisão específica
alembic downgrade 001_consolidated_base

# Reverter todas
alembic downgrade base
```

### Marcar como aplicada (banco existente)

Para bancos de produção que já possuem o schema:

```bash
# Marcar a migration base como já aplicada
alembic stamp 001_consolidated_base

# Marcar todas como aplicadas
alembic stamp head
```

## Convenções

### Nomenclatura

Formato: `{numero}_{descricao}.py`

- `001_consolidated_base.py` — Schema base
- `002_add_performance_indexes.py` — Índices de performance
- `003_add_novo_campo.py` — Exemplo de adição de campo

### Regras

1. **Nunca edite** migrations já aplicadas em produção  
2. **Sempre teste** localmente antes de aplicar em produção
3. **Inclua downgrade** — Toda migration deve ser reversível
4. **Uma responsabilidade** — Cada migration deve ter um único propósito
5. **Nomeie descritivamente** — O nome deve explicar a mudança

### Scripts SQL Legados

Os scripts `.sql` no diretório `migrations/` são **referência histórica**.  
Novas mudanças devem sempre usar Alembic.

| Script Legado | Coberto por |
|---------------|-------------|
| `create_all_config_tables.sql` | `001_consolidated_base.py` |
| `create_tags_sistema.sql` | `001_consolidated_base.py` |
| `create_permissions_table.sql` | `001_consolidated_base.py` |
| `create_google_tokens_table.sql` | `001_consolidated_base.py` |
| `create_risc_events_table.sql` | `001_consolidated_base.py` |
| `add_performance_indexes.*` | `002_add_performance_indexes.py` |

## Workflow de Desenvolvimento

1. **Desenvolva** a feature com as mudanças de schema necessárias
2. **Crie** a migration: `alembic revision -m "add_campo_xyz"`
3. **Teste** localmente: `alembic upgrade head`
4. **Reverta** para validar: `alembic downgrade -1`
5. **Aplique** novamente: `alembic upgrade head`
6. **Commit** a migration junto com o código
