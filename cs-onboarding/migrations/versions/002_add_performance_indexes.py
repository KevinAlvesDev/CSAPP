"""
Migration: Adicionar índices de performance

Adiciona índices compostos e parciais para otimizar as queries mais
frequentes da aplicação (dashboard, detalhes, checklist).

Revision ID: 002_add_performance_indexes
Revises: 001_consolidated_base
Create Date: 2026-02-11
"""

from alembic import op

revision = "002_add_performance_indexes"
down_revision = "001_consolidated_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Adiciona índices de performance."""

    # Dashboard: busca por usuario_cs + status (query principal)
    op.create_index(
        "idx_impl_usuario_status",
        "implantacoes",
        ["usuario_cs", "status"],
        if_not_exists=True,
    )

    # Dashboard: ordenação por data de criação
    op.create_index(
        "idx_impl_created_at",
        "implantacoes",
        ["created_at"],
        if_not_exists=True,
    )

    # Checklist: busca hierárquica otimizada
    op.create_index(
        "idx_checklist_parent_tipo_ordem",
        "checklist_items",
        ["parent_id", "tipo_item", "ordem"],
        if_not_exists=True,
    )

    # Comentários: busca por data (últimos comentários)
    op.create_index(
        "idx_comentarios_data_criacao",
        "comentarios_h",
        ["data_criacao"],
        if_not_exists=True,
    )

    # Timeline: busca por implantação + data
    op.create_index(
        "idx_timeline_impl_data",
        "timeline_logs",
        ["implantacao_id", "data_criacao"],
        if_not_exists=True,
    )

    # Perfil: busca por perfil_acesso (filtro do dashboard)
    op.create_index(
        "idx_perfil_acesso",
        "perfil_usuario",
        ["perfil_acesso"],
        if_not_exists=True,
    )


def downgrade() -> None:
    """Remove índices de performance."""
    op.drop_index("idx_impl_usuario_status", table_name="implantacoes")
    op.drop_index("idx_impl_created_at", table_name="implantacoes")
    op.drop_index("idx_checklist_parent_tipo_ordem", table_name="checklist_items")
    op.drop_index("idx_comentarios_data_criacao", table_name="comentarios_h")
    op.drop_index("idx_timeline_impl_data", table_name="timeline_logs")
    op.drop_index("idx_perfil_acesso", table_name="perfil_usuario")
