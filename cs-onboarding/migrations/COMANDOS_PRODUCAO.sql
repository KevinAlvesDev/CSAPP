ALTER TABLE implantacoes ALTER COLUMN valor_atribuido TYPE DECIMAL(10,2) USING COALESCE(NULLIF(valor_atribuido, '')::DECIMAL, 0.00);
ALTER TABLE implantacoes ALTER COLUMN valor_atribuido SET DEFAULT 0.00;

ALTER TABLE comentarios_h ADD COLUMN IF NOT EXISTS tag VARCHAR(50) DEFAULT NULL;

ALTER TABLE comentarios_h ADD CONSTRAINT comentarios_h_tag_check CHECK (tag IS NULL OR tag IN ('Ação interna', 'Reunião', 'No Show'));

CREATE INDEX IF NOT EXISTS idx_implantacoes_valor_atribuido ON implantacoes(valor_atribuido) WHERE valor_atribuido > 0;

CREATE INDEX IF NOT EXISTS idx_comentarios_h_tag ON comentarios_h(tag) WHERE tag IS NOT NULL;
