-- ========================================
-- SISTEMA DE PERFIS E PERMISSÕES (RBAC)
-- Versão SQLite
-- ========================================

-- 1. Tabela de Perfis de Acesso
CREATE TABLE IF NOT EXISTS perfis_acesso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(100) UNIQUE NOT NULL,
    descricao TEXT,
    sistema BOOLEAN DEFAULT 0,
    ativo BOOLEAN DEFAULT 1,
    cor VARCHAR(20) DEFAULT '#667eea',
    icone VARCHAR(50) DEFAULT 'bi-person-badge',
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100)
);

-- 2. Tabela de Recursos/Funcionalidades
CREATE TABLE IF NOT EXISTS recursos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo VARCHAR(100) UNIQUE NOT NULL,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    categoria VARCHAR(100) NOT NULL,
    tipo VARCHAR(50) DEFAULT 'acao',
    ordem INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT 1
);

-- 3. Tabela de Permissões (Many-to-Many)
CREATE TABLE IF NOT EXISTS permissoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    perfil_id INTEGER REFERENCES perfis_acesso(id) ON DELETE CASCADE,
    recurso_id INTEGER REFERENCES recursos(id) ON DELETE CASCADE,
    concedida BOOLEAN DEFAULT 1,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(perfil_id, recurso_id)
);

-- ========================================
-- DADOS INICIAIS
-- ========================================

-- Inserir Perfis Padrão
INSERT OR IGNORE INTO perfis_acesso (nome, descricao, sistema, cor, icone, criado_por) VALUES
('Administrador', 'Acesso total ao sistema', 1, '#dc3545', 'bi-shield-check', 'Sistema');

INSERT OR IGNORE INTO perfis_acesso (nome, descricao, sistema, cor, icone, criado_por) VALUES
('Implantador', 'Gerencia implantações e checklists', 1, '#0d6efd', 'bi-person-workspace', 'Sistema');

INSERT OR IGNORE INTO perfis_acesso (nome, descricao, sistema, cor, icone, criado_por) VALUES
('Visualizador', 'Apenas visualização, sem edição', 1, '#6c757d', 'bi-eye', 'Sistema');

-- Inserir Recursos do Sistema
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('dashboard.view', 'Visualizar Dashboard', 'Acessar página principal do dashboard', 'Dashboard', 'pagina', 1);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('dashboard.export', 'Exportar Relatórios', 'Exportar dados do dashboard', 'Dashboard', 'acao', 2);

INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('implantacoes.list', 'Listar Implantações', 'Ver lista de implantações', 'Implantações', 'pagina', 10);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('implantacoes.view', 'Visualizar Detalhes', 'Ver detalhes de uma implantação', 'Implantações', 'acao', 11);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('implantacoes.create', 'Criar Implantação', 'Criar nova implantação', 'Implantações', 'acao', 12);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('implantacoes.edit', 'Editar Implantação', 'Modificar dados da implantação', 'Implantações', 'acao', 13);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('implantacoes.delete', 'Excluir Implantação', 'Remover implantação do sistema', 'Implantações', 'acao', 14);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('implantacoes.finalize', 'Finalizar Implantação', 'Marcar implantação como concluída', 'Implantações', 'acao', 15);

INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('checklist.view', 'Visualizar Checklist', 'Ver checklist da implantação', 'Checklist', 'pagina', 20);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('checklist.check', 'Marcar Tarefas', 'Marcar/desmarcar tarefas como concluídas', 'Checklist', 'acao', 21);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('checklist.comment', 'Adicionar Comentários', 'Comentar em tarefas', 'Checklist', 'acao', 22);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('checklist.edit', 'Editar Tarefas', 'Modificar título e descrição de tarefas', 'Checklist', 'acao', 23);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('checklist.delete', 'Excluir Tarefas', 'Remover tarefas do checklist', 'Checklist', 'acao', 24);

INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('planos.list', 'Listar Planos', 'Ver lista de planos de sucesso', 'Planos de Sucesso', 'pagina', 30);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('planos.view', 'Visualizar Plano', 'Ver detalhes de um plano', 'Planos de Sucesso', 'acao', 31);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('planos.create', 'Criar Plano', 'Criar novo plano de sucesso', 'Planos de Sucesso', 'acao', 32);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('planos.edit', 'Editar Plano', 'Modificar plano existente', 'Planos de Sucesso', 'acao', 33);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('planos.clone', 'Clonar Plano', 'Duplicar plano existente', 'Planos de Sucesso', 'acao', 34);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('planos.delete', 'Excluir Plano', 'Remover plano do sistema', 'Planos de Sucesso', 'acao', 35);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('planos.apply', 'Aplicar Plano', 'Aplicar plano a uma implantação', 'Planos de Sucesso', 'acao', 36);

INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('usuarios.list', 'Listar Usuários', 'Ver lista de usuários', 'Usuários', 'pagina', 40);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('usuarios.view', 'Visualizar Usuário', 'Ver detalhes de um usuário', 'Usuários', 'acao', 41);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('usuarios.create', 'Criar Usuário', 'Adicionar novo usuário', 'Usuários', 'acao', 42);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('usuarios.edit', 'Editar Usuário', 'Modificar dados do usuário', 'Usuários', 'acao', 43);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('usuarios.delete', 'Excluir Usuário', 'Remover usuário do sistema', 'Usuários', 'acao', 44);

INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('perfis.list', 'Listar Perfis', 'Ver lista de perfis de acesso', 'Perfis de Acesso', 'pagina', 50);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('perfis.view', 'Visualizar Perfil', 'Ver detalhes de um perfil', 'Perfis de Acesso', 'acao', 51);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('perfis.create', 'Criar Perfil', 'Criar novo perfil de acesso', 'Perfis de Acesso', 'acao', 52);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('perfis.edit', 'Editar Perfil', 'Modificar perfil existente', 'Perfis de Acesso', 'acao', 53);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('perfis.delete', 'Excluir Perfil', 'Remover perfil do sistema', 'Perfis de Acesso', 'acao', 54);
INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
('perfis.permissions', 'Gerenciar Permissões', 'Definir permissões do perfil', 'Perfis de Acesso', 'acao', 55);

-- Conceder TODAS as permissões ao Administrador
INSERT OR IGNORE INTO permissoes (perfil_id, recurso_id, concedida)
SELECT 
    (SELECT id FROM perfis_acesso WHERE nome = 'Administrador'),
    r.id,
    1
FROM recursos r;

-- Conceder permissões ao Implantador (sem gerenciar usuários e perfis)
INSERT OR IGNORE INTO permissoes (perfil_id, recurso_id, concedida)
SELECT 
    (SELECT id FROM perfis_acesso WHERE nome = 'Implantador'),
    r.id,
    1
FROM recursos r
WHERE r.categoria NOT IN ('Usuários', 'Perfis de Acesso');

-- Conceder apenas visualização ao Visualizador
INSERT OR IGNORE INTO permissoes (perfil_id, recurso_id, concedida)
SELECT 
    (SELECT id FROM perfis_acesso WHERE nome = 'Visualizador'),
    r.id,
    1
FROM recursos r
WHERE r.codigo LIKE '%.view' OR r.codigo LIKE '%.list';

-- Índices
CREATE INDEX IF NOT EXISTS idx_permissoes_perfil ON permissoes(perfil_id);
CREATE INDEX IF NOT EXISTS idx_permissoes_recurso ON permissoes(recurso_id);
CREATE INDEX IF NOT EXISTS idx_recursos_categoria ON recursos(categoria);
CREATE INDEX IF NOT EXISTS idx_recursos_codigo ON recursos(codigo);
