# 📦 SCRIPTS DE MIGRATION PARA PRODUÇÃO

## 📁 Arquivos Criados

### 1. **`producao_melhorias_2025-12-22.sql`** (RECOMENDADO)
- ✅ Script completo com verificações de segurança
- ✅ Mensagens detalhadas de progresso
- ✅ Validação automática pós-execução
- ✅ Comentários e documentação
- ✅ Tratamento de erros
- **Tamanho:** ~8KB
- **Tempo de execução:** < 1 minuto

### 2. **`producao_melhorias_SIMPLES.sql`** (ALTERNATIVA RÁPIDA)
- ✅ Script minimalista
- ✅ Apenas comandos essenciais
- ✅ Fácil de ler e auditar
- **Tamanho:** ~600 bytes
- **Tempo de execução:** < 5 segundos

### 3. **`GUIA_EXECUCAO_PRODUCAO.md`** (DOCUMENTAÇÃO)
- ✅ Passo a passo completo
- ✅ Comandos de backup
- ✅ Verificações pós-migration
- ✅ Procedimento de rollback
- ✅ Troubleshooting

---

## 🚀 EXECUÇÃO RÁPIDA

### **Método 1: Via Terminal (psql)**

```bash
# 1. Fazer backup
pg_dump -h SEU_HOST -U SEU_USUARIO -d SEU_BANCO > backup_$(date +%Y%m%d).sql

# 2. Executar migration
psql -h SEU_HOST -U SEU_USUARIO -d SEU_BANCO -f migrations/producao_melhorias_SIMPLES.sql
```

### **Método 2: Via pgAdmin**

1. Abra o arquivo `producao_melhorias_SIMPLES.sql`
2. Copie todo o conteúdo
3. Cole no Query Tool do pgAdmin
4. Execute (F5)

### **Método 3: Via DBeaver**

1. Abra o arquivo `producao_melhorias_SIMPLES.sql`
2. Copie todo o conteúdo
3. Cole no SQL Editor do DBeaver
4. Execute (Ctrl+Enter)

---

## 📊 O QUE SERÁ CRIADO NO BANCO

### **Tabela: `implantacoes`**
```sql
+ valor_atribuido DECIMAL(10,2) DEFAULT 0.00
```
- Armazena valores monetários (ex: 15000.50 = R$ 15.000,50)
- Permite valores de R$ 0,00 até R$ 99.999.999,99
- Índice criado para consultas rápidas

### **Tabela: `comentarios_h`**
```sql
+ tag VARCHAR(50) DEFAULT NULL
```
- Armazena tags: "Ação interna", "Reunião" ou "No Show"
- Constraint garante apenas valores válidos
- Índice criado para consultas rápidas

---

## ✅ VERIFICAÇÃO RÁPIDA

Após executar, rode este comando para verificar:

```sql
-- Verificar se tudo foi criado
SELECT 
    'implantacoes.valor_atribuido' as item,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'implantacoes' AND column_name = 'valor_atribuido'
    ) THEN '✓ OK' ELSE '✗ ERRO' END as status
UNION ALL
SELECT 
    'comentarios_h.tag' as item,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'comentarios_h' AND column_name = 'tag'
    ) THEN '✓ OK' ELSE '✗ ERRO' END as status;
```

**Resultado esperado:**
```
item                              | status
----------------------------------+--------
implantacoes.valor_atribuido      | ✓ OK
comentarios_h.tag                 | ✓ OK
```

---

## 🔄 ROLLBACK (Se necessário)

Se precisar reverter as mudanças:

```sql
BEGIN;
DROP INDEX IF EXISTS idx_implantacoes_valor_atribuido;
DROP INDEX IF EXISTS idx_comentarios_h_tag;
ALTER TABLE comentarios_h DROP CONSTRAINT IF EXISTS comentarios_h_tag_check;
ALTER TABLE implantacoes DROP COLUMN IF EXISTS valor_atribuido;
ALTER TABLE comentarios_h DROP COLUMN IF EXISTS tag;
COMMIT;
```

---

## ⚠️ IMPORTANTE

### **ANTES DE EXECUTAR:**
1. ✅ Faça backup do banco
2. ✅ Execute em horário de baixo tráfego
3. ✅ Teste em homologação (se disponível)
4. ✅ Tenha o script de rollback pronto

### **APÓS EXECUTAR:**
1. ✅ Verifique se as colunas foram criadas
2. ✅ Teste a aplicação
3. ✅ Monitore logs de erro
4. ✅ Documente a execução

---

## 📞 SUPORTE

Em caso de dúvidas ou problemas:
1. Consulte o arquivo `GUIA_EXECUCAO_PRODUCAO.md`
2. Verifique os logs do PostgreSQL
3. Execute o script de rollback se necessário

---

## 🎯 RESUMO

**O que fazer:**
1. Backup do banco ✓
2. Executar `producao_melhorias_SIMPLES.sql` ✓
3. Verificar com query de validação ✓
4. Testar na aplicação ✓

**Tempo total:** 5-10 minutos
**Downtime:** 0 segundos (migration não-destrutiva)
**Risco:** Baixo (script com rollback disponível)
