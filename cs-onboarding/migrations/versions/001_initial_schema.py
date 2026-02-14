"""initial_schema

Revision ID: 001
Revises: 
Create Date: 2026-02-13 23:50:51.828573

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # Criação das Tabelas (PostgreSQL 9.3 Compatible - No JSONB, No ON CONFLICT)
    # =========================================================================
    
    op.execute("""
    -- 1. Tabela usuarios
    CREATE TABLE IF NOT EXISTS usuarios (
        usuario VARCHAR(255) PRIMARY KEY,
        senha TEXT NOT NULL,
        perfil_id INTEGER -- Será FK para perfis_acesso mais tarde
    );

    -- 2. Tabela perfis_acesso (RBAC)
    CREATE TABLE IF NOT EXISTS perfis_acesso (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(100) UNIQUE NOT NULL,
        descricao TEXT,
        sistema BOOLEAN DEFAULT FALSE,
        ativo BOOLEAN DEFAULT TRUE,
        cor VARCHAR(20) DEFAULT '#667eea',
        icone VARCHAR(50) DEFAULT 'bi-person-badge',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        criado_por VARCHAR(100)
    );

    -- FK usuarios -> perfis_acesso
    DO $$ 
    BEGIN 
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_usuarios_perfil') THEN 
            ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_perfil FOREIGN KEY (perfil_id) REFERENCES perfis_acesso(id); 
        END IF; 
    END $$;

    -- 3. Tabela perfil_usuario (Legado/Complementar)
    CREATE TABLE IF NOT EXISTS perfil_usuario (
        usuario VARCHAR(255) PRIMARY KEY REFERENCES usuarios(usuario),
        nome VARCHAR(255),
        foto_url TEXT,
        cargo VARCHAR(100),
        perfil_acesso VARCHAR(50), -- Mantido para compatibilidade código antigo
        ultimo_check_externo TIMESTAMP
    );

    -- 4. Tabela planos_sucesso
    CREATE TABLE IF NOT EXISTS planos_sucesso (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(255) NOT NULL,
        descricao TEXT,
        criado_por VARCHAR(255) REFERENCES usuarios(usuario),
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        dias_duracao INTEGER,
        ativo INTEGER DEFAULT 1,
        contexto VARCHAR(50) DEFAULT 'onboarding',
        permite_excluir_tarefas INTEGER DEFAULT 0,
        status VARCHAR(50) DEFAULT 'em_andamento',
        processo_id INTEGER -- FK implantacoes definida depois
    );

    -- 5. Tabela implantacoes
    CREATE TABLE IF NOT EXISTS implantacoes (
        id SERIAL PRIMARY KEY,
        usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario),
        nome_empresa VARCHAR(255) NOT NULL,
        tipo VARCHAR(100),
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50) DEFAULT 'nova',
        data_inicio_previsto TIMESTAMP,
        data_inicio_efetivo TIMESTAMP,
        data_finalizacao TIMESTAMP,
        plano_sucesso_id INTEGER REFERENCES planos_sucesso(id),
        data_atribuicao_plano TIMESTAMP,
        data_previsao_termino TIMESTAMP,
        email_responsavel VARCHAR(255),
        responsavel_cliente VARCHAR(255),
        cargo_responsavel VARCHAR(100),
        telefone_responsavel VARCHAR(50),
        data_inicio_producao TIMESTAMP,
        data_final_implantacao TIMESTAMP,
        id_favorecido VARCHAR(100),
        nivel_receita VARCHAR(100),
        chave_oamd VARCHAR(100),
        tela_apoio_link TEXT,
        informacao_infra TEXT,
        seguimento VARCHAR(100),
        tipos_planos TEXT,
        modalidades TEXT,
        horarios_func TEXT,
        formas_pagamento TEXT,
        diaria VARCHAR(50),
        freepass VARCHAR(50),
        alunos_ativos INTEGER,
        sistema_anterior VARCHAR(100),
        importacao VARCHAR(50),
        recorrencia_usa VARCHAR(50),
        boleto VARCHAR(50),
        nota_fiscal VARCHAR(50),
        catraca VARCHAR(50),
        facial VARCHAR(50),
        valor_atribuido VARCHAR(50),
        resp_estrategico_nome VARCHAR(255),
        resp_onb_nome VARCHAR(255),
        resp_estrategico_obs TEXT,
        contatos TEXT,
        motivo_parada TEXT,
        data_cancelamento TIMESTAMP,
        motivo_cancelamento TEXT,
        comprovante_cancelamento_url TEXT,
        definicao_carteira TEXT,
        contexto VARCHAR(50) DEFAULT 'onboarding'
    );
    
    -- FK Circular planos_sucesso -> implantacoes
    DO $$ 
    BEGIN 
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_planos_processo') THEN 
            ALTER TABLE planos_sucesso ADD CONSTRAINT fk_planos_processo FOREIGN KEY (processo_id) REFERENCES implantacoes(id) ON DELETE CASCADE; 
        END IF; 
    END $$;

    -- 6. Tabela checklist_items
    CREATE TABLE IF NOT EXISTS checklist_items (
        id SERIAL PRIMARY KEY,
        parent_id INTEGER REFERENCES checklist_items(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        completed INTEGER NOT NULL DEFAULT 0,
        comment TEXT,
        level INTEGER DEFAULT 0,
        ordem INTEGER DEFAULT 0,
        implantacao_id INTEGER REFERENCES implantacoes(id) ON DELETE CASCADE,
        plano_id INTEGER REFERENCES planos_sucesso(id) ON DELETE CASCADE,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        responsavel VARCHAR(255),
        status VARCHAR(50) DEFAULT 'pendente',
        percentual_conclusao INTEGER DEFAULT 0,
        obrigatoria INTEGER DEFAULT 0,
        tipo_item VARCHAR(50),
        descricao TEXT,
        tag VARCHAR(100),
        data_conclusao TIMESTAMP,
        dias_offset INTEGER,
        dias_uteis BOOLEAN DEFAULT FALSE,
        prazo_inicio DATE,
        prazo_fim DATE,
        previsao_original TIMESTAMP,
        nova_previsao TIMESTAMP,
        CHECK (percentual_conclusao >= 0 AND percentual_conclusao <= 100)
    );

    -- 7. Tabela comentarios_h
    CREATE TABLE IF NOT EXISTS comentarios_h (
        id SERIAL PRIMARY KEY,
        checklist_item_id INTEGER REFERENCES checklist_items(id),
        implantacao_id INTEGER REFERENCES implantacoes(id),
        tarefa_h_id INTEGER,
        subtarefa_h_id INTEGER,
        usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario),
        texto TEXT NOT NULL,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        imagem_url TEXT,
        visibilidade VARCHAR(50) DEFAULT 'interno',
        noshow BOOLEAN DEFAULT FALSE,
        tag VARCHAR(100)
    );

    -- 8. Tabela timeline_log
    CREATE TABLE IF NOT EXISTS timeline_log (
        id SERIAL PRIMARY KEY,
        implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id),
        usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario),
        tipo_evento VARCHAR(100) NOT NULL,
        detalhes TEXT,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 9. Tabela gamificacao_regras
    CREATE TABLE IF NOT EXISTS gamificacao_regras (
        id SERIAL PRIMARY KEY,
        regra_id VARCHAR(100) NOT NULL UNIQUE,
        categoria VARCHAR(100) NOT NULL,
        descricao TEXT NOT NULL,
        valor_pontos INTEGER NOT NULL DEFAULT 0,
        tipo_valor VARCHAR(50) DEFAULT 'pontos'
    );

    -- 10. Tabela gamificacao_metricas_mensais
    CREATE TABLE IF NOT EXISTS gamificacao_metricas_mensais (
        id SERIAL PRIMARY KEY,
        usuario_cs VARCHAR(255) NOT NULL REFERENCES usuarios(usuario),
        mes INTEGER NOT NULL,
        ano INTEGER NOT NULL,
        impl_finalizadas INTEGER DEFAULT 0,
        tma_dias REAL DEFAULT 0,
        nota_qualidade REAL DEFAULT 0,
        assiduidade REAL DEFAULT 0,
        planos_sucesso_pct REAL DEFAULT 0,
        reclamacoes INTEGER DEFAULT 0,
        perda_prazo INTEGER DEFAULT 0,
        pontos_totais INTEGER DEFAULT 0,
        UNIQUE(usuario_cs, mes, ano)
    );

    -- 11. Tabela smtp_settings
    CREATE TABLE IF NOT EXISTS smtp_settings (
        id SERIAL PRIMARY KEY,
        usuario_email VARCHAR(255) UNIQUE NOT NULL,
        host VARCHAR(255) NOT NULL,
        port INTEGER NOT NULL,
        "user" VARCHAR(255),
        password TEXT, -- Hash
        use_tls BOOLEAN DEFAULT TRUE,
        use_ssl BOOLEAN DEFAULT FALSE,
        ativo BOOLEAN DEFAULT TRUE
    );

    -- 12. Tabelas de Configuração Auxiliares
    CREATE TABLE IF NOT EXISTS tags_sistema (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(100) NOT NULL,
        icone VARCHAR(50) DEFAULT '',
        cor_badge VARCHAR(30) DEFAULT '#6c757d',
        ordem INTEGER DEFAULT 0,
        tipo VARCHAR(20) DEFAULT 'ambos',
        ativo INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS status_implantacao (
        id SERIAL PRIMARY KEY,
        codigo VARCHAR(50) NOT NULL UNIQUE,
        nome VARCHAR(100) NOT NULL,
        cor VARCHAR(30) DEFAULT '#6c757d',
        ordem INTEGER DEFAULT 0,
        ativo INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS niveis_atendimento (
        id SERIAL PRIMARY KEY,
        codigo VARCHAR(50) NOT NULL UNIQUE,
        descricao VARCHAR(255) NOT NULL,
        ordem INTEGER DEFAULT 0,
        ativo INTEGER DEFAULT 1
    );
    
    CREATE TABLE IF NOT EXISTS tipos_evento (
        id SERIAL PRIMARY KEY,
        codigo VARCHAR(50) NOT NULL UNIQUE,
        nome VARCHAR(100) NOT NULL,
        icone VARCHAR(50) DEFAULT '',
        cor VARCHAR(30) DEFAULT '#6c757d',
        ativo INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS motivos_parada (
        id SERIAL PRIMARY KEY,
        descricao VARCHAR(255) NOT NULL,
        ativo INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS motivos_cancelamento (
        id SERIAL PRIMARY KEY,
        descricao VARCHAR(255) NOT NULL,
        ativo INTEGER DEFAULT 1
    );

    -- 13. Tabela recursos (RBAC)
    CREATE TABLE IF NOT EXISTS recursos (
        id SERIAL PRIMARY KEY,
        codigo VARCHAR(100) UNIQUE NOT NULL,
        nome VARCHAR(255) NOT NULL,
        descricao TEXT,
        categoria VARCHAR(100) NOT NULL,
        tipo VARCHAR(50) DEFAULT 'acao',
        ordem INTEGER DEFAULT 0,
        ativo BOOLEAN DEFAULT TRUE
    );

    -- 14. Tabela permissoes (RBAC)
    CREATE TABLE IF NOT EXISTS permissoes (
        id SERIAL PRIMARY KEY,
        perfil_id INTEGER REFERENCES perfis_acesso(id) ON DELETE CASCADE,
        recurso_id INTEGER REFERENCES recursos(id) ON DELETE CASCADE,
        concedida BOOLEAN DEFAULT TRUE,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(perfil_id, recurso_id)
    );
    
    -- 15. Tabela implantacao_jira_links (Compatível PG 9.3)
    CREATE TABLE IF NOT EXISTS implantacao_jira_links (
        id SERIAL PRIMARY KEY,
        implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
        jira_key VARCHAR(20) NOT NULL,
        data_vinculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        vinculado_por TEXT,
        UNIQUE(implantacao_id, jira_key)
    );

    -- 16. Tabela avisos_implantacao
    CREATE TABLE IF NOT EXISTS avisos_implantacao (
        id SERIAL PRIMARY KEY,
        implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
        tipo VARCHAR(20) DEFAULT 'info',
        titulo VARCHAR(255) NOT NULL,
        mensagem TEXT NOT NULL,
        criado_por VARCHAR(255) NOT NULL,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- 17. Tabelas Google Tokens
    CREATE TABLE IF NOT EXISTS google_tokens (
        id SERIAL PRIMARY KEY,
        usuario VARCHAR(255) UNIQUE NOT NULL,
        access_token TEXT,
        refresh_token TEXT,
        token_type VARCHAR(50),
        expires_at TIMESTAMP,
        scopes TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 18. Tabelas Checklist Finalização
    CREATE TABLE IF NOT EXISTS checklist_finalizacao_templates (
        id SERIAL PRIMARY KEY,
        titulo VARCHAR(500) NOT NULL,
        descricao TEXT,
        obrigatorio BOOLEAN DEFAULT FALSE,
        ordem INTEGER DEFAULT 0,
        ativo BOOLEAN DEFAULT TRUE,
        requer_evidencia BOOLEAN DEFAULT FALSE,
        tipo_evidencia VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS checklist_finalizacao_items (
        id SERIAL PRIMARY KEY,
        implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
        template_id INTEGER REFERENCES checklist_finalizacao_templates(id) ON DELETE SET NULL,
        titulo VARCHAR(500) NOT NULL,
        descricao TEXT,
        obrigatorio BOOLEAN DEFAULT FALSE,
        concluido BOOLEAN DEFAULT FALSE,
        data_conclusao TIMESTAMP,
        usuario_conclusao VARCHAR(200),
        evidencia_tipo VARCHAR(50),
        evidencia_conteudo TEXT,
        evidencia_url VARCHAR(1000),
        observacoes TEXT,
        ordem INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- 19. Tabela audit_logs (Log Auditoria - JSON compatible)
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        user_email VARCHAR(255),
        action VARCHAR(50) NOT NULL,
        target_type VARCHAR(50),
        target_id VARCHAR(50),
        changes JSON, -- PG 9.3 has JSON
        metadata JSON,
        ip_address VARCHAR(45),
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ========================================
    # ÍNDICES
    -- ========================================
    CREATE INDEX IF NOT EXISTS idx_permissoes_perfil ON permissoes(perfil_id);
    CREATE INDEX IF NOT EXISTS idx_permissoes_recurso ON permissoes(recurso_id);
    CREATE INDEX IF NOT EXISTS idx_recursos_categoria ON recursos(categoria);
    CREATE INDEX IF NOT EXISTS idx_recursos_codigo ON recursos(codigo);
    
    CREATE INDEX IF NOT EXISTS idx_checklist_items_implantacao_id ON checklist_items (implantacao_id);
    CREATE INDEX IF NOT EXISTS idx_checklist_items_parent_id ON checklist_items (parent_id);
    CREATE INDEX IF NOT EXISTS idx_checklist_items_completed ON checklist_items (completed);
    
    CREATE INDEX IF NOT EXISTS idx_comentarios_h_checklist_item_id ON comentarios_h (checklist_item_id);
    CREATE INDEX IF NOT EXISTS idx_comentarios_h_implantacao_id ON comentarios_h (implantacao_id);
    
    CREATE INDEX IF NOT EXISTS idx_timeline_log_implantacao_id ON timeline_log (implantacao_id);
    
    CREATE INDEX IF NOT EXISTS idx_audit_user_email ON audit_logs(user_email);
    CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
    CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_logs(target_type, target_id);

    CREATE INDEX IF NOT EXISTS idx_checklist_fin_items_impl ON checklist_finalizacao_items(implantacao_id);
    
    -- ========================================
    # DADOS DE SEED (Idempotent)
    -- ========================================
    
    -- Perfis
    INSERT INTO perfis_acesso (nome, descricao, sistema, cor, icone, criado_por)
    SELECT 'Administrador', 'Acesso total ao sistema', TRUE, '#dc3545', 'bi-shield-check', 'Sistema'
    WHERE NOT EXISTS (SELECT 1 FROM perfis_acesso WHERE nome = 'Administrador');

    INSERT INTO perfis_acesso (nome, descricao, sistema, cor, icone, criado_por)
    SELECT 'Implantador', 'Gerencia implantações e checklists', TRUE, '#0d6efd', 'bi-person-workspace', 'Sistema'
    WHERE NOT EXISTS (SELECT 1 FROM perfis_acesso WHERE nome = 'Implantador');

    INSERT INTO perfis_acesso (nome, descricao, sistema, cor, icone, criado_por)
    SELECT 'Visualizador', 'Apenas visualização, sem edição', TRUE, '#6c757d', 'bi-eye', 'Sistema'
    WHERE NOT EXISTS (SELECT 1 FROM perfis_acesso WHERE nome = 'Visualizador');

    -- Recursos Iniciais (Amostra crítica apenas)
    INSERT INTO recursos (codigo, nome, descricao, categoria, tipo, ordem)
    SELECT 'dashboard.view', 'Visualizar Dashboard', 'Acessar página principal', 'Dashboard', 'pagina', 1
    WHERE NOT EXISTS (SELECT 1 FROM recursos WHERE codigo = 'dashboard.view');
    
    -- Tags Sistema
    INSERT INTO tags_sistema (nome, icone, cor_badge, ordem, tipo)
    SELECT 'Ação interna', 'bi-chat-left-dots', '#0d6efd', 1, 'comentario'
    WHERE NOT EXISTS (SELECT 1 FROM tags_sistema WHERE nome = 'Ação interna');
    
    """)


def downgrade():
    op.execute("""
    DROP TABLE IF EXISTS audit_logs CASCADE;
    DROP TABLE IF EXISTS checklist_finalizacao_items CASCADE;
    DROP TABLE IF EXISTS checklist_finalizacao_templates CASCADE;
    DROP TABLE IF EXISTS google_tokens CASCADE;
    DROP TABLE IF EXISTS avisos_implantacao CASCADE;
    DROP TABLE IF EXISTS implantacao_jira_links CASCADE;
    DROP TABLE IF EXISTS permissoes CASCADE;
    DROP TABLE IF EXISTS recursos CASCADE;
    DROP TABLE IF EXISTS motivos_cancelamento CASCADE;
    DROP TABLE IF EXISTS motivos_parada CASCADE;
    DROP TABLE IF EXISTS tipos_evento CASCADE;
    DROP TABLE IF EXISTS niveis_atendimento CASCADE;
    DROP TABLE IF EXISTS status_implantacao CASCADE;
    DROP TABLE IF EXISTS tags_sistema CASCADE;
    DROP TABLE IF EXISTS smtp_settings CASCADE;
    DROP TABLE IF EXISTS gamificacao_metricas_mensais CASCADE;
    DROP TABLE IF EXISTS gamificacao_regras CASCADE;
    DROP TABLE IF EXISTS timeline_log CASCADE;
    DROP TABLE IF EXISTS comentarios_h CASCADE;
    DROP TABLE IF EXISTS checklist_items CASCADE;
    DROP TABLE IF EXISTS implantacoes CASCADE;
    DROP TABLE IF EXISTS planos_sucesso CASCADE;
    DROP TABLE IF EXISTS perfil_usuario CASCADE;
    DROP TABLE IF EXISTS usuarios CASCADE;
    DROP TABLE IF EXISTS perfis_acesso CASCADE;
    """)
