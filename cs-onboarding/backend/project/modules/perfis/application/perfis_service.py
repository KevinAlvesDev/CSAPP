"""
Serviço de Perfis e Permissões (RBAC)
Gerencia perfis de acesso e suas permissões no sistema.
"""

from datetime import datetime

from flask import current_app, g

from ....common.context_navigation import normalize_context
from ....common.exceptions import DatabaseError, ValidationError
from ....db import db_connection, execute_db, query_db

PERFIS_TABLE = "perfis_acesso_contexto"
PERMISSOES_TABLE = "permissoes_contexto"


def _resolve_context(context=None):
    current_ctx = None
    try:
        current_ctx = getattr(g, "modulo_atual", None)
    except Exception:
        current_ctx = None
    return normalize_context(context) or normalize_context(current_ctx) or "onboarding"


def listar_perfis(incluir_inativos: bool = False, context: str | None = None) -> list[dict]:
    """
    Lista todos os perfis de acesso com resumo de permissões.
    """
    ctx = _resolve_context(context)
    sql = """
        SELECT
            p.id,
            p.contexto,
            p.nome,
            p.descricao,
            p.cor,
            p.icone,
            p.sistema,
            p.ativo,
            COUNT(DISTINCT perm.recurso_id) as total_permissoes,
            (SELECT COUNT(*) FROM recursos WHERE ativo = TRUE) as total_recursos,
            (
                SELECT COUNT(*)
                FROM perfil_usuario_contexto puc
                WHERE puc.contexto = p.contexto
                    AND COALESCE(puc.perfil_acesso, '') = COALESCE(p.nome, '')
            ) as total_usuarios
        FROM perfis_acesso_contexto p
        LEFT JOIN permissoes_contexto perm ON perm.perfil_ctx_id = p.id AND perm.concedida = TRUE
        WHERE p.contexto = %s
    """

    if not incluir_inativos:
        sql += " AND p.ativo = TRUE"

    sql += " GROUP BY p.id, p.contexto, p.nome, p.descricao, p.cor, p.icone, p.sistema, p.ativo ORDER BY p.nome"

    perfis = query_db(sql, (ctx,))
    return perfis or []


def obter_perfil(perfil_id: int, context: str | None = None) -> dict | None:
    """
    Obtém detalhes de um perfil específico.
    """
    ctx = _resolve_context(context)
    perfil = query_db(f"SELECT * FROM {PERFIS_TABLE} WHERE id = %s AND contexto = %s", (perfil_id, ctx), one=True)
    return perfil


def obter_perfil_completo(perfil_id: int, context: str | None = None) -> dict | None:
    """
    Obtém perfil com todas as suas permissões organizadas por categoria.
    """
    perfil = obter_perfil(perfil_id, context=context)
    if not perfil:
        return None

    # Buscar todos os recursos agrupados por categoria
    recursos = query_db(
        """
        SELECT
            r.id,
            r.codigo,
            r.nome,
            r.descricao,
            r.categoria,
            r.tipo,
            r.ordem,
            COALESCE(perm.concedida, FALSE) as tem_permissao
        FROM recursos r
        LEFT JOIN permissoes_contexto perm ON perm.recurso_id = r.id AND perm.perfil_ctx_id = %s
        WHERE r.ativo = TRUE
        ORDER BY r.categoria, r.ordem
    """,
        (perfil_id,),
    )

    # Agrupar por categoria
    categorias = {}
    for recurso in recursos:
        cat = recurso["categoria"]
        if cat not in categorias:
            categorias[cat] = {"nome": cat, "recursos": [], "total": 0, "concedidas": 0}

        categorias[cat]["recursos"].append(recurso)
        categorias[cat]["total"] += 1
        if recurso["tem_permissao"]:
            categorias[cat]["concedidas"] += 1

    perfil["categorias"] = list(categorias.values())
    perfil["total_permissoes"] = sum(cat["concedidas"] for cat in categorias.values())
    perfil["total_recursos"] = sum(cat["total"] for cat in categorias.values())

    return perfil


def criar_perfil(
    nome: str,
    descricao: str | None = None,
    cor: str = "#667eea",
    icone: str = "bi-person-badge",
    criado_por: str = "Sistema",
    context: str | None = None,
) -> int:
    """
    Cria um novo perfil de acesso.
    """
    if not nome or not nome.strip():
        raise ValidationError("Nome do perfil é obrigatório")
    ctx = _resolve_context(context)

    # Verificar se já existe
    existente = query_db(f"SELECT id FROM {PERFIS_TABLE} WHERE nome = %s AND contexto = %s", (nome.strip(), ctx), one=True)

    if existente:
        raise ValidationError(f"Já existe um perfil com o nome '{nome}'")

    sql = f"""
        INSERT INTO {PERFIS_TABLE} (contexto, nome, descricao, cor, icone, criado_por, criado_em, atualizado_em)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    now = datetime.now()

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        if db_type == "sqlite":
            sql = sql.replace("%s", "?")

        cursor.execute(sql, (ctx, nome.strip(), descricao or "", cor, icone, criado_por, now, now))

        if db_type == "postgres":
            cursor.execute("SELECT lastval()")
            perfil_id = cursor.fetchone()[0]
        else:
            perfil_id = cursor.lastrowid

        conn.commit()

    current_app.logger.info(f"Perfil '{nome}' criado com ID {perfil_id} por {criado_por}")
    return perfil_id


def atualizar_perfil(perfil_id: int, dados: dict, context: str | None = None) -> bool:
    """
    Atualiza dados básicos de um perfil.
    """
    ctx = _resolve_context(context)
    perfil = obter_perfil(perfil_id, context=ctx)
    if not perfil:
        raise ValidationError(f"Perfil com ID {perfil_id} não encontrado")

    campos = []
    valores = []

    if dados.get("nome"):
        campos.append("nome = %s")
        valores.append(dados["nome"].strip())

    if "descricao" in dados:
        campos.append("descricao = %s")
        valores.append(dados["descricao"] or "")

    if "cor" in dados:
        campos.append("cor = %s")
        valores.append(dados["cor"])

    if "icone" in dados:
        campos.append("icone = %s")
        valores.append(dados["icone"])

    if "ativo" in dados:
        campos.append("ativo = %s")
        valores.append(bool(dados["ativo"]))

    if not campos:
        return True

    campos.append("atualizado_em = %s")
    valores.append(datetime.now())
    valores.append(perfil_id)

    sql = f"UPDATE {PERFIS_TABLE} SET {', '.join(campos)} WHERE id = %s AND contexto = %s"

    valores.append(ctx)
    execute_db(sql, tuple(valores), raise_on_error=True)

    current_app.logger.info(f"Perfil ID {perfil_id} atualizado")
    return True


def excluir_perfil(perfil_id: int, context: str | None = None) -> bool:
    """
    Exclui um perfil (se não for do sistema e não tiver usuários).
    """
    ctx = _resolve_context(context)
    perfil = obter_perfil(perfil_id, context=ctx)
    if not perfil:
        raise ValidationError(f"Perfil com ID {perfil_id} não encontrado")

    if perfil["sistema"]:
        raise ValidationError("Perfis do sistema não podem ser excluídos")

    # Verificar se há usuários usando este perfil
    usuarios = query_db(
        "SELECT COUNT(*) as count FROM perfil_usuario_contexto WHERE contexto = %s AND perfil_acesso = %s",
        (ctx, perfil["nome"]),
        one=True,
    )

    if usuarios and usuarios["count"] > 0:
        raise ValidationError(
            f"Não é possível excluir o perfil '{perfil['nome']}' pois está sendo usado por {usuarios['count']} usuário(s)"
        )

    execute_db(f"DELETE FROM {PERFIS_TABLE} WHERE id = %s AND contexto = %s", (perfil_id, ctx), raise_on_error=True)

    current_app.logger.info(f"Perfil '{perfil['nome']}' (ID {perfil_id}) excluído")
    return True


def atualizar_permissoes(perfil_id: int, permissoes: list[int], context: str | None = None) -> bool:
    """
    Atualiza as permissões de um perfil.

    Args:
        perfil_id: ID do perfil
        permissoes: Lista de IDs de recursos que devem ter permissão
    """
    ctx = _resolve_context(context)
    perfil = obter_perfil(perfil_id, context=ctx)
    if not perfil:
        raise ValidationError(f"Perfil com ID {perfil_id} não encontrado")

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        try:
            # Remover todas as permissões atuais
            delete_sql = f"DELETE FROM {PERMISSOES_TABLE} WHERE perfil_ctx_id = %s"
            if db_type == "sqlite":
                delete_sql = delete_sql.replace("%s", "?")

            cursor.execute(delete_sql, (perfil_id,))

            # Inserir novas permissões
            if permissoes:
                insert_sql = (
                    f"INSERT INTO {PERMISSOES_TABLE} (perfil_ctx_id, recurso_id, concedida, criado_em) VALUES (%s, %s, %s, %s)"
                )
                if db_type == "sqlite":
                    insert_sql = insert_sql.replace("%s", "?")

                now = datetime.now()
                for recurso_id in permissoes:
                    cursor.execute(insert_sql, (perfil_id, recurso_id, True, now))

            conn.commit()

            current_app.logger.info(
                f"Permissões do perfil '{perfil['nome']}' atualizadas: {len(permissoes)} permissões concedidas"
            )
            return True

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao atualizar permissões: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao atualizar permissões: {e}") from e


def listar_recursos(categoria: str | None = None) -> list[dict]:
    """
    Lista todos os recursos disponíveis, opcionalmente filtrados por categoria.
    """
    sql = "SELECT * FROM recursos WHERE ativo = TRUE"
    params = []

    if categoria:
        sql += " AND categoria = %s"
        params.append(categoria)

    sql += " ORDER BY categoria, ordem"

    recursos = query_db(sql, tuple(params) if params else ())
    return recursos or []


def obter_categorias() -> list[str]:
    """
    Retorna lista de categorias únicas de recursos.
    """
    categorias = query_db("SELECT DISTINCT categoria FROM recursos WHERE ativo = TRUE ORDER BY categoria")
    return [cat["categoria"] for cat in categorias] if categorias else []


def verificar_permissao(perfil_id: int, recurso_codigo: str) -> bool:
    """
    Verifica se um perfil tem permissão para um recurso específico.
    """
    if not perfil_id or not recurso_codigo:
        return False

    resultado = query_db(
        """
        SELECT COUNT(*) as count
        FROM permissoes_contexto perm
        JOIN recursos r ON r.id = perm.recurso_id
        WHERE perm.perfil_ctx_id = %s
        AND r.codigo = %s
        AND perm.concedida = TRUE
        AND r.ativo = TRUE
    """,
        (perfil_id, recurso_codigo),
        one=True,
    )

    return resultado and resultado["count"] > 0


def resolver_perfil_id(perfil_contexto: dict | None, context: str | None = None) -> int | None:
    """
    Resolve o ID do perfil RBAC a partir do contexto do usuario.
    Aceita dicts vindos de g.perfil/perfil_usuario.
    """
    if not perfil_contexto:
        return None
    ctx = _resolve_context(context or (perfil_contexto.get("contexto") if isinstance(perfil_contexto, dict) else None))

    perfil_id = None
    if isinstance(perfil_contexto, dict):
        perfil_id = perfil_contexto.get("id") or perfil_contexto.get("perfil_id")
        perfil_nome = (perfil_contexto.get("perfil_acesso") or perfil_contexto.get("nome") or "").strip()
    else:
        try:
            perfil_id = perfil_contexto["id"]
        except Exception:
            perfil_id = None
        try:
            perfil_nome = (perfil_contexto["perfil_acesso"] or "").strip()
        except Exception:
            perfil_nome = ""

    if perfil_id:
        try:
            return int(perfil_id)
        except (TypeError, ValueError):
            current_app.logger.warning(f"perfil_id invalido no contexto: {perfil_id!r}")

    if not perfil_nome:
        return None

    perfil = query_db(
        "SELECT id FROM perfis_acesso_contexto WHERE LOWER(nome) = LOWER(%s) AND contexto = %s LIMIT 1",
        (perfil_nome, ctx),
        one=True,
    )
    if perfil and perfil.get("id"):
        return int(perfil["id"])
    return None


def verificar_permissao_por_contexto(perfil_contexto: dict | None, recurso_codigo: str) -> bool:
    """
    Verifica permissao de um recurso usando o contexto do usuario (g.perfil).
    """
    perfil_id = resolver_perfil_id(perfil_contexto)
    return verificar_permissao(perfil_id, recurso_codigo)


def clonar_perfil(perfil_id: int, novo_nome: str, criado_por: str = "Sistema", context: str | None = None) -> int:
    """
    Clona um perfil existente com todas as suas permissões.
    """
    ctx = _resolve_context(context)
    perfil_original = obter_perfil(perfil_id, context=ctx)
    if not perfil_original:
        raise ValidationError(f"Perfil com ID {perfil_id} não encontrado")

    # Criar novo perfil
    novo_perfil_id = criar_perfil(
        nome=novo_nome,
        descricao=f"Baseado em: {perfil_original['nome']}",
        cor=perfil_original["cor"],
        icone=perfil_original["icone"],
        criado_por=criado_por,
        context=ctx,
    )

    # Copiar permissões
    permissoes_originais = query_db(
        """
        SELECT recurso_id
        FROM permissoes_contexto
        WHERE perfil_ctx_id = %s AND concedida = TRUE
    """,
        (perfil_id,),
    )

    if permissoes_originais:
        recurso_ids = [p["recurso_id"] for p in permissoes_originais]
        atualizar_permissoes(novo_perfil_id, recurso_ids, context=ctx)

    current_app.logger.info(f"Perfil '{perfil_original['nome']}' clonado como '{novo_nome}' (ID {novo_perfil_id})")

    return novo_perfil_id
