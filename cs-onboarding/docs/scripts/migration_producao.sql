-- ============================================================
-- MIGRATION: Sincronização do Banco de Produção
-- Data: 2024-12-28
-- Executar no PostgreSQL de produção (Railway)
-- ============================================================

-- ============================================================
-- 1. CRIAR TABELAS FALTANTES
-- ============================================================

-- 1.1 Tabela de Perfis de Acesso
CREATE TABLE IF NOT EXISTS perfis_acesso (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    sistema BOOLEAN DEFAULT FALSE,
    ativo BOOLEAN DEFAULT TRUE,
    cor VARCHAR(20) DEFAULT '#6c757d',
    icone VARCHAR(50) DEFAULT 'bi-person',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100)
);

-- 1.2 Tabela de Recursos do Sistema
CREATE TABLE IF NOT EXISTS recursos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL UNIQUE,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    categoria VARCHAR(100),
    tipo VARCHAR(50) DEFAULT 'acao',
    ordem INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE
);

-- 1.3 Tabela de Permissões (relaciona perfis com recursos)
CREATE TABLE IF NOT EXISTS permissoes (
    id SERIAL PRIMARY KEY,
    perfil_id INTEGER REFERENCES perfis_acesso(id) ON DELETE CASCADE,
    recurso_id INTEGER REFERENCES recursos(id) ON DELETE CASCADE,
    concedida BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(perfil_id, recurso_id)
);

-- 1.4 Tabela Timeline (se não existir)
CREATE TABLE IF NOT EXISTS timeline (
    id SERIAL PRIMARY KEY,
    implantacao_id INTEGER REFERENCES implantacoes(id) ON DELETE CASCADE,
    action TEXT,
    details TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 2. INSERIR DADOS INICIAIS (Perfis e Recursos)
-- ============================================================

-- 2.1 Inserir Perfis de Acesso padrão
INSERT INTO perfis_acesso (nome, descricao, sistema, ativo, cor, icone) VALUES
('Administrador', 'Acesso total ao sistema', TRUE, TRUE, '#dc3545', 'bi-shield-lock'),
('Gerente', 'Acesso gerencial com visualização de todos os implantadores', TRUE, TRUE, '#ffc107', 'bi-people'),
('Implantador', 'Acesso padrão para implantadores', TRUE, TRUE, '#0d6efd', 'bi-person'),
('Visualizador', 'Apenas visualização, sem edição', TRUE, TRUE, '#6c757d', 'bi-eye')
ON CONFLICT (nome) DO NOTHING;

-- 2.2 Inserir Recursos do Sistema
INSERT INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES
-- Dashboard
('dashboard.view', 'Visualizar Dashboard', 'Acesso ao dashboard principal', 'Dashboard', 'visualizacao', 1),
('dashboard.filter', 'Filtrar por Implantador', 'Filtrar implantações por implantador', 'Dashboard', 'acao', 2),

-- Implantações
('implantacao.create', 'Criar Implantação', 'Criar novas implantações', 'Implantações', 'acao', 10),
('implantacao.edit', 'Editar Implantação', 'Editar dados de implantações', 'Implantações', 'acao', 11),
('implantacao.delete', 'Excluir Implantação', 'Excluir implantações', 'Implantações', 'acao', 12),
('implantacao.view_all', 'Ver Todas Implantações', 'Visualizar implantações de todos os usuários', 'Implantações', 'visualizacao', 13),

-- Planos de Sucesso
('plano.create', 'Criar Plano', 'Criar planos de sucesso', 'Planos', 'acao', 20),
('plano.edit', 'Editar Plano', 'Editar planos existentes', 'Planos', 'acao', 21),
('plano.delete', 'Excluir Plano', 'Excluir planos', 'Planos', 'acao', 22),
('plano.clone', 'Clonar Plano', 'Clonar planos existentes', 'Planos', 'acao', 23),

-- Usuários
('usuario.manage', 'Gerenciar Usuários', 'Gerenciar perfis de usuários', 'Usuários', 'admin', 30),
('perfil.manage', 'Gerenciar Perfis', 'Criar e editar perfis de acesso', 'Usuários', 'admin', 31),

-- Analytics
('analytics.view', 'Visualizar Analytics', 'Acesso ao dashboard gerencial', 'Analytics', 'visualizacao', 40),
('gamification.view', 'Visualizar Gamificação', 'Acesso às métricas de gamificação', 'Analytics', 'visualizacao', 41),
('gamification.edit', 'Editar Métricas', 'Editar métricas de gamificação', 'Analytics', 'acao', 42)
ON CONFLICT (codigo) DO NOTHING;

-- 2.3 Atribuir permissões padrão aos perfis
-- Administrador: tudo
INSERT INTO permissoes (perfil_id, recurso_id, concedida)
SELECT p.id, r.id, TRUE
FROM perfis_acesso p, recursos r
WHERE p.nome = 'Administrador'
ON CONFLICT (perfil_id, recurso_id) DO NOTHING;

-- Gerente: quase tudo, exceto gerenciar perfis
INSERT INTO permissoes (perfil_id, recurso_id, concedida)
SELECT p.id, r.id, TRUE
FROM perfis_acesso p, recursos r
WHERE p.nome = 'Gerente' AND r.codigo NOT IN ('perfil.manage')
ON CONFLICT (perfil_id, recurso_id) DO NOTHING;

-- Implantador: operações básicas
INSERT INTO permissoes (perfil_id, recurso_id, concedida)
SELECT p.id, r.id, TRUE
FROM perfis_acesso p, recursos r
WHERE p.nome = 'Implantador' AND r.codigo IN (
    'dashboard.view', 
    'implantacao.create', 
    'implantacao.edit',
    'plano.clone'
)
ON CONFLICT (perfil_id, recurso_id) DO NOTHING;

-- Visualizador: apenas visualização
INSERT INTO permissoes (perfil_id, recurso_id, concedida)
SELECT p.id, r.id, TRUE
FROM perfis_acesso p, recursos r
WHERE p.nome = 'Visualizador' AND r.tipo = 'visualizacao'
ON CONFLICT (perfil_id, recurso_id) DO NOTHING;

-- ============================================================
-- 3. VERIFICAR E CONFIRMAR
-- ============================================================
-- Execute após rodar os comandos acima:
-- SELECT * FROM perfis_acesso;
-- SELECT * FROM recursos;
-- SELECT COUNT(*) FROM permissoes;

-- ============================================================
-- FIM DA MIGRATION
-- ============================================================
