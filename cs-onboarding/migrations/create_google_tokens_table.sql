-- Tabela para armazenar tokens do Google OAuth
-- Suporta autorização incremental e refresh automático

CREATE TABLE IF NOT EXISTS google_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
CREATE INDEX IF NOT EXISTS idx_google_tokens_usuario ON google_tokens(usuario);

-- Índice para verificar tokens expirados
CREATE INDEX IF NOT EXISTS idx_google_tokens_expires_at ON google_tokens(expires_at);
