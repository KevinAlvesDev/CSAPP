# 🚀 GUIA DE EXECUÇÃO - MIGRATION PRODUÇÃO

## 📋 PRÉ-REQUISITOS

### 1. **BACKUP DO BANCO DE DADOS** (OBRIGATÓRIO!)

```bash
# Fazer backup completo do banco
pg_dump -h <HOST> -U <USUARIO> -d <NOME_BANCO> -F c -b -v -f backup_pre_migration_$(date +%Y%m%d_%H%M%S).backup

# OU backup em formato SQL (texto)
pg_dump -h <HOST> -U <USUARIO> -d <NOME_BANCO> > backup_pre_migration_$(date +%Y%m%d_%H%M%S).sql
```

### 2. **Verificar Conexão com o Banco**

```bash
# Testar conexão
psql -h <HOST> -U <USUARIO> -d <NOME_BANCO> -c "SELECT version();"
```

### 3. **Verificar Espaço em Disco**

```bash
# Verificar espaço disponível
df -h
```

---

## 🔧 EXECUÇÃO DA MIGRATION

### **Opção 1: Executar via psql (RECOMENDADO)**

```bash
# Conectar ao banco e executar o script
psql -h <HOST> -U <USUARIO> -d <NOME_BANCO> -f migrations/producao_melhorias_2025-12-22.sql

# OU executar com output detalhado
psql -h <HOST> -U <USUARIO> -d <NOME_BANCO> -f migrations/producao_melhorias_2025-12-22.sql -v ON_ERROR_STOP=1
```

### **Opção 2: Executar via pgAdmin**

1. Abra o pgAdmin
2. Conecte ao banco de produção
3. Clique com botão direito no banco → **Query Tool**
4. Abra o arquivo `migrations/producao_melhorias_2025-12-22.sql`
5. Clique em **Execute** (F5)
6. Verifique os resultados na aba **Messages**

### **Opção 3: Executar via DBeaver**

1. Abra o DBeaver
2. Conecte ao banco de produção
3. Clique com botão direito no banco → **SQL Editor** → **New SQL Script**
4. Cole o conteúdo do arquivo `migrations/producao_melhorias_2025-12-22.sql`
5. Clique em **Execute SQL Statement** (Ctrl+Enter)
6. Verifique os resultados

---

## ✅ VERIFICAÇÃO PÓS-MIGRATION

### 1. **Verificar se as colunas foram criadas**

```sql
-- Verificar coluna valor_atribuido
SELECT 
    column_name, 
    data_type, 
    column_default, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'implantacoes' 
AND column_name = 'valor_atribuido';

-- Verificar coluna tag
SELECT 
    column_name, 
    data_type, 
    column_default, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'comentarios_h' 
AND column_name = 'tag';
```

**Resultado esperado:**
```
Para implantacoes.valor_atribuido:
- data_type: numeric
- column_default: 0.00
- is_nullable: YES

Para comentarios_h.tag:
- data_type: character varying
- column_default: NULL
- is_nullable: YES
```

### 2. **Verificar constraints**

```sql
-- Verificar constraint de validação de tags
SELECT 
    constraint_name, 
    constraint_type
FROM information_schema.table_constraints 
WHERE table_name = 'comentarios_h' 
AND constraint_name = 'comentarios_h_tag_check';
```

**Resultado esperado:**
```
constraint_name: comentarios_h_tag_check
constraint_type: CHECK
```

### 3. **Verificar índices**

```sql
-- Verificar índices criados
SELECT 
    indexname, 
    indexdef
FROM pg_indexes 
WHERE tablename IN ('implantacoes', 'comentarios_h')
AND indexname LIKE 'idx_%';
```

**Resultado esperado:**
```
idx_implantacoes_valor_atribuido
idx_comentarios_h_tag
```

### 4. **Testar inserção de dados**

```sql
-- Testar update de valor_atribuido
UPDATE implantacoes 
SET valor_atribuido = 1000.50 
WHERE id = (SELECT id FROM implantacoes LIMIT 1);

-- Verificar se foi salvo
SELECT id, nome_empresa, valor_atribuido 
FROM implantacoes 
WHERE valor_atribuido > 0 
LIMIT 1;

-- Testar inserção de tag válida
UPDATE comentarios_h 
SET tag = 'Ação interna' 
WHERE id = (SELECT id FROM comentarios_h LIMIT 1);

-- Verificar se foi salvo
SELECT id, comentario, tag 
FROM comentarios_h 
WHERE tag IS NOT NULL 
LIMIT 1;

-- Testar constraint (deve dar erro)
UPDATE comentarios_h 
SET tag = 'Tag Inválida' 
WHERE id = (SELECT id FROM comentarios_h LIMIT 1);
-- Esperado: ERROR: new row for relation "comentarios_h" violates check constraint
```

---

## 🔄 ROLLBACK (SE NECESSÁRIO)

Se algo der errado, execute este script para reverter as mudanças:

```sql
-- ROLLBACK SCRIPT
BEGIN;

-- Remover índices
DROP INDEX IF EXISTS idx_implantacoes_valor_atribuido;
DROP INDEX IF EXISTS idx_comentarios_h_tag;

-- Remover constraint
ALTER TABLE comentarios_h DROP CONSTRAINT IF EXISTS comentarios_h_tag_check;

-- Remover colunas
ALTER TABLE implantacoes DROP COLUMN IF EXISTS valor_atribuido;
ALTER TABLE comentarios_h DROP COLUMN IF EXISTS tag;

COMMIT;

-- Verificar
SELECT 'ROLLBACK CONCLUÍDO' as status;
```

---

## 📊 MONITORAMENTO PÓS-DEPLOYMENT

### 1. **Verificar performance**

```sql
-- Verificar tamanho das tabelas
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('implantacoes', 'comentarios_h')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Verificar uso dos índices
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE indexname IN ('idx_implantacoes_valor_atribuido', 'idx_comentarios_h_tag');
```

### 2. **Verificar logs de erro**

```sql
-- Verificar se há erros relacionados às novas colunas
-- (Executar no servidor, não no banco)
tail -f /var/log/postgresql/postgresql-*.log | grep -i "valor_atribuido\|tag"
```

---

## 📝 CHECKLIST DE EXECUÇÃO

- [ ] Backup do banco criado e verificado
- [ ] Horário de baixo tráfego confirmado
- [ ] Conexão com banco de produção testada
- [ ] Script de migration executado
- [ ] Mensagens de sucesso verificadas
- [ ] Colunas criadas confirmadas (query de verificação)
- [ ] Constraints criadas confirmadas
- [ ] Índices criados confirmados
- [ ] Teste de inserção realizado
- [ ] Teste de constraint realizado
- [ ] Aplicação reiniciada (se necessário)
- [ ] Testes funcionais na interface realizados
- [ ] Monitoramento de erros ativo

---

## 🆘 TROUBLESHOOTING

### Erro: "permission denied for table"
```sql
-- Verificar permissões
GRANT ALL PRIVILEGES ON TABLE implantacoes TO <USUARIO>;
GRANT ALL PRIVILEGES ON TABLE comentarios_h TO <USUARIO>;
```

### Erro: "column already exists"
```
Isso é normal! O script detecta se a coluna já existe e pula a criação.
Verifique as mensagens NOTICE no output.
```

### Erro: "out of memory"
```
Isso não deve acontecer com este script (é muito leve).
Se acontecer, verifique o espaço em disco e memória do servidor.
```

---

## 📞 CONTATOS DE EMERGÊNCIA

Em caso de problemas críticos:
1. Restaurar backup imediatamente
2. Notificar equipe de desenvolvimento
3. Documentar o erro completo

---

## ✅ CONCLUSÃO

Após executar com sucesso:
1. ✅ Banco de produção atualizado
2. ✅ Novas funcionalidades disponíveis
3. ✅ Sistema pronto para uso

**Tempo estimado de execução: < 1 minuto**
**Downtime necessário: 0 segundos** (migration é não-destrutiva)
