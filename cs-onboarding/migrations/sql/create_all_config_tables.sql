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

INSERT INTO status_implantacao (codigo, nome, cor, icone, ordem)
SELECT 'nova', 'Nova', '#0d6efd', 'bi-plus-circle', 1
WHERE NOT EXISTS (SELECT 1 FROM status_implantacao WHERE codigo = 'nova');

INSERT INTO status_implantacao (codigo, nome, cor, icone, ordem)
SELECT 'andamento', 'Em Andamento', '#ffc107', 'bi-arrow-repeat', 2
WHERE NOT EXISTS (SELECT 1 FROM status_implantacao WHERE codigo = 'andamento');

INSERT INTO status_implantacao (codigo, nome, cor, icone, ordem)
SELECT 'futura', 'Futura', '#6c757d', 'bi-calendar-plus', 3
WHERE NOT EXISTS (SELECT 1 FROM status_implantacao WHERE codigo = 'futura');

INSERT INTO status_implantacao (codigo, nome, cor, icone, ordem)
SELECT 'parada', 'Parada', '#fd7e14', 'bi-pause-circle', 4
WHERE NOT EXISTS (SELECT 1 FROM status_implantacao WHERE codigo = 'parada');

INSERT INTO status_implantacao (codigo, nome, cor, icone, ordem)
SELECT 'sem_previsao', 'Sem Previsão', '#dc3545', 'bi-question-circle', 5
WHERE NOT EXISTS (SELECT 1 FROM status_implantacao WHERE codigo = 'sem_previsao');

INSERT INTO status_implantacao (codigo, nome, cor, icone, ordem)
SELECT 'atrasada', 'Atrasada', '#dc3545', 'bi-exclamation-triangle', 6
WHERE NOT EXISTS (SELECT 1 FROM status_implantacao WHERE codigo = 'atrasada');

INSERT INTO status_implantacao (codigo, nome, cor, icone, ordem)
SELECT 'finalizada', 'Finalizada', '#198754', 'bi-check-circle', 7
WHERE NOT EXISTS (SELECT 1 FROM status_implantacao WHERE codigo = 'finalizada');

INSERT INTO status_implantacao (codigo, nome, cor, icone, ordem)
SELECT 'cancelada', 'Cancelada', '#6c757d', 'bi-x-circle', 8
WHERE NOT EXISTS (SELECT 1 FROM status_implantacao WHERE codigo = 'cancelada');

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_status_implantacao_ativo' AND n.nspname = 'public') THEN
        CREATE INDEX idx_status_implantacao_ativo ON status_implantacao(ativo);
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_status_implantacao_ordem' AND n.nspname = 'public') THEN
        CREATE INDEX idx_status_implantacao_ordem ON status_implantacao(ordem);
    END IF;
END$$;

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

INSERT INTO carteiras (codigo, nome, descricao, cor)
SELECT 'M1', 'Carteira M1', 'Equipe M1', '#0d6efd'
WHERE NOT EXISTS (SELECT 1 FROM carteiras WHERE codigo = 'M1');

INSERT INTO carteiras (codigo, nome, descricao, cor)
SELECT 'MJ', 'Carteira MJ', 'Equipe MJ', '#6610f2'
WHERE NOT EXISTS (SELECT 1 FROM carteiras WHERE codigo = 'MJ');

INSERT INTO carteiras (codigo, nome, descricao, cor)
SELECT 'M5', 'Carteira M5', 'Equipe M5', '#6f42c1'
WHERE NOT EXISTS (SELECT 1 FROM carteiras WHERE codigo = 'M5');

INSERT INTO carteiras (codigo, nome, descricao, cor)
SELECT 'GC', 'Grandes Contas', 'Equipe de Grandes Contas', '#d63384'
WHERE NOT EXISTS (SELECT 1 FROM carteiras WHERE codigo = 'GC');

INSERT INTO carteiras (codigo, nome, descricao, cor)
SELECT 'PAY', 'Payment', 'Equipe Payment', '#dc3545'
WHERE NOT EXISTS (SELECT 1 FROM carteiras WHERE codigo = 'PAY');

INSERT INTO carteiras (codigo, nome, descricao, cor)
SELECT 'TW', 'Totalpass/Wellhub', 'Equipe Totalpass e Wellhub', '#fd7e14'
WHERE NOT EXISTS (SELECT 1 FROM carteiras WHERE codigo = 'TW');

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_carteiras_ativo' AND n.nspname = 'public') THEN
        CREATE INDEX idx_carteiras_ativo ON carteiras(ativo);
    END IF;
END$$;

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

INSERT INTO niveis_atendimento (codigo, nome, descricao, ordem)
SELECT 'CB', 'Contas Base', 'Atendimento padrão para contas base', 1
WHERE NOT EXISTS (SELECT 1 FROM niveis_atendimento WHERE codigo = 'CB');

INSERT INTO niveis_atendimento (codigo, nome, descricao, ordem)
SELECT 'N1', 'Nível 1', 'Atendimento prioritário nível 1', 2
WHERE NOT EXISTS (SELECT 1 FROM niveis_atendimento WHERE codigo = 'N1');

INSERT INTO niveis_atendimento (codigo, nome, descricao, ordem)
SELECT 'N2', 'Nível 2', 'Atendimento prioritário nível 2', 3
WHERE NOT EXISTS (SELECT 1 FROM niveis_atendimento WHERE codigo = 'N2');

INSERT INTO niveis_atendimento (codigo, nome, descricao, ordem)
SELECT 'VIP', 'VIP', 'Atendimento VIP para grandes contas', 4
WHERE NOT EXISTS (SELECT 1 FROM niveis_atendimento WHERE codigo = 'VIP');

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_niveis_atendimento_ativo' AND n.nspname = 'public') THEN
        CREATE INDEX idx_niveis_atendimento_ativo ON niveis_atendimento(ativo);
    END IF;
END$$;

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

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'criacao', 'Criação', 'bi-plus-circle', '#0d6efd'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'criacao');

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'tarefa_alterada', 'Tarefa Alterada', 'bi-check-square', '#198754'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'tarefa_alterada');

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'responsavel_alterado', 'Responsável Alterado', 'bi-person', '#ffc107'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'responsavel_alterado');

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'prazo_alterado', 'Prazo Alterado', 'bi-calendar', '#fd7e14'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'prazo_alterado');

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'comentario_adicionado', 'Comentário Adicionado', 'bi-chat-left-text', '#0dcaf0'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'comentario_adicionado');

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'status_alterado', 'Status Alterado', 'bi-arrow-repeat', '#6610f2'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'status_alterado');

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'plano_aplicado', 'Plano Aplicado', 'bi-clipboard-check', '#d63384'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'plano_aplicado');

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'finalizacao', 'Finalização', 'bi-flag', '#198754'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'finalizacao');

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'cancelamento', 'Cancelamento', 'bi-x-circle', '#dc3545'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'cancelamento');

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'pausa', 'Pausa', 'bi-pause-circle', '#fd7e14'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'pausa');

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'retomada', 'Retomada', 'bi-play-circle', '#198754'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'retomada');

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'aviso_criado', 'Aviso Criado', 'bi-exclamation-triangle', '#ffc107'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'aviso_criado');

INSERT INTO tipos_evento (codigo, nome, icone, cor)
SELECT 'jira_vinculado', 'Jira Vinculado', 'bi-link-45deg', '#0dcaf0'
WHERE NOT EXISTS (SELECT 1 FROM tipos_evento WHERE codigo = 'jira_vinculado');

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_tipos_evento_ativo' AND n.nspname = 'public') THEN
        CREATE INDEX idx_tipos_evento_ativo ON tipos_evento(ativo);
    END IF;
END$$;

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

INSERT INTO modulos_sistema (codigo, nome, descricao, icone, categoria, ordem)
SELECT 'nota_fiscal', 'Nota Fiscal', 'Módulo de emissão de notas fiscais', 'bi-file-earmark-text', 'Financeiro', 1
WHERE NOT EXISTS (SELECT 1 FROM modulos_sistema WHERE codigo = 'nota_fiscal');

INSERT INTO modulos_sistema (codigo, nome, descricao, icone, categoria, ordem)
SELECT 'vendas_online', 'Vendas Online', 'Módulo de vendas pela internet', 'bi-cart', 'Vendas', 2
WHERE NOT EXISTS (SELECT 1 FROM modulos_sistema WHERE codigo = 'vendas_online');

INSERT INTO modulos_sistema (codigo, nome, descricao, icone, categoria, ordem)
SELECT 'app_treino', 'App de Treino', 'Aplicativo mobile para treinos', 'bi-phone', 'Mobile', 3
WHERE NOT EXISTS (SELECT 1 FROM modulos_sistema WHERE codigo = 'app_treino');

INSERT INTO modulos_sistema (codigo, nome, descricao, icone, categoria, ordem)
SELECT 'recorrencia', 'Recorrência', 'Módulo de pagamentos recorrentes', 'bi-arrow-repeat', 'Financeiro', 4
WHERE NOT EXISTS (SELECT 1 FROM modulos_sistema WHERE codigo = 'recorrencia');

INSERT INTO modulos_sistema (codigo, nome, descricao, icone, categoria, ordem)
SELECT 'catraca', 'Catraca', 'Controle de acesso por catraca', 'bi-door-open', 'Acesso', 5
WHERE NOT EXISTS (SELECT 1 FROM modulos_sistema WHERE codigo = 'catraca');

INSERT INTO modulos_sistema (codigo, nome, descricao, icone, categoria, ordem)
SELECT 'facial', 'Reconhecimento Facial', 'Controle de acesso por reconhecimento facial', 'bi-person-badge', 'Acesso', 6
WHERE NOT EXISTS (SELECT 1 FROM modulos_sistema WHERE codigo = 'facial');

INSERT INTO modulos_sistema (codigo, nome, descricao, icone, categoria, ordem)
SELECT 'boleto', 'Boleto Bancário', 'Geração de boletos bancários', 'bi-file-earmark-bar-graph', 'Financeiro', 7
WHERE NOT EXISTS (SELECT 1 FROM modulos_sistema WHERE codigo = 'boleto');

INSERT INTO modulos_sistema (codigo, nome, descricao, icone, categoria, ordem)
SELECT 'pix', 'PIX', 'Pagamentos via PIX', 'bi-qr-code', 'Financeiro', 8
WHERE NOT EXISTS (SELECT 1 FROM modulos_sistema WHERE codigo = 'pix');

INSERT INTO modulos_sistema (codigo, nome, descricao, icone, categoria, ordem)
SELECT 'cartao', 'Cartão de Crédito', 'Pagamentos com cartão', 'bi-credit-card', 'Financeiro', 9
WHERE NOT EXISTS (SELECT 1 FROM modulos_sistema WHERE codigo = 'cartao');

INSERT INTO modulos_sistema (codigo, nome, descricao, icone, categoria, ordem)
SELECT 'wellhub', 'Wellhub', 'Integração com Wellhub (Gympass)', 'bi-heart-pulse', 'Integrações', 10
WHERE NOT EXISTS (SELECT 1 FROM modulos_sistema WHERE codigo = 'wellhub');

INSERT INTO modulos_sistema (codigo, nome, descricao, icone, categoria, ordem)
SELECT 'totalpass', 'Totalpass', 'Integração com Totalpass', 'bi-ticket-perforated', 'Integrações', 11
WHERE NOT EXISTS (SELECT 1 FROM modulos_sistema WHERE codigo = 'totalpass');

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_modulos_sistema_ativo' AND n.nspname = 'public') THEN
        CREATE INDEX idx_modulos_sistema_ativo ON modulos_sistema(ativo);
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_modulos_sistema_categoria' AND n.nspname = 'public') THEN
        CREATE INDEX idx_modulos_sistema_categoria ON modulos_sistema(categoria);
    END IF;
END$$;

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

INSERT INTO motivos_parada (descricao, categoria)
SELECT 'Aguardando resposta do cliente', 'Cliente'
WHERE NOT EXISTS (SELECT 1 FROM motivos_parada WHERE descricao = 'Aguardando resposta do cliente');

INSERT INTO motivos_parada (descricao, categoria)
SELECT 'Aguardando documentação', 'Documentação'
WHERE NOT EXISTS (SELECT 1 FROM motivos_parada WHERE descricao = 'Aguardando documentação');

INSERT INTO motivos_parada (descricao, categoria)
SELECT 'Aguardando aprovação interna', 'Interno'
WHERE NOT EXISTS (SELECT 1 FROM motivos_parada WHERE descricao = 'Aguardando aprovação interna');

INSERT INTO motivos_parada (descricao, categoria)
SELECT 'Problemas técnicos', 'Técnico'
WHERE NOT EXISTS (SELECT 1 FROM motivos_parada WHERE descricao = 'Problemas técnicos');

INSERT INTO motivos_parada (descricao, categoria)
SELECT 'Falta de recursos', 'Recursos'
WHERE NOT EXISTS (SELECT 1 FROM motivos_parada WHERE descricao = 'Falta de recursos');

INSERT INTO motivos_parada (descricao, categoria)
SELECT 'Dependência de terceiros', 'Externo'
WHERE NOT EXISTS (SELECT 1 FROM motivos_parada WHERE descricao = 'Dependência de terceiros');

INSERT INTO motivos_parada (descricao, categoria)
SELECT 'Aguardando pagamento', 'Financeiro'
WHERE NOT EXISTS (SELECT 1 FROM motivos_parada WHERE descricao = 'Aguardando pagamento');

INSERT INTO motivos_parada (descricao, categoria)
SELECT 'Feriado/Recesso', 'Temporal'
WHERE NOT EXISTS (SELECT 1 FROM motivos_parada WHERE descricao = 'Feriado/Recesso');

INSERT INTO motivos_parada (descricao, categoria)
SELECT 'Cliente solicitou pausa', 'Cliente'
WHERE NOT EXISTS (SELECT 1 FROM motivos_parada WHERE descricao = 'Cliente solicitou pausa');

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_motivos_parada_ativo' AND n.nspname = 'public') THEN
        CREATE INDEX idx_motivos_parada_ativo ON motivos_parada(ativo);
    END IF;
END$$;

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

INSERT INTO motivos_cancelamento (descricao, categoria)
SELECT 'Cliente desistiu', 'Cliente'
WHERE NOT EXISTS (SELECT 1 FROM motivos_cancelamento WHERE descricao = 'Cliente desistiu');

INSERT INTO motivos_cancelamento (descricao, categoria)
SELECT 'Falta de pagamento', 'Financeiro'
WHERE NOT EXISTS (SELECT 1 FROM motivos_cancelamento WHERE descricao = 'Falta de pagamento');

INSERT INTO motivos_cancelamento (descricao, categoria)
SELECT 'Problemas contratuais', 'Contratual'
WHERE NOT EXISTS (SELECT 1 FROM motivos_cancelamento WHERE descricao = 'Problemas contratuais');

INSERT INTO motivos_cancelamento (descricao, categoria)
SELECT 'Cliente fechou o negócio', 'Cliente'
WHERE NOT EXISTS (SELECT 1 FROM motivos_cancelamento WHERE descricao = 'Cliente fechou o negócio');

INSERT INTO motivos_cancelamento (descricao, categoria)
SELECT 'Não atende requisitos técnicos', 'Técnico'
WHERE NOT EXISTS (SELECT 1 FROM motivos_cancelamento WHERE descricao = 'Não atende requisitos técnicos');

INSERT INTO motivos_cancelamento (descricao, categoria)
SELECT 'Migrou para concorrente', 'Mercado'
WHERE NOT EXISTS (SELECT 1 FROM motivos_cancelamento WHERE descricao = 'Migrou para concorrente');

INSERT INTO motivos_cancelamento (descricao, categoria)
SELECT 'Insatisfação com serviço', 'Qualidade'
WHERE NOT EXISTS (SELECT 1 FROM motivos_cancelamento WHERE descricao = 'Insatisfação com serviço');

INSERT INTO motivos_cancelamento (descricao, categoria)
SELECT 'Mudança de estratégia do cliente', 'Cliente'
WHERE NOT EXISTS (SELECT 1 FROM motivos_cancelamento WHERE descricao = 'Mudança de estratégia do cliente');

INSERT INTO motivos_cancelamento (descricao, categoria)
SELECT 'Outros motivos', 'Outros'
WHERE NOT EXISTS (SELECT 1 FROM motivos_cancelamento WHERE descricao = 'Outros motivos');

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_motivos_cancelamento_ativo' AND n.nspname = 'public') THEN
        CREATE INDEX idx_motivos_cancelamento_ativo ON motivos_cancelamento(ativo);
    END IF;
END$$;

-- ============================================
-- 9. ADICIONAR TIMESTAMPS EM TABELAS HISTORY
-- ============================================

-- Adicionar changed_at nas tabelas de histórico
-- Adicionar changed_at nas tabelas de histórico
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'checklist_prazos_history' AND column_name = 'changed_at') THEN
        ALTER TABLE checklist_prazos_history ADD COLUMN changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'checklist_responsavel_history' AND column_name = 'changed_at') THEN
        ALTER TABLE checklist_responsavel_history ADD COLUMN changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'checklist_status_history' AND column_name = 'changed_at') THEN
        ALTER TABLE checklist_status_history ADD COLUMN changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
END$$;

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
