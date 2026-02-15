"""initial_schema

Revision ID: 000_initial
Revises: 
Create Date: 2026-02-13 23:50:51.828573

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '000_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    # =========================================================================
    # 1. Tabelas Legado (Necessárias para migrations 002-004 funcionarem)
    # =========================================================================
    
    # Fases/Grupos/Tarefas (Estrutura Antiga)
    op.create_table('fases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('nome', sa.String(length=255))
    )

    op.create_table('grupos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('fase_id', sa.Integer(), sa.ForeignKey('fases.id')),
        sa.Column('nome', sa.String(length=255))
    )

    op.create_table('tarefas_h',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('grupo_id', sa.Integer(), sa.ForeignKey('grupos.id')),
        sa.Column('nome', sa.String(length=255))
    )

    op.create_table('subtarefas_h',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tarefa_h_id', sa.Integer(), sa.ForeignKey('tarefas_h.id')),
        sa.Column('nome', sa.String(length=255)),
        sa.Column('concluido', sa.Boolean(), default=False)
        # Notas: colunas 'tag' e 'data_conclusao' são adicionadas na migration 003
    )

    # Planos (Estrutura Antiga)
    op.create_table('planos_fases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('nome', sa.String(length=255))
    )

    op.create_table('planos_grupos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('plano_fase_id', sa.Integer(), sa.ForeignKey('planos_fases.id')),
        sa.Column('nome', sa.String(length=255))
    )

    op.create_table('planos_tarefas',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('plano_grupo_id', sa.Integer(), sa.ForeignKey('planos_grupos.id')),
        sa.Column('nome', sa.String(length=255))
    )

    op.create_table('planos_subtarefas',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('plano_tarefa_id', sa.Integer(), sa.ForeignKey('planos_tarefas.id')),
        sa.Column('nome', sa.String(length=255))
    )

    # =========================================================================
    # 2. Tabelas Core
    # =========================================================================

    op.create_table('perfis_acesso',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('nome', sa.String(length=100), unique=True, nullable=False),
        sa.Column('descricao', sa.Text()),
        sa.Column('sistema', sa.Boolean(), default=False),
        sa.Column('ativo', sa.Boolean(), default=True),
        sa.Column('cor', sa.String(length=20), default='#667eea'),
        sa.Column('icone', sa.String(length=50), default='bi-person-badge'),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('criado_por', sa.String(length=100))
    )

    op.create_table('usuarios',
        sa.Column('usuario', sa.String(length=255), primary_key=True),
        sa.Column('senha', sa.Text(), nullable=False),
        sa.Column('perfil_id', sa.Integer(), sa.ForeignKey('perfis_acesso.id'))
    )

    op.create_table('perfil_usuario',
        sa.Column('usuario', sa.String(length=255), sa.ForeignKey('usuarios.usuario'), primary_key=True),
        sa.Column('nome', sa.String(length=255)),
        sa.Column('foto_url', sa.Text()),
        sa.Column('cargo', sa.String(length=100)),
        sa.Column('perfil_acesso', sa.String(length=50)),
        sa.Column('ultimo_check_externo', sa.DateTime())
    )

    op.create_table('planos_sucesso',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text()),
        sa.Column('criado_por', sa.String(length=255), sa.ForeignKey('usuarios.usuario')),
        sa.Column('data_criacao', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('data_atualizacao', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('dias_duracao', sa.Integer()),
        sa.Column('ativo', sa.Integer(), default=1),
        sa.Column('contexto', sa.String(length=50), default='onboarding'),
        sa.Column('permite_excluir_tarefas', sa.Integer(), default=0),
        sa.Column('status', sa.String(length=50), default='em_andamento'),
        sa.Column('processo_id', sa.Integer()) # FK circular adicionada depois
    )

    op.create_table('implantacoes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('usuario_cs', sa.String(length=255), sa.ForeignKey('usuarios.usuario'), nullable=False),
        sa.Column('nome_empresa', sa.String(length=255), nullable=False),
        sa.Column('tipo', sa.String(length=100)),
        sa.Column('data_criacao', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('status', sa.String(length=50), default='nova'),
        sa.Column('data_inicio_previsto', sa.DateTime()),
        sa.Column('data_inicio_efetivo', sa.DateTime()),
        sa.Column('data_finalizacao', sa.DateTime()),
        sa.Column('plano_sucesso_id', sa.Integer(), sa.ForeignKey('planos_sucesso.id')),
        sa.Column('data_atribuicao_plano', sa.DateTime()),
        sa.Column('data_previsao_termino', sa.DateTime()),
        sa.Column('email_responsavel', sa.String(length=255)),
        sa.Column('responsavel_cliente', sa.String(length=255)),
        sa.Column('cargo_responsavel', sa.String(length=100)),
        sa.Column('telefone_responsavel', sa.String(length=50)),
        sa.Column('data_inicio_producao', sa.DateTime()),
        sa.Column('data_final_implantacao', sa.DateTime()),
        sa.Column('id_favorecido', sa.String(length=100)),
        sa.Column('nivel_receita', sa.String(length=100)),
        sa.Column('chave_oamd', sa.String(length=100)),
        sa.Column('tela_apoio_link', sa.Text()),
        sa.Column('informacao_infra', sa.Text()),
        sa.Column('seguimento', sa.String(length=100)),
        sa.Column('tipos_planos', sa.Text()),
        sa.Column('modalidades', sa.Text()),
        sa.Column('horarios_func', sa.Text()),
        sa.Column('formas_pagamento', sa.Text()),
        sa.Column('diaria', sa.String(length=50)),
        sa.Column('freepass', sa.String(length=50)),
        sa.Column('alunos_ativos', sa.Integer()),
        sa.Column('sistema_anterior', sa.String(length=100)),
        sa.Column('importacao', sa.String(length=50)),
        sa.Column('recorrencia_usa', sa.String(length=50)),
        sa.Column('boleto', sa.String(length=50)),
        sa.Column('nota_fiscal', sa.String(length=50)),
        sa.Column('catraca', sa.String(length=50)),
        sa.Column('facial', sa.String(length=50)),
        sa.Column('valor_atribuido', sa.String(length=50)),
        sa.Column('resp_estrategico_nome', sa.String(length=255)),
        sa.Column('resp_onb_nome', sa.String(length=255)),
        sa.Column('resp_estrategico_obs', sa.Text()),
        sa.Column('contatos', sa.Text()),
        sa.Column('motivo_parada', sa.Text()),
        sa.Column('data_cancelamento', sa.DateTime()),
        sa.Column('motivo_cancelamento', sa.Text()),
        sa.Column('comprovante_cancelamento_url', sa.Text()),
        sa.Column('definicao_carteira', sa.Text()),
        sa.Column('contexto', sa.String(length=50), default='onboarding')
    )

    # FK Circular: planos_sucesso -> implantacoes
    if dialect == 'postgresql':
        op.execute(text("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_planos_processo') THEN ALTER TABLE planos_sucesso ADD CONSTRAINT fk_planos_processo FOREIGN KEY (processo_id) REFERENCES implantacoes(id) ON DELETE CASCADE; END IF; END $$;"))
    
    # Comentários
    op.create_table('comentarios_h',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('implantacao_id', sa.Integer(), sa.ForeignKey('implantacoes.id')),
        sa.Column('tarefa_h_id', sa.Integer()),
        sa.Column('subtarefa_h_id', sa.Integer()),
        sa.Column('usuario_cs', sa.String(length=255), sa.ForeignKey('usuarios.usuario'), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('data_criacao', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('imagem_url', sa.Text()),
        sa.Column('visibilidade', sa.String(length=50), default='interno'),
        sa.Column('noshow', sa.Boolean(), default=False),
        sa.Column('tag', sa.String(length=100))
        # checklist_item_id adicionado na migration 007
    )
    op.create_index('idx_comentarios_h_implantacao_id', 'comentarios_h', ['implantacao_id'])

    # Timeline Log
    op.create_table('timeline_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('implantacao_id', sa.Integer(), sa.ForeignKey('implantacoes.id'), nullable=False),
        sa.Column('usuario_cs', sa.String(length=255), sa.ForeignKey('usuarios.usuario'), nullable=False),
        sa.Column('tipo_evento', sa.String(length=100), nullable=False),
        sa.Column('detalhes', sa.Text()),
        sa.Column('data_criacao', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('idx_timeline_log_implantacao_id', 'timeline_log', ['implantacao_id'])

    # Gamificação
    op.create_table('gamificacao_regras',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('regra_id', sa.String(length=100), unique=True, nullable=False),
        sa.Column('categoria', sa.String(length=100), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=False),
        sa.Column('valor_pontos', sa.Integer(), nullable=False, default=0),
        sa.Column('tipo_valor', sa.String(length=50), default='pontos')
    )

    op.create_table('gamificacao_metricas_mensais',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('usuario_cs', sa.String(length=255), sa.ForeignKey('usuarios.usuario'), nullable=False),
        sa.Column('mes', sa.Integer(), nullable=False),
        sa.Column('ano', sa.Integer(), nullable=False),
        sa.Column('impl_finalizadas', sa.Integer(), default=0),
        sa.Column('tma_dias', sa.Float(), default=0),
        sa.Column('nota_qualidade', sa.Float(), default=0),
        sa.Column('assiduidade', sa.Float(), default=0),
        sa.Column('planos_sucesso_pct', sa.Float(), default=0),
        sa.Column('reclamacoes', sa.Integer(), default=0),
        sa.Column('perda_prazo', sa.Integer(), default=0),
        sa.Column('pontos_totais', sa.Integer(), default=0),
        sa.UniqueConstraint('usuario_cs', 'mes', 'ano', name='uq_gamificacao_metricas_mensais_usuario_mes_ano')
    )

    # Configs
    op.create_table('smtp_settings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('usuario_email', sa.String(length=255), unique=True, nullable=False),
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('user', sa.String(length=255)),
        sa.Column('password', sa.Text()),
        sa.Column('use_tls', sa.Boolean(), default=True),
        sa.Column('use_ssl', sa.Boolean(), default=False),
        sa.Column('ativo', sa.Boolean(), default=True)
    )

    # Tabelas Auxiliares
    op.create_table('tags_sistema',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('icone', sa.String(length=50), default=''),
        sa.Column('cor_badge', sa.String(length=30), default='#6c757d'),
        sa.Column('ordem', sa.Integer(), default=0),
        sa.Column('tipo', sa.String(length=20), default='ambos'),
        sa.Column('ativo', sa.Integer(), default=1)
    )

    op.create_table('status_implantacao',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('codigo', sa.String(length=50), unique=True, nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('cor', sa.String(length=30), default='#6c757d'),
        sa.Column('ordem', sa.Integer(), default=0),
        sa.Column('ativo', sa.Integer(), default=1)
    )

    op.create_table('niveis_atendimento',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('codigo', sa.String(length=50), unique=True, nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=False),
        sa.Column('ordem', sa.Integer(), default=0),
        sa.Column('ativo', sa.Integer(), default=1)
    )

    op.create_table('tipos_evento',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('codigo', sa.String(length=50), unique=True, nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('icone', sa.String(length=50), default=''),
        sa.Column('cor', sa.String(length=30), default='#6c757d'),
        sa.Column('ativo', sa.Integer(), default=1)
    )

    op.create_table('motivos_parada',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('descricao', sa.String(length=255), nullable=False),
        sa.Column('ativo', sa.Integer(), default=1)
    )

    op.create_table('motivos_cancelamento',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('descricao', sa.String(length=255), nullable=False),
        sa.Column('ativo', sa.Integer(), default=1)
    )

    # RBAC
    op.create_table('recursos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('codigo', sa.String(length=100), unique=True, nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text()),
        sa.Column('categoria', sa.String(length=100), nullable=False),
        sa.Column('tipo', sa.String(length=50), default='acao'),
        sa.Column('ordem', sa.Integer(), default=0),
        sa.Column('ativo', sa.Boolean(), default=True)
    )
    op.create_index('idx_recursos_categoria', 'recursos', ['categoria'])
    op.create_index('idx_recursos_codigo', 'recursos', ['codigo'])

    op.create_table('permissoes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('perfil_id', sa.Integer(), sa.ForeignKey('perfis_acesso.id', ondelete='CASCADE')),
        sa.Column('recurso_id', sa.Integer(), sa.ForeignKey('recursos.id', ondelete='CASCADE')),
        sa.Column('concedida', sa.Boolean(), default=True),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('perfil_id', 'recurso_id', name='uq_permissoes_perfil_recurso')
    )
    op.create_index('idx_permissoes_perfil', 'permissoes', ['perfil_id'])
    op.create_index('idx_permissoes_recurso', 'permissoes', ['recurso_id'])

    # Integrações e Avisos
    op.create_table('implantacao_jira_links',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('implantacao_id', sa.Integer(), sa.ForeignKey('implantacoes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('jira_key', sa.String(length=20), nullable=False),
        sa.Column('data_vinculo', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('vinculado_por', sa.Text()),
        sa.UniqueConstraint('implantacao_id', 'jira_key', name='uq_implantacao_jira_links')
    )

    op.create_table('avisos_implantacao',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('implantacao_id', sa.Integer(), sa.ForeignKey('implantacoes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tipo', sa.String(length=20), default='info'),
        sa.Column('titulo', sa.String(length=255), nullable=False),
        sa.Column('mensagem', sa.Text(), nullable=False),
        sa.Column('criado_por', sa.String(length=255), nullable=False),
        sa.Column('data_criacao', sa.DateTime(), server_default=sa.func.now())
    )

    op.create_table('google_tokens',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('usuario', sa.String(length=255), unique=True, nullable=False),
        sa.Column('access_token', sa.Text()),
        sa.Column('refresh_token', sa.Text()),
        sa.Column('token_type', sa.String(length=50)),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('scopes', sa.Text()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now())
    )

    # Checklist Finalização
    op.create_table('checklist_finalizacao_templates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('titulo', sa.String(length=500), nullable=False),
        sa.Column('descricao', sa.Text()),
        sa.Column('obrigatorio', sa.Boolean(), default=False),
        sa.Column('ordem', sa.Integer(), default=0),
        sa.Column('ativo', sa.Boolean(), default=True),
        sa.Column('requer_evidencia', sa.Boolean(), default=False),
        sa.Column('tipo_evidencia', sa.String(length=50)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now())
    )

    op.create_table('checklist_finalizacao_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('implantacao_id', sa.Integer(), sa.ForeignKey('implantacoes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('checklist_finalizacao_templates.id', ondelete='SET NULL')),
        sa.Column('titulo', sa.String(length=500), nullable=False),
        sa.Column('descricao', sa.Text()),
        sa.Column('obrigatorio', sa.Boolean(), default=False),
        sa.Column('concluido', sa.Boolean(), default=False),
        sa.Column('data_conclusao', sa.DateTime()),
        sa.Column('usuario_conclusao', sa.String(length=200)),
        sa.Column('evidencia_tipo', sa.String(length=50)),
        sa.Column('evidencia_conteudo', sa.Text()),
        sa.Column('evidencia_url', sa.String(length=1000)),
        sa.Column('observacoes', sa.Text()),
        sa.Column('ordem', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('idx_checklist_fin_items_impl', 'checklist_finalizacao_items', ['implantacao_id'])

    # Audit Logs
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_email', sa.String(length=255)),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('target_type', sa.String(length=50)),
        sa.Column('target_id', sa.String(length=50)),
        sa.Column('changes', sa.JSON() if dialect == 'postgresql' else sa.Text()),
        sa.Column('metadata', sa.JSON() if dialect == 'postgresql' else sa.Text()),
        sa.Column('ip_address', sa.String(length=45)),
        sa.Column('user_agent', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('idx_audit_user_email', 'audit_logs', ['user_email'])
    op.create_index('idx_audit_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_target', 'audit_logs', ['target_type', 'target_id'])

    # Seeds básicos
    try:
        op.execute(text("INSERT INTO perfis_acesso (nome, descricao, sistema, cor, icone, criado_por) VALUES ('Administrador', 'Acesso total ao sistema', TRUE, '#dc3545', 'bi-shield-check', 'Sistema')"))
        op.execute(text("INSERT INTO perfis_acesso (nome, descricao, sistema, cor, icone, criado_por) VALUES ('Implantador', 'Gerencia implantações e checklists', TRUE, '#0d6efd', 'bi-person-workspace', 'Sistema')"))
        op.execute(text("INSERT INTO perfis_acesso (nome, descricao, sistema, cor, icone, criado_por) VALUES ('Visualizador', 'Apenas visualização, sem edição', TRUE, '#6c757d', 'bi-eye', 'Sistema')"))
        op.execute(text("INSERT INTO recursos (codigo, nome, descricao, categoria, tipo, ordem) VALUES ('dashboard.view', 'Visualizar Dashboard', 'Acessar página principal', 'Dashboard', 'pagina', 1)"))
        op.execute(text("INSERT INTO tags_sistema (nome, icone, cor_badge, ordem, tipo) VALUES ('Ação interna', 'bi-chat-left-dots', '#0d6efd', 1, 'comentario')"))
    except:
        # Ignore seed errors if already exists
        pass


def downgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'postgresql':
        op.execute(text("DROP TABLE IF EXISTS audit_logs CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS checklist_finalizacao_items CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS checklist_finalizacao_templates CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS google_tokens CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS avisos_implantacao CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS implantacao_jira_links CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS permissoes CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS recursos CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS motivos_cancelamento CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS motivos_parada CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS tipos_evento CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS niveis_atendimento CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS status_implantacao CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS tags_sistema CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS smtp_settings CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS gamificacao_metricas_mensais CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS gamificacao_regras CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS timeline_log CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS comentarios_h CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS implantacoes CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS planos_sucesso CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS perfil_usuario CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS usuarios CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS perfis_acesso CASCADE"))
        
        # Tabelas Legado
        op.execute(text("DROP TABLE IF EXISTS planos_subtarefas CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS planos_tarefas CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS planos_grupos CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS planos_fases CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS subtarefas_h CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS tarefas_h CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS grupos CASCADE"))
        op.execute(text("DROP TABLE IF EXISTS fases CASCADE"))
    else:
        # SQLite (No CASCADE support)
        tables = [
            'audit_logs', 'checklist_finalizacao_items', 'checklist_finalizacao_templates',
            'google_tokens', 'avisos_implantacao', 'implantacao_jira_links', 'permissoes',
            'recursos', 'motivos_cancelamento', 'motivos_parada', 'tipos_evento',
            'niveis_atendimento', 'status_implantacao', 'tags_sistema', 'smtp_settings',
            'gamificacao_metricas_mensais', 'gamificacao_regras', 'timeline_log',
            'comentarios_h', 'implantacoes', 'planos_sucesso', 'perfil_usuario',
            'usuarios', 'perfis_acesso',
            'planos_subtarefas', 'planos_tarefas', 'planos_grupos', 'planos_fases',
            'subtarefas_h', 'tarefas_h', 'grupos', 'fases'
        ]
        for table in tables:
            op.execute(text(f"DROP TABLE IF EXISTS {table}"))
