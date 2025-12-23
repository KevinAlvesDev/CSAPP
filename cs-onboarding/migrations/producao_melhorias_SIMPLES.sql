-- ============================================================================
-- MIGRATION SIMPLIFICADA - Produção
-- Data: 2025-12-22
-- ============================================================================
-- IMPORTANTE: FAÇA BACKUP ANTES DE EXECUTAR!
-- ============================================================================

BEGIN;

-- 1. Adicionar coluna valor_atribuido
ALTER TABLE implantacoes 
ADD COLUMN IF NOT EXISTS valor_atribuido DECIMAL(10,2) DEFAULT 0.00;

-- 2. Adicionar coluna tag
ALTER TABLE comentarios_h 
ADD COLUMN IF NOT EXISTS tag VARCHAR(50) DEFAULT NULL;

-- 3. Adicionar constraint de validação
ALTER TABLE comentarios_h 
ADD CONSTRAINT comentarios_h_tag_check 
CHECK (tag IS NULL OR tag IN ('Ação interna', 'Reunião', 'No Show'));

-- 4. Criar índices
CREATE INDEX IF NOT EXISTS idx_implantacoes_valor_atribuido 
ON implantacoes(valor_atribuido) WHERE valor_atribuido > 0;

CREATE INDEX IF NOT EXISTS idx_comentarios_h_tag 
ON comentarios_h(tag) WHERE tag IS NOT NULL;

COMMIT;

-- Verificação
SELECT 'MIGRATION CONCLUÍDA!' as status;
