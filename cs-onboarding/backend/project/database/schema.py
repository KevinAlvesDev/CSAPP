import click

from flask import current_app

from flask.cli import with_appcontext



from ..db import get_db_connection



def init_app(app):

    """Inicializa as extensões e comandos do banco de dados no Flask."""

    app.cli.add_command(init_db_command)



def init_db():

    """

    Realiza o Seeding do banco de dados (inserção de dados iniciais).

    A criação e alteração do schema (DDL) é gerenciada exclusivamente pelo Alembic.

    """

    conn, db_type = None, None

    try:

        conn, db_type = get_db_connection()

        cursor = conn.cursor()



        # --------------------------------------------------------------------------

        # SEEDING: Inserção de dados básicos obrigatórios para o funcionamento

        # --------------------------------------------------------------------------



        # Regras de gamificação padrão
        _inserir_regras_gamificacao_padrao(cursor, db_type)
        _replicar_regras_gamificacao_para_todos_contextos(cursor, db_type)
        

        # Perfis de Acesso e Recursos (RBAC)

        _popular_dados_iniciais_perfis(cursor, db_type)

        

        # Dados de Configuração (Tags, Status, etc)

        _popular_dados_configuracao(cursor, db_type)

        

        # Garantir recursos específicos

        _garantir_recurso_dispensa_checklist(cursor, db_type)



        conn.commit()

        current_app.logger.info("Seeding do banco de dados concluído com sucesso.")



    except Exception as e:

        current_app.logger.error(f"Erro ao realizar seeding do DB: {e}", exc_info=True)

        if conn:

            conn.rollback()

    finally:

        if conn:

            conn.close()



@click.command("init-db")

@with_appcontext

def init_db_command():

    """Popula o banco de dados com dados iniciais via linha de comando."""

    init_db()

    click.echo("Seeding do banco de dados concluído.")



def _inserir_regras_gamificacao_padrao(cursor, db_type):
    """Insere regras básicas de gamificação para todos os contextos suportados."""
    try:
        regras = [
            ("impl_finalizada", "Onboarding", "Finalizar uma implantação", 100, "pontos"),
            ("tarefa_concluida", "Checklist", "Concluir uma tarefa do checklist", 10, "pontos"),
            ("plano_sucesso_vinculado", "Planos", "Vincular um plano de sucesso", 50, "pontos"),
        ]
        contextos = ("onboarding", "grandes_contas", "ongoing")

        for contexto in contextos:
            for regra in regras:
                regra_id, categoria, descricao, valor_pontos, tipo_valor = regra
                if db_type == "postgres":
                    cursor.execute(
                        """
                        INSERT INTO gamificacao_regras
                            (regra_id, contexto, categoria, descricao, valor_pontos, tipo_valor)
                        SELECT %s, %s, %s, %s, %s, %s
                        WHERE NOT EXISTS (
                            SELECT 1 FROM gamificacao_regras
                            WHERE regra_id = %s AND contexto = %s
                        )
                        """,
                        (regra_id, contexto, categoria, descricao, valor_pontos, tipo_valor,
                         regra_id, contexto),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO gamificacao_regras
                            (regra_id, contexto, categoria, descricao, valor_pontos, tipo_valor)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (regra_id, contexto, categoria, descricao, valor_pontos, tipo_valor),
                    )
    except Exception as e:
        current_app.logger.warning(f"Erro ao inserir regras de gamificação: {e}", exc_info=True)


def _replicar_regras_gamificacao_para_todos_contextos(cursor, db_type):
    """Sem-op: replicação já feita em _inserir_regras_gamificacao_padrao."""
    pass


def _popular_dados_iniciais_perfis(cursor, db_type):
    """Insere dados iniciais para perfis, contextos, recursos e permissões padrão."""
    try:
        # ── 1. Perfis base ─────────────────────────────────────────────────────
        perfis = [
            ("Administrador", "Acesso total ao sistema",                      True, "#dc3545", "bi-shield-check"),
            ("Gerente",       "Gestão de equipe e indicadores",               True, "#198754", "bi-person-check"),
            ("Coordenador",   "Coordenação operacional",                      True, "#fd7e14", "bi-person-gear"),
            ("Implantador",   "Gerencia implantações e checklists",           True, "#0d6efd", "bi-person-workspace"),
            ("Sem Acesso",    "Usuário aguardando liberação de acesso",       True, "#adb5bd", "bi-lock"),
        ]
        for perfil in perfis:
            if db_type == "postgres":
                cursor.execute("""
                    INSERT INTO perfis_acesso (nome, descricao, sistema, cor, icone)
                    SELECT %s, %s, %s, %s, %s
                    WHERE NOT EXISTS (SELECT 1 FROM perfis_acesso WHERE nome = %s)
                """, perfil + (perfil[0],))
            else:
                cursor.execute("""
                    INSERT OR IGNORE INTO perfis_acesso (nome, descricao, sistema, cor, icone)
                    VALUES (?, ?, ?, ?, ?)
                """, perfil)

        # ── 2. Perfis por contexto — apenas módulos permitidos por perfil ──────
        MODULOS_POR_PERFIL = {
            "Administrador": ["onboarding", "ongoing", "grandes_contas"],
            "Gerente":       ["onboarding", "ongoing", "grandes_contas"],
            "Coordenador":   ["onboarding", "ongoing"],
            "Implantador":   ["onboarding"],
            "Sem Acesso":    ["onboarding", "ongoing", "grandes_contas"],
        }
        for nome_perfil, contextos in MODULOS_POR_PERFIL.items():
            for ctx in contextos:
                if db_type == "postgres":
                    cursor.execute("""
                        INSERT INTO perfis_acesso_contexto
                            (contexto, nome, descricao, sistema, ativo, cor, icone, criado_por)
                        SELECT %s, p.nome, p.descricao, p.sistema, p.ativo, p.cor, p.icone, 'seed'
                        FROM perfis_acesso p
                        WHERE p.nome = %s
                        AND NOT EXISTS (
                            SELECT 1 FROM perfis_acesso_contexto
                            WHERE contexto = %s AND nome = %s
                        )
                    """, (ctx, nome_perfil, ctx, nome_perfil))
                else:
                    cursor.execute("""
                        INSERT OR IGNORE INTO perfis_acesso_contexto
                            (contexto, nome, descricao, sistema, ativo, cor, icone, criado_por)
                        SELECT ?, p.nome, p.descricao, p.sistema, p.ativo, p.cor, p.icone, 'seed'
                        FROM perfis_acesso p WHERE p.nome = ?
                    """, (ctx, nome_perfil))

        # ── 3. Recursos — cobertura total do sistema ───────────────────────────
        recursos = [
            # Dashboard
            ("dashboard.view",              "Visualizar Dashboard",             "Acessar página principal",                  "Dashboard",         "pagina", 1),
            # Implantações
            ("implantacoes.list",           "Listar Implantações",              "Ver lista de implantações",                 "Implantações",      "pagina", 10),
            ("implantacoes.create",         "Criar Implantação",                "Criar nova implantação",                    "Implantações",      "acao",   11),
            ("implantacoes.view_details",   "Ver Detalhes da Implantação",      "Acessar página de detalhes",                "Implantações",      "acao",   12),
            ("implantacoes.edit_details",   "Editar Dados da Implantação",      "Editar informações gerais",                 "Implantações",      "acao",   13),
            ("implantacoes.delete",         "Excluir Implantação",              "Excluir permanentemente",                   "Implantações",      "acao",   14),
            ("implantacoes.transfer",       "Transferir Implantação",           "Transferir para outro CS",                  "Implantações",      "acao",   15),
            ("implantacoes.change_status",  "Alterar Status",                   "Iniciar, parar, finalizar, cancelar...",    "Implantações",      "acao",   16),
            ("implantacoes.ai_summary",     "Gerar Resumo por IA",              "Gerar resumo automático da implantação",    "Implantações",      "acao",   17),
            # Checklist
            ("checklist.view",              "Visualizar Checklist",             "Ver tarefas da implantação",                "Checklist",         "pagina", 20),
            ("checklist.check",             "Marcar/Desmarcar Tarefa",          "Concluir ou reabrir uma tarefa",            "Checklist",         "acao",   21),
            ("checklist.create_item",       "Criar Item de Checklist",          "Adicionar nova tarefa",                     "Checklist",         "acao",   22),
            ("checklist.edit_item",         "Editar Item de Checklist",         "Alterar nome/descrição de uma tarefa",      "Checklist",         "acao",   23),
            ("checklist.delete",            "Excluir Item de Checklist",        "Remover tarefa permanentemente",            "Checklist",         "acao",   24),
            ("checklist.move_item",         "Mover/Reordenar Item",             "Mover tarefa na hierarquia",                "Checklist",         "acao",   25),
            ("checklist.dispense",          "Dispensar Item de Checklist",      "Marcar tarefa como dispensada",             "Checklist",         "acao",   26),
            ("checklist.edit_responsible",  "Alterar Responsável",              "Atribuir responsável à tarefa",             "Checklist",         "acao",   27),
            ("checklist.edit_deadline",     "Alterar Prazo",                    "Definir/alterar prazo da tarefa",           "Checklist",         "acao",   28),
            # Comentários
            ("comentarios.view",            "Visualizar Comentários",           "Ver histórico de comentários",              "Comentários",       "pagina", 30),
            ("comentarios.create",          "Criar Comentário",                 "Adicionar novo comentário",                 "Comentários",       "acao",   31),
            ("comentarios.edit",            "Editar Comentário",                "Alterar comentário existente",              "Comentários",       "acao",   32),
            ("comentarios.delete",          "Excluir Comentário",               "Remover comentário permanentemente",        "Comentários",       "acao",   33),
            ("comentarios.send_email",      "Enviar E-mail de Comentário",      "Disparar e-mail a partir de comentário",    "Comentários",       "acao",   34),
            # Planos de Sucesso
            ("planos.list",                 "Listar Planos de Sucesso",         "Ver planos disponíveis",                    "Planos de Sucesso", "pagina", 40),
            ("planos.create",               "Criar Plano de Sucesso",           "Criar novo plano de sucesso",               "Planos de Sucesso", "acao",   41),
            ("planos.edit",                 "Editar Plano de Sucesso",          "Alterar dados do plano",                    "Planos de Sucesso", "acao",   42),
            ("planos.delete",               "Excluir Plano de Sucesso",         "Remover plano permanentemente",             "Planos de Sucesso", "acao",   43),
            ("planos.apply",                "Aplicar Plano à Implantação",      "Vincular plano a uma implantação",          "Planos de Sucesso", "acao",   44),
            ("planos.complete",             "Concluir Plano",                   "Marcar plano como concluído",               "Planos de Sucesso", "acao",   45),
            # Avisos
            ("avisos.view",                 "Visualizar Avisos",                "Ver avisos da implantação",                 "Avisos",            "pagina", 50),
            ("avisos.create",               "Criar Aviso",                      "Adicionar aviso à implantação",             "Avisos",            "acao",   51),
            ("avisos.edit",                 "Editar Aviso",                     "Alterar aviso existente",                   "Avisos",            "acao",   52),
            ("avisos.delete",               "Excluir Aviso",                    "Remover aviso permanentemente",             "Avisos",            "acao",   53),
            # Analytics
            ("analytics.view",              "Visualizar Analytics",             "Acessar dashboard analítico",               "Analytics",         "pagina", 60),
            # Timeline
            ("timeline.view",               "Visualizar Timeline",              "Ver histórico de atividades",               "Timeline",          "pagina", 70),
            ("timeline.export",             "Exportar Timeline (CSV)",          "Baixar histórico em CSV",                   "Timeline",          "acao",   71),
            # Gamificação
            ("gamificacao.view_report",     "Visualizar Relatório Gamificação", "Ver ranking e pontuações",                  "Gamificação",       "pagina", 80),
            ("gamificacao.manage_rules",    "Gerenciar Regras de Gamificação",  "Criar/editar regras de pontuação",          "Gamificação",       "acao",   81),
            ("gamificacao.manage_metrics",  "Preencher Métricas Mensais",       "Registrar métricas de desempenho",          "Gamificação",       "acao",   82),
            # Integração OAMD
            ("oamd.consult",                "Consultar Empresa no OAMD",        "Buscar dados da empresa no OAMD",           "Integrações",       "acao",   90),
            ("oamd.apply",                  "Aplicar Dados do OAMD",            "Importar dados do OAMD para implantação",   "Integrações",       "acao",   91),
            # Integração JIRA
            ("jira.view",                   "Visualizar Issues JIRA",           "Ver issues vinculadas à implantação",       "Integrações",       "pagina", 100),
            ("jira.create",                 "Criar Issue no JIRA",              "Abrir nova issue no JIRA",                  "Integrações",       "acao",   101),
            ("jira.delete",                 "Desvincular Issue do JIRA",        "Remover vínculo de issue",                  "Integrações",       "acao",   102),
            # Carteira
            ("carteira.view",               "Visualizar Carteira",              "Ver definição de carteira",                 "Carteira",          "pagina", 110),
            ("carteira.edit",               "Editar Definição de Carteira",     "Alterar configuração de carteira",          "Carteira",          "acao",   111),
            # Usuários
            ("usuarios.view",               "Visualizar Usuários",              "Ver lista de usuários do sistema",          "Usuários",          "pagina", 120),
            ("usuarios.edit_access",        "Gerenciar Acesso de Usuário",      "Atribuir/alterar perfil de um usuário",     "Usuários",          "acao",   121),
            ("usuarios.delete",             "Excluir Usuário",                  "Remover usuário do sistema",                "Usuários",          "acao",   122),
            # Perfis de Acesso
            ("perfis.view",                 "Visualizar Perfis de Acesso",      "Ver lista de perfis configurados",          "Perfis de Acesso",  "pagina", 130),
            ("perfis.create",               "Criar Perfil de Acesso",           "Criar novo perfil com permissões",          "Perfis de Acesso",  "acao",   131),
            ("perfis.edit",                 "Editar Perfil de Acesso",          "Alterar permissões de um perfil",           "Perfis de Acesso",  "acao",   132),
            ("perfis.delete",               "Excluir Perfil de Acesso",         "Remover perfil permanentemente",            "Perfis de Acesso",  "acao",   133),
            ("perfis.clone",                "Duplicar Perfil de Acesso",        "Criar cópia de um perfil existente",        "Perfis de Acesso",  "acao",   134),
            # Configurações
            ("config.tags",                 "Gerenciar Tags",                   "Criar/editar tags do sistema",              "Configurações",     "acao",   140),
            ("config.status",               "Gerenciar Status de Implantação",  "Criar/editar status personalizados",        "Configurações",     "acao",   141),
            ("config.gamification",         "Configurar Gamificação",           "Ajustar configurações de gamificação",      "Configurações",     "acao",   142),
            ("config.backup",               "Backup do Banco de Dados",         "Exportar backup completo do banco",         "Configurações",     "acao",   143),
            ("config.smtp",                 "Configurar E-mail (SMTP)",         "Definir servidor de envio de e-mails",      "Configurações",     "acao",   144),
            # Chat interno
            ("chat.view",                   "Visualizar Chat",                  "Acessar chat interno entre usuários",       "Comunicação",       "pagina", 150),
            ("chat.send",                   "Enviar Mensagens no Chat",         "Enviar mensagens no chat interno",          "Comunicação",       "acao",   151),
        ]
        for rec in recursos:
            if db_type == "postgres":
                cursor.execute("""
                    INSERT INTO recursos (codigo, nome, descricao, categoria, tipo, ordem)
                    SELECT %s, %s, %s, %s, %s, %s
                    WHERE NOT EXISTS (SELECT 1 FROM recursos WHERE codigo = %s)
                """, rec + (rec[0],))
            else:
                cursor.execute("""
                    INSERT OR IGNORE INTO recursos (codigo, nome, descricao, categoria, tipo, ordem)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, rec)

        # ── 4. Permissões padrão por perfil ───────────────────────────────────
        _TODOS = [r[0] for r in recursos]

        PERMISSOES_PADRAO = {
            "Administrador": _TODOS,
            "Gerente": [c for c in _TODOS if c not in {
                "usuarios.delete",
                "perfis.create", "perfis.edit", "perfis.delete", "perfis.clone",
                "config.backup", "config.smtp",
            }],
            "Coordenador": [
                "dashboard.view",
                "implantacoes.list", "implantacoes.create", "implantacoes.view_details",
                "implantacoes.edit_details", "implantacoes.change_status", "implantacoes.ai_summary",
                "checklist.view", "checklist.check", "checklist.create_item", "checklist.edit_item",
                "checklist.delete", "checklist.move_item", "checklist.dispense", "checklist.edit_responsible",
                "checklist.edit_deadline",
                "comentarios.view", "comentarios.create", "comentarios.edit", "comentarios.send_email",
                "planos.list", "planos.create", "planos.edit", "planos.apply", "planos.complete",
                "avisos.view", "avisos.create", "avisos.edit",
                "analytics.view",
                "timeline.view",
                "gamificacao.view_report", "gamificacao.manage_metrics",
                "oamd.consult", "oamd.apply",
                "jira.view", "jira.create",
                "carteira.view", "carteira.edit",
                "usuarios.view",
            ],
            "Implantador": [
                "dashboard.view",
                "implantacoes.list", "implantacoes.create", "implantacoes.view_details",
                "implantacoes.edit_details",
                "checklist.view", "checklist.check", "checklist.create_item", "checklist.edit_item",
                "checklist.move_item", "checklist.edit_responsible", "checklist.edit_deadline",
                "comentarios.view", "comentarios.create", "comentarios.edit", "comentarios.send_email",
                "planos.list", "planos.apply", "planos.complete",
                "avisos.view",
                "timeline.view",
                "gamificacao.manage_metrics",
                "oamd.consult",
                "jira.view",
                "carteira.view",
            ],
            "Sem Acesso": [],
        }

        ph = "%s" if db_type == "postgres" else "?"
        for nome_perfil, codigos in PERMISSOES_PADRAO.items():
            for codigo in codigos:
                if db_type == "postgres":
                    cursor.execute("""
                        INSERT INTO permissoes_contexto (perfil_ctx_id, recurso_id, concedida, criado_em)
                        SELECT pac.id, r.id, TRUE, CURRENT_TIMESTAMP
                        FROM perfis_acesso_contexto pac
                        JOIN recursos r ON r.codigo = %s
                        WHERE pac.nome = %s
                        AND NOT EXISTS (
                            SELECT 1 FROM permissoes_contexto
                            WHERE perfil_ctx_id = pac.id AND recurso_id = r.id
                        )
                    """, (codigo, nome_perfil))
                else:
                    cursor.execute("""
                        INSERT OR IGNORE INTO permissoes_contexto (perfil_ctx_id, recurso_id, concedida, criado_em)
                        SELECT pac.id, r.id, 1, CURRENT_TIMESTAMP
                        FROM perfis_acesso_contexto pac
                        JOIN recursos r ON r.codigo = ?
                        WHERE pac.nome = ?
                    """, (codigo, nome_perfil))

    except Exception as e:
        current_app.logger.warning(f"Erro ao popular perfis/recursos: {e}", exc_info=True)



def _garantir_recurso_dispensa_checklist(cursor, db_type):

    """Garante recurso checklist.dispense."""



def _popular_dados_configuracao(cursor, db_type):

    """Insere dados de tags, status, etc."""

    # Tags

    tags = [("Ação interna", 1, "comentario"), ("Reunião", 2, "comentario")]

    for t in tags:

        if db_type == "postgres":

            cursor.execute("""

                INSERT INTO tags_sistema (nome, ordem, tipo) 

                SELECT %s, %s, %s

                WHERE NOT EXISTS (

                    SELECT 1 FROM tags_sistema WHERE nome = %s

                )

            """, t + (t[0],))

        else:

            cursor.execute("INSERT OR IGNORE INTO tags_sistema (nome, ordem, tipo) VALUES (?, ?, ?)", t)



    # Status

    statuses = [("nova", "Nova", "#6c757d", 1), ("andamento", "Em Andamento", "#0d6efd", 4)]

    for s in statuses:

        if db_type == "postgres":

            cursor.execute("""

                INSERT INTO status_implantacao (codigo, nome, cor, ordem) 

                SELECT %s, %s, %s, %s

                WHERE NOT EXISTS (

                    SELECT 1 FROM status_implantacao WHERE codigo = %s

                )

            """, s + (s[0],))

        else:

            cursor.execute("INSERT OR IGNORE INTO status_implantacao (codigo, nome, cor, ordem) VALUES (?, ?, ?, ?)", s)
