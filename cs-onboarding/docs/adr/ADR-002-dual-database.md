# ADR-002: PostgreSQL + SQLite Dual Database Support

**Status:** Aceita  
**Data:** 2025-01-01  
**Decisores:** Time de Desenvolvimento

## Contexto

O sistema precisa funcionar em dois ambientes com requisitos diferentes:

1. **Produção**: Banco de dados robusto, confiável, com suporte a concorrência
2. **Desenvolvimento local**: Setup rápido, sem dependências externas

Além disso, uma integração com o sistema OAMD requer acesso a um banco de dados externo via SSH tunnel.

## Decisão

Adotamos uma estratégia **dual-database**:

- **Produção**: PostgreSQL (Railway)
- **Desenvolvimento**: SQLite local (zero-config)
- **Integração**: PostgreSQL externo (OAMD via SSH tunnel)

A seleção é feita via variável de ambiente `USE_SQLITE_LOCALLY` e `DATABASE_URL`.

## Justificativa

### PostgreSQL para Produção
- Suporte completo a JSON, arrays, CTEs e window functions
- Concorrência robusta (MVCC)
- Extensões como `pg_trgm` para busca fuzzy
- Hosting gerenciado via Railway

### SQLite para Desenvolvimento
- **Zero setup**: Não precisa instalar nenhum serviço
- Arquivo local criado automaticamente
- Schema inicializado via `schema.py` no startup
- Seeding automático (usuário admin padrão)
- Perfeito para desenvolvimento rápido e testes

### Banco Externo (OAMD)
- Acesso via SSH tunnel (script `abrir_tunel.py`)
- Usado para integração com dados de clientes (planos de sucesso)
- Conexão gerenciada separadamente (`EXTERNAL_DB_URL`)

## Implementação

```python
# config.py
USE_SQLITE_LOCALLY = os.environ.get("USE_SQLITE_LOCALLY", "").lower() in ("true", "1", "yes")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Detecção automática
if USE_SQLITE_ENV or (DATABASE_URL and DATABASE_URL.startswith("sqlite")):
    USE_SQLITE_LOCALLY = True
elif DATABASE_URL:
    USE_SQLITE_LOCALLY = False
else:
    USE_SQLITE_LOCALLY = True  # Fallback para SQLite
```

### Abstração de Queries

O sistema usa `%s` como placeholder universal. A camada de dados traduz automaticamente:

- PostgreSQL: `%s` (nativo)
- SQLite: Converte `%s` → `?` via wrapper

### Diferenças tratadas

| Feature | PostgreSQL | SQLite | Adaptação |
|---------|------------|--------|-----------|
| Placeholder | `%s` | `?` | Wrapper automático |
| Boolean | `TRUE/FALSE` | `1/0` | Cast em queries |
| ILIKE | Nativo | `LIKE` (case-insensitive) | Wrapper |
| JSON | Nativo | TEXT | Serialização manual |
| ON CONFLICT | `ON CONFLICT DO UPDATE` | `INSERT OR REPLACE` | Query adaptada |

## Consequências

### Positivas
- Onboarding de devs em < 5 minutos (sem instalar PostgreSQL)
- Desenvolvimento offline possível
- Testes rápidos com SQLite em memória

### Negativas
- Diferenças de comportamento entre PostgreSQL e SQLite (edge cases)
- Necessidade de manter compatibilidade dual em queries
- Schema definido em dois formatos (SQL puro + `schema.py`)
- Queries complexas podem não funcionar em SQLite (CTEs, window functions)

### Riscos
- Bugs que aparecem apenas em produção (PostgreSQL-specific)
- Drift entre esquema SQLite local e PostgreSQL de produção
- **Mitigação**: Testes de integração com PostgreSQL no CI

## Alternativas Rejeitadas

1. **Apenas PostgreSQL**: Exigiria que todos os devs instalassem PostgreSQL e configurassem banco local
2. **Docker Compose**: Adicionaria complexidade (Docker) para devs que não estão familiarizados
3. **PostgreSQL embutido**: Não existe solução madura como SQLite
