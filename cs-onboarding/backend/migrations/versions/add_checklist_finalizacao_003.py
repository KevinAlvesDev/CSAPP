"""
Migration: Adiciona tabelas para Checklist de Finalização
Versão: 003
Data: 2026-01-04
"""


def upgrade_postgres(cursor):
    """Cria tabelas para checklist de finalização no PostgreSQL"""

    # Tabela de templates de checklist (itens padrão)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checklist_finalizacao_templates (
            id SERIAL PRIMARY KEY,
            titulo VARCHAR(500) NOT NULL,
            descricao TEXT,
            obrigatorio BOOLEAN DEFAULT FALSE,
            ordem INTEGER DEFAULT 0,
            ativo BOOLEAN DEFAULT TRUE,
            requer_evidencia BOOLEAN DEFAULT FALSE,
            tipo_evidencia VARCHAR(50),  -- 'arquivo', 'link', 'texto'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de itens do checklist por implantação
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checklist_finalizacao_items (
            id SERIAL PRIMARY KEY,
            implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
            template_id INTEGER REFERENCES checklist_finalizacao_templates(id) ON DELETE SET NULL,
            titulo VARCHAR(500) NOT NULL,
            descricao TEXT,
            obrigatorio BOOLEAN DEFAULT FALSE,
            concluido BOOLEAN DEFAULT FALSE,
            data_conclusao TIMESTAMP,
            usuario_conclusao VARCHAR(200),
            evidencia_tipo VARCHAR(50),
            evidencia_conteudo TEXT,
            evidencia_url VARCHAR(1000),
            observacoes TEXT,
            ordem INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Índices para performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_checklist_fin_items_impl
        ON checklist_finalizacao_items(implantacao_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_checklist_fin_items_concluido
        ON checklist_finalizacao_items(implantacao_id, concluido)
    """)

    # Inserir templates padrão
    templates_padrao = [
        (
            "Cliente confirmou go-live por email?",
            "Confirmação formal do cliente de que o sistema está pronto para uso",
            True,
            1,
            True,
        ),
        (
            "Documentação técnica entregue?",
            "Manuais, guias e documentação do sistema foram enviados ao cliente",
            True,
            2,
            True,
        ),
        (
            "Treinamento realizado e gravado?",
            "Sessão de treinamento foi realizada e gravação foi compartilhada",
            True,
            3,
            True,
        ),
        (
            "Contatos de suporte compartilhados?",
            "Cliente recebeu informações de como obter suporte técnico",
            True,
            4,
            True,
        ),
        ("Pesquisa de satisfação enviada?", "Formulário de feedback foi enviado ao cliente", False, 5, True),
        ("Dados de acesso validados?", "Credenciais de acesso foram testadas e confirmadas", True, 6, False),
        ("Integração com sistemas externos testada?", "APIs e integrações foram validadas em produção", False, 7, True),
        ("Backup inicial realizado?", "Primeiro backup dos dados foi executado com sucesso", True, 8, False),
        (
            "Plano de contingência apresentado?",
            "Cliente foi informado sobre procedimentos em caso de problemas",
            False,
            9,
            False,
        ),
        ("Termo de aceite assinado?", "Documento formal de aceite da implantação foi assinado", True, 10, True),
    ]

    for titulo, descricao, obrigatorio, ordem, requer_evidencia in templates_padrao:
        cursor.execute(
            """
            INSERT INTO checklist_finalizacao_templates
            (titulo, descricao, obrigatorio, ordem, requer_evidencia, tipo_evidencia)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (titulo, descricao, obrigatorio, ordem, requer_evidencia, "link" if requer_evidencia else None),
        )


def upgrade_sqlite(cursor):
    """Cria tabelas para checklist de finalização no SQLite"""

    # Tabela de templates de checklist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checklist_finalizacao_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo VARCHAR(500) NOT NULL,
            descricao TEXT,
            obrigatorio BOOLEAN DEFAULT 0,
            ordem INTEGER DEFAULT 0,
            ativo BOOLEAN DEFAULT 1,
            requer_evidencia BOOLEAN DEFAULT 0,
            tipo_evidencia VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de itens do checklist por implantação
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checklist_finalizacao_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
            template_id INTEGER REFERENCES checklist_finalizacao_templates(id) ON DELETE SET NULL,
            titulo VARCHAR(500) NOT NULL,
            descricao TEXT,
            obrigatorio BOOLEAN DEFAULT 0,
            concluido BOOLEAN DEFAULT 0,
            data_conclusao TIMESTAMP,
            usuario_conclusao VARCHAR(200),
            evidencia_tipo VARCHAR(50),
            evidencia_conteudo TEXT,
            evidencia_url VARCHAR(1000),
            observacoes TEXT,
            ordem INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Índices
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_checklist_fin_items_impl
        ON checklist_finalizacao_items(implantacao_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_checklist_fin_items_concluido
        ON checklist_finalizacao_items(implantacao_id, concluido)
    """)

    # Inserir templates padrão
    templates_padrao = [
        (
            "Cliente confirmou go-live por email?",
            "Confirmação formal do cliente de que o sistema está pronto para uso",
            1,
            1,
            1,
        ),
        (
            "Documentação técnica entregue?",
            "Manuais, guias e documentação do sistema foram enviados ao cliente",
            1,
            2,
            1,
        ),
        (
            "Treinamento realizado e gravado?",
            "Sessão de treinamento foi realizada e gravação foi compartilhada",
            1,
            3,
            1,
        ),
        ("Contatos de suporte compartilhados?", "Cliente recebeu informações de como obter suporte técnico", 1, 4, 1),
        ("Pesquisa de satisfação enviada?", "Formulário de feedback foi enviado ao cliente", 0, 5, 1),
        ("Dados de acesso validados?", "Credenciais de acesso foram testadas e confirmadas", 1, 6, 0),
        ("Integração com sistemas externos testada?", "APIs e integrações foram validadas em produção", 0, 7, 1),
        ("Backup inicial realizado?", "Primeiro backup dos dados foi executado com sucesso", 1, 8, 0),
        (
            "Plano de contingência apresentado?",
            "Cliente foi informado sobre procedimentos em caso de problemas",
            0,
            9,
            0,
        ),
        ("Termo de aceite assinado?", "Documento formal de aceite da implantação foi assinado", 1, 10, 1),
    ]

    for titulo, descricao, obrigatorio, ordem, requer_evidencia in templates_padrao:
        cursor.execute(
            """
            INSERT INTO checklist_finalizacao_templates
            (titulo, descricao, obrigatorio, ordem, requer_evidencia, tipo_evidencia)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (titulo, descricao, obrigatorio, ordem, requer_evidencia, "link" if requer_evidencia else None),
        )


def downgrade_postgres(cursor):
    """Remove tabelas do checklist de finalização no PostgreSQL"""
    cursor.execute("DROP TABLE IF EXISTS checklist_finalizacao_items CASCADE")
    cursor.execute("DROP TABLE IF EXISTS checklist_finalizacao_templates CASCADE")


def downgrade_sqlite(cursor):
    """Remove tabelas do checklist de finalização no SQLite"""
    cursor.execute("DROP TABLE IF EXISTS checklist_finalizacao_items")
    cursor.execute("DROP TABLE IF EXISTS checklist_finalizacao_templates")
