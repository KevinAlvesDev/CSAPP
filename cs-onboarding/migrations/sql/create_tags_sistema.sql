-- ============================================
-- Migração: Criar Sistema de Tags Dinâmico
-- Corrige Bug #3 - Tags Hardcoded (Bug Recorrente)
-- ============================================

-- Criar tabela de tags do sistema
CREATE TABLE IF NOT EXISTS tags_sistema (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    icone VARCHAR(50) NOT NULL,
    cor_badge VARCHAR(50) NOT NULL,
    tipo VARCHAR(50) NOT NULL DEFAULT 'comentario',  -- 'comentario', 'tarefa', 'ambos'
    ordem INTEGER NOT NULL DEFAULT 0,
    ativo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Popular com tags atuais em uso no sistema
-- Popular com tags atuais em uso no sistema
INSERT INTO tags_sistema (nome, icone, cor_badge, ordem, tipo)
SELECT 'Ação interna', 'bi-briefcase', 'bg-primary', 1, 'ambos'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Ação interna');

INSERT INTO tags_sistema (nome, icone, cor_badge, ordem, tipo)
SELECT 'Reunião', 'bi-calendar-event', 'bg-danger', 2, 'ambos'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Reunião');

INSERT INTO tags_sistema (nome, icone, cor_badge, ordem, tipo)
SELECT 'No Show', 'bi-calendar-x', 'bg-warning text-dark', 3, 'comentario'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'No Show');

INSERT INTO tags_sistema (nome, icone, cor_badge, ordem, tipo)
SELECT 'Simples registro', 'bi-pencil-square', 'bg-secondary', 4, 'comentario'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Simples registro');

INSERT INTO tags_sistema (nome, icone, cor_badge, ordem, tipo)
SELECT 'Cliente', 'bi-person-badge', 'bg-info', 5, 'tarefa'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Cliente');

INSERT INTO tags_sistema (nome, icone, cor_badge, ordem, tipo)
SELECT 'Rede', 'bi-diagram-3', 'bg-success', 6, 'tarefa'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Rede');

-- Criar índices para performance
-- Criar índices para performance
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_tags_sistema_tipo' AND n.nspname = 'public') THEN
        CREATE INDEX idx_tags_sistema_tipo ON tags_sistema(tipo);
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_tags_sistema_ativo' AND n.nspname = 'public') THEN
        CREATE INDEX idx_tags_sistema_ativo ON tags_sistema(ativo);
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_tags_sistema_ordem' AND n.nspname = 'public') THEN
        CREATE INDEX idx_tags_sistema_ordem ON tags_sistema(ordem);
    END IF;
END$$;

-- Comentários para documentação
COMMENT ON TABLE tags_sistema IS 'Tags dinâmicas do sistema para comentários e tarefas';
COMMENT ON COLUMN tags_sistema.tipo IS 'Tipo de tag: comentario, tarefa ou ambos';
COMMENT ON COLUMN tags_sistema.ordem IS 'Ordem de exibição na interface';
COMMENT ON COLUMN tags_sistema.ativo IS 'Se false, tag não aparece para seleção';
