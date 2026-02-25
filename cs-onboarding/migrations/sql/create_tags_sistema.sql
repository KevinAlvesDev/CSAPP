-- ============================================
-- Migracao: Criar Sistema de Tags Dinamico
-- ============================================

CREATE TABLE IF NOT EXISTS tags_sistema (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    tipo VARCHAR(50) NOT NULL DEFAULT 'comentario',
    ordem INTEGER NOT NULL DEFAULT 0,
    ativo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO tags_sistema (nome, ordem, tipo)
SELECT 'Acao interna', 1, 'ambos'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Acao interna');

INSERT INTO tags_sistema (nome, ordem, tipo)
SELECT 'Reuniao', 2, 'ambos'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Reuniao');

INSERT INTO tags_sistema (nome, ordem, tipo)
SELECT 'No Show', 3, 'comentario'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'No Show');

INSERT INTO tags_sistema (nome, ordem, tipo)
SELECT 'Simples registro', 4, 'comentario'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Simples registro');

INSERT INTO tags_sistema (nome, ordem, tipo)
SELECT 'Cliente', 5, 'tarefa'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Cliente');

INSERT INTO tags_sistema (nome, ordem, tipo)
SELECT 'Rede', 6, 'tarefa'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Rede');

INSERT INTO tags_sistema (nome, ordem, tipo)
SELECT 'Visita', 7, 'comentario'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Visita');

INSERT INTO tags_sistema (nome, ordem, tipo)
SELECT 'Live', 8, 'comentario'
WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Live');

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

COMMENT ON TABLE tags_sistema IS 'Tags dinamicas do sistema para comentarios e tarefas';
COMMENT ON COLUMN tags_sistema.tipo IS 'Tipo de tag: comentario, tarefa ou ambos';
COMMENT ON COLUMN tags_sistema.ordem IS 'Ordem de exibicao na interface';
COMMENT ON COLUMN tags_sistema.ativo IS 'Se false, tag nao aparece para selecao';
