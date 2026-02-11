"""
Migration: Adiciona tabelas de configuração faltantes e coluna contexto em planos_sucesso
Versão: 005
Data: 2026-02-11
"""


def upgrade_postgres(cursor):
    """Atualiza schema no PostgreSQL"""

    # 1. Adicionar coluna contexto em planos_sucesso se não existir
    try:
        cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN IF NOT EXISTS contexto VARCHAR(50) DEFAULT 'onboarding'")
    except Exception:
        pass  # Pode já existir ou tabela não existir (se for migration inicial)

    # 2. Criar tabelas de configuração se não existirem
    
    # tags_sistema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags_sistema (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL UNIQUE,
            icone VARCHAR(50) DEFAULT 'bi-tag',
            cor_badge VARCHAR(20) DEFAULT '#6c757d',
            ordem INTEGER DEFAULT 0,
            tipo VARCHAR(20) DEFAULT 'ambos',
            ativo BOOLEAN DEFAULT TRUE
        )
    """)

    # status_implantacao
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status_implantacao (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(50) NOT NULL UNIQUE,
            nome VARCHAR(100) NOT NULL,
            cor VARCHAR(20) DEFAULT '#6c757d',
            ordem INTEGER DEFAULT 0,
            ativo BOOLEAN DEFAULT TRUE
        )
    """)

    # niveis_atendimento
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS niveis_atendimento (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(50) NOT NULL UNIQUE,
            descricao VARCHAR(255) NOT NULL,
            ordem INTEGER DEFAULT 0,
            ativo BOOLEAN DEFAULT TRUE
        )
    """)

    # tipos_evento
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tipos_evento (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(50) NOT NULL UNIQUE,
            nome VARCHAR(100) NOT NULL,
            icone VARCHAR(50) DEFAULT '',
            cor VARCHAR(30) DEFAULT '#6c757d',
            ativo BOOLEAN DEFAULT TRUE
        )
    """)

    # motivos_parada
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS motivos_parada (
            id SERIAL PRIMARY KEY,
            descricao VARCHAR(255) NOT NULL,
            ativo BOOLEAN DEFAULT TRUE
        )
    """)

    # motivos_cancelamento
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS motivos_cancelamento (
            id SERIAL PRIMARY KEY,
            descricao VARCHAR(255) NOT NULL,
            ativo BOOLEAN DEFAULT TRUE
        )
    """)

    # 3. Seed de dados básicos (apenas se tabelas estiverem vazias)
    _seed_data(cursor, is_sqlite=False)


def upgrade_sqlite(cursor):
    """Atualiza schema no SQLite"""

    # 1. Adicionar coluna contexto
    try:
        # SQLite não suporta IF NOT EXISTS em ADD COLUMN facilmente, então tentamos e ignoramos erro
        cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN contexto TEXT DEFAULT 'onboarding'")
    except Exception:
        pass

    # 2. Criar tabelas config
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome VARCHAR(100) NOT NULL UNIQUE,
            icone VARCHAR(50) DEFAULT 'bi-tag',
            cor_badge VARCHAR(20) DEFAULT '#6c757d',
            ordem INTEGER DEFAULT 0,
            tipo VARCHAR(20) DEFAULT 'ambos',
            ativo INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status_implantacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo VARCHAR(50) NOT NULL UNIQUE,
            nome VARCHAR(100) NOT NULL,
            cor VARCHAR(20) DEFAULT '#6c757d',
            ordem INTEGER DEFAULT 0,
            ativo INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS niveis_atendimento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo VARCHAR(50) NOT NULL UNIQUE,
            descricao VARCHAR(255) NOT NULL,
            ordem INTEGER DEFAULT 0,
            ativo INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tipos_evento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo VARCHAR(50) NOT NULL UNIQUE,
            nome VARCHAR(100) NOT NULL,
            icone VARCHAR(50) DEFAULT '',
            cor VARCHAR(30) DEFAULT '#6c757d',
            ativo INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS motivos_parada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao VARCHAR(255) NOT NULL,
            ativo INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS motivos_cancelamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao VARCHAR(255) NOT NULL,
            ativo INTEGER DEFAULT 1
        )
    """)

    # 3. Seed data
    _seed_data(cursor, is_sqlite=True)


def _seed_data(cursor, is_sqlite=False):
    """Função auxiliar para popular dados"""
    
    placeholder = "?" if is_sqlite else "%s"

    # Tags
    cursor.execute("SELECT COUNT(*) FROM tags_sistema")
    if cursor.fetchone()[0] == 0:
        tags = [
            ("Ação interna", "bi-chat-left-dots", "#0d6efd", 1, "comentario"),
            ("Reunião", "bi-camera-video", "#198754", 2, "comentario"),
            ("No Show", "bi-x-circle", "#dc3545", 3, "comentario"),
            ("Treinamento", "bi-mortarboard", "#6f42c1", 4, "ambos"),
            ("Migração", "bi-arrow-left-right", "#fd7e14", 5, "ambos"),
            ("Suporte", "bi-headset", "#20c997", 6, "ambos"),
        ]
        for nome, icone, cor, ordem, tipo in tags:
            cursor.execute(f"INSERT INTO tags_sistema (nome, icone, cor_badge, ordem, tipo) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})", (nome, icone, cor, ordem, tipo))

    # Status
    cursor.execute("SELECT COUNT(*) FROM status_implantacao")
    if cursor.fetchone()[0] == 0:
        statuses = [
            ("nova", "Nova", "#6c757d", 1),
            ("futura", "Futura", "#0dcaf0", 2),
            ("sem_previsao", "Sem Previsão", "#adb5bd", 3),
            ("andamento", "Em Andamento", "#0d6efd", 4),
            ("parada", "Parada", "#ffc107", 5),
            ("finalizada", "Finalizada", "#198754", 6),
            ("cancelada", "Cancelada", "#dc3545", 7),
        ]
        for codigo, nome, cor, ordem in statuses:
            cursor.execute(f"INSERT INTO status_implantacao (codigo, nome, cor, ordem) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})", (codigo, nome, cor, ordem))

    # Niveis
    cursor.execute("SELECT COUNT(*) FROM niveis_atendimento")
    if cursor.fetchone()[0] == 0:
        niveis = [
            ("basico", "Básico", 1),
            ("intermediario", "Intermediário", 2),
            ("avancado", "Avançado", 3),
            ("premium", "Premium", 4),
        ]
        for codigo, descricao, ordem in niveis:
            cursor.execute(f"INSERT INTO niveis_atendimento (codigo, descricao, ordem) VALUES ({placeholder}, {placeholder}, {placeholder})", (codigo, descricao, ordem))


    # Tipos Evento
    cursor.execute("SELECT COUNT(*) FROM tipos_evento")
    if cursor.fetchone()[0] == 0:
        tipos = [
            ("implantacao_criada", "Implantação Criada", "bi-plus-circle", "#198754"),
            ("status_alterado", "Status Alterado", "bi-arrow-repeat", "#0d6efd"),
            ("tarefa_alterada", "Tarefa Alterada", "bi-check2-square", "#6f42c1"),
            ("novo_comentario", "Novo Comentário", "bi-chat-left-text", "#fd7e14"),
            ("detalhes_alterados", "Detalhes Alterados", "bi-pencil-square", "#20c997"),
            ("responsavel_alterado", "Responsável Alterado", "bi-person-lines-fill", "#0dcaf0"),
            ("prazo_alterado", "Prazo Alterado", "bi-calendar-event", "#ffc107"),
            ("plano_aplicado", "Plano Aplicado", "bi-diagram-3", "#6610f2"),
            ("comentario_excluido", "Comentário Excluído", "bi-trash", "#dc3545"),
        ]
        for codigo, nome, icone, cor in tipos:
            cursor.execute(f"INSERT INTO tipos_evento (codigo, nome, icone, cor) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})", (codigo, nome, icone, cor))

    # Motivos Parada
    cursor.execute("SELECT COUNT(*) FROM motivos_parada")
    if cursor.fetchone()[0] == 0:
        motivos_p = ["Cliente sem disponibilidade", "Problemas técnicos do cliente", "Pendência financeira", "Férias/recesso", "Aguardando decisão do cliente", "Outros"]
        for desc in motivos_p:
            cursor.execute(f"INSERT INTO motivos_parada (descricao) VALUES ({placeholder})", (desc,))

    # Motivos Cancelamento
    cursor.execute("SELECT COUNT(*) FROM motivos_cancelamento")
    if cursor.fetchone()[0] == 0:
        motivos_c = ["Desistência do cliente", "Mudança de sistema", "Encerramento de contrato", "Inadimplência", "Duplicidade", "Outros"]
        for desc in motivos_c:
            cursor.execute(f"INSERT INTO motivos_cancelamento (descricao) VALUES ({placeholder})", (desc,))


def downgrade_postgres(cursor):
    # Não remover coluna contexto pois pode ter dados
    pass

def downgrade_sqlite(cursor):
    pass
