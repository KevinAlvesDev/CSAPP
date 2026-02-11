"""
Serviço de Checklist de Finalização
Gerencia os itens do checklist que devem ser completados antes de finalizar uma implantação
"""

from datetime import datetime

from flask import current_app

from ..db import db_connection, query_db


def criar_checklist_para_implantacao(implantacao_id: int) -> bool:
    """
    Cria os itens do checklist de finalização para uma implantação
    baseado nos templates ativos.
    """
    try:
        # Verificar se já existe checklist para esta implantação
        existing = query_db(
            "SELECT COUNT(*) as count FROM checklist_finalizacao_items WHERE implantacao_id = %s",
            (implantacao_id,),
            one=True,
        )

        if existing and existing["count"] > 0:
            current_app.logger.info(f"Checklist já existe para implantação {implantacao_id}")
            return True

        # Buscar templates ativos
        templates = query_db(
            """
            SELECT id, titulo, descricao, obrigatorio, ordem, requer_evidencia, tipo_evidencia
            FROM checklist_finalizacao_templates
            WHERE ativo = %s
            ORDER BY ordem ASC
            """,
            (True,),
        )

        if not templates:
            current_app.logger.warning("Nenhum template de checklist encontrado")
            return False

        # Criar itens para a implantação
        with db_connection() as (conn, db_type):
            cursor = conn.cursor()

            for template in templates:
                if db_type == "postgres":
                    cursor.execute(
                        """
                        INSERT INTO checklist_finalizacao_items
                        (implantacao_id, template_id, titulo, descricao, obrigatorio, ordem, evidencia_tipo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                        (
                            implantacao_id,
                            template["id"],
                            template["titulo"],
                            template["descricao"],
                            template["obrigatorio"],
                            template["ordem"],
                            template.get("tipo_evidencia"),
                        ),
                    )
                else:  # SQLite
                    cursor.execute(
                        """
                        INSERT INTO checklist_finalizacao_items
                        (implantacao_id, template_id, titulo, descricao, obrigatorio, ordem, evidencia_tipo)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            implantacao_id,
                            template["id"],
                            template["titulo"],
                            template["descricao"],
                            1 if template["obrigatorio"] else 0,
                            template["ordem"],
                            template.get("tipo_evidencia"),
                        ),
                    )

            conn.commit()

        current_app.logger.info(f"Checklist criado para implantação {implantacao_id} com {len(templates)} itens")
        return True

    except Exception as e:
        current_app.logger.error(f"Erro ao criar checklist para implantação {implantacao_id}: {e}", exc_info=True)
        return False


def obter_checklist_implantacao(implantacao_id: int) -> dict:
    """
    Retorna o checklist de finalização de uma implantação com estatísticas.
    """
    try:
        # Buscar itens do checklist
        items = (
            query_db(
                """
            SELECT id, titulo, descricao, obrigatorio, concluido, data_conclusao,
                   usuario_conclusao, evidencia_tipo, evidencia_conteudo, evidencia_url,
                   observacoes, ordem
            FROM checklist_finalizacao_items
            WHERE implantacao_id = %s
            ORDER BY ordem ASC
            """,
                (implantacao_id,),
            )
            or []
        )

        # Calcular estatísticas
        total = len(items)
        concluidos = sum(1 for item in items if item["concluido"])
        obrigatorios = [item for item in items if item["obrigatorio"]]
        obrigatorios_pendentes = [item for item in obrigatorios if not item["concluido"]]

        progresso = (concluidos / total * 100) if total > 0 else 0
        validado = len(obrigatorios_pendentes) == 0

        return {
            "items": items,
            "total": total,
            "concluidos": concluidos,
            "pendentes": total - concluidos,
            "obrigatorios_total": len(obrigatorios),
            "obrigatorios_pendentes": len(obrigatorios_pendentes),
            "progresso": round(progresso, 1),
            "validado": validado,
        }

    except Exception as e:
        current_app.logger.error(f"Erro ao obter checklist da implantação {implantacao_id}: {e}", exc_info=True)
        return {
            "items": [],
            "total": 0,
            "concluidos": 0,
            "pendentes": 0,
            "obrigatorios_total": 0,
            "obrigatorios_pendentes": 0,
            "progresso": 0,
            "validado": False,
        }


def marcar_item_checklist(
    item_id: int,
    concluido: bool,
    usuario: str,
    evidencia_tipo: str | None = None,
    evidencia_conteudo: str | None = None,
    evidencia_url: str | None = None,
    observacoes: str | None = None,
) -> bool:
    """
    Marca um item do checklist como concluído ou pendente.
    """
    try:
        data_conclusao = datetime.now() if concluido else None
        usuario_conclusao = usuario if concluido else None

        with db_connection() as (conn, db_type):
            cursor = conn.cursor()

            if db_type == "postgres":
                cursor.execute(
                    """
                    UPDATE checklist_finalizacao_items
                    SET concluido = %s,
                        data_conclusao = %s,
                        usuario_conclusao = %s,
                        evidencia_tipo = %s,
                        evidencia_conteudo = %s,
                        evidencia_url = %s,
                        observacoes = %s,
                        updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        concluido,
                        data_conclusao,
                        usuario_conclusao,
                        evidencia_tipo,
                        evidencia_conteudo,
                        evidencia_url,
                        observacoes,
                        datetime.now(),
                        item_id,
                    ),
                )
            else:  # SQLite
                cursor.execute(
                    """
                    UPDATE checklist_finalizacao_items
                    SET concluido = ?,
                        data_conclusao = ?,
                        usuario_conclusao = ?,
                        evidencia_tipo = ?,
                        evidencia_conteudo = ?,
                        evidencia_url = ?,
                        observacoes = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        1 if concluido else 0,
                        data_conclusao,
                        usuario_conclusao,
                        evidencia_tipo,
                        evidencia_conteudo,
                        evidencia_url,
                        observacoes,
                        datetime.now(),
                        item_id,
                    ),
                )

            conn.commit()

        # Registrar logs
        status_texto = "concluído" if concluido else "pendente"
        current_app.logger.info(f"Item {item_id} do checklist marcado como {status_texto} por {usuario}")

        # Adicionar à Linha do Tempo da Implantação
        try:
            # Buscar implantacao_id e titulo do item para o log
            item = query_db(
                "SELECT implantacao_id, titulo FROM checklist_finalizacao_items WHERE id = %s", (item_id,), one=True
            )
            if item:
                from .implantacao.crud import logar_timeline

                logar_timeline(
                    item["implantacao_id"],
                    usuario,
                    "checklist_item",
                    f"Item do checklist '{item['titulo']}' marcado como {status_texto}.",
                )
        except Exception as e:
            current_app.logger.error(f"Erro ao logar timeline do checklist: {e}")

        return True

    except Exception as e:
        current_app.logger.error(f"Erro ao marcar item {item_id} do checklist: {e}", exc_info=True)
        return False


def validar_checklist_completo(implantacao_id: int) -> tuple[bool, str]:
    """
    Valida se todos os itens obrigatórios do checklist foram concluídos.
    Retorna (validado, mensagem)
    """
    try:
        checklist = obter_checklist_implantacao(implantacao_id)

        if checklist["obrigatorios_pendentes"] > 0:
            return False, f"{checklist['obrigatorios_pendentes']} item(ns) obrigatório(s) ainda pendente(s)"

        if checklist["total"] == 0:
            return False, "Checklist não foi criado para esta implantação"

        return True, "Checklist validado com sucesso"

    except Exception as e:
        current_app.logger.error(f"Erro ao validar checklist da implantação {implantacao_id}: {e}", exc_info=True)
        return False, f"Erro ao validar checklist: {e!s}"


def obter_templates_checklist() -> list[dict]:
    """
    Retorna todos os templates de checklist ativos.
    """
    try:
        templates = (
            query_db(
                """
            SELECT id, titulo, descricao, obrigatorio, ordem, requer_evidencia, tipo_evidencia, ativo
            FROM checklist_finalizacao_templates
            ORDER BY ordem ASC
            """
            )
            or []
        )

        return templates

    except Exception as e:
        current_app.logger.error(f"Erro ao obter templates de checklist: {e}", exc_info=True)
        return []
