-- Migration: Adicionar campo valor_atribuido
-- Data: 2025-12-22
-- Descrição: Adiciona campo para armazenar o valor atribuído à implantação

ALTER TABLE implantacoes 
ADD COLUMN IF NOT EXISTS valor_atribuido DECIMAL(10,2) DEFAULT 0.00;

-- Comentário da coluna
COMMENT ON COLUMN implantacoes.valor_atribuido IS 'Valor em reais atribuído à implantação';
