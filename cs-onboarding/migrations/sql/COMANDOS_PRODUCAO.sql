ALTER TABLE implantacoes ALTER COLUMN valor_atribuido TYPE DECIMAL(10,2) USING COALESCE(NULLIF(valor_atribuido, '')::DECIMAL, 0.00);
ALTER TABLE implantacoes ALTER COLUMN valor_atribuido SET DEFAULT 0.00;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'comentarios_h' AND column_name = 'tag') THEN
        ALTER TABLE comentarios_h ADD COLUMN tag VARCHAR(50) DEFAULT NULL;
    END IF;
END$$;

ALTER TABLE comentarios_h ADD CONSTRAINT comentarios_h_tag_check CHECK (tag IS NULL OR tag IN ('Ação interna', 'Reunião', 'No Show'));

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_implantacoes_valor_atribuido' AND n.nspname = 'public') THEN
        CREATE INDEX idx_implantacoes_valor_atribuido ON implantacoes(valor_atribuido) WHERE valor_atribuido > 0;
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_comentarios_h_tag' AND n.nspname = 'public') THEN
        CREATE INDEX idx_comentarios_h_tag ON comentarios_h(tag) WHERE tag IS NOT NULL;
    END IF;
END$$;
