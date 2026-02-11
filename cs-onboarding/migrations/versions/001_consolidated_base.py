"""
Migration consolidada: Schema base completo (v1.0)

Consolida todas as migrations anteriores (scripts SQL manuais + migrations
no diretório backend/project/database/migrations) em uma única revisão.

Esta migration cria todo o schema do zero quando aplicada em um banco vazio.
Para bancos existentes (produção), ela apenas marca como "aplicada" sem
executar nada (via stamp).

Revision ID: 001_consolidated_base
Revises: (nenhuma)
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "001_consolidated_base"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria o schema base completo."""

    # ──────────────────────────────────────────────
    # TABELA: usuarios
    # ──────────────────────────────────────────────
    op.create_table(
        "usuarios",
        sa.Column("usuario", sa.String(255), primary_key=True),
        sa.Column("senha", sa.String(255), nullable=False),
        sa.Column("ativo", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ──────────────────────────────────────────────
    # TABELA: perfil_usuario
    # ──────────────────────────────────────────────
    op.create_table(
        "perfil_usuario",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("usuario", sa.String(255), sa.ForeignKey("usuarios.usuario"), nullable=False, unique=True),
        sa.Column("nome", sa.String(255)),
        sa.Column("perfil_acesso", sa.String(50)),
        sa.Column("cargo", sa.String(255)),
        sa.Column("foto_url", sa.Text()),
        sa.Column("ultimo_check_externo", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ──────────────────────────────────────────────
    # TABELA: implantacoes
    # ──────────────────────────────────────────────
    op.create_table(
        "implantacoes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome_empresa", sa.String(255), nullable=False),
        sa.Column("usuario_cs", sa.String(255), sa.ForeignKey("usuarios.usuario")),
        sa.Column("status", sa.String(50), default="nova"),
        sa.Column("tipo", sa.String(50), default="onboarding"),
        sa.Column("contexto", sa.String(50)),
        sa.Column("prioridade", sa.String(20)),
        sa.Column("plano_sucesso_id", sa.Integer()),
        sa.Column("data_atribuicao_plano", sa.DateTime()),
        sa.Column("data_previsao_termino", sa.DateTime()),
        sa.Column("data_inicio_efetivo", sa.DateTime()),
        sa.Column("data_finalizacao", sa.DateTime()),
        sa.Column("data_parada", sa.DateTime()),
        sa.Column("motivo_parada", sa.Text()),
        sa.Column("data_cancelamento", sa.DateTime()),
        sa.Column("data_retomada", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        # Campos adicionais de detalhamento da empresa
        sa.Column("cnpj", sa.String(20)),
        sa.Column("razao_social", sa.String(255)),
        sa.Column("nivel_receita", sa.String(50)),
        sa.Column("seguimento", sa.String(100)),
        sa.Column("tipo_plano", sa.String(100)),
        sa.Column("modalidade", sa.String(100)),
        sa.Column("horario_funcionamento", sa.String(100)),
        sa.Column("sistema_anterior", sa.String(100)),
        sa.Column("forma_pagamento", sa.String(100)),
        sa.Column("recorrencia_usada", sa.String(100)),
        sa.Column("observacoes", sa.Text()),
    )

    # Index para consultas frequentes no dashboard
    op.create_index("idx_implantacoes_usuario_cs", "implantacoes", ["usuario_cs"])
    op.create_index("idx_implantacoes_status", "implantacoes", ["status"])
    op.create_index("idx_implantacoes_contexto", "implantacoes", ["contexto"])

    # ──────────────────────────────────────────────
    # TABELA: checklist_items
    # ──────────────────────────────────────────────
    op.create_table(
        "checklist_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("implantacao_id", sa.Integer(), sa.ForeignKey("implantacoes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("checklist_items.id", ondelete="CASCADE")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("tipo_item", sa.String(20), nullable=False),  # fase, grupo, tarefa, subtarefa
        sa.Column("completed", sa.Boolean(), default=False),
        sa.Column("tag", sa.String(100)),
        sa.Column("ordem", sa.Integer(), default=0),
        sa.Column("responsavel", sa.String(255)),
        sa.Column("prazo_inicio", sa.Date()),
        sa.Column("prazo_fim", sa.Date()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Indexes críticos para performance (elimina full-scan)
    op.create_index("idx_checklist_implantacao_id", "checklist_items", ["implantacao_id"])
    op.create_index("idx_checklist_parent_id", "checklist_items", ["parent_id"])
    op.create_index("idx_checklist_tipo_item", "checklist_items", ["tipo_item"])
    op.create_index(
        "idx_checklist_impl_tipo",
        "checklist_items",
        ["implantacao_id", "tipo_item"],
    )

    # ──────────────────────────────────────────────
    # TABELA: checklist_comentarios (comentarios_h)
    # ──────────────────────────────────────────────
    op.create_table(
        "comentarios_h",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("checklist_item_id", sa.Integer(), sa.ForeignKey("checklist_items.id", ondelete="CASCADE")),
        sa.Column("usuario_cs", sa.String(255)),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("tag", sa.String(100)),
        sa.Column("visibilidade", sa.String(20), default="publico"),
        sa.Column("editado", sa.Boolean(), default=False),
        sa.Column("editado_em", sa.DateTime()),
        sa.Column("tarefa_h_id", sa.Integer()),
        sa.Column("subtarefa_h_id", sa.Integer()),
        sa.Column("data_criacao", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("email_enviado", sa.Boolean(), default=False),
        sa.Column("email_enviado_em", sa.DateTime()),
    )

    op.create_index("idx_comentarios_h_item_id", "comentarios_h", ["checklist_item_id"])

    # ──────────────────────────────────────────────
    # TABELA: timeline_logs
    # ──────────────────────────────────────────────
    op.create_table(
        "timeline_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("implantacao_id", sa.Integer(), sa.ForeignKey("implantacoes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usuario", sa.String(255)),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("detalhe", sa.Text()),
        sa.Column("data_criacao", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_index("idx_timeline_implantacao_id", "timeline_logs", ["implantacao_id"])

    # ──────────────────────────────────────────────
    # TABELA: planos_sucesso
    # ──────────────────────────────────────────────
    op.create_table(
        "planos_sucesso",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("descricao", sa.Text()),
        sa.Column("dias_duracao", sa.Integer(), default=30),
        sa.Column("ativo", sa.Boolean(), default=True),
        sa.Column("contexto", sa.String(50)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ──────────────────────────────────────────────
    # TABELA: plano_fases
    # ──────────────────────────────────────────────
    op.create_table(
        "plano_fases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("plano_id", sa.Integer(), sa.ForeignKey("planos_sucesso.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("ordem", sa.Integer(), default=0),
    )

    # ──────────────────────────────────────────────
    # TABELA: plano_acoes
    # ──────────────────────────────────────────────
    op.create_table(
        "plano_acoes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fase_id", sa.Integer(), sa.ForeignKey("plano_fases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("ordem", sa.Integer(), default=0),
    )

    # ──────────────────────────────────────────────
    # TABELA: plano_tarefas
    # ──────────────────────────────────────────────
    op.create_table(
        "plano_tarefas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("acao_id", sa.Integer(), sa.ForeignKey("plano_acoes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("ordem", sa.Integer(), default=0),
        sa.Column("prazo_dias_offset", sa.Integer(), default=0),
    )

    # ──────────────────────────────────────────────
    # TABELA: tags_sistema
    # ──────────────────────────────────────────────
    op.create_table(
        "tags_sistema",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(100), nullable=False, unique=True),
        sa.Column("cor", sa.String(20)),
        sa.Column("icone", sa.String(50)),
        sa.Column("categoria", sa.String(50)),
        sa.Column("ativo", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ──────────────────────────────────────────────
    # TABELA: permissions
    # ──────────────────────────────────────────────
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("perfil", sa.String(50), nullable=False),
        sa.Column("permission_key", sa.String(100), nullable=False),
        sa.Column("allowed", sa.Boolean(), default=True),
        sa.UniqueConstraint("perfil", "permission_key", name="uq_permissions_perfil_key"),
    )

    # ──────────────────────────────────────────────
    # TABELA: google_tokens
    # ──────────────────────────────────────────────
    op.create_table(
        "google_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_email", sa.String(255), sa.ForeignKey("usuarios.usuario"), nullable=False),
        sa.Column("access_token", sa.Text()),
        sa.Column("refresh_token", sa.Text()),
        sa.Column("token_expiry", sa.DateTime()),
        sa.Column("scopes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ──────────────────────────────────────────────
    # TABELA: gamification_rules
    # ──────────────────────────────────────────────
    op.create_table(
        "gamification_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("descricao", sa.Text()),
        sa.Column("pontos", sa.Integer(), default=0),
        sa.Column("tipo", sa.String(50)),
        sa.Column("condicao", sa.Text()),
        sa.Column("ativo", sa.Boolean(), default=True),
    )

    # ──────────────────────────────────────────────
    # TABELA: risc_events (auditoria de risco)
    # ──────────────────────────────────────────────
    op.create_table(
        "risc_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("implantacao_id", sa.Integer(), sa.ForeignKey("implantacoes.id")),
        sa.Column("tipo_evento", sa.String(100), nullable=False),
        sa.Column("descricao", sa.Text()),
        sa.Column("severidade", sa.String(20)),
        sa.Column("resolvido", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop de todas as tabelas (em ordem reversa por dependências)."""
    op.drop_table("risc_events")
    op.drop_table("gamification_rules")
    op.drop_table("google_tokens")
    op.drop_table("permissions")
    op.drop_table("tags_sistema")
    op.drop_table("plano_tarefas")
    op.drop_table("plano_acoes")
    op.drop_table("plano_fases")
    op.drop_table("planos_sucesso")
    op.drop_table("timeline_logs")
    op.drop_table("comentarios_h")
    op.drop_table("checklist_items")
    op.drop_table("implantacoes")
    op.drop_table("perfil_usuario")
    op.drop_table("usuarios")
