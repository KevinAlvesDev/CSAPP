-- Migration: Adicionar 'Simples registro' às tags permitidas de comentários
-- Data: 2026-01-06
-- Descrição: Adiciona nova tag 'Simples registro' ao constraint de tags de comentários

-- Para PostgreSQL
-- Remover constraint antiga
ALTER TABLE comentarios_h DROP CONSTRAINT IF EXISTS comentarios_h_tag_check;

-- Adicionar nova constraint com 'Simples registro'
ALTER TABLE comentarios_h ADD CONSTRAINT comentarios_h_tag_check 
CHECK (tag IS NULL OR tag IN ('Ação interna', 'Reunião', 'No Show', 'Simples registro'));

-- Para SQLite (não suporta ALTER CONSTRAINT, precisa recriar tabela)
-- Comentado pois SQLite não valida constraints em runtime da mesma forma
-- Se necessário, pode ser feito via recreate table

COMMENT ON CONSTRAINT comentarios_h_tag_check ON comentarios_h IS 
'Tags permitidas: Ação interna, Reunião, No Show, Simples registro';
