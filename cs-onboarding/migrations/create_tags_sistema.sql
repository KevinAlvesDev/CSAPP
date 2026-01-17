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
INSERT INTO tags_sistema (nome, icone, cor_badge, ordem, tipo) VALUES
('Ação interna', 'bi-briefcase', 'bg-primary', 1, 'ambos'),
('Reunião', 'bi-calendar-event', 'bg-danger', 2, 'ambos'),
('No Show', 'bi-calendar-x', 'bg-warning text-dark', 3, 'comentario'),
('Simples registro', 'bi-pencil-square', 'bg-secondary', 4, 'comentario'),
('Cliente', 'bi-person-badge', 'bg-info', 5, 'tarefa'),
('Rede', 'bi-diagram-3', 'bg-success', 6, 'tarefa')
ON CONFLICT (nome) DO NOTHING;

-- Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_tags_sistema_tipo ON tags_sistema(tipo);
CREATE INDEX IF NOT EXISTS idx_tags_sistema_ativo ON tags_sistema(ativo);
CREATE INDEX IF NOT EXISTS idx_tags_sistema_ordem ON tags_sistema(ordem);

-- Comentários para documentação
COMMENT ON TABLE tags_sistema IS 'Tags dinâmicas do sistema para comentários e tarefas';
COMMENT ON COLUMN tags_sistema.tipo IS 'Tipo de tag: comentario, tarefa ou ambos';
COMMENT ON COLUMN tags_sistema.ordem IS 'Ordem de exibição na interface';
COMMENT ON COLUMN tags_sistema.ativo IS 'Se false, tag não aparece para seleção';
