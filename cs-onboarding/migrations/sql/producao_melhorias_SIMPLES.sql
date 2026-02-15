-- ============================================================================
-- MIGRATION SIMPLIFICADA - Produção
-- Data: 2025-12-22
-- ============================================================================
-- IMPORTANTE: FAÇA BACKUP ANTES DE EXECUTAR!
-- ============================================================================

BEGIN;

-- 1. Adicionar coluna valor_atribuido
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'implantacoes' AND column_name = 'valor_atribuido') THEN
        ALTER TABLE implantacoes ADD COLUMN valor_atribuido DECIMAL(10,2) DEFAULT 0.00;
    END IF;
END$$;

-- 2. Adicionar coluna tag
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'comentarios_h' AND column_name = 'tag') THEN
        ALTER TABLE comentarios_h ADD COLUMN tag VARCHAR(50) DEFAULT NULL;
    END IF;
END$$;

-- 3. Adicionar constraint de validação
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'comentarios_h_tag_check' AND table_name = 'comentarios_h') THEN
        ALTER TABLE comentarios_h ADD CONSTRAINT comentarios_h_tag_check CHECK (tag IS NULL OR tag IN ('Ação interna', 'Reunião', 'No Show'));
    END IF;
END$$;

-- 4. Criar índices
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_implantacoes_valor_atribuido' AND n.nspname = 'public') THEN
        CREATE INDEX idx_implantacoes_valor_atribuido ON implantacoes(valor_atribuido) WHERE valor_atribuido > 0;
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_comentarios_h_tag' AND n.nspname = 'public') THEN
        CREATE INDEX idx_comentarios_h_tag ON comentarios_h(tag) WHERE tag IS NOT NULL;
    END IF;
END$$;

COMMIT;

-- Verificação
SELECT 'MIGRATION CONCLUÍDA!' as status;
