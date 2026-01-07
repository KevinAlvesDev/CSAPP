"""
Módulo de Comentários do Checklist
Adicionar, listar e excluir comentários.
Princípio SOLID: Single Responsibility
"""
import logging
from datetime import datetime, timezone, timedelta

from flask import g

from ...common.validation import sanitize_string
from ...db import db_transaction_with_lock, query_db, execute_db, logar_timeline
from .utils import _format_datetime

logger = logging.getLogger(__name__)


def add_comment_to_item(item_id, text, visibilidade='interno', usuario_email=None, noshow=False, tag=None, imagem_url=None, imagem_base64=None):
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
    except (ValueError, TypeError):
        raise ValueError("item_id deve ser um inteiro válido")

    if not text or not text.strip():
        raise ValueError("Texto do comentário é obrigatório")

    usuario_email = usuario_email or (g.user_email if hasattr(g, 'user_email') else None)
    text = sanitize_string(text.strip(), max_length=8000, min_length=1)
    noshow = bool(noshow) or (tag == 'No Show')

    with db_transaction_with_lock() as (conn, cursor, db_type):
        # 1. Verificar item
        check_query = "SELECT id, implantacao_id, title FROM checklist_items WHERE id = %s"
        if db_type == 'sqlite': check_query = check_query.replace('%s', '?')
        cursor.execute(check_query, (item_id,))
        item = cursor.fetchone()
        if not item:
            raise ValueError(f"Item {item_id} não encontrado")
        
        # Handle result access
        if hasattr(item, 'keys'):
            implantacao_id = item['implantacao_id']
            item_title = item['title']
        else:
            implantacao_id = item[1]
            item_title = item[2]

        # 2. Garantir coluna checklist_item_id e tag em comentarios_h (Self-healing)
        if db_type == 'postgres':
            try:
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='comentarios_h' AND column_name='checklist_item_id'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN IF NOT EXISTS checklist_item_id INTEGER")
                    try:
                        cursor.execute("ALTER TABLE comentarios_h ADD CONSTRAINT fk_comentarios_checklist_item FOREIGN KEY (checklist_item_id) REFERENCES checklist_items(id)")
                    except Exception:
                        pass
                # Garantir coluna tag
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='comentarios_h' AND column_name='tag'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN IF NOT EXISTS tag VARCHAR(50)")
            except Exception:
                pass
        elif db_type == 'sqlite':
            try:
                cursor.execute("PRAGMA table_info(comentarios_h)")
                cols = [r[1] for r in cursor.fetchall()]
                if 'checklist_item_id' not in cols:
                    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN checklist_item_id INTEGER")
                if 'tag' not in cols:
                    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN tag TEXT")
            except Exception:
                pass

        # 3. Inserir no histórico (comentarios_h)
        # Usar horário local de Brasília (UTC-3)
        tz_brasilia = timezone(timedelta(hours=-3))
        now = datetime.now(tz_brasilia)
        noshow_val = noshow if db_type == 'postgres' else (1 if noshow else 0)
        insert_sql = """
            INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, data_criacao, visibilidade, noshow, tag, imagem_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        if db_type == 'sqlite': insert_sql = insert_sql.replace('%s', '?')
        cursor.execute(insert_sql, (item_id, usuario_email, text, now, visibilidade, noshow_val, tag, imagem_url))
        
        # 4. Atualizar campo legado 'comment' no checklist_items
        update_legacy_sql = "UPDATE checklist_items SET comment = %s, updated_at = %s WHERE id = %s"
        if db_type == 'sqlite': update_legacy_sql = update_legacy_sql.replace('%s', '?')
        cursor.execute(update_legacy_sql, (text, now, item_id))

        # 5. Log na timeline
        try:
            detalhe = f"Comentário criado — {item_title} <span class=\"d-none related-id\" data-item-id=\"{item_id}\"></span>"
            log_sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
            if db_type == 'sqlite': log_sql = log_sql.replace('%s', '?')
            cursor.execute(log_sql, (implantacao_id, usuario_email, 'novo_comentario', detalhe, now))
        except Exception as e:
            logger.warning(f"Erro ao logar timeline: {e}")

        conn.commit()

        return {
            'ok': True,
            'item_id': item_id,
            'comentario': {
                'texto': text,
                'usuario_cs': usuario_email,
                'data_criacao': now.isoformat(),
                'visibilidade': visibilidade,
                'noshow': noshow,
                'tag': tag
            }
        }


def listar_comentarios_implantacao(impl_id, page=1, per_page=20):
    """
    Lista todos os comentários de uma implantação com paginação.
    """
    offset = (page - 1) * per_page
    
    count_query = """
        SELECT COUNT(*) as total
        FROM comentarios_h c
        JOIN checklist_items ci ON c.checklist_item_id = ci.id
        WHERE ci.implantacao_id = %s
    """
    total_res = query_db(count_query, (impl_id,), one=True)
    total = total_res['total'] if total_res else 0

    comments_query = """
        SELECT 
            c.id, c.texto, c.usuario_cs, c.data_criacao, c.visibilidade, c.noshow, c.imagem_url, c.tag,
            ci.id as item_id, ci.title as item_title,
            COALESCE(p.nome, c.usuario_cs) as usuario_nome
        FROM comentarios_h c
        JOIN checklist_items ci ON c.checklist_item_id = ci.id
        LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
        WHERE ci.implantacao_id = %s
        ORDER BY c.data_criacao DESC
        LIMIT %s OFFSET %s
    """
    comments = query_db(comments_query, (impl_id, per_page, offset))
    
    formatted_comments = []
    for c in comments:
        c_dict = dict(c)
        c_dict['data_criacao'] = _format_datetime(c_dict.get('data_criacao'))
        formatted_comments.append(c_dict)
        
    return {
        'comments': formatted_comments,
        'total': total,
        'page': page,
        'per_page': per_page
    }


def listar_comentarios_item(item_id):
    """
    Lista todos os comentários de um item específico.
    """
    comentarios = query_db(
        """
        SELECT c.id, c.texto, c.usuario_cs, c.data_criacao, c.visibilidade, c.imagem_url, c.noshow, c.tag,
                COALESCE(p.nome, c.usuario_cs) as usuario_nome
        FROM comentarios_h c
        LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
        WHERE c.checklist_item_id = %s
        ORDER BY c.data_criacao DESC
        """,
        (item_id,)
    ) or []

    item_info = query_db(
        """
        SELECT i.email_responsavel
        FROM checklist_items ci
        JOIN implantacoes i ON ci.implantacao_id = i.id
        WHERE ci.id = %s
        """,
        (item_id,),
        one=True
    )
    email_responsavel = item_info.get('email_responsavel', '') if item_info else ''

    comentarios_formatados = []
    for c in comentarios:
        c_dict = dict(c)
        c_dict['data_criacao'] = _format_datetime(c_dict.get('data_criacao'))
        c_dict['email_responsavel'] = email_responsavel
        c_dict['tarefa_id'] = item_id  # Adicionar item_id para permitir recarregar após exclusão
        comentarios_formatados.append(c_dict)

    return {
        'comentarios': comentarios_formatados,
        'email_responsavel': email_responsavel
    }


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
        one=True
    )
    return dados


def excluir_comentario_service(comentario_id, usuario_email, is_manager):
    """
    Exclui um comentário (apenas dono ou gestor).
    """
    comentario = query_db(
        "SELECT id, usuario_cs FROM comentarios_h WHERE id = %s",
        (comentario_id,),
        one=True
    )
    if not comentario:
        raise ValueError('Comentário não encontrado')

    is_owner = comentario['usuario_cs'] == usuario_email
    if not (is_owner or is_manager):
        raise ValueError('Permissão negada')

    # Fetch related item info BEFORE delete
    item_info = query_db(
        """
        SELECT ci.id as item_id, ci.title as item_title, ci.implantacao_id
        FROM comentarios_h c
        JOIN checklist_items ci ON c.checklist_item_id = ci.id
        WHERE c.id = %s
        """,
        (comentario_id,), one=True
    )

    execute_db("DELETE FROM comentarios_h WHERE id = %s", (comentario_id,))

    # Verificar se ainda há comentários para este item e atualizar campo legado
    if item_info and item_info.get('item_id'):
        remaining = query_db(
            "SELECT COUNT(*) as cnt FROM comentarios_h WHERE checklist_item_id = %s",
            (item_info['item_id'],), one=True
        )
        if remaining and remaining.get('cnt', 0) == 0:
            # Limpa o campo legado 'comment' pois não há mais comentários
            execute_db(
                "UPDATE checklist_items SET comment = NULL WHERE id = %s",
                (item_info['item_id'],)
            )

    if item_info:
        try:
            detalhe = f"Comentário em '{item_info.get('item_title', '')}' excluído."
            logar_timeline(item_info['implantacao_id'], usuario_email, 'comentario_excluido', detalhe)
        except Exception:
            pass
