-- ========================================
-- SISTEMA DE PERFIS E PERMISSÕES (RBAC)
-- ========================================

-- 1. Tabela de Perfis de Acesso
CREATE TABLE IF NOT EXISTS perfis_acesso (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL,
    descricao TEXT,
    sistema BOOLEAN DEFAULT FALSE,  -- Perfis do sistema não podem ser excluídos
    ativo BOOLEAN DEFAULT TRUE,
    cor VARCHAR(20) DEFAULT '#667eea',  -- Cor para identificação visual
    icone VARCHAR(50) DEFAULT 'bi-person-badge',  -- Ícone Bootstrap
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100)
);

-- 2. Tabela de Recursos/Funcionalidades
CREATE TABLE IF NOT EXISTS recursos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) UNIQUE NOT NULL,  -- ex: 'dashboard.view'
    nome VARCHAR(255) NOT NULL,           -- ex: 'Visualizar Dashboard'
    descricao TEXT,
    categoria VARCHAR(100) NOT NULL,      -- ex: 'Dashboard', 'Implantações'
    tipo VARCHAR(50) DEFAULT 'acao',      -- 'pagina', 'acao', 'api'
    ordem INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE
);

-- 3. Tabela de Permissões (Many-to-Many)
CREATE TABLE IF NOT EXISTS permissoes (
    id SERIAL PRIMARY KEY,
    perfil_id INTEGER REFERENCES perfis_acesso(id) ON DELETE CASCADE,
    recurso_id INTEGER REFERENCES recursos(id) ON DELETE CASCADE,
    concedida BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(perfil_id, recurso_id)
);

-- 4. Adicionar perfil_id na tabela de usuários (se não existir)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'usuarios' AND column_name = 'perfil_id'
    ) THEN
        ALTER TABLE usuarios ADD COLUMN perfil_id INTEGER REFERENCES perfis_acesso(id);
    END IF;
END $$;

-- ========================================
-- DADOS INICIAIS
-- ========================================

-- Inserir Perfis Padrão
INSERT INTO perfis_acesso (nome, descricao, sistema, cor, icone, criado_por) VALUES
('Administrador', 'Acesso total ao sistema', TRUE, '#dc3545', 'bi-shield-check', 'Sistema'),
('Implantador', 'Gerencia implantações e checklists', TRUE, '#0d6efd', 'bi-person-workspace', 'Sistema'),
('Visualizador', 'Apenas visualização, sem edição', TRUE, '#6c757d', 'bi-eye', 'Sistema')
ON CONFLICT (nome) DO NOTHING;

-- Inserir Recursos do Sistema
INSERT INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
-- Dashboard
('dashboard.view', 'Visualizar Dashboard', 'Acessar página principal do dashboard', 'Dashboard', 'pagina', 1),
('dashboard.export', 'Exportar Relatórios', 'Exportar dados do dashboard', 'Dashboard', 'acao', 2),

-- Implantações
('implantacoes.list', 'Listar Implantações', 'Ver lista de implantações', 'Implantações', 'pagina', 10),
('implantacoes.view', 'Visualizar Detalhes', 'Ver detalhes de uma implantação', 'Implantações', 'acao', 11),
('implantacoes.create', 'Criar Implantação', 'Criar nova implantação', 'Implantações', 'acao', 12),
('implantacoes.edit', 'Editar Implantação', 'Modificar dados da implantação', 'Implantações', 'acao', 13),
('implantacoes.delete', 'Excluir Implantação', 'Remover implantação do sistema', 'Implantações', 'acao', 14),
('implantacoes.finalize', 'Finalizar Implantação', 'Marcar implantação como concluída', 'Implantações', 'acao', 15),

-- Checklist
('checklist.view', 'Visualizar Checklist', 'Ver checklist da implantação', 'Checklist', 'pagina', 20),
('checklist.check', 'Marcar Tarefas', 'Marcar/desmarcar tarefas como concluídas', 'Checklist', 'acao', 21),
('checklist.comment', 'Adicionar Comentários', 'Comentar em tarefas', 'Checklist', 'acao', 22),
('checklist.edit', 'Editar Tarefas', 'Modificar título e descrição de tarefas', 'Checklist', 'acao', 23),
('checklist.delete', 'Excluir Tarefas', 'Remover tarefas do checklist', 'Checklist', 'acao', 24),

-- Planos de Sucesso
('planos.list', 'Listar Planos', 'Ver lista de planos de sucesso', 'Planos de Sucesso', 'pagina', 30),
('planos.view', 'Visualizar Plano', 'Ver detalhes de um plano', 'Planos de Sucesso', 'acao', 31),
('planos.create', 'Criar Plano', 'Criar novo plano de sucesso', 'Planos de Sucesso', 'acao', 32),
('planos.edit', 'Editar Plano', 'Modificar plano existente', 'Planos de Sucesso', 'acao', 33),
('planos.clone', 'Clonar Plano', 'Duplicar plano existente', 'Planos de Sucesso', 'acao', 34),
('planos.delete', 'Excluir Plano', 'Remover plano do sistema', 'Planos de Sucesso', 'acao', 35),
('planos.apply', 'Aplicar Plano', 'Aplicar plano a uma implantação', 'Planos de Sucesso', 'acao', 36),

-- Usuários
('usuarios.list', 'Listar Usuários', 'Ver lista de usuários', 'Usuários', 'pagina', 40),
('usuarios.view', 'Visualizar Usuário', 'Ver detalhes de um usuário', 'Usuários', 'acao', 41),
('usuarios.create', 'Criar Usuário', 'Adicionar novo usuário', 'Usuários', 'acao', 42),
('usuarios.edit', 'Editar Usuário', 'Modificar dados do usuário', 'Usuários', 'acao', 43),
('usuarios.delete', 'Excluir Usuário', 'Remover usuário do sistema', 'Usuários', 'acao', 44),

-- Perfis de Acesso
('perfis.list', 'Listar Perfis', 'Ver lista de perfis de acesso', 'Perfis de Acesso', 'pagina', 50),
('perfis.view', 'Visualizar Perfil', 'Ver detalhes de um perfil', 'Perfis de Acesso', 'acao', 51),
('perfis.create', 'Criar Perfil', 'Criar novo perfil de acesso', 'Perfis de Acesso', 'acao', 52),
('perfis.edit', 'Editar Perfil', 'Modificar perfil existente', 'Perfis de Acesso', 'acao', 53),
('perfis.delete', 'Excluir Perfil', 'Remover perfil do sistema', 'Perfis de Acesso', 'acao', 54),
('perfis.permissions', 'Gerenciar Permissões', 'Definir permissões do perfil', 'Perfis de Acesso', 'acao', 55)

ON CONFLICT (codigo) DO NOTHING;

-- Conceder TODAS as permissões ao Administrador
INSERT INTO permissoes (perfil_id, recurso_id, concedida)
SELECT 
    (SELECT id FROM perfis_acesso WHERE nome = 'Administrador'),
    r.id,
    TRUE
FROM recursos r
ON CONFLICT (perfil_id, recurso_id) DO NOTHING;

-- Conceder permissões ao Implantador (sem gerenciar usuários e perfis)
INSERT INTO permissoes (perfil_id, recurso_id, concedida)
SELECT 
    (SELECT id FROM perfis_acesso WHERE nome = 'Implantador'),
    r.id,
    TRUE
FROM recursos r
WHERE r.categoria NOT IN ('Usuários', 'Perfis de Acesso')
ON CONFLICT (perfil_id, recurso_id) DO NOTHING;

-- Conceder apenas visualização ao Visualizador
INSERT INTO permissoes (perfil_id, recurso_id, concedida)
SELECT 
    (SELECT id FROM perfis_acesso WHERE nome = 'Visualizador'),
    r.id,
    TRUE
FROM recursos r
WHERE r.codigo LIKE '%.view' OR r.codigo LIKE '%.list'
ON CONFLICT (perfil_id, recurso_id) DO NOTHING;

-- ========================================
-- ÍNDICES PARA PERFORMANCE
-- ========================================
CREATE INDEX IF NOT EXISTS idx_permissoes_perfil ON permissoes(perfil_id);
CREATE INDEX IF NOT EXISTS idx_permissoes_recurso ON permissoes(recurso_id);
CREATE INDEX IF NOT EXISTS idx_recursos_categoria ON recursos(categoria);
CREATE INDEX IF NOT EXISTS idx_recursos_codigo ON recursos(codigo);
CREATE INDEX IF NOT EXISTS idx_usuarios_perfil ON usuarios(perfil_id);

-- ========================================
-- VIEWS ÚTEIS
-- ========================================

-- View: Permissões por Perfil
CREATE OR REPLACE VIEW v_permissoes_perfil AS
SELECT 
    p.id as perfil_id,
    p.nome as perfil_nome,
    r.id as recurso_id,
    r.codigo as recurso_codigo,
    r.nome as recurso_nome,
    r.categoria,
    COALESCE(perm.concedida, FALSE) as tem_permissao
FROM perfis_acesso p
CROSS JOIN recursos r
LEFT JOIN permissoes perm ON perm.perfil_id = p.id AND perm.recurso_id = r.id
WHERE p.ativo = TRUE AND r.ativo = TRUE
ORDER BY p.nome, r.categoria, r.ordem;

-- View: Contagem de Permissões por Perfil
CREATE OR REPLACE VIEW v_perfis_resumo AS
SELECT 
    p.id,
    p.nome,
    p.descricao,
    p.cor,
    p.icone,
    p.sistema,
    p.ativo,
    COUNT(DISTINCT perm.recurso_id) as total_permissoes,
    (SELECT COUNT(*) FROM recursos WHERE ativo = TRUE) as total_recursos,
    COUNT(DISTINCT u.id) as total_usuarios
FROM perfis_acesso p
LEFT JOIN permissoes perm ON perm.perfil_id = p.id AND perm.concedida = TRUE
LEFT JOIN usuarios u ON u.perfil_id = p.id
WHERE p.ativo = TRUE
GROUP BY p.id, p.nome, p.descricao, p.cor, p.icone, p.sistema, p.ativo
ORDER BY p.nome;

COMMENT ON TABLE perfis_acesso IS 'Perfis de acesso do sistema (RBAC)';
COMMENT ON TABLE recursos IS 'Recursos/funcionalidades disponíveis no sistema';
COMMENT ON TABLE permissoes IS 'Permissões concedidas a cada perfil';
