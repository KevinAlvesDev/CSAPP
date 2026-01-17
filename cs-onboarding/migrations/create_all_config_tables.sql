-- ============================================
-- Migração Completa: Criar Todas as Tabelas de Configuração
-- Corrige Bugs #3, #9-14 - Dados Hardcoded
-- ============================================

-- ============================================
-- 1. TABELA DE TAGS DO SISTEMA
-- ============================================

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

-- Popular com tags atuais
INSERT INTO tags_sistema (nome, icone, cor_badge, ordem, tipo) VALUES
('Ação interna', 'bi-briefcase', 'bg-primary', 1, 'ambos'),
('Reunião', 'bi-calendar-event', 'bg-danger', 2, 'ambos'),
('No Show', 'bi-calendar-x', 'bg-warning text-dark', 3, 'comentario'),
('Simples registro', 'bi-pencil-square', 'bg-secondary', 4, 'comentario'),
('Cliente', 'bi-person-badge', 'bg-info', 5, 'tarefa'),
('Rede', 'bi-diagram-3', 'bg-success', 6, 'tarefa')
ON CONFLICT (nome) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_tags_sistema_tipo ON tags_sistema(tipo);
CREATE INDEX IF NOT EXISTS idx_tags_sistema_ativo ON tags_sistema(ativo);
CREATE INDEX IF NOT EXISTS idx_tags_sistema_ordem ON tags_sistema(ordem);

-- ============================================
-- 2. TABELA DE STATUS DE IMPLANTAÇÃO
-- ============================================

CREATE TABLE IF NOT EXISTS status_implantacao (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nome VARCHAR(100) NOT NULL,
    cor VARCHAR(20) DEFAULT '#6c757d',
    icone VARCHAR(50) DEFAULT 'bi-circle',
    ordem INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO status_implantacao (codigo, nome, cor, icone, ordem) VALUES
('nova', 'Nova', '#0d6efd', 'bi-plus-circle', 1),
('andamento', 'Em Andamento', '#ffc107', 'bi-arrow-repeat', 2),
('futura', 'Futura', '#6c757d', 'bi-calendar-plus', 3),
('parada', 'Parada', '#fd7e14', 'bi-pause-circle', 4),
('sem_previsao', 'Sem Previsão', '#dc3545', 'bi-question-circle', 5),
('atrasada', 'Atrasada', '#dc3545', 'bi-exclamation-triangle', 6),
('finalizada', 'Finalizada', '#198754', 'bi-check-circle', 7),
('cancelada', 'Cancelada', '#6c757d', 'bi-x-circle', 8)
ON CONFLICT (codigo) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_status_implantacao_ativo ON status_implantacao(ativo);
CREATE INDEX IF NOT EXISTS idx_status_implantacao_ordem ON status_implantacao(ordem);

-- ============================================
-- 3. TABELA DE CARTEIRAS/EQUIPES
-- ============================================

CREATE TABLE IF NOT EXISTS carteiras (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL UNIQUE,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    cor VARCHAR(20) DEFAULT '#667eea',
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO carteiras (codigo, nome, descricao, cor) VALUES
('M1', 'Carteira M1', 'Equipe M1', '#0d6efd'),
('MJ', 'Carteira MJ', 'Equipe MJ', '#6610f2'),
('M5', 'Carteira M5', 'Equipe M5', '#6f42c1'),
('GC', 'Grandes Contas', 'Equipe de Grandes Contas', '#d63384'),
('PAY', 'Payment', 'Equipe Payment', '#dc3545'),
('TW', 'Totalpass/Wellhub', 'Equipe Totalpass e Wellhub', '#fd7e14')
ON CONFLICT (codigo) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_carteiras_ativo ON carteiras(ativo);

-- ============================================
-- 4. TABELA DE NÍVEIS DE ATENDIMENTO
-- ============================================

CREATE TABLE IF NOT EXISTS niveis_atendimento (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL UNIQUE,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    ordem INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO niveis_atendimento (codigo, nome, descricao, ordem) VALUES
('CB', 'Contas Base', 'Atendimento padrão para contas base', 1),
('N1', 'Nível 1', 'Atendimento prioritário nível 1', 2),
('N2', 'Nível 2', 'Atendimento prioritário nível 2', 3),
('VIP', 'VIP', 'Atendimento VIP para grandes contas', 4)
ON CONFLICT (codigo) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_niveis_atendimento_ativo ON niveis_atendimento(ativo);

-- ============================================
-- 5. TABELA DE TIPOS DE EVENTO (TIMELINE)
-- ============================================

CREATE TABLE IF NOT EXISTS tipos_evento (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nome VARCHAR(100) NOT NULL,
    icone VARCHAR(50) DEFAULT 'bi-circle',
    cor VARCHAR(20) DEFAULT '#6c757d',
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO tipos_evento (codigo, nome, icone, cor) VALUES
('criacao', 'Criação', 'bi-plus-circle', '#0d6efd'),
('tarefa_alterada', 'Tarefa Alterada', 'bi-check-square', '#198754'),
('responsavel_alterado', 'Responsável Alterado', 'bi-person', '#ffc107'),
('prazo_alterado', 'Prazo Alterado', 'bi-calendar', '#fd7e14'),
('comentario_adicionado', 'Comentário Adicionado', 'bi-chat-left-text', '#0dcaf0'),
('status_alterado', 'Status Alterado', 'bi-arrow-repeat', '#6610f2'),
('plano_aplicado', 'Plano Aplicado', 'bi-clipboard-check', '#d63384'),
('finalizacao', 'Finalização', 'bi-flag', '#198754'),
('cancelamento', 'Cancelamento', 'bi-x-circle', '#dc3545'),
('pausa', 'Pausa', 'bi-pause-circle', '#fd7e14'),
('retomada', 'Retomada', 'bi-play-circle', '#198754'),
('aviso_criado', 'Aviso Criado', 'bi-exclamation-triangle', '#ffc107'),
('jira_vinculado', 'Jira Vinculado', 'bi-link-45deg', '#0dcaf0')
ON CONFLICT (codigo) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_tipos_evento_ativo ON tipos_evento(ativo);

-- ============================================
-- 6. TABELA DE MÓDULOS DO SISTEMA
-- ============================================

CREATE TABLE IF NOT EXISTS modulos_sistema (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    icone VARCHAR(50) DEFAULT 'bi-puzzle',
    categoria VARCHAR(50),
    ativo BOOLEAN DEFAULT true,
    ordem INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO modulos_sistema (codigo, nome, descricao, icone, categoria, ordem) VALUES
('nota_fiscal', 'Nota Fiscal', 'Módulo de emissão de notas fiscais', 'bi-file-earmark-text', 'Financeiro', 1),
('vendas_online', 'Vendas Online', 'Módulo de vendas pela internet', 'bi-cart', 'Vendas', 2),
('app_treino', 'App de Treino', 'Aplicativo mobile para treinos', 'bi-phone', 'Mobile', 3),
('recorrencia', 'Recorrência', 'Módulo de pagamentos recorrentes', 'bi-arrow-repeat', 'Financeiro', 4),
('catraca', 'Catraca', 'Controle de acesso por catraca', 'bi-door-open', 'Acesso', 5),
('facial', 'Reconhecimento Facial', 'Controle de acesso por reconhecimento facial', 'bi-person-badge', 'Acesso', 6),
('boleto', 'Boleto Bancário', 'Geração de boletos bancários', 'bi-file-earmark-bar-graph', 'Financeiro', 7),
('pix', 'PIX', 'Pagamentos via PIX', 'bi-qr-code', 'Financeiro', 8),
('cartao', 'Cartão de Crédito', 'Pagamentos com cartão', 'bi-credit-card', 'Financeiro', 9),
('wellhub', 'Wellhub', 'Integração com Wellhub (Gympass)', 'bi-heart-pulse', 'Integrações', 10),
('totalpass', 'Totalpass', 'Integração com Totalpass', 'bi-ticket-perforated', 'Integrações', 11)
ON CONFLICT (codigo) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_modulos_sistema_ativo ON modulos_sistema(ativo);
CREATE INDEX IF NOT EXISTS idx_modulos_sistema_categoria ON modulos_sistema(categoria);

-- ============================================
-- 7. TABELA DE MOTIVOS DE PARADA
-- ============================================

CREATE TABLE IF NOT EXISTS motivos_parada (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(255) NOT NULL UNIQUE,
    categoria VARCHAR(50),
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO motivos_parada (descricao, categoria) VALUES
('Aguardando resposta do cliente', 'Cliente'),
('Aguardando documentação', 'Documentação'),
('Aguardando aprovação interna', 'Interno'),
('Problemas técnicos', 'Técnico'),
('Falta de recursos', 'Recursos'),
('Dependência de terceiros', 'Externo'),
('Aguardando pagamento', 'Financeiro'),
('Feriado/Recesso', 'Temporal'),
('Cliente solicitou pausa', 'Cliente')
ON CONFLICT (descricao) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_motivos_parada_ativo ON motivos_parada(ativo);

-- ============================================
-- 8. TABELA DE MOTIVOS DE CANCELAMENTO
-- ============================================

CREATE TABLE IF NOT EXISTS motivos_cancelamento (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(255) NOT NULL UNIQUE,
    categoria VARCHAR(50),
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO motivos_cancelamento (descricao, categoria) VALUES
('Cliente desistiu', 'Cliente'),
('Falta de pagamento', 'Financeiro'),
('Problemas contratuais', 'Contratual'),
('Cliente fechou o negócio', 'Cliente'),
('Não atende requisitos técnicos', 'Técnico'),
('Migrou para concorrente', 'Mercado'),
('Insatisfação com serviço', 'Qualidade'),
('Mudança de estratégia do cliente', 'Cliente'),
('Outros motivos', 'Outros')
ON CONFLICT (descricao) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_motivos_cancelamento_ativo ON motivos_cancelamento(ativo);

-- ============================================
-- 9. ADICIONAR TIMESTAMPS EM TABELAS HISTORY
-- ============================================

-- Adicionar changed_at nas tabelas de histórico
ALTER TABLE checklist_prazos_history 
ADD COLUMN IF NOT EXISTS changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE checklist_responsavel_history 
ADD COLUMN IF NOT EXISTS changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE checklist_status_history 
ADD COLUMN IF NOT EXISTS changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- ============================================
-- 10. COMENTÁRIOS DE DOCUMENTAÇÃO
-- ============================================

COMMENT ON TABLE tags_sistema IS 'Tags dinâmicas do sistema para comentários e tarefas';
COMMENT ON TABLE status_implantacao IS 'Status possíveis para implantações';
COMMENT ON TABLE carteiras IS 'Carteiras/Equipes de atendimento';
COMMENT ON TABLE niveis_atendimento IS 'Níveis de prioridade de atendimento';
COMMENT ON TABLE tipos_evento IS 'Tipos de eventos para timeline';
COMMENT ON TABLE modulos_sistema IS 'Módulos disponíveis no sistema';
COMMENT ON TABLE motivos_parada IS 'Motivos para parada de implantação';
COMMENT ON TABLE motivos_cancelamento IS 'Motivos para cancelamento de implantação';

-- ============================================
-- FIM DA MIGRAÇÃO
-- ============================================

-- Verificar tabelas criadas
SELECT 
    tablename, 
    schemaname 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN (
    'tags_sistema',
    'status_implantacao',
    'carteiras',
    'niveis_atendimento',
    'tipos_evento',
    'modulos_sistema',
    'motivos_parada',
    'motivos_cancelamento'
)
ORDER BY tablename;
