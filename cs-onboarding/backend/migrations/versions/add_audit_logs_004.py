"""
Migration: Adiciona tabela de logs de auditoria
Versão: 004
Data: 2026-01-05
"""


def upgrade_postgres(cursor):
    """Cria tabela de auditoria no PostgreSQL"""

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255),
            action VARCHAR(50) NOT NULL, -- CREATE, UPDATE, DELETE, LOGIN, LOGOUT, ACTION
            target_type VARCHAR(50),     -- implantacao, checklist, usuario, sistema
            target_id VARCHAR(50),       -- ID do objeto afetado
            changes JSONB,               -- Mudanças {before: ..., after: ...}
            metadata JSONB,              -- Dados extras (razão, contexto)
            ip_address VARCHAR(45),
            user_agent TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Índices para busca rápida
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_user_email ON audit_logs(user_email);
        CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
        CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_logs(target_type, target_id);
        CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at);
    """)


def upgrade_sqlite(cursor):
    """Cria tabela de auditoria no SQLite"""

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email VARCHAR(255),
            action VARCHAR(50) NOT NULL,
            target_type VARCHAR(50),
            target_id VARCHAR(50),
            changes TEXT,                -- JSON armazenado como texto
            metadata TEXT,               -- JSON armazenado como texto
            ip_address VARCHAR(45),
            user_agent TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Índices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_email ON audit_logs(user_email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_logs(target_type, target_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at)")


def downgrade_postgres(cursor):
    """Remove tabela de auditoria no PostgreSQL"""
    cursor.execute("DROP TABLE IF EXISTS audit_logs CASCADE")


def downgrade_sqlite(cursor):
    """Remove tabela de auditoria no SQLite"""
    cursor.execute("DROP TABLE IF EXISTS audit_logs")
