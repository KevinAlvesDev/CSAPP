"""
Módulo de Status de Implantação
Responsável pelas mudanças de status: iniciar, parar, finalizar, retomar, etc.
Princípio SOLID: Single Responsibility
"""

from datetime import datetime

from flask import current_app

from ...constants import PERFIS_COM_GESTAO
from ...db import execute_db, logar_timeline, query_db


def iniciar_implantacao_service(implantacao_id, usuario_cs_email):
    """
    Inicia uma implantação (muda status para 'andamento').
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status, tipo FROM implantacoes WHERE id = %s", (implantacao_id,), one=True
    )

    if not impl:
        raise ValueError("Implantação não encontrada.")

    # Administradores podem iniciar qualquer implantação
    from flask import g

    user_perfil = getattr(g, "user_perfil_acesso", None)
    is_admin = user_perfil == "Administrador"

    if not is_admin and impl.get("usuario_cs") != usuario_cs_email:
        raise ValueError("Operação negada. Implantação não pertence a você.")

    if impl.get("status") not in ["nova", "futura", "sem_previsao"]:
        raise ValueError(f'Operação negada. Implantação com status "{impl.get("status")}" não pode ser iniciada.')

    agora = datetime.now()
    novo_tipo = impl.get("tipo")
    if novo_tipo == "futura":
        novo_tipo = "completa"

    execute_db(
        "UPDATE implantacoes SET tipo = %s, status = 'andamento', data_inicio_efetivo = %s, data_inicio_previsto = NULL WHERE id = %s",
        (novo_tipo, agora, implantacao_id),
    )
    logar_timeline(
        implantacao_id,
        usuario_cs_email,
        "status_alterado",
        f'Implantação "{impl.get("nome_empresa", "N/A")}" iniciada.',
    )

    return True


def desfazer_inicio_implantacao_service(implantacao_id, usuario_cs_email):
    """
    Reverte o início de uma implantação (volta status para 'nova').
    Útil caso o usuário tenha clicado em Iniciar por engano.
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True
    )

    if not impl:
        raise ValueError("Implantação não encontrada.")

    # Administradores podem desfazer início de qualquer implantação
    from flask import g

    user_perfil = getattr(g, "user_perfil_acesso", None)
    is_admin = user_perfil == "Administrador"

    if not is_admin and impl.get("usuario_cs") != usuario_cs_email:
        raise ValueError("Operação negada. Implantação não pertence a você.")

    if impl.get("status") != "andamento":
        raise ValueError(
            f'Apenas implantações "Em Andamento" podem ter o início desfeito. Status atual: {impl.get("status")}'
        )

    # Volta para 'nova', limpa a data de início efetivo, mas mantém o tipo
    execute_db("UPDATE implantacoes SET status = 'nova', data_inicio_efetivo = NULL WHERE id = %s", (implantacao_id,))

    logar_timeline(
        implantacao_id,
        usuario_cs_email,
        "status_alterado",
        f'Início da implantação "{impl.get("nome_empresa", "N/A")}" desfeito (cancelar início).',
    )

    return True


def agendar_implantacao_service(implantacao_id, usuario_cs_email, data_prevista_iso):
    """
    Agenda uma implantação (muda status para 'futura').
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status, plano_sucesso_id FROM implantacoes WHERE id = %s",
        (implantacao_id,),
        one=True,
    )

    if not impl:
        raise ValueError("Implantação não encontrada.")

    if impl.get("usuario_cs") != usuario_cs_email:
        raise ValueError("Operação negada. Implantação não pertence a você.")

    if impl.get("status") not in ["nova", "sem_previsao", "futura"]:
        raise ValueError('Apenas implantações "Novas", "Sem previsão" ou "Futuras" podem ser agendadas.')

    # Validar que a data é futura
    try:
        from datetime import datetime

        data_prevista = datetime.fromisoformat(data_prevista_iso.replace("Z", "+00:00"))
        hoje = datetime.now().date()

        if data_prevista.date() <= hoje:
            raise ValueError("A data de início previsto deve ser uma data futura.")
    except ValueError as e:
        if "data futura" in str(e).lower():
            raise
        raise ValueError("Data inválida. Use o formato AAAA-MM-DD.")

    execute_db(
        "UPDATE implantacoes SET status = 'futura', data_inicio_previsto = %s WHERE id = %s",
        (data_prevista_iso, implantacao_id),
    )
    logar_timeline(
        implantacao_id,
        usuario_cs_email,
        "status_alterado",
        f'Início da implantação "{impl.get("nome_empresa")}" agendado para {data_prevista_iso}.',
    )

    return impl.get("nome_empresa")


def marcar_sem_previsao_service(implantacao_id, usuario_cs_email):
    """
    Marca uma implantação como 'sem_previsao'.
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True
    )

    if not impl:
        raise ValueError("Implantação não encontrada.")

    if impl.get("usuario_cs") != usuario_cs_email:
        raise ValueError("Operação negada. Implantação não pertence a você.")

    if impl.get("status") != "nova":
        raise ValueError('Apenas implantações "Novas" podem ser marcadas como Sem previsão.')

    updated = execute_db(
        "UPDATE implantacoes SET status = 'sem_previsao', data_inicio_previsto = NULL WHERE id = %s", (implantacao_id,)
    )
    if not updated:
        raise Exception("Falha ao atualizar status para Sem previsão.")

    logar_timeline(
        implantacao_id,
        usuario_cs_email,
        "status_alterado",
        f'Implantação "{impl.get("nome_empresa")}" marcada como "Sem previsão".',
    )

    return impl.get("nome_empresa")


def finalizar_implantacao_service(implantacao_id, usuario_cs_email, data_final_iso):
    """
    Finaliza uma implantação.
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status, plano_sucesso_id FROM implantacoes WHERE id = %s",
        (implantacao_id,),
        one=True,
    )

    if not impl:
        raise ValueError("Implantação não encontrada.")

    if impl.get("usuario_cs") != usuario_cs_email:
        raise ValueError("Permissão negada. Esta implantação não pertence a você.")

    if impl.get("status") != "andamento":
        raise ValueError(
            f"Operação não permitida: status atual é '{impl.get('status')}'. Retome ou inicie antes de finalizar."
        )

    # NOVA VALIDAÇÃO: Checklist de Finalização
    try:
        from ..checklist_finalizacao_service import validar_checklist_completo

        validado, mensagem = validar_checklist_completo(implantacao_id)
        if not validado:
            raise ValueError(f"Checklist de Finalização incompleto: {mensagem}")

        current_app.logger.info(f"Checklist de finalização validado para implantação {implantacao_id}")
    except ImportError:
        current_app.logger.warning("Serviço de checklist de finalização não disponível, pulando validação")
    except Exception as e:
        # Se houver erro na validação do checklist, logar mas não bloquear
        current_app.logger.error(f"Erro ao validar checklist de finalização: {e}", exc_info=True)

    # Validação de pendências do Plano de Sucesso
    plano_id = impl.get("plano_sucesso_id")
    if plano_id:
        subtarefas_pendentes = (
            query_db(
                """
            SELECT COUNT(*) as total
            FROM checklist_items
            WHERE implantacao_id = %s
            AND tipo_item = 'subtarefa'
            AND completed = false
            """,
                (implantacao_id,),
                one=True,
            )
            or {}
        )

        tarefas_pendentes_sem_sub = (
            query_db(
                """
            SELECT COUNT(*) as total
            FROM checklist_items ci
            WHERE ci.implantacao_id = %s
            AND ci.tipo_item = 'tarefa'
            AND ci.completed = false
            AND NOT EXISTS (
                SELECT 1 FROM checklist_items s
                WHERE s.parent_id = ci.id
                AND s.tipo_item = 'subtarefa'
            )
            """,
                (implantacao_id,),
                one=True,
            )
            or {}
        )

        total_pendentes = int(subtarefas_pendentes.get("total", 0) or 0) + int(
            tarefas_pendentes_sem_sub.get("total", 0) or 0
        )

        if total_pendentes > 0:
            nomes = (
                query_db(
                    """
                SELECT title as nome
                FROM checklist_items
                WHERE implantacao_id = %s
                  AND tipo_item = 'subtarefa'
                  AND completed = false
                ORDER BY title LIMIT 10
                """,
                    (implantacao_id,),
                )
                or []
            )
            nomes_txt = ", ".join([n.get("nome") for n in nomes])
            raise ValueError(
                f"Não é possível finalizar: {total_pendentes} tarefa(s) do Plano de Sucesso pendente(s). Pendentes: {nomes_txt}..."
            )

    execute_db(
        "UPDATE implantacoes SET status = 'finalizada', data_finalizacao = %s WHERE id = %s",
        (data_final_iso, implantacao_id),
    )
    logar_timeline(
        implantacao_id,
        usuario_cs_email,
        "status_alterado",
        f'Implantação "{impl.get("nome_empresa", "N/A")}" finalizada.',
    )

    return True


def parar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso, data_parada_iso, motivo):
    """
    Para uma implantação.
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True
    )

    if not impl:
        raise ValueError("Implantação não encontrada.")

    is_owner = impl.get("usuario_cs") == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise ValueError("Permissão negada. Esta implantação não pertence a você.")

    if impl.get("status") != "andamento":
        raise ValueError('Apenas implantações "Em Andamento" podem ser marcadas como "Parada".')

    execute_db(
        "UPDATE implantacoes SET status = 'parada', data_finalizacao = %s, motivo_parada = %s WHERE id = %s",
        (data_parada_iso, motivo, implantacao_id),
    )
    logar_timeline(
        implantacao_id,
        usuario_cs_email,
        "status_alterado",
        f'Implantação "{impl.get("nome_empresa", "N/A")}" parada retroativamente em {data_parada_iso}. Motivo: {motivo}',
    )

    return True


def retomar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso):
    """
    Retoma uma implantação parada.
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True
    )

    if not impl:
        raise ValueError("Implantação não encontrada.")

    is_owner = impl.get("usuario_cs") == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise ValueError("Permissão negada. Esta implantação não pertence a você.")

    if impl.get("status") != "parada":
        raise ValueError('Apenas implantações "Paradas" podem ser retomadas.')

    execute_db(
        "UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL, motivo_parada = '' WHERE id = %s",
        (implantacao_id,),
    )
    logar_timeline(
        implantacao_id,
        usuario_cs_email,
        "status_alterado",
        f'Implantação "{impl.get("nome_empresa", "N/A")}" retomada.',
    )

    return True


def reabrir_implantacao_service(implantacao_id, usuario_cs_email):
    """
    Reabre uma implantação finalizada.
    """
    impl = query_db(
        "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True
    )

    if not impl:
        raise ValueError("Implantação não encontrada.")

    if impl.get("usuario_cs") != usuario_cs_email:
        raise ValueError("Permissão negada.")

    if impl.get("status") != "finalizada":
        raise ValueError('Apenas implantações "Finalizadas" podem ser reabertas.')

    execute_db("UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL WHERE id = %s", (implantacao_id,))
    logar_timeline(
        implantacao_id,
        usuario_cs_email,
        "status_alterado",
        f'Implantação "{impl.get("nome_empresa", "N/A")}" reaberta.',
    )

    return True
