-- ============================================================================
-- MIGRATION: Melhorias - Campo Valor Atribuído e Tags de Comentários
-- Data: 2025-12-22
-- Ambiente: PRODUÇÃO (PostgreSQL)
-- ============================================================================
-- 
-- DESCRIÇÃO:
-- Este script adiciona suporte para:
-- 1. Campo "Valor Atribuído" nas implantações
-- 2. Tags de comentários (Ação interna, Reunião, No Show)
--
-- IMPORTANTE:
-- - Faça BACKUP do banco antes de executar!
-- - Execute em horário de baixo tráfego
-- - Teste em ambiente de homologação primeiro (se disponível)
-- ============================================================================

-- Iniciar transação para garantir atomicidade
BEGIN;

-- ============================================================================
-- 1. ADICIONAR COLUNA "valor_atribuido" NA TABELA "implantacoes"
-- ============================================================================

-- Verificar se a coluna já existe (PostgreSQL)
DO $$ 
BEGIN
    -- Tentar adicionar a coluna
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'implantacoes' 
        AND column_name = 'valor_atribuido'
    ) THEN
        ALTER TABLE implantacoes 
        ADD COLUMN valor_atribuido DECIMAL(10,2) DEFAULT 0.00;
        
        RAISE NOTICE 'Coluna "valor_atribuido" adicionada com sucesso à tabela "implantacoes"';
    ELSE
        RAISE NOTICE 'Coluna "valor_atribuido" já existe na tabela "implantacoes"';
    END IF;
END $$;

-- Adicionar comentário na coluna para documentação
COMMENT ON COLUMN implantacoes.valor_atribuido IS 'Valor monetário atribuído à implantação (em reais)';

-- ============================================================================
-- 2. ADICIONAR COLUNA "tag" NA TABELA "comentarios_h"
-- ============================================================================

-- Verificar se a coluna já existe (PostgreSQL)
DO $$ 
BEGIN
    -- Tentar adicionar a coluna
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'comentarios_h' 
        AND column_name = 'tag'
    ) THEN
        ALTER TABLE comentarios_h 
        ADD COLUMN tag VARCHAR(50) DEFAULT NULL;
        
        RAISE NOTICE 'Coluna "tag" adicionada com sucesso à tabela "comentarios_h"';
    ELSE
        RAISE NOTICE 'Coluna "tag" já existe na tabela "comentarios_h"';
    END IF;
END $$;

-- Adicionar comentário na coluna para documentação
COMMENT ON COLUMN comentarios_h.tag IS 'Tag do comentário: "Ação interna", "Reunião" ou "No Show"';

-- ============================================================================
-- 3. ADICIONAR CONSTRAINT PARA VALIDAR TAGS (OPCIONAL MAS RECOMENDADO)
-- ============================================================================

-- Adicionar constraint para garantir que apenas tags válidas sejam inseridas
DO $$ 
BEGIN
    -- Verificar se a constraint já existe
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.table_constraints 
        WHERE constraint_name = 'comentarios_h_tag_check' 
        AND table_name = 'comentarios_h'
    ) THEN
        ALTER TABLE comentarios_h 
        ADD CONSTRAINT comentarios_h_tag_check 
        CHECK (tag IS NULL OR tag IN ('Ação interna', 'Reunião', 'No Show'));
        
        RAISE NOTICE 'Constraint de validação de tags adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Constraint de validação de tags já existe';
    END IF;
END $$;

-- ============================================================================
-- 4. CRIAR ÍNDICES PARA MELHORAR PERFORMANCE (OPCIONAL MAS RECOMENDADO)
-- ============================================================================

-- Índice para consultas por valor atribuído
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_implantacoes_valor_atribuido' AND n.nspname = 'public') THEN
        CREATE INDEX idx_implantacoes_valor_atribuido ON implantacoes(valor_atribuido) WHERE valor_atribuido > 0;
    END IF;
END$$;

COMMENT ON INDEX idx_implantacoes_valor_atribuido IS 'Índice para consultas de implantações com valor atribuído';

-- Índice para consultas por tag de comentário
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_comentarios_h_tag' AND n.nspname = 'public') THEN
        CREATE INDEX idx_comentarios_h_tag ON comentarios_h(tag) WHERE tag IS NOT NULL;
    END IF;
END$$;

COMMENT ON INDEX idx_comentarios_h_tag IS 'Índice para consultas de comentários por tag';

-- ============================================================================
-- 5. ATUALIZAR ESTATÍSTICAS DO BANCO (OPCIONAL MAS RECOMENDADO)
-- ============================================================================

ANALYZE implantacoes;
ANALYZE comentarios_h;

-- ============================================================================
-- 6. VERIFICAÇÃO FINAL
-- ============================================================================

-- Verificar se as colunas foram criadas corretamente
DO $$ 
DECLARE
    v_valor_atribuido_exists BOOLEAN;
    v_tag_exists BOOLEAN;
BEGIN
    -- Verificar coluna valor_atribuido
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'implantacoes' 
        AND column_name = 'valor_atribuido'
    ) INTO v_valor_atribuido_exists;
    
    -- Verificar coluna tag
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'comentarios_h' 
        AND column_name = 'tag'
    ) INTO v_tag_exists;
    
    -- Exibir resultado
    IF v_valor_atribuido_exists AND v_tag_exists THEN
        RAISE NOTICE '✓ SUCESSO: Todas as colunas foram criadas corretamente!';
        RAISE NOTICE '  - implantacoes.valor_atribuido: OK';
        RAISE NOTICE '  - comentarios_h.tag: OK';
    ELSE
        IF NOT v_valor_atribuido_exists THEN
            RAISE WARNING '✗ ERRO: Coluna "valor_atribuido" não foi criada!';
        END IF;
        IF NOT v_tag_exists THEN
            RAISE WARNING '✗ ERRO: Coluna "tag" não foi criada!';
        END IF;
    END IF;
END $$;

-- Confirmar transação
COMMIT;

-- ============================================================================
-- FIM DA MIGRATION
-- ============================================================================

-- Exibir resumo
SELECT 
    'MIGRATION CONCLUÍDA COM SUCESSO!' as status,
    CURRENT_TIMESTAMP as executado_em;

-- Exibir estrutura das colunas criadas
SELECT 
    'implantacoes' as tabela,
    'valor_atribuido' as coluna,
    data_type as tipo,
    column_default as valor_padrao,
    is_nullable as permite_nulo
FROM information_schema.columns 
WHERE table_name = 'implantacoes' 
AND column_name = 'valor_atribuido'

UNION ALL

SELECT 
    'comentarios_h' as tabela,
    'tag' as coluna,
    data_type as tipo,
    column_default as valor_padrao,
    is_nullable as permite_nulo
FROM information_schema.columns 
WHERE table_name = 'comentarios_h' 
AND column_name = 'tag';
