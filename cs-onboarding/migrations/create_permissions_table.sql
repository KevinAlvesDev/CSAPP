-- ============================================
-- Migração: Tabela de Configuração de Permissões
-- Permite personalizar regras de acesso por perfil
-- ============================================

CREATE TABLE IF NOT EXISTS config_permissoes (
    id SERIAL PRIMARY KEY,
    perfil_acesso VARCHAR(50) NOT NULL,
    funcionalidade VARCHAR(100) NOT NULL,
    valor_config JSONB DEFAULT '{}',
    ativo BOOLEAN DEFAULT true,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(perfil_acesso, funcionalidade)
);

-- Popular com permissões padrão
-- Admin pode tudo
INSERT INTO config_permissoes (perfil_acesso, funcionalidade, valor_config) VALUES
('admin', 'comentarios.editar', '{"max_horas": -1, "pode_excluir_outros": true}'),
('gestor', 'comentarios.editar', '{"max_horas": -1, "pode_excluir_outros": true}'),
('cs', 'comentarios.editar', '{"max_horas": 3, "pode_excluir_outros": false}')
ON CONFLICT (perfil_acesso, funcionalidade) DO NOTHING;

COMMENT ON TABLE config_permissoes IS 'Tabela para armazenar configurações dinâmicas de permissão por perfil';
