-- Migration: Adicionar campo valor_atribuido
-- Data: 2025-12-22
-- Descrição: Adiciona campo para armazenar o valor atribuído à implantação

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'implantacoes' AND column_name = 'valor_atribuido') THEN
        ALTER TABLE implantacoes ADD COLUMN valor_atribuido DECIMAL(10,2) DEFAULT 0.00;
    END IF;
END$$;

-- Comentário da coluna
COMMENT ON COLUMN implantacoes.valor_atribuido IS 'Valor em reais atribuído à implantação';
