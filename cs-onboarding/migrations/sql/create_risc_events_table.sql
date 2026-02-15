-- Tabela para armazenar logs de eventos RISC (Proteção entre Contas)
-- Usada para auditoria e troubleshooting de eventos de segurança

CREATE TABLE IF NOT EXISTS risc_events (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,  -- Tipo do evento (sessions-revoked, account-disabled, etc)
    user_id TEXT NOT NULL,  -- ID do usuário no Google (sub)
    event_payload TEXT NOT NULL,  -- Payload completo do evento (JSON)
    action_taken TEXT,  -- Ação tomada pelo sistema
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Quando o evento foi recebido
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Quando foi processado
);

-- Índices para performance
-- Índices para performance
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_risc_events_user_id' AND n.nspname = 'public') THEN
        CREATE INDEX idx_risc_events_user_id ON risc_events(user_id);
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_risc_events_event_type' AND n.nspname = 'public') THEN
        CREATE INDEX idx_risc_events_event_type ON risc_events(event_type);
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_risc_events_received_at' AND n.nspname = 'public') THEN
        CREATE INDEX idx_risc_events_received_at ON risc_events(received_at);
    END IF;
END$$;

-- Índice composto para queries comuns
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_risc_events_user_type' AND n.nspname = 'public') THEN
        CREATE INDEX idx_risc_events_user_type ON risc_events(user_id, event_type);
    END IF;
END$$;
