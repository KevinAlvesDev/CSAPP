"""Initial schema — all app tables, sequences and indexes.

Compatible with PostgreSQL 9.3 (no features from 9.4+ used).
No JSONB (use TEXT), no IF NOT EXISTS for sequences/indexes (use DO $$ blocks),
no INSERT ... ON CONFLICT (use WHERE NOT EXISTS).

Revision ID: 001
Revises: None
Create Date: 2026-03-12
"""

from alembic import op
from sqlalchemy import text

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _create_index(indexname: str, tablename: str, columns: str) -> None:
    """Create index only if it doesn't already exist (PG 9.3 safe)."""
    op.execute(text(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = '{indexname}'
            ) THEN
                CREATE INDEX {indexname} ON {tablename}({columns});
            END IF;
        END
        $$;
    """))


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:

    # ── GRUPO 1 — tabelas sem dependências ──────────────────────────────────

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS tags_sistema (
            id    SERIAL PRIMARY KEY,
            nome  TEXT NOT NULL,
            ordem INT  DEFAULT 0,
            tipo  TEXT DEFAULT 'comentario'
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS status_implantacao (
            id     SERIAL PRIMARY KEY,
            codigo TEXT NOT NULL,
            nome   TEXT NOT NULL,
            cor    TEXT DEFAULT '#6c757d',
            ordem  INT  DEFAULT 0,
            ativo  BOOLEAN DEFAULT TRUE,
            CONSTRAINT uq_status_implantacao_codigo UNIQUE (codigo)
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS niveis_atendimento (
            id       SERIAL PRIMARY KEY,
            codigo   TEXT NOT NULL,
            nome     TEXT NOT NULL,
            descricao TEXT,
            CONSTRAINT uq_niveis_atendimento_codigo UNIQUE (codigo)
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS tipos_evento (
            id     SERIAL PRIMARY KEY,
            codigo TEXT NOT NULL,
            nome   TEXT NOT NULL,
            cor    TEXT DEFAULT '#6c757d',
            icone  TEXT DEFAULT 'bi-circle',
            CONSTRAINT uq_tipos_evento_codigo UNIQUE (codigo)
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS motivos_parada (
            id        SERIAL PRIMARY KEY,
            descricao TEXT    NOT NULL,
            ativo     BOOLEAN DEFAULT TRUE
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS motivos_cancelamento (
            id        SERIAL PRIMARY KEY,
            descricao TEXT    NOT NULL,
            ativo     BOOLEAN DEFAULT TRUE
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS smtp_settings (
            id           SERIAL PRIMARY KEY,
            host         TEXT,
            port         INT  DEFAULT 587,
            username     TEXT,
            password     TEXT,
            use_tls      BOOLEAN DEFAULT TRUE,
            from_email   TEXT,
            criado_em    TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW()
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS google_tokens (
            id            SERIAL PRIMARY KEY,
            user_email    TEXT NOT NULL,
            access_token  TEXT,
            refresh_token TEXT,
            token_expiry  TIMESTAMP,
            criado_em     TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_google_tokens_user_email UNIQUE (user_email)
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id          SERIAL PRIMARY KEY,
            user_email  TEXT,
            action      TEXT,
            target_type TEXT,
            target_id   TEXT,
            changes     TEXT,
            metadata    TEXT,
            ip_address  TEXT,
            criado_em   TIMESTAMP DEFAULT NOW()
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS perfis_acesso (
            id        SERIAL PRIMARY KEY,
            nome      TEXT    NOT NULL,
            descricao TEXT,
            sistema   BOOLEAN DEFAULT FALSE,
            ativo     BOOLEAN DEFAULT TRUE,
            cor       TEXT    DEFAULT '#6c757d',
            icone     TEXT    DEFAULT 'bi-person-badge',
            criado_em TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_perfis_acesso_nome UNIQUE (nome)
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS recursos (
            id        SERIAL PRIMARY KEY,
            codigo    TEXT NOT NULL,
            nome      TEXT NOT NULL,
            descricao TEXT,
            categoria TEXT,
            tipo      TEXT DEFAULT 'acao',
            ordem     INT  DEFAULT 0,
            ativo     BOOLEAN DEFAULT TRUE,
            CONSTRAINT uq_recursos_codigo UNIQUE (codigo)
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS checklist_finalizacao_templates (
            id        SERIAL PRIMARY KEY,
            nome      TEXT    NOT NULL,
            descricao TEXT,
            ativo     BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT NOW()
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS gamificacao_regras (
            id           SERIAL PRIMARY KEY,
            regra_id     TEXT NOT NULL,
            contexto     TEXT NOT NULL,
            categoria    TEXT,
            descricao    TEXT,
            valor_pontos INT  DEFAULT 0,
            tipo_valor   TEXT DEFAULT 'pontos',
            ativo        BOOLEAN DEFAULT TRUE,
            CONSTRAINT uq_gamificacao_regras_regra_ctx UNIQUE (regra_id, contexto)
        );
    """))

    # ── GRUPO 2 — dependem de Grupo 1 ───────────────────────────────────────

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS perfis_acesso_contexto (
            id         SERIAL PRIMARY KEY,
            nome       TEXT    NOT NULL,
            descricao  TEXT,
            sistema    BOOLEAN DEFAULT FALSE,
            ativo      BOOLEAN DEFAULT TRUE,
            cor        TEXT    DEFAULT '#6c757d',
            icone      TEXT    DEFAULT 'bi-person-badge',
            contexto   TEXT    NOT NULL,
            criado_por TEXT,
            criado_em  TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_perfis_acesso_contexto_nome_ctx UNIQUE (nome, contexto)
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS permissoes (
            id         SERIAL PRIMARY KEY,
            perfil_id  INT REFERENCES perfis_acesso(id) ON DELETE CASCADE,
            recurso_id INT REFERENCES recursos(id) ON DELETE CASCADE,
            concedida  BOOLEAN DEFAULT TRUE,
            CONSTRAINT uq_permissoes_perfil_recurso UNIQUE (perfil_id, recurso_id)
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS perfil_usuario (
            usuario                TEXT PRIMARY KEY,
            nome                   TEXT,
            ultimo_check_externo   TIMESTAMP,
            criado_em              TIMESTAMP DEFAULT NOW()
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS implantacoes (
            id                    SERIAL PRIMARY KEY,
            nome_empresa          TEXT    NOT NULL,
            cnpj                  TEXT,
            usuario_cs            TEXT,
            status_id             INT REFERENCES status_implantacao(id) ON DELETE SET NULL,
            tipo                  TEXT    DEFAULT 'onboarding',
            valor_monetario       NUMERIC(15,2),
            nivel_atendimento_id  INT REFERENCES niveis_atendimento(id) ON DELETE SET NULL,
            plano_sucesso_id      INT,
            responsavel_nome      TEXT,
            responsavel_email     TEXT,
            data_inicio           DATE,
            data_previsao         DATE,
            data_finalizacao      DATE,
            motivo_parada_id      INT REFERENCES motivos_parada(id) ON DELETE SET NULL,
            motivo_cancelamento_id INT REFERENCES motivos_cancelamento(id) ON DELETE SET NULL,
            definicao_carteira    TEXT,
            criado_em             TIMESTAMP DEFAULT NOW(),
            atualizado_em         TIMESTAMP DEFAULT NOW()
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS gamificacao_metricas_mensais (
            id         SERIAL PRIMARY KEY,
            usuario_cs TEXT    NOT NULL,
            contexto   TEXT    NOT NULL,
            ano        INT     NOT NULL,
            mes        INT     NOT NULL,
            metrica    TEXT    NOT NULL,
            valor      NUMERIC(10,2) DEFAULT 0,
            criado_em  TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_gamificacao_metricas_chave UNIQUE (usuario_cs, contexto, ano, mes, metrica)
        );
    """))

    # ── GRUPO 3 — dependem de Grupo 2 ───────────────────────────────────────

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS perfil_usuario_contexto (
            id            SERIAL PRIMARY KEY,
            user_email    TEXT NOT NULL,
            perfil_ctx_id INT  REFERENCES perfis_acesso_contexto(id) ON DELETE CASCADE,
            contexto      TEXT NOT NULL,
            criado_em     TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_perfil_usuario_contexto UNIQUE (user_email, contexto)
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS permissoes_contexto (
            id            SERIAL PRIMARY KEY,
            perfil_ctx_id INT REFERENCES perfis_acesso_contexto(id) ON DELETE CASCADE,
            recurso_id    INT REFERENCES recursos(id) ON DELETE CASCADE,
            concedida     BOOLEAN DEFAULT TRUE,
            criado_em     TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_permissoes_contexto_perfil_recurso UNIQUE (perfil_ctx_id, recurso_id)
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS checklist_items (
            id                   SERIAL PRIMARY KEY,
            implantacao_id       INT REFERENCES implantacoes(id) ON DELETE CASCADE,
            parent_id            INT REFERENCES checklist_items(id) ON DELETE CASCADE,
            titulo               TEXT NOT NULL,
            descricao            TEXT,
            concluido            BOOLEAN DEFAULT FALSE,
            status               TEXT    DEFAULT 'pendente',
            obrigatoria          BOOLEAN DEFAULT TRUE,
            percentual_conclusao NUMERIC(5,2) DEFAULT 0,
            tag                  TEXT,
            responsavel          TEXT,
            prazo                DATE,
            ordem                INT     DEFAULT 0,
            dispensado           BOOLEAN DEFAULT FALSE,
            motivo_dispensa      TEXT,
            criado_em            TIMESTAMP DEFAULT NOW(),
            atualizado_em        TIMESTAMP DEFAULT NOW()
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS timeline_log (
            id             SERIAL PRIMARY KEY,
            implantacao_id INT REFERENCES implantacoes(id) ON DELETE CASCADE,
            usuario_cs     TEXT,
            tipo_evento    TEXT,
            detalhes       TEXT,
            criado_em      TIMESTAMP DEFAULT NOW()
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS comentarios_h (
            id                 SERIAL PRIMARY KEY,
            implantacao_id     INT REFERENCES implantacoes(id) ON DELETE CASCADE,
            checklist_item_id  INT REFERENCES checklist_items(id) ON DELETE CASCADE,
            usuario_cs         TEXT,
            texto              TEXT    NOT NULL,
            visibilidade       TEXT    DEFAULT 'interno',
            noshow             BOOLEAN DEFAULT FALSE,
            tag                TEXT,
            imagem_url         TEXT,
            data_criacao       TIMESTAMP DEFAULT NOW()
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS avisos_implantacao (
            id             SERIAL PRIMARY KEY,
            implantacao_id INT REFERENCES implantacoes(id) ON DELETE CASCADE,
            titulo         TEXT    NOT NULL,
            conteudo       TEXT,
            tipo           TEXT    DEFAULT 'info',
            ativo          BOOLEAN DEFAULT TRUE,
            usuario_cs     TEXT,
            criado_em      TIMESTAMP DEFAULT NOW(),
            atualizado_em  TIMESTAMP
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS implantacao_jira_links (
            id              SERIAL PRIMARY KEY,
            implantacao_id  INT  REFERENCES implantacoes(id) ON DELETE CASCADE,
            jira_issue_key  TEXT NOT NULL,
            jira_summary    TEXT,
            jira_status     TEXT,
            criado_em       TIMESTAMP DEFAULT NOW()
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS implantacao_planos (
            id             SERIAL PRIMARY KEY,
            implantacao_id INT REFERENCES implantacoes(id) ON DELETE CASCADE,
            plano_id       INT NOT NULL,
            aplicado_em    TIMESTAMP DEFAULT NOW(),
            concluido_em   TIMESTAMP,
            usuario_cs     TEXT
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS checklist_finalizacao_items (
            id             SERIAL PRIMARY KEY,
            template_id    INT REFERENCES checklist_finalizacao_templates(id) ON DELETE SET NULL,
            implantacao_id INT REFERENCES implantacoes(id) ON DELETE CASCADE,
            titulo         TEXT    NOT NULL,
            concluido      BOOLEAN DEFAULT FALSE,
            criado_em      TIMESTAMP DEFAULT NOW()
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS risc_events (
            id             SERIAL PRIMARY KEY,
            implantacao_id INT REFERENCES implantacoes(id) ON DELETE CASCADE,
            tipo           TEXT,
            descricao      TEXT,
            criado_em      TIMESTAMP DEFAULT NOW()
        );
    """))

    # ── GRUPO 4 — dependem de checklist_items ───────────────────────────────

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS checklist_status_history (
            id               SERIAL PRIMARY KEY,
            item_id          INT REFERENCES checklist_items(id) ON DELETE CASCADE,
            status_anterior  TEXT,
            status_novo      TEXT,
            usuario          TEXT,
            criado_em        TIMESTAMP DEFAULT NOW()
        );
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS checklist_responsavel_history (
            id                   SERIAL PRIMARY KEY,
            item_id              INT REFERENCES checklist_items(id) ON DELETE CASCADE,
            responsavel_anterior TEXT,
            responsavel_novo     TEXT,
            usuario              TEXT,
            criado_em            TIMESTAMP DEFAULT NOW()
        );
    """))

    # ── INDEXES ─────────────────────────────────────────────────────────────

    _create_index("idx_implantacoes_status_id",         "implantacoes",                "status_id")
    _create_index("idx_implantacoes_usuario_cs",         "implantacoes",                "usuario_cs")
    _create_index("idx_implantacoes_criado_em",          "implantacoes",                "criado_em")
    _create_index("idx_implantacoes_tipo",               "implantacoes",                "tipo")

    _create_index("idx_checklist_items_implantacao_id",  "checklist_items",             "implantacao_id")
    _create_index("idx_checklist_items_parent_id",       "checklist_items",             "parent_id")
    _create_index("idx_checklist_items_status",          "checklist_items",             "status")

    _create_index("idx_timeline_log_implantacao_id",     "timeline_log",                "implantacao_id")
    _create_index("idx_timeline_log_criado_em",          "timeline_log",                "criado_em")
    _create_index("idx_timeline_log_tipo_evento",        "timeline_log",                "tipo_evento")

    _create_index("idx_comentarios_h_implantacao_id",    "comentarios_h",               "implantacao_id")
    _create_index("idx_comentarios_h_criado_em",         "comentarios_h",               "criado_em")

    _create_index("idx_perfis_acesso_contexto_ctx",      "perfis_acesso_contexto",      "contexto")

    _create_index("idx_permissoes_contexto_pfctx",       "permissoes_contexto",         "perfil_ctx_id")
    _create_index("idx_permissoes_contexto_recurso",     "permissoes_contexto",         "recurso_id")

    _create_index("idx_perfil_usuario_contexto_email",   "perfil_usuario_contexto",     "user_email")
    _create_index("idx_perfil_usuario_contexto_ctx",     "perfil_usuario_contexto",     "contexto")

    _create_index("idx_audit_logs_criado_em",            "audit_logs",                  "criado_em")
    _create_index("idx_audit_logs_user_email",           "audit_logs",                  "user_email")

    _create_index("idx_gamificacao_regras_contexto",     "gamificacao_regras",          "contexto")
    _create_index("idx_gamificacao_regras_regra_id",     "gamificacao_regras",          "regra_id")
    _create_index("idx_gamificacao_metricas_usuario_ctx","gamificacao_metricas_mensais", "usuario_cs, contexto")

    _create_index("idx_avisos_implantacao_id",           "avisos_implantacao",          "implantacao_id")
    _create_index("idx_jira_links_implantacao_id",       "implantacao_jira_links",      "implantacao_id")
    _create_index("idx_recursos_categoria",              "recursos",                    "categoria")
    _create_index("idx_recursos_ordem",                  "recursos",                    "ordem")

    _create_index("idx_checklist_status_history_item",   "checklist_status_history",    "item_id")
    _create_index("idx_checklist_resp_history_item",     "checklist_responsavel_history", "item_id")

    _create_index("idx_implantacao_planos_impl_id",      "implantacao_planos",          "implantacao_id")
    _create_index("idx_checklist_fin_items_impl_id",     "checklist_finalizacao_items", "implantacao_id")


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # Ordem reversa das dependências FK
    tables = [
        "checklist_responsavel_history",
        "checklist_status_history",
        "risc_events",
        "checklist_finalizacao_items",
        "implantacao_planos",
        "implantacao_jira_links",
        "avisos_implantacao",
        "comentarios_h",
        "timeline_log",
        "checklist_items",
        "permissoes_contexto",
        "perfil_usuario_contexto",
        "gamificacao_metricas_mensais",
        "implantacoes",
        "perfil_usuario",
        "permissoes",
        "perfis_acesso_contexto",
        "gamificacao_regras",
        "checklist_finalizacao_templates",
        "recursos",
        "perfis_acesso",
        "audit_logs",
        "google_tokens",
        "smtp_settings",
        "motivos_cancelamento",
        "motivos_parada",
        "tipos_evento",
        "niveis_atendimento",
        "status_implantacao",
        "tags_sistema",
    ]
    for table in tables:
        op.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
