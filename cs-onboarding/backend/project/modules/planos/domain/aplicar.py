"""
Módulo de Aplicação de Planos
Aplicar e remover planos de implantações.
Princípio SOLID: Single Responsibility
"""

from datetime import date, datetime

from flask import current_app

from ....common.date_helpers import add_business_days, adjust_to_business_day
from ....common.context_profiles import resolve_context
from ....common.exceptions import DatabaseError, ValidationError
from ....db import db_connection, query_db
from .crud import _extrair_estrutura_checklist, obter_plano_completo
from .estrutura import _criar_estrutura_plano_checklist


def aplicar_plano_a_implantacao(implantacao_id: int, plano_id: int, usuario: str) -> bool:
    """
    Aplica um plano de sucesso a uma implantação.
    """
    if not implantacao_id or not plano_id:
        raise ValidationError("ID da implantação e do plano são obrigatórios")

    implantacao = query_db(
        "SELECT id, data_inicio_efetivo, data_criacao FROM implantacoes WHERE id = %s", (implantacao_id,), one=True
    )
    if not implantacao:
        raise ValidationError(f"Implantação com ID {implantacao_id} não encontrada")

    plano = obter_plano_completo(plano_id)
    if not plano:
        raise ValidationError(f"Plano com ID {plano_id} não encontrado")

    if not plano.get("ativo"):
        raise ValidationError(f"Plano '{plano['nome']}' está inativo")

    data_inicio = implantacao.get("data_inicio_efetivo") or implantacao.get("data_criacao")
    data_previsao_termino = None
    dias_duracao = plano.get("dias_duracao")

    if dias_duracao:
        try:
            base = data_inicio
            if isinstance(base, str):
                base = datetime.strptime(base[:10], "%Y-%m-%d")
            elif isinstance(base, date) and not isinstance(base, datetime):
                base = datetime.combine(base, datetime.min.time())
            if not isinstance(base, datetime):
                base = datetime.now()

            base_dia_util = adjust_to_business_day(base.date())
            data_previsao_termino = add_business_days(base_dia_util, int(dias_duracao))
            data_previsao_termino = adjust_to_business_day(data_previsao_termino)
        except Exception as e:
            current_app.logger.warning(f"Erro ao calcular previs??o t??rmino em dias ??teis: {e}")
            base_dia_util = adjust_to_business_day(datetime.now().date())
            data_previsao_termino = add_business_days(base_dia_util, int(dias_duracao))

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        try:
            # Deletar apenas comentários vinculados a checklist_items desta implantação
            # NÃO deletar comentários órfãos - eles são comentários preservados de planos anteriores
            sql_limpar_comentarios = """
                DELETE FROM comentarios_h
                WHERE checklist_item_id IN (
                    SELECT id FROM checklist_items WHERE implantacao_id = %s
                )
            """
            if db_type == "sqlite":
                sql_limpar_comentarios = sql_limpar_comentarios.replace("%s", "?")
            cursor.execute(sql_limpar_comentarios, (implantacao_id,))

            # Agora deletar os itens do checklist
            sql_limpar = "DELETE FROM checklist_items WHERE implantacao_id = %s"
            if db_type == "sqlite":
                sql_limpar = sql_limpar.replace("%s", "?")
            cursor.execute(sql_limpar, (implantacao_id,))

            _clonar_plano_para_implantacao(cursor, db_type, plano, implantacao_id, usuario)

            sql_update = """
                UPDATE implantacoes
                SET plano_sucesso_id = %s, data_atribuicao_plano = %s, data_previsao_termino = %s
                WHERE id = %s
            """
            if db_type == "sqlite":
                sql_update = sql_update.replace("%s", "?")

            cursor.execute(sql_update, (plano_id, datetime.now(), data_previsao_termino, implantacao_id))

            conn.commit()

            current_app.logger.info(
                f"Plano '{plano['nome']}' aplicado à implantação {implantacao_id} por {usuario}. Previsão de término: {data_previsao_termino}"
            )
            return True

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao aplicar plano: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao aplicar plano: {e}") from e


def aplicar_plano_a_implantacao_checklist(
    implantacao_id: int,
    plano_id: int,
    usuario: str,
    responsavel_nome: str | None = None,
    preservar_comentarios: bool = False,
) -> bool:
    """
    Aplica um plano de sucesso a uma implantação usando checklist_items.
    Clona a estrutura do plano (itens com implantacao_id = NULL) para a implantação.

    Args:
        preservar_comentarios: Se True, preserva os comentários existentes desvinculando-os
                               dos checklist_items antes de deletá-los.
    """
    if not implantacao_id or not plano_id:
        raise ValidationError("ID da implantação e do plano são obrigatórios")

    implantacao = query_db(
        "SELECT id, data_inicio_efetivo, data_criacao FROM implantacoes WHERE id = %s", (implantacao_id,), one=True
    )
    if not implantacao:
        raise ValidationError(f"Implantação com ID {implantacao_id} não encontrada")

    plano = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)
    if not plano:
        raise ValidationError(f"Plano com ID {plano_id} não encontrado")

    if not plano.get("ativo", True):
        raise ValidationError(f"Plano '{plano['nome']}' está inativo")

    data_inicio = implantacao.get("data_inicio_efetivo") or implantacao.get("data_criacao")
    data_previsao_termino = None
    dias_duracao = plano.get("dias_duracao")

    if dias_duracao:
        base = data_inicio
        if isinstance(base, str):
            try:
                base = datetime.strptime(base[:10], "%Y-%m-%d")
            except Exception:
                base = datetime.now()
        elif isinstance(base, date) and not isinstance(base, datetime):
            base = datetime.combine(base, datetime.min.time())
        if not isinstance(base, datetime):
            base = datetime.now()

        base_dia_util = adjust_to_business_day(base.date())
        data_previsao_termino = add_business_days(base_dia_util, int(dias_duracao))
        data_previsao_termino = adjust_to_business_day(data_previsao_termino)

    estrutura_plano = _extrair_estrutura_checklist(plano_id)

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        try:
            # Garantir serializacao por implantacao (evita corrida em aplicacoes concorrentes).
            sql_lock_impl = "SELECT id FROM implantacoes WHERE id = %s"
            if db_type == "postgres":
                sql_lock_impl += " FOR UPDATE"
            if db_type == "sqlite":
                sql_lock_impl = sql_lock_impl.replace("%s", "?")
            cursor.execute(sql_lock_impl, (implantacao_id,))

            # Não concluir automaticamente planos em andamento ao trocar de plano.
            # Conclusão só deve ocorrer explicitamente e com progresso válido (100%).

            # Preservar histórico do plano atual antes de trocar:
            # - garante vínculo por plano_id (legado podia estar nulo)
            # - arquiva itens removendo vínculo implantacao_id (não deleta histórico)
            plano_anterior_id = None
            sql_plano_atual = "SELECT plano_sucesso_id FROM implantacoes WHERE id = %s"
            if db_type == "sqlite":
                sql_plano_atual = sql_plano_atual.replace("%s", "?")
            cursor.execute(sql_plano_atual, (implantacao_id,))
            row_plano_atual = cursor.fetchone()
            if row_plano_atual:
                if isinstance(row_plano_atual, dict):
                    plano_anterior_id = row_plano_atual.get("plano_sucesso_id")
                else:
                    plano_anterior_id = row_plano_atual[0]

            if plano_anterior_id:
                sql_backfill_plano_id = """
                    UPDATE checklist_items
                    SET plano_id = %s
                    WHERE implantacao_id = %s
                      AND (plano_id IS NULL OR plano_id <> %s)
                """
                if db_type == "sqlite":
                    sql_backfill_plano_id = sql_backfill_plano_id.replace("%s", "?")
                cursor.execute(sql_backfill_plano_id, (plano_anterior_id, implantacao_id, plano_anterior_id))

            sql_arquivar_itens = "UPDATE checklist_items SET implantacao_id = NULL WHERE implantacao_id = %s"
            if db_type == "sqlite":
                sql_arquivar_itens = sql_arquivar_itens.replace("%s", "?")
            cursor.execute(sql_arquivar_itens, (implantacao_id,))

            # Constraint parcial do Postgres permite somente 1 plano em_andamento por processo_id.
            # Ao trocar plano, o anterior vira historico "substituido" (nao concluido).
            now = datetime.now()
            sql_desativar_em_andamento = """
                UPDATE planos_sucesso
                SET status = %s, data_atualizacao = %s
                WHERE processo_id = %s
                  AND status = 'em_andamento'
            """
            if db_type == "sqlite":
                sql_desativar_em_andamento = sql_desativar_em_andamento.replace("%s", "?")
            cursor.execute(sql_desativar_em_andamento, ("substituido", now, implantacao_id))

            # Criar instância do plano vinculada ao processo (snapshot do template)
            plano_instancia_id = _criar_instancia_plano_cursor(
                cursor, db_type, plano, estrutura_plano, implantacao_id, usuario
            )

            # Histórico preservado por padrão: não deletar comentários/itens antigos aqui.
            # preservar_comentarios permanece por compatibilidade de assinatura.

            # Responsável padrão: nome completo do usuário (fallback: email)
            if responsavel_nome and isinstance(responsavel_nome, str) and responsavel_nome.strip():
                responsavel_padrao = responsavel_nome.strip()
            else:
                try:
                    ctx = resolve_context(plano.get("contexto"))
                    perfil = query_db(
                        """
                        SELECT pu.nome
                        FROM perfil_usuario pu
                        LEFT JOIN perfil_usuario_contexto puc ON pu.usuario = puc.usuario AND puc.contexto = %s
                        WHERE pu.usuario = %s
                        """,
                        (ctx, usuario),
                        one=True,
                    )
                    responsavel_padrao = perfil.get("nome") if perfil and perfil.get("nome") else usuario
                except Exception:
                    responsavel_padrao = usuario

            _clonar_plano_para_implantacao_checklist(
                cursor,
                db_type,
                plano_instancia_id,
                implantacao_id,
                responsavel_padrao,
                data_inicio,
                int(dias_duracao or 0),
                data_previsao_termino,
            )

            sql_update = """
                UPDATE implantacoes
                SET plano_sucesso_id = %s, data_atribuicao_plano = %s, data_previsao_termino = %s
                WHERE id = %s
            """
            if db_type == "sqlite":
                sql_update = sql_update.replace("%s", "?")

            cursor.execute(sql_update, (plano_instancia_id, datetime.now(), data_previsao_termino, implantacao_id))

            conn.commit()

            current_app.logger.info(
                f"Plano '{plano['nome']}' aplicado à implantação {implantacao_id} usando checklist_items por {usuario}. Previsão: {data_previsao_termino}"
            )

            try:
                from ....common.utils import format_date_iso_for_json
                from ....db import logar_timeline

                prev_txt = format_date_iso_for_json(data_previsao_termino) if data_previsao_termino else None

                detalhe = f"Plano aplicado: '{plano.get('nome')}'"
                if prev_txt:
                    detalhe += f"; previsão de término: {prev_txt}"
                logar_timeline(implantacao_id, usuario, "plano_aplicado", detalhe)
            except Exception:
                pass

            # Limpar cache relacionado à implantação
            try:
                from ....config.cache_config import clear_implantacao_cache, clear_user_cache

                clear_implantacao_cache(implantacao_id)
                clear_user_cache(usuario)
            except Exception:
                pass

            return True

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao aplicar plano: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao aplicar plano: {e}") from e


def criar_instancia_plano_para_implantacao(
    plano_id: int,
    implantacao_id: int,
    usuario: str,
    cursor=None,
    db_type: str | None = None,
) -> int:
    """
    Cria uma instancia (snapshot) de um plano template para uma implantacao.
    Nao altera checklist_items da implantacao.
    """
    if not plano_id or not implantacao_id:
        raise ValidationError("ID do plano e da implantacao sao obrigatorios")

    plano = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)
    if not plano:
        raise ValidationError(f"Plano com ID {plano_id} nao encontrado")

    estrutura_plano = _extrair_estrutura_checklist(plano_id)

    own_conn = cursor is None
    if own_conn:
        with db_connection() as (conn, db_type):
            cursor = conn.cursor()
            plano_instancia_id = _criar_instancia_plano_cursor(
                cursor, db_type, plano, estrutura_plano, implantacao_id, usuario
            )
            conn.commit()
            return plano_instancia_id

    if not db_type:
        raise ValidationError("db_type obrigatorio quando cursor e fornecido")

    return _criar_instancia_plano_cursor(cursor, db_type, plano, estrutura_plano, implantacao_id, usuario)


def _criar_instancia_plano_cursor(cursor, db_type, plano, estrutura_plano, implantacao_id, usuario):
    def _nome_disponivel(nome):
        sql_chk = "SELECT COUNT(*) FROM planos_sucesso WHERE nome = %s"
        if db_type == "sqlite":
            sql_chk = sql_chk.replace("%s", "?")
        cursor.execute(sql_chk, (nome,))
        row = cursor.fetchone()
        if isinstance(row, dict):
            return (row.get("COUNT(*)", 0) or row.get("count", 0) or 0) == 0
        return (row[0] if row else 0) == 0

    base_nome = (plano.get("nome", "") or "").strip() or "Plano"
    nome_instancia = base_nome
    if not _nome_disponivel(nome_instancia):
        nome_instancia = f"{base_nome} (Implantacao {implantacao_id})"
    if not _nome_disponivel(nome_instancia):
        suffix = 2
        while True:
            candidato = f"{base_nome} (Implantacao {implantacao_id} #{suffix})"
            if _nome_disponivel(candidato):
                nome_instancia = candidato
                break
            suffix += 1

    sql_plano = """
        INSERT INTO planos_sucesso
        (nome, descricao, criado_por, data_criacao, data_atualizacao, dias_duracao, permite_excluir_tarefas, contexto, status, processo_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    if db_type == "sqlite":
        sql_plano = sql_plano.replace("%s", "?")

    now = datetime.now()
    cursor.execute(
        sql_plano,
        (
            nome_instancia,
            plano.get("descricao", "") or "",
            usuario,
            now,
            now,
            plano.get("dias_duracao"),
            bool(plano.get("permite_excluir_tarefas", False)),
            plano.get("contexto", "onboarding"),
            "em_andamento",
            implantacao_id,
        ),
    )

    if db_type == "postgres":
        cursor.execute("SELECT lastval()")
        plano_instancia_id = cursor.fetchone()[0]
    else:
        plano_instancia_id = cursor.lastrowid

    _criar_estrutura_plano_checklist(cursor, db_type, plano_instancia_id, estrutura_plano)
    return plano_instancia_id


def remover_plano_de_implantacao(implantacao_id: int, usuario: str, excluir_comentarios: bool = False) -> bool:
    """
    Remove o plano de sucesso de uma implantação.

    Args:
        implantacao_id: ID da implantação
        usuario: Usuário que está removendo o plano
        excluir_comentarios: Se True, exclui os comentários junto com o plano.
                            Se False (padrão), preserva os comentários na aba "Comentários".
    """
    if not implantacao_id:
        raise ValidationError("ID da implantação é obrigatório")

    implantacao = query_db("SELECT plano_sucesso_id FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)

    if not implantacao:
        raise ValidationError(f"Implantação com ID {implantacao_id} não encontrada")

    if not implantacao.get("plano_sucesso_id"):
        return True

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        try:
            if excluir_comentarios:
                # Excluir todos os comentários da implantação
                sql_excluir_comentarios = """
                    DELETE FROM comentarios_h
                    WHERE checklist_item_id IN (
                        SELECT id FROM checklist_items WHERE implantacao_id = %s
                    )
                    OR implantacao_id = %s
                """
                if db_type == "sqlite":
                    sql_excluir_comentarios = sql_excluir_comentarios.replace("%s", "?")
                cursor.execute(sql_excluir_comentarios, (implantacao_id, implantacao_id))
                current_app.logger.info(f"Comentários da implantação {implantacao_id} excluídos por {usuario}")
            else:
                # Preservar comentários: desvincular dos itens antes de deletar
                from ....modules.checklist.domain.comments import preservar_comentarios_implantacao

                preservar_comentarios_implantacao(implantacao_id, cursor=cursor, db_type=db_type)
                current_app.logger.info(f"Comentários da implantação {implantacao_id} preservados por {usuario}")

            # Deletar os itens do checklist
            sql_limpar = "DELETE FROM checklist_items WHERE implantacao_id = %s"
            if db_type == "sqlite":
                sql_limpar = sql_limpar.replace("%s", "?")
            cursor.execute(sql_limpar, (implantacao_id,))

            # Atualizar implantação para remover referência ao plano
            sql_update = """
                UPDATE implantacoes
                SET plano_sucesso_id = NULL, data_atribuicao_plano = NULL
                WHERE id = %s
            """
            if db_type == "sqlite":
                sql_update = sql_update.replace("%s", "?")
            cursor.execute(sql_update, (implantacao_id,))

            conn.commit()

            current_app.logger.info(f"Plano removido da implantação {implantacao_id} por {usuario}")

            try:
                from ....db import logar_timeline

                acao = "plano_removido"
                detalhe = f"Plano de sucesso removido da implantação por {usuario}."
                if excluir_comentarios:
                    detalhe += " Comentários excluídos."
                else:
                    detalhe += " Comentários preservados."
                logar_timeline(implantacao_id, usuario, acao, detalhe)
            except Exception:
                pass

            return True

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao remover plano: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao remover plano: {e}") from e


def _clonar_plano_para_implantacao(
    cursor, db_type: str, plano: dict, implantacao_id: int, responsavel: str | None = None
):
    """
    Clona a estrutura do plano para a implantação usando checklist_items.
    Converte itens do plano (tipo_item='plano_*') para itens de implantação (tipo_item='fase'/'grupo'/'tarefa'/'subtarefa').
    """
    plano_id = plano.get("id")
    if not plano_id:
        raise ValidationError("Plano deve ter um ID válido")

    if db_type == "postgres":
        cursor.execute(
            """
            SELECT id, parent_id, title, completed, comment, level, ordem, tipo_item, descricao, obrigatoria, status, tag
            FROM checklist_items
            WHERE plano_id = %s
            ORDER BY ordem, id
        """,
            (plano_id,),
        )
    else:
        cursor.execute(
            """
            SELECT id, parent_id, title, completed, comment, level, ordem, tipo_item, descricao, obrigatoria, status, tag
            FROM checklist_items
            WHERE plano_id = ?
            ORDER BY ordem, id
        """,
            (plano_id,),
        )

    items_plano = cursor.fetchall()

    if not items_plano:
        return

    id_map = {}

    def clonar_item(item_plano, parent_id_implantacao):
        item_id_plano = item_plano[0] if isinstance(item_plano, tuple) else item_plano["id"]
        item_plano[1] if isinstance(item_plano, tuple) else item_plano.get("parent_id")
        title = item_plano[2] if isinstance(item_plano, tuple) else item_plano["title"]
        completed = item_plano[3] if isinstance(item_plano, tuple) else item_plano.get("completed", False)
        comment = item_plano[4] if isinstance(item_plano, tuple) else item_plano.get("comment", "")
        level = item_plano[5] if isinstance(item_plano, tuple) else item_plano.get("level", 0)
        ordem = item_plano[6] if isinstance(item_plano, tuple) else item_plano.get("ordem", 0)
        tipo_item_plano = item_plano[7] if isinstance(item_plano, tuple) else item_plano.get("tipo_item", "")
        descricao = item_plano[8] if isinstance(item_plano, tuple) else item_plano.get("descricao", "")
        obrigatoria = item_plano[9] if isinstance(item_plano, tuple) else item_plano.get("obrigatoria", False)
        status = item_plano[10] if isinstance(item_plano, tuple) else item_plano.get("status", "pendente")
        tag = item_plano[11] if isinstance(item_plano, tuple) and len(item_plano) > 11 else item_plano.get("tag")

        tipo_item_implantacao = (
            tipo_item_plano.replace("plano_", "") if tipo_item_plano.startswith("plano_") else tipo_item_plano
        )

        if db_type == "postgres":
            sql_insert = """
                INSERT INTO checklist_items
                (parent_id, title, completed, comment, level, ordem, implantacao_id, plano_id, tipo_item, descricao, obrigatoria, status, responsavel, tag, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """
            cursor.execute(
                sql_insert,
                (
                    parent_id_implantacao,
                    title,
                    completed,
                    comment or descricao,
                    level,
                    ordem,
                    implantacao_id,
                    plano_id,
                    tipo_item_implantacao,
                    descricao,
                    obrigatoria,
                    status,
                    responsavel,
                    tag,
                ),
            )
            novo_id = cursor.fetchone()[0]
        else:
            sql_insert = """
                INSERT INTO checklist_items
                (parent_id, title, completed, comment, level, ordem, implantacao_id, plano_id, tipo_item, descricao, obrigatoria, status, responsavel, tag, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            cursor.execute(
                sql_insert,
                (
                    parent_id_implantacao,
                    title,
                    1 if completed else 0,
                    comment or descricao,
                    level,
                    ordem,
                    implantacao_id,
                    plano_id,
                    tipo_item_implantacao,
                    descricao,
                    1 if obrigatoria else 0,
                    status,
                    responsavel,
                    tag,
                ),
            )
            novo_id = cursor.lastrowid

        id_map[item_id_plano] = novo_id

        if db_type == "postgres":
            cursor.execute(
                """
                SELECT id, parent_id, title, completed, comment, level, ordem, tipo_item, descricao, obrigatoria, status, tag
                FROM checklist_items
                WHERE plano_id = %s AND parent_id = %s
                ORDER BY ordem, id
            """,
                (plano_id, item_id_plano),
            )
        else:
            cursor.execute(
                """
                SELECT id, parent_id, title, completed, comment, level, ordem, tipo_item, descricao, obrigatoria, status, tag
                FROM checklist_items
                WHERE plano_id = ? AND parent_id = ?
                ORDER BY ordem, id
            """,
                (plano_id, item_id_plano),
            )

        filhos = cursor.fetchall()
        for filho in filhos:
            clonar_item(filho, novo_id)

    for item in items_plano:
        parent_id_plano = item[1] if isinstance(item, tuple) else item.get("parent_id")
        if parent_id_plano is None:
            clonar_item(item, None)


def _clonar_plano_para_implantacao_checklist(
    cursor,
    db_type: str,
    plano_id: int,
    implantacao_id: int,
    responsavel_padrao: str,
    data_base,
    dias_duracao: int,
    data_previsao_termino=None,
):
    """
    Clona a estrutura do plano (itens com implantacao_id = NULL) para a implantação.
    Usa abordagem iterativa para clonar toda a árvore mantendo a hierarquia.
    IMPORTANTE: Copia também o tipo_item convertendo de 'plano_*' para o tipo de implantação.
    """
    item_map = {}

    def clone_item_recursivo(plano_item_id, new_parent_id):
        if db_type == "postgres":
            sql_item = "SELECT title, completed, comment, level, ordem, obrigatoria, tipo_item, descricao, status, responsavel, tag, dias_offset FROM checklist_items WHERE id = %s"
            cursor.execute(sql_item, (plano_item_id,))
            row = cursor.fetchone()
            if not row:
                return None

            title, completed, comment, level, ordem, obrigatoria = row[0], row[1], row[2], row[3], row[4], row[5]
            tipo_item_plano = row[6] or ""
            descricao = row[7] or ""
            status = row[8] or "pendente"
            responsavel = row[9]
            tag = row[10]
            item_dias_offset = row[11]
        else:
            sql_item = "SELECT title, completed, comment, level, ordem, obrigatoria, tipo_item, descricao, status, responsavel, tag, dias_offset FROM checklist_items WHERE id = ?"
            cursor.execute(sql_item, (plano_item_id,))
            row = cursor.fetchone()
            if not row:
                return None

            title = row[0]
            completed = bool(row[1]) if row[1] is not None else False
            comment = row[2]
            level = row[3] if row[3] is not None else 0
            ordem = row[4] if row[4] is not None else 0
            obrigatoria = bool(row[5]) if row[5] is not None else False
            tipo_item_plano = row[6] or ""
            descricao = row[7] or ""
            status = row[8] or "pendente"
            responsavel = row[9]
            tag = row[10]
            item_dias_offset = row[11]

        tipo_item_implantacao = (
            tipo_item_plano.replace("plano_", "") if tipo_item_plano.startswith("plano_") else tipo_item_plano
        )

        if not tipo_item_implantacao:
            if level == 0:
                tipo_item_implantacao = "fase"
            elif level == 1:
                tipo_item_implantacao = "grupo"
            elif level == 2:
                tipo_item_implantacao = "tarefa"
            else:
                tipo_item_implantacao = "subtarefa"

        if db_type == "postgres":
            # Calcular previsao_original individual: se dias_offset definido, usar data_base + offset (Sempre Dias Úteis)
            if item_dias_offset is not None and data_base:
                try:
                    from ....common.date_helpers import add_business_days
                    base = data_base
                    if isinstance(base, str):
                        base = datetime.strptime(base[:10], "%Y-%m-%d")
                    elif isinstance(base, date) and not isinstance(base, datetime):
                        base = datetime.combine(base, datetime.min.time())

                    previsao_original = add_business_days(base.date() if hasattr(base, 'date') else base, int(item_dias_offset))
                except Exception:
                    previsao_original = data_previsao_termino
            else:
                previsao_original = data_previsao_termino
            responsavel = responsavel_padrao
            sql_insert = """
                INSERT INTO checklist_items (parent_id, title, completed, comment, level, ordem, implantacao_id, plano_id, obrigatoria, tipo_item, descricao, status, responsavel, tag, previsao_original, nova_previsao, dias_offset, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """
            cursor.execute(
                sql_insert,
                (
                    new_parent_id,
                    title,
                    completed,
                    comment,
                    level,
                    ordem,
                    implantacao_id,
                    plano_id,
                    obrigatoria,
                    tipo_item_implantacao,
                    descricao,
                    status,
                    responsavel,
                    tag,
                    previsao_original,
                    None,
                    item_dias_offset,
                ),
            )
            result = cursor.fetchone()
            new_item_id = result[0] if result else None
        else:
            # Calcular previsao_original individual: se dias_offset definido, usar data_base + offset (Sempre Dias Úteis)
            if item_dias_offset is not None and data_base:
                try:
                    from ....common.date_helpers import add_business_days
                    base = data_base
                    if isinstance(base, str):
                        base = datetime.strptime(base[:10], "%Y-%m-%d")
                    elif isinstance(base, date) and not isinstance(base, datetime):
                        base = datetime.combine(base, datetime.min.time())

                    # PULA FINS DE SEMANA (DIAS ÚTEIS)
                    previsao_original = add_business_days(base.date() if hasattr(base, 'date') else base, int(item_dias_offset))
                except Exception:
                    previsao_original = data_previsao_termino
            else:
                previsao_original = data_previsao_termino
            responsavel = responsavel_padrao
            sql_insert = """
                INSERT INTO checklist_items (parent_id, title, completed, comment, level, ordem, implantacao_id, plano_id, obrigatoria, tipo_item, descricao, status, responsavel, tag, previsao_original, nova_previsao, dias_offset, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            cursor.execute(
                sql_insert,
                (
                    new_parent_id,
                    title,
                    1 if completed else 0,
                    comment,
                    level,
                    ordem,
                    implantacao_id,
                    plano_id,
                    1 if obrigatoria else 0,
                    tipo_item_implantacao,
                    descricao,
                    status,
                    responsavel,
                    tag,
                    previsao_original,
                    None,
                    item_dias_offset,
                ),
            )
            new_item_id = cursor.lastrowid

        if not new_item_id:
            return None

        item_map[plano_item_id] = new_item_id

        if db_type == "postgres":
            sql_filhos = "SELECT id FROM checklist_items WHERE parent_id = %s AND plano_id = %s ORDER BY ordem, id"
            cursor.execute(sql_filhos, (plano_item_id, plano_id))
            filhos = cursor.fetchall()
        else:
            sql_filhos = "SELECT id FROM checklist_items WHERE parent_id = ? AND plano_id = ? ORDER BY ordem, id"
            cursor.execute(sql_filhos, (plano_item_id, plano_id))
            filhos = cursor.fetchall()

        for filho_row in filhos:
            filho_plano_id = filho_row[0]
            clone_item_recursivo(filho_plano_id, new_item_id)

        return new_item_id

    if db_type == "postgres":
        sql_raiz = "SELECT id FROM checklist_items WHERE plano_id = %s AND parent_id IS NULL ORDER BY ordem, id"
        cursor.execute(sql_raiz, (plano_id,))
        raizes = cursor.fetchall()
    else:
        sql_raiz = "SELECT id FROM checklist_items WHERE plano_id = ? AND parent_id IS NULL ORDER BY ordem, id"
        cursor.execute(sql_raiz, (plano_id,))
        raizes = cursor.fetchall()

    for raiz_row in raizes:
        clone_item_recursivo(raiz_row[0], None)
