"""
Módulo CRUD de Planos de Sucesso
Criar, listar, atualizar, excluir e obter planos.
Princípio SOLID: Single Responsibility
"""

from datetime import datetime
from typing import Dict, List, Optional

from flask import current_app

from ...common.exceptions import DatabaseError, ValidationError
from ...db import db_connection, execute_db, query_db
from .estrutura import _criar_estrutura_plano, _criar_estrutura_plano_checklist
from .validacao import validar_estrutura_checklist, validar_estrutura_hierarquica


def criar_plano_sucesso(
    nome: str,
    descricao: str,
    criado_por: str,
    estrutura: Dict,
    dias_duracao: int = None,
    context: str = "onboarding",
) -> int:
    """
    Cria um plano de sucesso com estrutura hierárquica.
    """
    if not nome or not nome.strip():
        raise ValidationError("Nome do plano é obrigatório")

    if not criado_por:
        raise ValidationError("Usuário criador é obrigatório")

    validar_estrutura_hierarquica(estrutura)

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        # Garantir que as colunas existam (migração automática para SQLite)
        if db_type == "sqlite":
            try:
                cursor.execute("PRAGMA table_info(planos_sucesso)")
                colunas_existentes = [row[1] for row in cursor.fetchall()]

                if "data_atualizacao" not in colunas_existentes:
                    cursor.execute(
                        "ALTER TABLE planos_sucesso ADD COLUMN data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP"
                    )
                    conn.commit()
                    current_app.logger.info("Coluna data_atualizacao adicionada à tabela planos_sucesso")

                if "dias_duracao" not in colunas_existentes:
                    cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN dias_duracao INTEGER")
                    conn.commit()
                    current_app.logger.info("Coluna dias_duracao adicionada à tabela planos_sucesso")
            except Exception as mig_error:
                current_app.logger.warning(f"Erro ao verificar/migrar colunas de planos_sucesso: {mig_error}")

        try:
            sql_plano = """
                INSERT INTO planos_sucesso (nome, descricao, criado_por, data_criacao, data_atualizacao, dias_duracao, permite_excluir_tarefas, contexto)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            if db_type == "sqlite":
                sql_plano = sql_plano.replace("%s", "?")

            now = datetime.now()
            permite_excluir = estrutura.get("permite_excluir_tarefas", False)
            cursor.execute(
                sql_plano,
                (
                    nome.strip(),
                    descricao or "",
                    criado_por,
                    now,
                    now,
                    dias_duracao,
                    permite_excluir,
                    context,
                ),
            )

            if db_type == "postgres":
                cursor.execute("SELECT lastval()")
                plano_id = cursor.fetchone()[0]
            else:
                plano_id = cursor.lastrowid

            _criar_estrutura_plano(cursor, db_type, plano_id, estrutura)

            conn.commit()

            current_app.logger.info(f"Plano de sucesso '{nome}' criado com ID {plano_id} por {criado_por}")
            return plano_id

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao criar plano de sucesso: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao criar plano de sucesso: {e}") from e


def criar_plano_sucesso_checklist(
    nome: str,
    descricao: str,
    criado_por: str,
    estrutura: Dict,
    dias_duracao: int = None,
    context: str = "onboarding",
) -> int:
    """
    Cria um plano de sucesso usando a tabela checklist_items (hierarquia infinita).
    A estrutura é salva como uma árvore de itens na tabela checklist_items, vinculada ao plano.
    Aceita estrutura no formato antigo (fases/grupos) ou novo (items hierárquicos).
    """
    if not nome or not nome.strip():
        raise ValidationError("Nome do plano é obrigatório")

    if not criado_por:
        raise ValidationError("Usuário criador é obrigatório")

    validar_estrutura_checklist(estrutura)

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        # Garantir que as colunas existam (migração automática para SQLite)
        if db_type == "sqlite":
            try:
                cursor.execute("PRAGMA table_info(planos_sucesso)")
                colunas_existentes = [row[1] for row in cursor.fetchall()]

                if "data_atualizacao" not in colunas_existentes:
                    cursor.execute(
                        "ALTER TABLE planos_sucesso ADD COLUMN data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP"
                    )
                    conn.commit()
                    current_app.logger.info("Coluna data_atualizacao adicionada à tabela planos_sucesso")

                if "dias_duracao" not in colunas_existentes:
                    cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN dias_duracao INTEGER")
                    conn.commit()
                    current_app.logger.info("Coluna dias_duracao adicionada à tabela planos_sucesso")
            except Exception as mig_error:
                current_app.logger.warning(f"Erro ao verificar/migrar colunas de planos_sucesso: {mig_error}")

        try:
            sql_plano = """
                INSERT INTO planos_sucesso (nome, descricao, criado_por, data_criacao, data_atualizacao, dias_duracao, permite_excluir_tarefas, contexto)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            if db_type == "sqlite":
                sql_plano = sql_plano.replace("%s", "?")

            now = datetime.now()
            permite_excluir = estrutura.get("permite_excluir_tarefas", False)
            cursor.execute(
                sql_plano,
                (
                    nome.strip(),
                    descricao or "",
                    criado_por,
                    now,
                    now,
                    dias_duracao,
                    permite_excluir,
                    context,
                ),
            )

            if db_type == "postgres":
                cursor.execute("SELECT lastval()")
                plano_id = cursor.fetchone()[0]
            else:
                plano_id = cursor.lastrowid

            _criar_estrutura_plano_checklist(cursor, db_type, plano_id, estrutura)

            conn.commit()

            current_app.logger.info(
                f"Plano de sucesso '{nome}' criado com ID {plano_id} usando checklist_items por {criado_por}"
            )
            return plano_id

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao criar plano de sucesso: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao criar plano de sucesso: {e}") from e


def atualizar_plano_sucesso(plano_id: int, dados: Dict) -> bool:
    """
    Atualiza dados básicos de um plano de sucesso.
    """
    if not plano_id:
        raise ValidationError("ID do plano é obrigatório")

    plano_existente = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)
    if not plano_existente:
        raise ValidationError(f"Plano com ID {plano_id} não encontrado")

    with db_connection() as (conn, db_type):
        if db_type == "sqlite":
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(planos_sucesso)")
                colunas_existentes = [row[1] for row in cursor.fetchall()]

                if "data_atualizacao" not in colunas_existentes:
                    cursor.execute(
                        "ALTER TABLE planos_sucesso ADD COLUMN data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP"
                    )
                    conn.commit()
                    current_app.logger.info("Coluna data_atualizacao adicionada à tabela planos_sucesso")

                if "dias_duracao" not in colunas_existentes:
                    cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN dias_duracao INTEGER")
                    conn.commit()
                    current_app.logger.info("Coluna dias_duracao adicionada à tabela planos_sucesso")
            except Exception as mig_error:
                current_app.logger.warning(f"Erro ao verificar/migrar colunas de planos_sucesso: {mig_error}")

    campos_atualizaveis = []
    valores = []

    if "nome" in dados and dados["nome"]:
        campos_atualizaveis.append("nome = %s")
        valores.append(dados["nome"].strip())

    if "descricao" in dados:
        campos_atualizaveis.append("descricao = %s")
        valores.append(dados["descricao"] or "")

    if "ativo" in dados:
        campos_atualizaveis.append("ativo = %s")
        valores.append(bool(dados["ativo"]))

    if "dias_duracao" in dados:
        campos_atualizaveis.append("dias_duracao = %s")
        valores.append(int(dados["dias_duracao"]) if dados["dias_duracao"] else None)

    if "permite_excluir_tarefas" in dados:
        campos_atualizaveis.append("permite_excluir_tarefas = %s")
        valores.append(bool(dados["permite_excluir_tarefas"]))

    if not campos_atualizaveis:
        return True

    campos_atualizaveis.append("data_atualizacao = %s")
    valores.append(datetime.now())
    valores.append(plano_id)

    sql = f"UPDATE planos_sucesso SET {', '.join(campos_atualizaveis)} WHERE id = %s"

    result = execute_db(sql, tuple(valores), raise_on_error=True)

    current_app.logger.info(f"Plano de sucesso ID {plano_id} atualizado")
    return result is not None


def excluir_plano_sucesso(plano_id: int) -> bool:
    """
    Exclui um plano de sucesso (se não estiver em uso).
    """
    if not plano_id:
        raise ValidationError("ID do plano é obrigatório")

    plano = query_db("SELECT nome FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)
    if not plano:
        raise ValidationError(f"Plano com ID {plano_id} não encontrado")

    implantacoes_usando = query_db(
        "SELECT COUNT(*) as count FROM implantacoes WHERE plano_sucesso_id = %s", (plano_id,), one=True
    )

    if implantacoes_usando and implantacoes_usando["count"] > 0:
        raise ValidationError(
            f"Não é possível excluir o plano '{plano['nome']}' pois está sendo usado por {implantacoes_usando['count']} implantação(ões)"
        )

    result = execute_db("DELETE FROM planos_sucesso WHERE id = %s", (plano_id,), raise_on_error=True)

    current_app.logger.info(f"Plano de sucesso '{plano['nome']}' (ID {plano_id}) excluído")
    return result is not None


def listar_planos_sucesso(
    ativo_apenas: bool = True, busca: str = None, context: str = None
) -> List[Dict]:
    """
    Lista todos os planos de sucesso.
    """
    sql = "SELECT * FROM planos_sucesso WHERE 1=1"
    params = []

    if context:
        if context == "onboarding":
            sql += " AND (contexto IS NULL OR contexto = 'onboarding')"
        else:
            sql += " AND contexto = %s"
            params.append(context)

    if ativo_apenas:
        sql += " AND ativo = %s"
        params.append(True)

    if busca:
        sql += " AND (nome LIKE %s OR descricao LIKE %s)"
        busca_pattern = f"%{busca}%"
        params.extend([busca_pattern, busca_pattern])

    sql += " ORDER BY nome ASC"

    planos = query_db(sql, tuple(params) if params else ())
    return planos or []


def obter_plano_completo(plano_id: int) -> Optional[Dict]:
    """
    Retorna plano completo usando checklist_items (estrutura consolidada).
    Retorna no formato 'items' para compatibilidade com o editor moderno.
    """
    plano = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)

    if not plano:
        return None

    items = query_db(
        """
        SELECT id, parent_id, title, completed, comment, level, ordem, tipo_item, descricao, obrigatoria, status, tag
        FROM checklist_items
        WHERE plano_id = %s
        ORDER BY ordem, id
        """,
        (plano_id,),
    )

    if not items:
        plano["items"] = []
        plano["fases"] = []
        return plano

    from ..checklist_service import build_nested_tree

    flat_items = []
    for item in items:
        flat_items.append(
            {
                "id": item["id"],
                "parent_id": item["parent_id"],
                "title": item["title"],
                "completed": item["completed"],
                "comment": item.get("comment", "") or item.get("descricao", ""),
                "level": item.get("level", 0),
                "ordem": item.get("ordem", 0),
                "obrigatoria": item.get("obrigatoria", False),
                "tag": item.get("tag"),
            }
        )

    nested_items = build_nested_tree(flat_items)
    plano["items"] = nested_items
    plano["estrutura"] = {"items": nested_items}

    # Removed unused items_map to satisfy linter

    def tipo_item_val(x):
        return x.get("tipo_item") or ""

    fases_items = [item for item in items if tipo_item_val(item) == "plano_fase" and item["parent_id"] is None]
    grupos_items = {item["parent_id"]: [] for item in items if tipo_item_val(item) == "plano_grupo"}
    tarefas_items = {item["parent_id"]: [] for item in items if tipo_item_val(item) == "plano_tarefa"}
    subtarefas_items = {item["parent_id"]: [] for item in items if tipo_item_val(item) == "plano_subtarefa"}

    for item in items:
        tipo_item = tipo_item_val(item)
        if tipo_item == "plano_grupo" and item["parent_id"]:
            grupos_items[item["parent_id"]].append(item)
        elif tipo_item == "plano_tarefa" and item["parent_id"]:
            tarefas_items[item["parent_id"]].append(item)
        elif tipo_item == "plano_subtarefa" and item["parent_id"]:
            subtarefas_items[item["parent_id"]].append(item)

    plano["fases"] = []
    for fase_item in sorted(fases_items, key=lambda x: x.get("ordem", 0)):
        fase = {
            "id": fase_item["id"],
            "nome": fase_item["title"],
            "descricao": fase_item.get("descricao") or fase_item.get("comment", ""),
            "ordem": fase_item.get("ordem", 0),
            "grupos": [],
        }

        grupos_fase = sorted(grupos_items.get(fase_item["id"], []), key=lambda x: x.get("ordem", 0))
        for grupo_item in grupos_fase:
            grupo = {
                "id": grupo_item["id"],
                "nome": grupo_item["title"],
                "descricao": grupo_item.get("descricao") or grupo_item.get("comment", ""),
                "ordem": grupo_item.get("ordem", 0),
                "tarefas": [],
            }

            tarefas_grupo = sorted(tarefas_items.get(grupo_item["id"], []), key=lambda x: x.get("ordem", 0))
            for tarefa_item in tarefas_grupo:
                tarefa = {
                    "id": tarefa_item["id"],
                    "nome": tarefa_item["title"],
                    "descricao": tarefa_item.get("descricao") or tarefa_item.get("comment", ""),
                    "obrigatoria": tarefa_item.get("obrigatoria", False),
                    "status": tarefa_item.get("status", "pendente"),
                    "ordem": tarefa_item.get("ordem", 0),
                    "subtarefas": [],
                }

                subtarefas_tarefa = sorted(subtarefas_items.get(tarefa_item["id"], []), key=lambda x: x.get("ordem", 0))
                for subtarefa_item in subtarefas_tarefa:
                    subtarefa = {
                        "id": subtarefa_item["id"],
                        "nome": subtarefa_item["title"],
                        "descricao": subtarefa_item.get("descricao") or subtarefa_item.get("comment", ""),
                        "ordem": subtarefa_item.get("ordem", 0),
                    }
                    tarefa["subtarefas"].append(subtarefa)

                grupo["tarefas"].append(tarefa)

            fase["grupos"].append(grupo)

        plano["fases"].append(fase)

    return plano


def obter_plano_completo_checklist(plano_id: int) -> Optional[Dict]:
    """
    Retorna plano completo usando checklist_items (hierarquia infinita).
    Retorna estrutura aninhada para compatibilidade com frontend.
    """
    plano = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)

    if not plano:
        return None

    count_items = query_db("SELECT COUNT(*) as count FROM checklist_items WHERE plano_id = %s", (plano_id,), one=True)

    if not count_items or count_items.get("count", 0) == 0:
        return None

    items = query_db(
        """
        SELECT id, parent_id, title, completed, comment, level, ordem
        FROM checklist_items
        WHERE plano_id = %s
        ORDER BY ordem, id
        """,
        (plano_id,),
    )

    if not items:
        return plano

    from ..checklist_service import build_nested_tree

    flat_items = []
    for item in items:
        flat_items.append(
            {
                "id": item["id"],
                "parent_id": item["parent_id"],
                "title": item["title"],
                "completed": item["completed"],
                "comment": item["comment"],
                "level": item["level"],
                "ordem": item["ordem"],
            }
        )

    nested_items = build_nested_tree(flat_items)

    plano["items"] = nested_items
    plano["estrutura"] = {"items": nested_items}

    return plano


def obter_plano_da_implantacao(implantacao_id: int) -> Optional[Dict]:
    """
    Retorna o plano associado a uma implantação.
    """
    implantacao = query_db("SELECT plano_sucesso_id FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)

    if not implantacao or not implantacao.get("plano_sucesso_id"):
        return None

    return obter_plano_completo(implantacao["plano_sucesso_id"])


def _plano_usa_checklist_items(plano_id: int) -> bool:
    """
    Verifica se o plano usa checklist_items (novo formato) ou estrutura antiga.
    """
    count = query_db("SELECT COUNT(*) as count FROM checklist_items WHERE plano_id = %s", (plano_id,), one=True)

    return count and count.get("count", 0) > 0


def clonar_plano_sucesso(
    plano_id: int,
    novo_nome: str,
    criado_por: str,
    nova_descricao: str = None,
    context: str = None,
) -> int:
    """
    Clona um plano de sucesso existente com todas as suas tarefas.

    Args:
        plano_id: ID do plano a ser clonado
        novo_nome: Nome do novo plano
        criado_por: Usuário que está clonando
        nova_descricao: Descrição opcional (se None, usa "Baseado em: [nome original]")
        context: Contexto do novo plano (opcional)

    Returns:
        ID do novo plano criado

    Raises:
        ValidationError: Se o plano original não existir ou dados inválidos
        DatabaseError: Se houver erro ao clonar
    """
    if not plano_id:
        raise ValidationError("ID do plano original é obrigatório")

    if not novo_nome or not novo_nome.strip():
        raise ValidationError("Nome do novo plano é obrigatório")

    if not criado_por:
        raise ValidationError("Usuário criador é obrigatório")

    # Buscar plano original
    plano_original = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)

    if not plano_original:
        raise ValidationError(f"Plano com ID {plano_id} não encontrado")

    # Verificar se usa checklist_items
    usa_checklist = _plano_usa_checklist_items(plano_id)

    if usa_checklist:
        # Buscar estrutura do plano original
        items = query_db(
            """
            SELECT id, parent_id, title, comment, level, ordem, tipo_item, descricao, obrigatoria, tag
            FROM checklist_items
            WHERE plano_id = %s
            ORDER BY ordem, id
            """,
            (plano_id,),
        )

        if not items:
            raise ValidationError("Plano original não possui estrutura para clonar")

        # Construir estrutura hierárquica
        from ..checklist_service import build_nested_tree

        flat_items = []
        for item in items:
            flat_items.append(
                {
                    "id": item["id"],
                    "parent_id": item["parent_id"],
                    "title": item["title"],
                    "comment": item.get("comment", "") or item.get("descricao", ""),
                    "level": item.get("level", 0),
                    "ordem": item.get("ordem", 0),
                    "tipo_item": item.get("tipo_item"),
                    "obrigatoria": item.get("obrigatoria", False),
                    "tag": item.get("tag"),
                }
            )

        nested_items = build_nested_tree(flat_items)
        estrutura = {"items": nested_items}

        # Definir descrição
        if nova_descricao is None:
            nova_descricao = f"Baseado em: {plano_original['nome']}"

        # Criar novo plano
        novo_plano_id = criar_plano_sucesso_checklist(
            nome=novo_nome.strip(),
            descricao=nova_descricao,
            criado_por=criado_por,
            estrutura=estrutura,
            dias_duracao=plano_original.get("dias_duracao"),
            context=context or plano_original.get("contexto", "onboarding"),
        )

        current_app.logger.info(
            f"Plano '{plano_original['nome']}' (ID {plano_id}) clonado como '{novo_nome}' (ID {novo_plano_id}) por {criado_por}"
        )

        return novo_plano_id

    else:
        # Plano usa estrutura antiga (fases/grupos/tarefas)
        raise ValidationError(
            "Este plano usa estrutura antiga. Por favor, recrie o plano usando o editor moderno antes de clonar."
        )
