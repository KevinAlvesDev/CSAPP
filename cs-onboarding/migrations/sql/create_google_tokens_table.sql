-- Tabela para armazenar tokens do Google OAuth
-- Suporta autorização incremental e refresh automático

CREATE TABLE IF NOT EXISTS google_tokens (
    id SERIAL PRIMARY KEY,
    usuario TEXT NOT NULL UNIQUE,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type TEXT DEFAULT 'Bearer',
    expires_at TIMESTAMP,
    scopes TEXT,  -- Escopos concedidos, separados por espaço
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario) REFERENCES perfil_usuario(usuario) ON DELETE CASCADE
);

-- Índice para busca rápida por usuário
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_google_tokens_usuario' AND n.nspname = 'public') THEN
        CREATE INDEX idx_google_tokens_usuario ON google_tokens(usuario);
    END IF;
END$$;

-- Índice para verificar tokens expirados
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_google_tokens_expires_at' AND n.nspname = 'public') THEN
        CREATE INDEX idx_google_tokens_expires_at ON google_tokens(expires_at);
    END IF;
END$$;
