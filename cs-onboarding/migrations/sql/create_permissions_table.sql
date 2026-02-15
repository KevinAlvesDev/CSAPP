-- ============================================
-- Migração: Tabela de Configuração de Permissões
-- Permite personalizar regras de acesso por perfil
-- ============================================

CREATE TABLE IF NOT EXISTS config_permissoes (
    id SERIAL PRIMARY KEY,
    perfil_acesso VARCHAR(50) NOT NULL,
    funcionalidade VARCHAR(100) NOT NULL,
    valor_config JSON DEFAULT '{}',
    ativo BOOLEAN DEFAULT true,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(perfil_acesso, funcionalidade)
);

-- Popular com permissões padrão
-- Admin pode tudo
INSERT INTO config_permissoes (perfil_acesso, funcionalidade, valor_config)
SELECT 'admin', 'comentarios.editar', '{"max_horas": -1, "pode_excluir_outros": true}'
WHERE NOT EXISTS (SELECT 1 FROM config_permissoes WHERE perfil_acesso = 'admin' AND funcionalidade = 'comentarios.editar');

INSERT INTO config_permissoes (perfil_acesso, funcionalidade, valor_config)
SELECT 'gestor', 'comentarios.editar', '{"max_horas": -1, "pode_excluir_outros": true}'
WHERE NOT EXISTS (SELECT 1 FROM config_permissoes WHERE perfil_acesso = 'gestor' AND funcionalidade = 'comentarios.editar');

INSERT INTO config_permissoes (perfil_acesso, funcionalidade, valor_config)
SELECT 'cs', 'comentarios.editar', '{"max_horas": 3, "pode_excluir_outros": false}'
WHERE NOT EXISTS (SELECT 1 FROM config_permissoes WHERE perfil_acesso = 'cs' AND funcionalidade = 'comentarios.editar');

COMMENT ON TABLE config_permissoes IS 'Tabela para armazenar configurações dinâmicas de permissão por perfil';
