"""
API v1 - Endpoints versionados

Esta é a primeira versão estável da API.
Mudanças breaking devem ser feitas em uma nova versão (v2, v3, etc).


Endpoints disponíveis:
- GET  /api/v1/implantacoes - Lista implantações
- GET  /api/v1/implantacoes/<id> - Detalhes de uma implantação
- GET  /api/v1/oamd/implantacoes/<id>/consulta - Consulta dados externos (OAMD)
- POST /api/v1/oamd/implantacoes/<id>/aplicar - Aplica dados externos
"""

import contextlib
from datetime import UTC

from flask import Blueprint, g, jsonify, request
from flask_limiter.util import get_remote_address

from ..blueprints.auth import login_required
from ..common.audit_decorator import audit
from ..config.cache_config import clear_implantacao_cache
from ..config.logging_config import api_logger
from ..constants import PERFIS_COM_GESTAO
from ..core.extensions import limiter
from ..db import logar_timeline
from ..domain.implantacao import aplicar_dados_oamd, consultar_dados_oamd, listar_implantacoes, obter_implantacao_basica
from ..security.api_security import validate_api_origin


def _adapt_query(query, db_type):
    """
    Adapta placeholders SQL para o tipo de banco.
    SQLite usa '?' e PostgreSQL usa '%s'.
    """
    if db_type == "sqlite":
        return query.replace("%s", "?")
    return query


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@api_v1_bp.before_request
def _api_v1_origin_guard():
    return validate_api_origin(lambda: None)()


@api_v1_bp.route("/health", methods=["GET"])
def health():
    """Health check endpoint para API v1."""
    return jsonify({"status": "ok", "version": "v1", "api": "CSAPP API v1"})


@api_v1_bp.route("/implantacoes", methods=["GET"])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def list_implantacoes():
    """
    Lista implantações do usuário.

    Query params:
        - status: Filtrar por status (opcional)
        - page: Número da página (opcional, padrão 1)
        - per_page: Itens por página (opcional, padrão 50)
        - context: Filtrar por contexto (onboarding, ongoing, grandes_contas) (opcional)

    Returns:
        JSON com lista de implantações
    """
    try:
        user_email = g.user_email
        status_filter = request.args.get("status")
        page = request.args.get("page", 1)
        per_page = request.args.get("per_page", 50)
        context = request.args.get("context")

        # Validar valores aceitos para context
        valid_contexts = ("onboarding", "ongoing", "grandes_contas")
        if context and context not in valid_contexts:
            context = None  # Ignorar valores inválidos

        result = listar_implantacoes(
            user_email=user_email,
            status_filter=status_filter,
            page=page,
            per_page=per_page,
            is_admin=False,
            context=context,
        )

        return jsonify({"ok": True, **result})

    except Exception as e:
        api_logger.error(f"Error listing implantacoes: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@api_v1_bp.route("/implantacoes/<int:impl_id>", methods=["GET"])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def get_implantacao(impl_id):
    """
    Retorna detalhes de uma implantação.

    Args:
        impl_id: ID da implantação

    Returns:
        JSON com detalhes da implantação
    """
    try:
        user_email = g.user_email
        is_manager = g.perfil and g.perfil.get("perfil_acesso") in PERFIS_COM_GESTAO

        data = obter_implantacao_basica(impl_id, user_email, is_manager)

        if not data:
            return jsonify({"ok": False, "error": "Implantação não encontrada"}), 404

        # DEBUG: Log valor_monetario
        api_logger.info(f"[DEBUG API] valor_monetario retornado: '{data.get('valor_monetario')}'")

        return jsonify({"ok": True, "data": data})

    except Exception as e:
        api_logger.error(f"Error getting implantacao {impl_id}: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@api_v1_bp.route("/oamd/implantacoes/<int:impl_id>/consulta", methods=["GET"])
@login_required
@limiter.limit("60 per minute", key_func=lambda: g.user_email or get_remote_address())
def consultar_oamd_implantacao(impl_id):
    try:
        user_email = g.user_email

        # Permitir passar id_favorecido via query parameter como fallback
        id_favorecido_param = request.args.get("id_favorecido")

        result = consultar_dados_oamd(impl_id=impl_id, user_email=user_email, id_favorecido_direto=id_favorecido_param)

        return jsonify({"ok": True, "data": result})

    except ValueError as ve:
        api_logger.warning(f"Implantação {impl_id} não encontrada para usuário {user_email}: {ve}")
        return jsonify({"ok": False, "error": f"Implantação #{impl_id} não encontrada", "detail": str(ve)}), 404
    except Exception as e:
        api_logger.error(f"Erro ao consultar OAMD para implantação {impl_id}: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro interno na consulta ao OAMD"}), 500


@api_v1_bp.route("/oamd/implantacoes/<int:impl_id>/aplicar", methods=["POST"])
@login_required
@limiter.limit("60 per minute", key_func=lambda: g.user_email or get_remote_address())
def aplicar_oamd_implantacao(impl_id):
    try:
        user_email = g.user_email

        # Reaproveitar a consulta externa para obter os dados frescos
        info = consultar_dados_oamd(impl_id, user_email)

        persist = info.get("persistibles") or {}
        derived = info.get("derived") or {}

        updates = {}
        if persist.get("id_favorecido"):
            updates["id_favorecido"] = str(persist["id_favorecido"])
        if persist.get("chave_oamd"):
            updates["chave_oamd"] = str(persist["chave_oamd"])
        if derived.get("informacao_infra"):
            updates["informacao_infra"] = str(derived["informacao_infra"])
        if derived.get("tela_apoio_link"):
            updates["tela_apoio_link"] = str(derived["tela_apoio_link"])

        # Campos adicionais OAMD para auto-save
        if persist.get("status_implantacao"):
            updates["status_implantacao_oamd"] = str(persist["status_implantacao"])
        if persist.get("nivel_atendimento"):
            updates["nivel_atendimento"] = str(persist["nivel_atendimento"])
        if persist.get("cnpj"):
            updates["cnpj"] = str(persist["cnpj"])
        if persist.get("data_cadastro"):
            updates["data_cadastro"] = str(persist["data_cadastro"])
        if persist.get("nivel_receita_do_cliente"):
            updates["valor_atribuido"] = str(persist["nivel_receita_do_cliente"])
            # Tentar limpar para numero se possível, mas mantemos string por enquanto pois o campo é texto no HTML

        result = aplicar_dados_oamd(impl_id, user_email, updates)

        # Limpar cache para refletir mudanças no frontend imediatamente
        try:
            clear_implantacao_cache(impl_id)
        except Exception as e:
            api_logger.warning(f"Erro ao limpar cache após aplicar OAMD: {e}")

        return jsonify({"ok": True, "updated": result.get("updated"), "fields": result.get("fields")})

    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 404
    except Exception as e:
        api_logger.error(f"Erro ao aplicar dados OAMD na implantação {impl_id}: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro interno ao aplicar dados"}), 500


@api_v1_bp.route("/implantacoes/<int:impl_id>/carteira", methods=["GET"])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def get_carteira_content(impl_id):
    """
    Retorna o conteúdo da definição de carteira de uma implantação.

    Args:
        impl_id: ID da implantação

    Returns:
        JSON com o conteúdo da carteira
    """
    try:
        from ..db import get_db_connection

        user_email = g.user_email
        is_manager = g.perfil and g.perfil.get("perfil_acesso") in PERFIS_COM_GESTAO

        conn, db_type = get_db_connection()
        cur = conn.cursor()

        # Verificar se o usuário tem acesso à implantação
        if is_manager:
            cur.execute(_adapt_query("SELECT definicao_carteira FROM implantacoes WHERE id = %s", db_type), (impl_id,))
        else:
            cur.execute(
                _adapt_query("SELECT definicao_carteira FROM implantacoes WHERE id = %s AND usuario_cs = %s", db_type),
                (impl_id, user_email),
            )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"ok": False, "error": "Implantação não encontrada"}), 404

        content = row[0] or ""

        return jsonify({"ok": True, "content": content})

    except Exception as e:
        api_logger.error(f"Erro ao buscar definição de carteira {impl_id}: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao buscar definição de carteira"}), 500


@api_v1_bp.route("/implantacoes/<int:impl_id>/carteira", methods=["POST"])
@login_required
@limiter.limit("60 per minute", key_func=lambda: g.user_email or get_remote_address())
def save_carteira_content(impl_id):
    """
    Salva o conteúdo da definição de carteira de uma implantação.

    Args:
        impl_id: ID da implantação

    Body:
        {"content": "texto da definição de carteira"}

    Returns:
        JSON com status da operação
    """
    try:
        from ..db import get_db_connection

        user_email = g.user_email
        is_manager = g.perfil and g.perfil.get("perfil_acesso") in PERFIS_COM_GESTAO

        data = request.get_json()
        if not data or "content" not in data:
            return jsonify({"ok": False, "error": "Conteúdo não fornecido"}), 400

        content = data["content"]

        conn, db_type = get_db_connection()
        cur = conn.cursor()

        # Verificar se o usuário tem acesso à implantação
        if is_manager:
            cur.execute(_adapt_query("SELECT id FROM implantacoes WHERE id = %s", db_type), (impl_id,))
        else:
            cur.execute(
                _adapt_query("SELECT id FROM implantacoes WHERE id = %s AND usuario_cs = %s", db_type),
                (impl_id, user_email),
            )

        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"ok": False, "error": "Implantação não encontrada"}), 404

        # Atualizar definição de carteira
        cur.execute(
            _adapt_query("UPDATE implantacoes SET definicao_carteira = %s WHERE id = %s", db_type), (content, impl_id)
        )

        conn.commit()
        cur.close()
        conn.close()

        # Limpar cache
        try:
            clear_implantacao_cache(impl_id)
        except Exception as e:
            api_logger.warning(f"Erro ao limpar cache após salvar carteira: {e}")

        return jsonify({"ok": True, "message": "Definição de carteira salva com sucesso"})

    except Exception as e:
        api_logger.error(f"Erro ao salvar definição de carteira {impl_id}: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao salvar definição de carteira"}), 500


# ============================================================================
# AVISOS PERSONALIZADOS
# ============================================================================


@api_v1_bp.route("/implantacoes/<int:impl_id>/avisos", methods=["GET"])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def list_avisos(impl_id):
    """
    Lista todos os avisos personalizados de uma implantação.
    """
    try:
        from ..db import get_db_connection

        user_email = g.user_email
        is_manager = g.perfil and g.perfil.get("perfil_acesso") in PERFIS_COM_GESTAO

        conn, db_type = get_db_connection()
        cur = conn.cursor()

        # Verificar acesso
        if is_manager:
            cur.execute(_adapt_query("SELECT id FROM implantacoes WHERE id = %s", db_type), (impl_id,))
        else:
            cur.execute(
                _adapt_query("SELECT id FROM implantacoes WHERE id = %s AND usuario_cs = %s", db_type),
                (impl_id, user_email),
            )

        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"ok": False, "error": "Implantação não encontrada"}), 404

        # Buscar avisos
        cur.execute(
            _adapt_query(
                """
            SELECT id, tipo, titulo, mensagem, criado_por, data_criacao
            FROM avisos_implantacao
            WHERE implantacao_id = %s
            ORDER BY data_criacao DESC
        """,
                db_type,
            ),
            (impl_id,),
        )

        avisos = []
        for row in cur.fetchall():
            # Tratar data_criacao (SQLite retorna string, PostgreSQL retorna datetime)
            data_criacao = row[5]
            if data_criacao:
                if isinstance(data_criacao, str):
                    # SQLite retorna string, manter como está
                    data_criacao_iso = data_criacao
                else:
                    # PostgreSQL retorna datetime em UTC, converter para Brasília
                    from datetime import timedelta, timezone

                    tz_brasilia = timezone(timedelta(hours=-3))

                    # Se o datetime não tem timezone, assumir que é UTC
                    if data_criacao.tzinfo is None:
                        data_criacao = data_criacao.replace(tzinfo=UTC)

                    # Converter para Brasília
                    data_brasilia = data_criacao.astimezone(tz_brasilia)
                    data_criacao_iso = data_brasilia.isoformat()
            else:
                data_criacao_iso = None

            avisos.append(
                {
                    "id": row[0],
                    "tipo": row[1],
                    "titulo": row[2],
                    "mensagem": row[3],
                    "criado_por": row[4],
                    "data_criacao": data_criacao_iso,
                }
            )

        cur.close()
        conn.close()

        return jsonify({"ok": True, "avisos": avisos})

    except Exception as e:
        api_logger.error(f"Erro ao listar avisos {impl_id}: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao listar avisos"}), 500


@api_v1_bp.route("/implantacoes/<int:impl_id>/avisos/<int:aviso_id>", methods=["GET"])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def get_aviso(impl_id, aviso_id):
    """
    Obtém um aviso específico.
    """
    try:
        from ..db import get_db_connection

        user_email = g.user_email
        is_manager = g.perfil and g.perfil.get("perfil_acesso") in PERFIS_COM_GESTAO

        conn, db_type = get_db_connection()
        cur = conn.cursor()

        # Verificar acesso
        if is_manager:
            cur.execute(_adapt_query("SELECT id FROM implantacoes WHERE id = %s", db_type), (impl_id,))
        else:
            cur.execute(
                _adapt_query("SELECT id FROM implantacoes WHERE id = %s AND usuario_cs = %s", db_type),
                (impl_id, user_email),
            )

        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"ok": False, "error": "Implantação não encontrada"}), 404

        # Buscar aviso
        cur.execute(
            _adapt_query(
                """
            SELECT id, tipo, titulo, mensagem, criado_por, data_criacao
            FROM avisos_implantacao
            WHERE id = %s AND implantacao_id = %s
        """,
                db_type,
            ),
            (aviso_id, impl_id),
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"ok": False, "error": "Aviso não encontrado"}), 404

        # Tratar data_criacao (SQLite retorna string, PostgreSQL retorna datetime)
        data_criacao = row[5]
        if data_criacao:
            if isinstance(data_criacao, str):
                data_criacao_iso = data_criacao
            else:
                # PostgreSQL retorna datetime em UTC, converter para Brasília
                from datetime import timedelta, timezone

                tz_brasilia = timezone(timedelta(hours=-3))

                # Se o datetime não tem timezone, assumir que é UTC
                if data_criacao.tzinfo is None:
                    data_criacao = data_criacao.replace(tzinfo=UTC)

                # Converter para Brasília
                data_brasilia = data_criacao.astimezone(tz_brasilia)
                data_criacao_iso = data_brasilia.isoformat()
        else:
            data_criacao_iso = None

        aviso = {
            "id": row[0],
            "tipo": row[1],
            "titulo": row[2],
            "mensagem": row[3],
            "criado_por": row[4],
            "data_criacao": data_criacao_iso,
        }

        return jsonify({"ok": True, "aviso": aviso})

    except Exception as e:
        api_logger.error(f"Erro ao buscar aviso {aviso_id}: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao buscar aviso"}), 500


@api_v1_bp.route("/implantacoes/<int:impl_id>/avisos", methods=["POST"])
@login_required
@limiter.limit("60 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="CREATE_AVISO", target_type="implantacao")
def create_aviso(impl_id):
    """
    Cria um novo aviso personalizado.
    """
    try:
        from ..db import get_db_connection

        user_email = g.user_email
        is_manager = g.perfil and g.perfil.get("perfil_acesso") in PERFIS_COM_GESTAO

        data = request.get_json()
        if not data:
            return jsonify({"ok": False, "error": "Dados não fornecidos"}), 400

        tipo = data.get("tipo", "info")
        titulo = data.get("titulo", "").strip()
        mensagem = data.get("mensagem", "").strip()

        if not titulo or not mensagem:
            return jsonify({"ok": False, "error": "Título e mensagem são obrigatórios"}), 400

        if tipo not in ["info", "warning", "danger", "success"]:
            tipo = "info"

        conn, db_type = get_db_connection()
        cur = conn.cursor()

        # Verificar acesso
        if is_manager:
            cur.execute(_adapt_query("SELECT id FROM implantacoes WHERE id = %s", db_type), (impl_id,))
        else:
            cur.execute(
                _adapt_query("SELECT id FROM implantacoes WHERE id = %s AND usuario_cs = %s", db_type),
                (impl_id, user_email),
            )

        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"ok": False, "error": "Implantação não encontrada"}), 404

        # Criar aviso com horário de Brasília (UTC-3)
        from datetime import datetime, timedelta, timezone

        tz_brasilia = timezone(timedelta(hours=-3))
        now_brasilia = datetime.now(tz_brasilia)

        if db_type == "sqlite":
            cur.execute(
                _adapt_query(
                    """
                INSERT INTO avisos_implantacao
                (implantacao_id, tipo, titulo, mensagem, criado_por, data_criacao)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                    db_type,
                ),
                (impl_id, tipo, titulo, mensagem, user_email, now_brasilia),
            )
            aviso_id = cur.lastrowid
        else:
            cur.execute(
                _adapt_query(
                    """
                INSERT INTO avisos_implantacao
                (implantacao_id, tipo, titulo, mensagem, criado_por, data_criacao)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                    db_type,
                ),
                (impl_id, tipo, titulo, mensagem, user_email, now_brasilia),
            )
            aviso_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()

        # Registrar na Timeline
        with contextlib.suppress(Exception):
            logar_timeline(impl_id, user_email, "aviso_criado", f'Aviso "{titulo}" foi criado.')

        return jsonify({"ok": True, "message": "Aviso criado com sucesso", "aviso_id": aviso_id}), 201

    except Exception as e:
        api_logger.error(f"Erro ao criar aviso {impl_id}: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao criar aviso"}), 500


@api_v1_bp.route("/implantacoes/<int:impl_id>/avisos/<int:aviso_id>", methods=["PUT"])
@login_required
@limiter.limit("60 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="UPDATE_AVISO", target_type="implantacao")
def update_aviso(impl_id, aviso_id):
    """
    Atualiza um aviso existente.
    """
    try:
        from ..db import get_db_connection

        user_email = g.user_email
        is_manager = g.perfil and g.perfil.get("perfil_acesso") in PERFIS_COM_GESTAO

        data = request.get_json()
        if not data:
            return jsonify({"ok": False, "error": "Dados não fornecidos"}), 400

        tipo = data.get("tipo", "info")
        titulo = data.get("titulo", "").strip()
        mensagem = data.get("mensagem", "").strip()

        if not titulo or not mensagem:
            return jsonify({"ok": False, "error": "Título e mensagem são obrigatórios"}), 400

        if tipo not in ["info", "warning", "danger", "success"]:
            tipo = "info"

        conn, db_type = get_db_connection()
        cur = conn.cursor()

        # Verificar acesso e propriedade do aviso
        if is_manager:
            cur.execute(
                _adapt_query(
                    """
                SELECT a.id FROM avisos_implantacao a
                JOIN implantacoes i ON a.implantacao_id = i.id
                WHERE a.id = %s AND a.implantacao_id = %s
            """,
                    db_type,
                ),
                (aviso_id, impl_id),
            )
        else:
            cur.execute(
                _adapt_query(
                    """
                SELECT a.id FROM avisos_implantacao a
                JOIN implantacoes i ON a.implantacao_id = i.id
                WHERE a.id = %s AND a.implantacao_id = %s
                AND (a.criado_por = %s OR i.usuario_cs = %s)
            """,
                    db_type,
                ),
                (aviso_id, impl_id, user_email, user_email),
            )

        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"ok": False, "error": "Aviso não encontrado"}), 404

        # Atualizar aviso
        cur.execute(
            _adapt_query(
                """
            UPDATE avisos_implantacao
            SET tipo = %s, titulo = %s, mensagem = %s
            WHERE id = %s
        """,
                db_type,
            ),
            (tipo, titulo, mensagem, aviso_id),
        )

        conn.commit()
        cur.close()
        conn.close()

        # Registrar na Timeline
        with contextlib.suppress(Exception):
            logar_timeline(impl_id, user_email, "aviso_atualizado", f'Aviso "{titulo}" foi atualizado.')

        return jsonify({"ok": True, "message": "Aviso atualizado com sucesso"})

    except Exception as e:
        api_logger.error(f"Erro ao atualizar aviso {aviso_id}: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao atualizar aviso"}), 500


@api_v1_bp.route("/implantacoes/<int:impl_id>/avisos/<int:aviso_id>", methods=["DELETE"])
@login_required
@limiter.limit("60 per minute", key_func=lambda: g.user_email or get_remote_address())
@audit(action="DELETE_AVISO", target_type="implantacao")
def delete_aviso(impl_id, aviso_id):
    """
    Exclui um aviso.
    """
    try:
        from ..db import get_db_connection

        user_email = g.user_email
        is_manager = g.perfil and g.perfil.get("perfil_acesso") in PERFIS_COM_GESTAO

        conn, db_type = get_db_connection()
        cur = conn.cursor()

        # Verificar acesso e propriedade
        if is_manager:
            cur.execute(
                _adapt_query(
                    """
                SELECT a.id FROM avisos_implantacao a
                JOIN implantacoes i ON a.implantacao_id = i.id
                WHERE a.id = %s AND a.implantacao_id = %s
            """,
                    db_type,
                ),
                (aviso_id, impl_id),
            )
        else:
            cur.execute(
                _adapt_query(
                    """
                SELECT a.id FROM avisos_implantacao a
                JOIN implantacoes i ON a.implantacao_id = i.id
                WHERE a.id = %s AND a.implantacao_id = %s
                AND (a.criado_por = %s OR i.usuario_cs = %s)
            """,
                    db_type,
                ),
                (aviso_id, impl_id, user_email, user_email),
            )

        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"ok": False, "error": "Aviso não encontrado"}), 404

        # Excluir aviso
        cur.execute(_adapt_query("DELETE FROM avisos_implantacao WHERE id = %s", db_type), (aviso_id,))

        conn.commit()
        cur.close()
        conn.close()

        # Registrar na Timeline
        with contextlib.suppress(Exception):
            logar_timeline(impl_id, user_email, "aviso_excluido", "Aviso foi excluído.")

        return jsonify({"ok": True, "message": "Aviso excluído com sucesso"})

    except Exception as e:
        api_logger.error(f"Erro ao excluir aviso {aviso_id}: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao excluir aviso"}), 500
