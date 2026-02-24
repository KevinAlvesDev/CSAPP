"""
Módulo de Comentários do Checklist
Adicionar, listar e excluir comentários.
Princípio SOLID: Single Responsibility
"""

import contextlib
import logging
from datetime import datetime, timedelta, timezone

from flask import g

from ....common.validation import sanitize_string
from ....config.cache_config import clear_dashboard_cache, clear_implantacao_cache
from ....db import db_transaction_with_lock, execute_db, logar_timeline, query_db
from .utils import _format_datetime

logger = logging.getLogger(__name__)


def add_comment_to_item(
    item_id,
    text,
    visibilidade="interno",
    usuario_email=None,
    noshow=False,
    tag=None,
    imagem_url=None,
    imagem_base64=None,
):
    """
    Adiciona um comentário ao histórico e atualiza o campo legado 'comment' no item.
    Centraliza a lógica de comentários.

    Args:
        tag: Tag do comentário (Ação interna, Reunião, No Show)
        imagem_url: URL da imagem anexada ao comentário (opcional)
        imagem_base64: Imagem em base64 (opcional, será usada como imagem_url inline)
    """
    # Se foi fornecida imagem em base64, usar ela como imagem_url inline
    if imagem_base64 and not imagem_url:
        imagem_url = imagem_base64
    try:
        item_id = int(item_id)
    except (ValueError, TypeError) as err:
        raise ValueError("item_id deve ser um inteiro válido") from err

    has_attachment = bool(imagem_url or imagem_base64)
    if (not text or not text.strip()) and not has_attachment:
        raise ValueError("Informe texto ou anexo no comentário")

    usuario_email = usuario_email or (g.user_email if hasattr(g, "user_email") else None)
    text = sanitize_string((text or "").strip(), max_length=12000, min_length=0)
    noshow = bool(noshow) or (tag == "No Show")

    with db_transaction_with_lock() as (conn, cursor, db_type):
        # 1. Verificar item
        check_query = "SELECT id, implantacao_id, title FROM checklist_items WHERE id = %s"
        if db_type == "sqlite":
            check_query = check_query.replace("%s", "?")
        cursor.execute(check_query, (item_id,))
        item = cursor.fetchone()
        if not item:
            raise ValueError(f"Item {item_id} não encontrado")

        # Handle result access
        if hasattr(item, "keys"):
            implantacao_id = item["implantacao_id"]
            item_title = item["title"]
        else:
            implantacao_id = item[1]
            item_title = item[2]

        # 2. Garantir coluna checklist_item_id, implantacao_id e tag em comentarios_h (Self-healing)
        if db_type == "postgres":
            try:
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='comentarios_h' AND column_name='checklist_item_id'"
                )
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN IF NOT EXISTS checklist_item_id INTEGER")
                    with contextlib.suppress(Exception):
                        cursor.execute(
                            "ALTER TABLE comentarios_h ADD CONSTRAINT fk_comentarios_checklist_item FOREIGN KEY (checklist_item_id) REFERENCES checklist_items(id)"
                        )
                # Garantir coluna implantacao_id
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='comentarios_h' AND column_name='implantacao_id'"
                )
                if not cursor.fetchone():
                    cursor.execute(
                        "ALTER TABLE comentarios_h ADD COLUMN IF NOT EXISTS implantacao_id INTEGER REFERENCES implantacoes(id)"
                    )
                # Garantir coluna tag
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='comentarios_h' AND column_name='tag'"
                )
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN IF NOT EXISTS tag VARCHAR(50)")
            except Exception:
                pass
        elif db_type == "sqlite":
            try:
                cursor.execute("PRAGMA table_info(comentarios_h)")
                cols = [r[1] for r in cursor.fetchall()]
                if "checklist_item_id" not in cols:
                    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN checklist_item_id INTEGER")
                if "implantacao_id" not in cols:
                    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN implantacao_id INTEGER")
                if "tag" not in cols:
                    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN tag TEXT")
            except Exception:
                pass

        # 3. Inserir no histórico (comentarios_h)
        # Usar horário local de Brasília (UTC-3)
        tz_brasilia = timezone(timedelta(hours=-3))
        now = datetime.now(tz_brasilia)
        noshow_val = noshow if db_type == "postgres" else (1 if noshow else 0)
        insert_sql = """
            INSERT INTO comentarios_h (checklist_item_id, implantacao_id, usuario_cs, texto, data_criacao, visibilidade, noshow, tag, imagem_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        if db_type == "postgres":
            insert_sql += " RETURNING id"

        if db_type == "sqlite":
            insert_sql = insert_sql.replace("%s", "?")
        cursor.execute(
            insert_sql, (item_id, implantacao_id, usuario_email, text, now, visibilidade, noshow_val, tag, imagem_url)
        )

        if db_type == "postgres":
            res_id = cursor.fetchone()
            new_id = res_id[0] if res_id else None
        else:
            new_id = cursor.lastrowid

        # 4. Atualizar campo legado 'comment' no checklist_items
        update_legacy_sql = "UPDATE checklist_items SET comment = %s, updated_at = %s WHERE id = %s"
        if db_type == "sqlite":
            update_legacy_sql = update_legacy_sql.replace("%s", "?")
        cursor.execute(update_legacy_sql, (text, now, item_id))

        # 5. Log na timeline
        try:
            detalhe = (
                f'Comentário criado — {item_title} <span class="d-none related-id" data-item-id="{item_id}"></span>'
            )
            log_sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
            if db_type == "sqlite":
                log_sql = log_sql.replace("%s", "?")
            cursor.execute(log_sql, (implantacao_id, usuario_email, "novo_comentario", detalhe, now))
        except Exception as e:
            logger.warning(f"Erro ao logar timeline: {e}")

        conn.commit()

        # Invalidar cache do dashboard para refletir novo comentário
        try:
            clear_implantacao_cache(implantacao_id)
            clear_dashboard_cache()  # Limpa cache de todos dashboards
        except Exception as e:
            logger.warning(f"Erro ao invalidar cache após criar comentário: {e}")

        # Emitir evento de domínio
        try:
            from ....core.events import ChecklistComentarioAdicionado, event_bus

            event_bus.emit(ChecklistComentarioAdicionado(
                item_id=item_id,
                implantacao_id=implantacao_id,
                autor=usuario_email or "",
                tag=tag or "",
            ))
        except Exception:
            pass

        return {
            "ok": True,
            "item_id": item_id,
            "id": new_id,
            "comentario": {
                "id": new_id,
                "texto": text,
                "usuario_cs": usuario_email,
                "data_criacao": _format_datetime(now),
                "created_at_iso": now.isoformat(),
                "visibilidade": visibilidade,
                "noshow": noshow,
                "tag": tag,
            },
        }


def listar_comentarios_implantacao(impl_id, page=1, per_page=20):
    """
    Lista todos os comentários de uma implantação com paginação.
    """
    offset = (page - 1) * per_page

    # Contagem: comentários vinculados a checklist_items desta implantação
    # + comentários órfãos (se existirem)
    count_query = """
        SELECT COUNT(*) as total
        FROM comentarios_h c
        LEFT JOIN checklist_items ci ON c.checklist_item_id = ci.id
        WHERE (ci.implantacao_id = %s)
           OR (c.implantacao_id = %s)
    """
    total_res = query_db(count_query, (impl_id, impl_id), one=True)
    total = total_res["total"] if total_res else 0

    # Lista comentários: primeiro os vinculados a itens, depois os órfãos
    comments_query = """
        SELECT
            c.id, c.texto, c.usuario_cs, c.data_criacao, c.visibilidade, c.noshow, c.imagem_url, c.tag,
            ci.id as item_id, ci.title as item_title,
            COALESCE(p.nome, c.usuario_cs) as usuario_nome
        FROM comentarios_h c
        LEFT JOIN checklist_items ci ON c.checklist_item_id = ci.id
        LEFT JOIN implantacoes i ON COALESCE(ci.implantacao_id, c.implantacao_id) = i.id
        LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
        LEFT JOIN perfil_usuario_contexto puc ON c.usuario_cs = puc.usuario AND puc.contexto = COALESCE(i.contexto, 'onboarding')
        WHERE
            -- Robustez máxima: considera vinculado se o item pertencer à implantação
            -- OU se o próprio comentário apontar para a implantação (mesmo que item deletado/nulo)
            ci.implantacao_id = %s
            OR
            c.implantacao_id = %s

        ORDER BY data_criacao DESC
        LIMIT %s OFFSET %s
    """
    comments = query_db(comments_query, (impl_id, impl_id, per_page, offset))

    formatted_comments = []
    for c in comments:
        c_dict = dict(c)
        # Store ISO BEFORE formatting for display
        raw_date = c_dict.get("data_criacao")
        if hasattr(raw_date, "isoformat"):
            c_dict["created_at_iso"] = raw_date.isoformat()
        else:
            c_dict["created_at_iso"] = raw_date  # Assuming it's already a string if not datetime

        c_dict["data_criacao"] = _format_datetime(raw_date)
        formatted_comments.append(c_dict)

    return {"comments": formatted_comments, "total": total, "page": page, "per_page": per_page}


def listar_comentarios_item(item_id):
    """
    Lista todos os comentários de um item específico.
    """
    comentarios = (
        query_db(
            """
        SELECT c.id, c.texto, c.usuario_cs, c.data_criacao, c.visibilidade, c.imagem_url, c.noshow, c.tag,
                COALESCE(p.nome, c.usuario_cs) as usuario_nome
        FROM comentarios_h c
        LEFT JOIN checklist_items ci ON c.checklist_item_id = ci.id
        LEFT JOIN implantacoes i ON ci.implantacao_id = i.id
        LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
        LEFT JOIN perfil_usuario_contexto puc ON c.usuario_cs = puc.usuario AND puc.contexto = COALESCE(i.contexto, 'onboarding')
        WHERE c.checklist_item_id = %s
        ORDER BY c.data_criacao DESC
        """,
            (item_id,),
        )
        or []
    )

    item_info = query_db(
        """
        SELECT i.email_responsavel
        FROM checklist_items ci
        JOIN implantacoes i ON ci.implantacao_id = i.id
        WHERE ci.id = %s
        """,
        (item_id,),
        one=True,
    )
    email_responsavel = item_info.get("email_responsavel", "") if item_info else ""

    comentarios_formatados = []
    for c in comentarios:
        c_dict = dict(c)
        raw_date = c_dict.get("data_criacao")
        if hasattr(raw_date, "isoformat"):
            c_dict["created_at_iso"] = raw_date.isoformat()
        else:
            c_dict["created_at_iso"] = raw_date

        c_dict["data_criacao"] = _format_datetime(raw_date)
        c_dict["email_responsavel"] = email_responsavel
        c_dict["tarefa_id"] = item_id  # Adicionar item_id para permitir recarregar após exclusão
        comentarios_formatados.append(c_dict)

    return {"comentarios": comentarios_formatados, "email_responsavel": email_responsavel}


def obter_comentario_para_email(comentario_id):
    """
    Obtém dados de um comentário para envio de e-mail.
    """
    dados = query_db(
        """
        SELECT c.id, c.texto, c.visibilidade, c.usuario_cs,
                ci.title as tarefa_nome,
                i.id as impl_id, i.nome_empresa, i.email_responsavel
        FROM comentarios_h c
        JOIN checklist_items ci ON c.checklist_item_id = ci.id
        JOIN implantacoes i ON ci.implantacao_id = i.id
        WHERE c.id = %s
        """,
        (comentario_id,),
        one=True,
    )
    return dados


def registrar_envio_email_comentario(implantacao_id, usuario_email, detalhe):
    with contextlib.suppress(Exception):
        logar_timeline(implantacao_id, usuario_email, "email_comentario_enviado", detalhe)


def _check_edit_permission(comentario, usuario_email, is_manager):
    """
    Verifica se o usuário pode editar/excluir o comentário.
    Regras:
    1. Gestor: Acesso total irrestrito (sem limite de tempo).
    2. Dono: Apenas até 3 horas após criação.
    """
    # 0. Gestor tem permissão total (Bypass de todas as restrições)
    if is_manager:
        return

    # 1. Se não é gestor, DEVE ser o dono
    is_owner = comentario["usuario_cs"] == usuario_email
    if not is_owner:
        raise ValueError("Permissão negada: apenas o autor ou gestores podem alterar.")

    # 2. Check 3-hour limit
    data_criacao = comentario["data_criacao"]

    # Normalização de Timezone para comparação
    tz_brasilia = timezone(timedelta(hours=-3))
    agora = datetime.now(tz_brasilia)

    # Se data_criacao for string (SQLite as vezes), converter
    if isinstance(data_criacao, str):
        with contextlib.suppress(ValueError):
            data_criacao = datetime.fromisoformat(data_criacao)

    # Se for naive, assumir que é do mesmo TZ que salvamos (Brasília)
    if data_criacao.tzinfo is None:
        data_criacao = data_criacao.replace(tzinfo=tz_brasilia)
    else:
        data_criacao = data_criacao.astimezone(tz_brasilia)

    diff = agora - data_criacao
    if diff > timedelta(hours=3):
        raise ValueError("Permissão negada: o tempo limite de 3 horas para edição/exclusão expirou.")


def update_comment_service(comentario_id, novo_texto, usuario_email, is_manager):
    """
    Atualiza o texto de um comentário existente.
    """
    if not novo_texto or not novo_texto.strip():
        raise ValueError("Texto do comentário é obrigatório")

    novo_texto = sanitize_string(novo_texto.strip(), max_length=12000, min_length=1)

    comentario = query_db(
        "SELECT id, usuario_cs, data_criacao, checklist_item_id FROM comentarios_h WHERE id = %s",
        (comentario_id,),
        one=True,
    )
    if not comentario:
        raise ValueError("Comentário não encontrado")

    # Validar permissões e prazo
    _check_edit_permission(comentario, usuario_email, is_manager)

    item_id = comentario["checklist_item_id"]

    with db_transaction_with_lock() as (conn, cursor, db_type):
        update_sql = "UPDATE comentarios_h SET texto = %s WHERE id = %s"
        if db_type == "sqlite":
            update_sql = update_sql.replace("%s", "?")
        cursor.execute(update_sql, (novo_texto, comentario_id))

        # Verificar se este é o comentário mais recente deste item para atualizar o campo legado
        # Se for o mais recente (ou um dos), atualizamos o legado para refletir o texto atual.
        # Busca o último comentário APÓS o update (que acabamos de fazer, mas a data não mudou)
        latest_query = "SELECT texto FROM comentarios_h WHERE checklist_item_id = %s ORDER BY data_criacao DESC LIMIT 1"
        if db_type == "sqlite":
            latest_query = latest_query.replace("%s", "?")
        cursor.execute(latest_query, (item_id,))
        latest = cursor.fetchone()

        should_update_legacy = False
        if latest:
            latest_text = latest["texto"] if hasattr(latest, "keys") else latest[0]
            # Se o texto do último comentário for igual ao novo texto (significa que editamos o último), atualiza legado
            if latest_text == novo_texto:
                should_update_legacy = True

        if should_update_legacy:
            legacy_sql = "UPDATE checklist_items SET comment = %s WHERE id = %s"
            if db_type == "sqlite":
                legacy_sql = legacy_sql.replace("%s", "?")
            cursor.execute(legacy_sql, (novo_texto, item_id))

        conn.commit()

    # Invalidar cache após edição
    try:
        # Buscar implantacao_id para invalidar cache
        item_info = query_db(
            "SELECT implantacao_id FROM checklist_items WHERE id = %s",
            (item_id,),
            one=True,
        )
        if item_info:
            clear_implantacao_cache(item_info["implantacao_id"])
        clear_dashboard_cache()  # Limpa cache de todos dashboards
    except Exception as e:
        logger.warning(f"Erro ao invalidar cache após editar comentário: {e}")

    return {"ok": True, "message": "Comentário atualizado", "novo_texto": novo_texto}


def excluir_comentario_service(comentario_id, usuario_email, is_manager):
    """
    Exclui um comentário (apenas dono ou gestor, até 3h).
    """
    comentario = query_db(
        "SELECT id, usuario_cs, data_criacao, checklist_item_id FROM comentarios_h WHERE id = %s",
        (comentario_id,),
        one=True,
    )
    if not comentario:
        raise ValueError("Comentário não encontrado")

    # Validar permissões e prazo
    _check_edit_permission(comentario, usuario_email, is_manager)

    checklist_item_id = comentario["checklist_item_id"]

    # Fetch related item info BEFORE delete for logging
    item_info = query_db(
        """
        SELECT ci.id as item_id, ci.title as item_title, ci.implantacao_id
        FROM checklist_items ci
        WHERE ci.id = %s
        """,
        (checklist_item_id,),
        one=True,
    )

    execute_db("DELETE FROM comentarios_h WHERE id = %s", (comentario_id,))

    # Verificar se ainda há comentários para este item e atualizar campo legado
    if checklist_item_id:
        # Buscar o agora "novo" último comentário para restaurar o legado, ou limpar se vazio
        latest_rem = query_db(
            "SELECT texto FROM comentarios_h WHERE checklist_item_id = %s ORDER BY data_criacao DESC LIMIT 1",
            (checklist_item_id,),
            one=True,
        )

        new_legacy_text = None
        if latest_rem:
            new_legacy_text = latest_rem["texto"]

        execute_db("UPDATE checklist_items SET comment = %s WHERE id = %s", (new_legacy_text, checklist_item_id))

    if item_info:
        try:
            detalhe = f"Comentário em '{item_info.get('item_title', '')}' excluído."
            logar_timeline(item_info["implantacao_id"], usuario_email, "comentario_excluido", detalhe)
        except Exception:
            pass

        # Invalidar cache após exclusão
        try:
            clear_implantacao_cache(item_info["implantacao_id"])
            clear_dashboard_cache()  # Limpa cache de todos dashboards
        except Exception as e:
            logger.warning(f"Erro ao invalidar cache após excluir comentário: {e}")


def contar_comentarios_implantacao(impl_id, incluir_orfaos=True):
    """
    Conta o número total de comentários de uma implantação.
    Usado para exibir confirmação antes de aplicar/trocar plano.
    """
    if incluir_orfaos:
        count_query = """
            SELECT COUNT(*) as total
            FROM comentarios_h c
            LEFT JOIN checklist_items ci ON c.checklist_item_id = ci.id
            WHERE (ci.implantacao_id = %s)
               OR (c.implantacao_id = %s)
        """
        params = (impl_id, impl_id)
    else:
        # Apenas comentários vinculados às tarefas atuais da implantação.
        count_query = """
            SELECT COUNT(*) as total
            FROM comentarios_h c
            INNER JOIN checklist_items ci ON c.checklist_item_id = ci.id
            WHERE ci.implantacao_id = %s
        """
        params = (impl_id,)

    result = query_db(count_query, params, one=True)
    return result["total"] if result else 0


def preservar_comentarios_implantacao(impl_id, cursor=None, db_type=None):
    """
    Preserva os comentários de uma implantação desvinculando-os dos checklist_items.
    Os comentários ficam 'órfãos' (checklist_item_id = NULL) mas mantém o implantacao_id.
    Chamado antes de deletar os checklist_items ao aplicar novo plano.

    Args:
        impl_id: ID da implantação
        cursor: Cursor opcional para usar transação existente
        db_type: Tipo do banco (postgres/sqlite) - obrigatório se cursor for passado
    """
    # Se cursor foi passado, usar ele diretamente (dentro de transação existente)
    # Senão, usar execute_db que cria sua própria transação
    use_external_cursor = cursor is not None

    # Primeiro, garantir que todos os comentários tenham implantacao_id preenchido
    # (para comentários antigos que podem não ter)
    update_impl_id_query = """
        UPDATE comentarios_h
        SET implantacao_id = (
            SELECT ci.implantacao_id
            FROM checklist_items ci
            WHERE ci.id = comentarios_h.checklist_item_id
        )
        WHERE checklist_item_id IS NOT NULL
        AND implantacao_id IS NULL
        AND checklist_item_id IN (
            SELECT id FROM checklist_items WHERE implantacao_id = %s
        )
    """

    if use_external_cursor:
        if db_type == "sqlite":
            update_impl_id_query = update_impl_id_query.replace("%s", "?")
        cursor.execute(update_impl_id_query, (impl_id,))
    else:
        execute_db(update_impl_id_query, (impl_id,))

    # Agora desvincular os comentários dos itens (torná-los órfãos)
    desvincular_query = """
        UPDATE comentarios_h
        SET checklist_item_id = NULL
        WHERE checklist_item_id IN (
            SELECT id FROM checklist_items WHERE implantacao_id = %s
        )
    """

    if use_external_cursor:
        if db_type == "sqlite":
            desvincular_query = desvincular_query.replace("%s", "?")
        cursor.execute(desvincular_query, (impl_id,))
    else:
        execute_db(desvincular_query, (impl_id,))

    logger.info(f"Comentários da implantação {impl_id} preservados (desvinculados dos itens)")
