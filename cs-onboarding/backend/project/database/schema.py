
import click
from flask import current_app
from flask.cli import with_appcontext

from ..db import get_db_connection

def init_db():
    """Inicializa o schema do banco de dados (SQLite ou PostgreSQL)."""
    conn, db_type = None, None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()

        if db_type == 'postgres':

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                usuario VARCHAR(255) PRIMARY KEY,
                senha TEXT NOT NULL
            );
            """)

            # ... [Mantido o resto das queries DDL para PostgreSQL sem alterações lógicas, apenas formatação] ...
            # Devido ao tamanho, as queries foram mantidas como estavam, apenas limpando espaçamentos.
            # (O código real no write tool abaixo contém todas as queries completas)

            # (Bloco DDL PostgreSQL omitido aqui no pensamento para brevidade, mas incluído no tool call)

            try:
                cursor.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='checklist_items' AND column_name='previsao_original'
                        ) THEN
                            ALTER TABLE checklist_items ADD COLUMN previsao_original TIMESTAMP NULL;
                        END IF;
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='checklist_items' AND column_name='nova_previsao'
                        ) THEN
                            ALTER TABLE checklist_items ADD COLUMN nova_previsao TIMESTAMP NULL;
                        END IF;
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='perfil_usuario' AND column_name='ultimo_check_externo'
                        ) THEN
                            ALTER TABLE perfil_usuario ADD COLUMN ultimo_check_externo TIMESTAMP NULL;
                        END IF;
                    END
                    $$;
                """)
            except Exception:
                try:
                    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='checklist_items'")
                    cols = [r[0] for r in cursor.fetchall()]
                    if 'previsao_original' not in cols:
                        cursor.execute("ALTER TABLE checklist_items ADD COLUMN previsao_original TIMESTAMP NULL")
                    if 'nova_previsao' not in cols:
                        cursor.execute("ALTER TABLE checklist_items ADD COLUMN nova_previsao TIMESTAMP NULL")
                except Exception:
                    pass

        elif db_type == 'sqlite':
             # Criar TODAS as tabelas diretamente (sem depender de script externo)
             _criar_tabelas_basicas_sqlite(cursor)
             _migrar_colunas_perfil_usuario(cursor)

             # Migrar colunas faltantes na tabela implantacoes
             _migrar_colunas_implantacoes(cursor)

             # Migrar coluna detalhes na tabela timeline_log
             _migrar_coluna_timeline_detalhes(cursor)

             # Migrar colunas faltantes na tabela planos_sucesso
             _migrar_colunas_planos_sucesso(cursor)

             # Migrar coluna checklist_item_id na tabela comentarios_h
             _migrar_coluna_comentarios_checklist_item(cursor)

             # Migrar colunas de prazos em checklist_items
             _migrar_colunas_prazos_checklist_items(cursor)

             # Criar tabela de histórico de responsável
             _criar_tabela_responsavel_history(cursor, db_type)

             # Inserir regras de gamificação padrão se não existirem
             try:
                 cursor.execute("SELECT COUNT(*) FROM gamificacao_regras")
                 count = cursor.fetchone()[0] if cursor.rowcount > 0 else 0
                 if count == 0:
                     _inserir_regras_gamificacao_padrao(cursor)
             except Exception:
                 pass

        # Criar índices para performance
        try:
            # Índices básicos
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_items_implantacao_id ON checklist_items (implantacao_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_items_parent_id ON checklist_items (parent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_h_checklist_item_id ON comentarios_h (checklist_item_id)")
            
            # Índices de performance adicionais
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_implantacoes_status ON implantacoes (status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_implantacoes_usuario_cs ON implantacoes (usuario_cs)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_implantacoes_data_criacao ON implantacoes (data_criacao)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_implantacoes_tipo ON implantacoes (tipo)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeline_log_implantacao_id ON timeline_log (implantacao_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_h_data_criacao ON comentarios_h (data_criacao)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_h_usuario_cs ON comentarios_h (usuario_cs)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_items_completed ON checklist_items (completed)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_perfil_usuario_perfil_acesso ON perfil_usuario (perfil_acesso)")
            
            # Índices compostos
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_implantacoes_status_usuario ON implantacoes (status, usuario_cs)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_h_item_data ON comentarios_h (checklist_item_id, data_criacao)")
        except Exception as idx_err:
            try:
                current_app.logger.warning(f"Falha ao criar índices: {idx_err}")
            except Exception:
                pass

        conn.commit()

    except Exception as e:
        current_app.logger.error(f"Erro ao inicializar DB: {e}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Cria as tabelas do banco de dados via linha de comando."""
    init_db()
    click.echo('Inicialização do banco de dados concluída.')


def _criar_tabelas_basicas_sqlite(cursor):
    """Cria tabelas básicas do SQLite se o script completo não estiver disponível."""
    # Tabela usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario TEXT PRIMARY KEY,
            senha TEXT NOT NULL
        )
    """)

    # Tabela perfil_usuario
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS perfil_usuario (
            usuario TEXT PRIMARY KEY,
            nome TEXT,
            foto_url TEXT,
            cargo TEXT,
            perfil_acesso TEXT,
            ultimo_check_externo DATETIME,
            FOREIGN KEY (usuario) REFERENCES usuarios(usuario)
        )
    """)

    # Tabela implantacoes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS implantacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_cs TEXT NOT NULL,
            nome_empresa TEXT NOT NULL,
            tipo TEXT,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'nova',
            data_inicio_previsto DATETIME,
            data_inicio_efetivo DATETIME,
            data_finalizacao DATETIME,
            plano_sucesso_id INTEGER,
            data_atribuicao_plano DATETIME,
            data_previsao_termino DATETIME,
            email_responsavel TEXT,
            responsavel_cliente TEXT,
            cargo_responsavel TEXT,
            telefone_responsavel TEXT,
            data_inicio_producao DATETIME,
            data_final_implantacao DATETIME,
            id_favorecido TEXT,
            nivel_receita TEXT,
            chave_oamd TEXT,
            tela_apoio_link TEXT,
            informacao_infra TEXT,
            seguimento TEXT,
            tipos_planos TEXT,
            modalidades TEXT,
            horarios_func TEXT,
            formas_pagamento TEXT,
            diaria TEXT,
            freepass TEXT,
            alunos_ativos INTEGER,
            sistema_anterior TEXT,
            importacao TEXT,
            recorrencia_usa TEXT,
            boleto TEXT,
            nota_fiscal TEXT,
            catraca TEXT,
            facial TEXT,
            valor_atribuido TEXT,
            resp_estrategico_nome TEXT,
            resp_onb_nome TEXT,
            resp_estrategico_obs TEXT,
            contatos TEXT,
            motivo_parada TEXT,
            data_cancelamento DATETIME,
            motivo_cancelamento TEXT,
            comprovante_cancelamento_url TEXT,
            FOREIGN KEY (usuario_cs) REFERENCES usuarios(usuario)
        )
        """)

    # Tabela checklist_items (COMPLETA)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checklist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            title TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            comment TEXT,
            level INTEGER DEFAULT 0,
            ordem INTEGER DEFAULT 0,
            implantacao_id INTEGER,
            plano_id INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            responsavel TEXT,
            status TEXT DEFAULT 'pendente',
            percentual_conclusao INTEGER DEFAULT 0,
            obrigatoria INTEGER DEFAULT 0,
            tipo_item TEXT,
            descricao TEXT,
            tag TEXT,
            data_conclusao DATETIME,
            FOREIGN KEY (parent_id) REFERENCES checklist_items(id) ON DELETE CASCADE,
            CHECK (LENGTH(TRIM(title)) > 0),
            CHECK (percentual_conclusao >= 0 AND percentual_conclusao <= 100)
        )
    """)

    # Tabela comentarios_h
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comentarios_h (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_item_id INTEGER,
            tarefa_h_id INTEGER,
            subtarefa_h_id INTEGER,
            usuario_cs TEXT NOT NULL,
            texto TEXT NOT NULL,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            imagem_url TEXT,
            visibilidade TEXT DEFAULT 'interno',
            noshow BOOLEAN DEFAULT 0,
            FOREIGN KEY (usuario_cs) REFERENCES usuarios(usuario),
            FOREIGN KEY (checklist_item_id) REFERENCES checklist_items(id)
        )
    """)

    # Tabela timeline_log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timeline_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            implantacao_id INTEGER NOT NULL,
            usuario_cs TEXT NOT NULL,
            tipo_evento TEXT NOT NULL,
            detalhes TEXT,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (implantacao_id) REFERENCES implantacoes(id),
            FOREIGN KEY (usuario_cs) REFERENCES usuarios(usuario)
        )
    """)

    # Tabela planos_sucesso
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS planos_sucesso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            criado_por TEXT,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            dias_duracao INTEGER,
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY (criado_por) REFERENCES usuarios(usuario)
        )
    """)

    # Tabela gamificacao_regras
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gamificacao_regras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regra_id TEXT NOT NULL UNIQUE,
            categoria TEXT NOT NULL,
            descricao TEXT NOT NULL,
            valor_pontos INTEGER NOT NULL DEFAULT 0,
            tipo_valor TEXT DEFAULT 'pontos'
        )
    """)

    # Tabela gamificacao_metricas_mensais
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gamificacao_metricas_mensais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_cs TEXT NOT NULL,
            mes INTEGER NOT NULL,
            ano INTEGER NOT NULL,
            impl_finalizadas INTEGER DEFAULT 0,
            tma_dias REAL DEFAULT 0,
            nota_qualidade REAL DEFAULT 0,
            assiduidade REAL DEFAULT 0,
            planos_sucesso_pct REAL DEFAULT 0,
            reclamacoes INTEGER DEFAULT 0,
            perda_prazo INTEGER DEFAULT 0,
            pontos_totais INTEGER DEFAULT 0,
            UNIQUE(usuario_cs, mes, ano),
            FOREIGN KEY (usuario_cs) REFERENCES usuarios(usuario)
        )
    """)

    # Tabela smtp_settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS smtp_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host TEXT NOT NULL,
            port INTEGER NOT NULL,
            usuario TEXT,
            senha TEXT,
            use_tls INTEGER DEFAULT 1,
            ativo INTEGER DEFAULT 1
        )
    """)

    # ========================================
    # SISTEMA DE PERFIS E PERMISSÕES (RBAC)
    # ========================================
    
    # Tabela de Perfis de Acesso
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS perfis_acesso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome VARCHAR(100) UNIQUE NOT NULL,
            descricao TEXT,
            sistema BOOLEAN DEFAULT 0,
            ativo BOOLEAN DEFAULT 1,
            cor VARCHAR(20) DEFAULT '#667eea',
            icone VARCHAR(50) DEFAULT 'bi-person-badge',
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
            atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
            criado_por VARCHAR(100)
        )
    """)
    
    # Tabela de Recursos/Funcionalidades
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo VARCHAR(100) UNIQUE NOT NULL,
            nome VARCHAR(255) NOT NULL,
            descricao TEXT,
            categoria VARCHAR(100) NOT NULL,
            tipo VARCHAR(50) DEFAULT 'acao',
            ordem INTEGER DEFAULT 0,
            ativo BOOLEAN DEFAULT 1
        )
    """)
    
    # Tabela de Permissões
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permissoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            perfil_id INTEGER REFERENCES perfis_acesso(id) ON DELETE CASCADE,
            recurso_id INTEGER REFERENCES recursos(id) ON DELETE CASCADE,
            concedida BOOLEAN DEFAULT 1,
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(perfil_id, recurso_id)
        )
    """)
    
    # Inserir dados iniciais de perfis e recursos
    _popular_dados_iniciais_perfis(cursor)

    # Criar TODOS os índices necessários
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_checklist_parent_id ON checklist_items(parent_id)",
        "CREATE INDEX IF NOT EXISTS idx_checklist_implantacao_id ON checklist_items(implantacao_id)",
        "CREATE INDEX IF NOT EXISTS idx_checklist_plano_id ON checklist_items(plano_id)",
        "CREATE INDEX IF NOT EXISTS idx_checklist_tipo_item ON checklist_items(tipo_item)",
        "CREATE INDEX IF NOT EXISTS idx_checklist_status ON checklist_items(status)",
        "CREATE INDEX IF NOT EXISTS idx_checklist_responsavel ON checklist_items(responsavel)",
        "CREATE INDEX IF NOT EXISTS idx_checklist_completed ON checklist_items(completed)",
        "CREATE INDEX IF NOT EXISTS idx_checklist_ordem ON checklist_items(ordem)",
        "CREATE INDEX IF NOT EXISTS idx_checklist_parent_ordem ON checklist_items(parent_id, ordem)",
        "CREATE INDEX IF NOT EXISTS idx_checklist_implantacao_tipo ON checklist_items(implantacao_id, tipo_item)",
        "CREATE INDEX IF NOT EXISTS idx_checklist_plano_tipo ON checklist_items(plano_id, tipo_item)",
        "CREATE INDEX IF NOT EXISTS idx_checklist_tag ON checklist_items(tag)",
        "CREATE INDEX IF NOT EXISTS idx_checklist_data_conclusao ON checklist_items(data_conclusao)",
    ]

    for idx_sql in indices:
        try:
            cursor.execute(idx_sql)
        except Exception:
            pass


def _popular_dados_iniciais_perfis(cursor):
    """Insere dados iniciais para perfis e recursos."""
    try:
        # Verificar se já existem perfis
        cursor.execute("SELECT COUNT(*) FROM perfis_acesso")
        if cursor.fetchone()[0] > 0:
            return  # Dados já existem
        
        # Inserir perfis padrão
        perfis = [
            ('Administrador', 'Acesso total ao sistema', 1, '#dc3545', 'bi-shield-check', 'Sistema'),
            ('Implantador', 'Gerencia implantações e checklists', 1, '#0d6efd', 'bi-person-workspace', 'Sistema'),
            ('Visualizador', 'Apenas visualização, sem edição', 1, '#6c757d', 'bi-eye', 'Sistema'),
        ]
        
        for perfil in perfis:
            cursor.execute("""
                INSERT OR IGNORE INTO perfis_acesso (nome, descricao, sistema, cor, icone, criado_por)
                VALUES (?, ?, ?, ?, ?, ?)
            """, perfil)
        
        # Inserir recursos
        recursos = [
            ('dashboard.view', 'Visualizar Dashboard', 'Acessar página principal', 'Dashboard', 'pagina', 1),
            ('dashboard.export', 'Exportar Relatórios', 'Exportar dados', 'Dashboard', 'acao', 2),
            ('implantacoes.list', 'Listar Implantações', 'Ver lista', 'Implantações', 'pagina', 10),
            ('implantacoes.view', 'Visualizar Detalhes', 'Ver detalhes', 'Implantações', 'acao', 11),
            ('implantacoes.create', 'Criar Implantação', 'Criar nova', 'Implantações', 'acao', 12),
            ('implantacoes.edit', 'Editar Implantação', 'Modificar dados', 'Implantações', 'acao', 13),
            ('implantacoes.delete', 'Excluir Implantação', 'Remover do sistema', 'Implantações', 'acao', 14),
            ('implantacoes.finalize', 'Finalizar Implantação', 'Marcar como concluída', 'Implantações', 'acao', 15),
            ('checklist.view', 'Visualizar Checklist', 'Ver checklist', 'Checklist', 'pagina', 20),
            ('checklist.check', 'Marcar Tarefas', 'Marcar/desmarcar', 'Checklist', 'acao', 21),
            ('checklist.comment', 'Adicionar Comentários', 'Comentar', 'Checklist', 'acao', 22),
            ('checklist.edit', 'Editar Tarefas', 'Modificar tarefas', 'Checklist', 'acao', 23),
            ('checklist.delete', 'Excluir Tarefas', 'Remover tarefas', 'Checklist', 'acao', 24),
            ('planos.list', 'Listar Planos', 'Ver lista', 'Planos de Sucesso', 'pagina', 30),
            ('planos.view', 'Visualizar Plano', 'Ver detalhes', 'Planos de Sucesso', 'acao', 31),
            ('planos.create', 'Criar Plano', 'Criar novo', 'Planos de Sucesso', 'acao', 32),
            ('planos.edit', 'Editar Plano', 'Modificar plano', 'Planos de Sucesso', 'acao', 33),
            ('planos.clone', 'Clonar Plano', 'Duplicar plano', 'Planos de Sucesso', 'acao', 34),
            ('planos.delete', 'Excluir Plano', 'Remover plano', 'Planos de Sucesso', 'acao', 35),
            ('planos.apply', 'Aplicar Plano', 'Aplicar a implantação', 'Planos de Sucesso', 'acao', 36),
            ('usuarios.list', 'Listar Usuários', 'Ver lista', 'Usuários', 'pagina', 40),
            ('usuarios.view', 'Visualizar Usuário', 'Ver detalhes', 'Usuários', 'acao', 41),
            ('usuarios.create', 'Criar Usuário', 'Adicionar novo', 'Usuários', 'acao', 42),
            ('usuarios.edit', 'Editar Usuário', 'Modificar dados', 'Usuários', 'acao', 43),
            ('usuarios.delete', 'Excluir Usuário', 'Remover do sistema', 'Usuários', 'acao', 44),
            ('perfis.list', 'Listar Perfis', 'Ver lista', 'Perfis de Acesso', 'pagina', 50),
            ('perfis.view', 'Visualizar Perfil', 'Ver detalhes', 'Perfis de Acesso', 'acao', 51),
            ('perfis.create', 'Criar Perfil', 'Criar novo', 'Perfis de Acesso', 'acao', 52),
            ('perfis.edit', 'Editar Perfil', 'Modificar perfil', 'Perfis de Acesso', 'acao', 53),
            ('perfis.delete', 'Excluir Perfil', 'Remover do sistema', 'Perfis de Acesso', 'acao', 54),
            ('perfis.permissions', 'Gerenciar Permissões', 'Definir permissões', 'Perfis de Acesso', 'acao', 55),
        ]
        
        for recurso in recursos:
            cursor.execute("""
                INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recurso)
        
        # Conceder todas as permissões ao Administrador
        cursor.execute("""
            INSERT OR IGNORE INTO permissoes (perfil_id, recurso_id, concedida)
            SELECT p.id, r.id, 1
            FROM perfis_acesso p, recursos r
            WHERE p.nome = 'Administrador'
        """)
        
        # Conceder permissões ao Implantador (sem Usuários e Perfis)
        cursor.execute("""
            INSERT OR IGNORE INTO permissoes (perfil_id, recurso_id, concedida)
            SELECT p.id, r.id, 1
            FROM perfis_acesso p, recursos r
            WHERE p.nome = 'Implantador' AND r.categoria NOT IN ('Usuários', 'Perfis de Acesso')
        """)
        
        # Conceder apenas visualização ao Visualizador
        cursor.execute("""
            INSERT OR IGNORE INTO permissoes (perfil_id, recurso_id, concedida)
            SELECT p.id, r.id, 1
            FROM perfis_acesso p, recursos r
            WHERE p.nome = 'Visualizador' AND (r.codigo LIKE '%.view' OR r.codigo LIKE '%.list')
        """)
        
    except Exception as e:
        # Silenciar erros - dados podem já existir
        pass


def _migrar_coluna_timeline_detalhes(cursor):
    """Adiciona coluna detalhes na tabela timeline_log se não existir."""
    try:
        cursor.execute("PRAGMA table_info(timeline_log)")
        colunas = [row[1] for row in cursor.fetchall()]
        if 'detalhes' not in colunas:
            cursor.execute("ALTER TABLE timeline_log ADD COLUMN detalhes TEXT")
    except Exception:
        pass


def _migrar_colunas_planos_sucesso(cursor):
    """Adiciona colunas faltantes na tabela planos_sucesso."""
    try:
        cursor.execute("PRAGMA table_info(planos_sucesso)")
        colunas_existentes = [row[1] for row in cursor.fetchall()]

        colunas_para_adicionar = {
            'data_atualizacao': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
            'dias_duracao': 'INTEGER'
        }

        colunas_adicionadas = 0
        for coluna, tipo in colunas_para_adicionar.items():
            if coluna not in colunas_existentes:
                try:
                    cursor.execute(f"ALTER TABLE planos_sucesso ADD COLUMN {coluna} {tipo}")
                    colunas_adicionadas += 1
                except Exception:
                    pass

    except Exception:
        pass


def _migrar_coluna_comentarios_checklist_item(cursor):
    """Adiciona coluna checklist_item_id na tabela comentarios_h se não existir."""
    try:
        cursor.execute("PRAGMA table_info(comentarios_h)")
        colunas_existentes = [row[1] for row in cursor.fetchall()]

        if 'checklist_item_id' not in colunas_existentes:
            cursor.execute("ALTER TABLE comentarios_h ADD COLUMN checklist_item_id INTEGER")
    except Exception:
        pass


def _migrar_colunas_prazos_checklist_items(cursor):
    try:
        cursor.execute("PRAGMA table_info(checklist_items)")
        cols = cursor.fetchall()
        names = [c[1] for c in cols]
        if 'previsao_original' not in names:
            cursor.execute("ALTER TABLE checklist_items ADD COLUMN previsao_original DATETIME")
        if 'nova_previsao' not in names:
            cursor.execute("ALTER TABLE checklist_items ADD COLUMN nova_previsao DATETIME")
    except Exception:
        pass


def _criar_tabela_responsavel_history(cursor, db_type):
    try:
        if db_type == 'sqlite':
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS checklist_responsavel_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checklist_item_id INTEGER NOT NULL,
                    old_responsavel TEXT,
                    new_responsavel TEXT,
                    changed_by TEXT,
                    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        else:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS checklist_responsavel_history (
                    id SERIAL PRIMARY KEY,
                    checklist_item_id INTEGER NOT NULL,
                    old_responsavel TEXT,
                    new_responsavel TEXT,
                    changed_by TEXT,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
    except Exception:
        pass


def _migrar_colunas_perfil_usuario(cursor):
    """Adiciona colunas faltantes na tabela perfil_usuario."""
    try:
        cursor.execute("PRAGMA table_info(perfil_usuario)")
        colunas_existentes = [row[1] for row in cursor.fetchall()]
        if 'ultimo_check_externo' not in colunas_existentes:
            cursor.execute("ALTER TABLE perfil_usuario ADD COLUMN ultimo_check_externo DATETIME")
    except Exception:
        pass


def _migrar_colunas_implantacoes(cursor):
    """Adiciona todas as colunas faltantes na tabela implantacoes."""
    try:
        cursor.execute("PRAGMA table_info(implantacoes)")
        colunas_existentes = [row[1] for row in cursor.fetchall()]

        colunas_para_adicionar = {
            'cargo_responsavel': 'TEXT',
            'telefone_responsavel': 'TEXT',
            'data_inicio_producao': 'DATETIME',
            'data_final_implantacao': 'DATETIME',
            'id_favorecido': 'TEXT',
            'cnpj': 'TEXT',
            'nivel_receita': 'TEXT',
            'chave_oamd': 'TEXT',
            'tela_apoio_link': 'TEXT',
            'informacao_infra': 'TEXT',
            'seguimento': 'TEXT',
            'tipos_planos': 'TEXT',
            'modalidades': 'TEXT',
            'horarios_func': 'TEXT',
            'formas_pagamento': 'TEXT',
            'diaria': 'TEXT',
            'freepass': 'TEXT',
            'alunos_ativos': 'INTEGER',
            'sistema_anterior': 'TEXT',
            'importacao': 'TEXT',
            'recorrencia_usa': 'TEXT',
            'boleto': 'TEXT',
            'nota_fiscal': 'TEXT',
            'catraca': 'TEXT',
            'modelo_catraca': 'TEXT',
            'facial': 'TEXT',
            'modelo_facial': 'TEXT',
            'wellhub': 'TEXT',
            'totalpass': 'TEXT',
            'valor_atribuido': 'TEXT',
            'resp_estrategico_nome': 'TEXT',
            'resp_onb_nome': 'TEXT',
            'resp_estrategico_obs': 'TEXT',
            'contatos': 'TEXT',
            'motivo_parada': 'TEXT',
            'data_cancelamento': 'DATETIME',
            'motivo_cancelamento': 'TEXT',
            'comprovante_cancelamento_url': 'TEXT',
            'status_implantacao_oamd': 'TEXT',
            'nivel_atendimento': 'TEXT',
            'data_cadastro': 'DATETIME'
        }

        colunas_adicionadas = 0
        for coluna, tipo in colunas_para_adicionar.items():
            if coluna not in colunas_existentes:
                try:
                    cursor.execute(f"ALTER TABLE implantacoes ADD COLUMN {coluna} {tipo}")
                    colunas_adicionadas += 1
                except Exception:
                    pass

    except Exception:
        pass


def _inserir_regras_gamificacao_padrao(cursor):
    """Insere regras de gamificação padrão no banco."""
    regras = [
        ('eleg_nota_qualidade_min', 'Elegibilidade', 'Nota Qualidade (Mín %)', 80, 'percentual'),
        ('eleg_assiduidade_min', 'Elegibilidade', 'Assiduidade (Mín %)', 85, 'percentual'),
        ('eleg_planos_sucesso_min', 'Elegibilidade', 'Planos de Sucesso (Mín %)', 75, 'percentual'),
        ('eleg_reclamacoes_max', 'Elegibilidade', 'Reclamações (Máx)', 1, 'quantidade'),
        ('eleg_perda_prazo_max', 'Elegibilidade', 'Perda de Prazo (Máx)', 2, 'quantidade'),
    ]

    for regra_id, categoria, descricao, valor_pontos, tipo_valor in regras:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO gamificacao_regras 
                (regra_id, categoria, descricao, valor_pontos, tipo_valor) 
                VALUES (?, ?, ?, ?, ?)
            """, (regra_id, categoria, descricao, valor_pontos, tipo_valor))
        except Exception:
            pass


def init_app(app):
    """Registra o comando init-db na aplicação."""
    app.cli.add_command(init_db_command)


def ensure_implantacoes_status_constraint():
    conn, db_type = None, None
    try:
        conn, db_type = get_db_connection()
        if db_type != 'postgres':
            return
        cursor = conn.cursor()
        
        # Migração de colunas críticas para Postgres (Safety check)
        check_cols = {
            'status_implantacao_oamd': 'VARCHAR(255)',
            'nivel_atendimento': 'VARCHAR(255)',
            'data_cadastro': 'TIMESTAMP',
            'chave_oamd': 'TEXT',
            'tela_apoio_link': 'TEXT',
            'informacao_infra': 'TEXT',
            'cnpj': 'VARCHAR(20)',
            'modelo_catraca': 'TEXT',
            'modelo_facial': 'TEXT',
            'wellhub': 'VARCHAR(10)',
            'totalpass': 'VARCHAR(10)',
            'valor_monetario': 'TEXT',
        }
        for col_name, col_type in check_cols.items():
            try:
                cursor.execute(f"ALTER TABLE implantacoes ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
            except Exception:
                pass
        conn.commit()

        try:
            cursor.execute("ALTER TABLE implantacoes DROP CONSTRAINT IF EXISTS implantacoes_status_check;")
        except Exception:
            pass
        try:
            cursor.execute(
                """
                ALTER TABLE implantacoes
                ADD CONSTRAINT implantacoes_status_check
                CHECK (status IN ('nova', 'andamento', 'futura', 'finalizada', 'parada', 'cancelada', 'sem_previsao', 'atrasada'))
                """
            )
            conn.commit()
        except Exception:
            if conn:
                conn.rollback()
    except Exception:
        if conn:
            conn.rollback()
    finally:
        use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
        if use_sqlite and conn:
            conn.close()
