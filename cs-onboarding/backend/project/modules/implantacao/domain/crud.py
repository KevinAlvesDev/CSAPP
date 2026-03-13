import logging
logger = logging.getLogger(__name__)
"""
Módulo de CRUD de Implantação
Responsável por criar, excluir, transferir e cancelar implantações.
Princípio SOLID: Single Responsibility
"""

import contextlib
from datetime import datetime, timezone

from flask import current_app

from ....common.utils import format_date_br
from ....common.exceptions import ValidationError, BusinessRuleError, DatabaseError, AuthorizationError
from ....config.cache_config import clear_implantacao_cache, clear_user_cache
from ....constants import MODULO_OPCOES, PERFIS_COM_GESTAO
from ....db import logar_timeline


def criar_implantacao_service(
    nome_empresa, usuario_atribuido, usuario_criador, id_favorecido=None, contexto="onboarding"
):
    """
    Cria uma nova implantação completa.
    """
    if not nome_empresa:
        raise ValidationError("Nome da empresa é obrigatório.")
    if not usuario_atribuido:
        raise ValidationError("Usuário a ser atribuído é obrigatório.")

    from ....db import Session
    from ....models import Implantacao

    # Verifica se já existe um SISTEMA ativo para esta empresa (permite Sistema + Módulo simultaneamente)
    # E verifica dentro do MESMO CONTEXTO
    existente = (
        Session.query(Implantacao)
        .filter(
            Implantacao.nome_empresa.ilike(nome_empresa),
            Implantacao.tipo == "completa",
            Implantacao.contexto == contexto,
            Implantacao.status.in_(["nova", "futura", "andamento", "parada"]),
        )
        .first()
    )

    if existente:
        raise BusinessRuleError(
            f'Já existe uma implantação de sistema ativa para "{nome_empresa}" neste contexto (status: {existente.status}).',
            details={"status": existente.status, "nome_empresa": nome_empresa}
        )

    nova_impl = Implantacao(
        usuario_cs=usuario_atribuido,
        nome_empresa=nome_empresa,
        tipo="completa",
        data_criacao=datetime.now(timezone.utc),
        status="nova",
        id_favorecido=id_favorecido,
        contexto=contexto,
    )

    try:
        Session.add(nova_impl)
        Session.commit()
        implantacao_id = nova_impl.id
    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        Session.rollback()
        raise DatabaseError(f"Falha ao salvar nova implantação: {e}")

    try:
        logar_timeline(
            implantacao_id,
            usuario_criador,
            "implantacao_criada",
            f'Implantação "{nome_empresa}" ({nova_impl.tipo.capitalize()}) criada e atribuída a {usuario_atribuido}. Contexto: {contexto}.',
        )
    except Exception as e:
        current_app.logger.warning(f"Falha ao registrar timeline para implantação {implantacao_id}: {e}", exc_info=True)

    # Criar checklist de finalização automaticamente
    try:
        from ....modules.checklist.application.checklist_finalizacao_service import criar_checklist_para_implantacao

        criar_checklist_para_implantacao(implantacao_id)
        current_app.logger.info(f"Checklist de finalização criado automaticamente para implantação {implantacao_id}")
    except Exception as e:
        current_app.logger.warning(
            f"Não foi possível criar checklist de finalização para implantação {implantacao_id}: {e}"
        )

    # Limpar cache do usuário atribuído
    with contextlib.suppress(Exception):
        clear_user_cache(usuario_atribuido)

    # Emitir evento de domínio
    try:
        from ....core.events import ImplantacaoCriada, event_bus

        event_bus.emit(ImplantacaoCriada(
            implantacao_id=implantacao_id,
            usuario_cs=usuario_criador,
            nome_empresa=nome_empresa,
        ))
    except Exception as e:
        current_app.logger.warning(f"Falha ao emitir evento ImplantacaoCriada para implantação {implantacao_id}: {e}", exc_info=True)

    return implantacao_id


def criar_implantacao_modulo_service(
    nome_empresa, usuario_atribuido, usuario_criador, modulo_tipo, id_favorecido=None, contexto="onboarding"
):
    """
    Cria uma nova implantação de módulo.
    """
    if not nome_empresa:
        raise ValidationError("Nome da empresa é obrigatório.")
    if not usuario_atribuido:
        raise ValidationError("Usuário a ser atribuído é obrigatório.")

    from ....db import Session
    from ....models import Implantacao

    modulo_opcoes = {
        "nota_fiscal": "Nota fiscal",
        "vendas_online": "Vendas Online",
        "app_treino": "App Treino",
        "recorrencia": "Recorrência",
    }
    if modulo_tipo not in modulo_opcoes:
        raise ValidationError("Módulo inválido.", details={"modulo_tipo": modulo_tipo})

    # Permite criação de múltiplos módulos simultâneos para a mesma empresa.
    # Validação de unicidade removida em 29/01/2026 para permitir N módulos ativos.

    nova_impl = Implantacao(
        usuario_cs=usuario_atribuido,
        nome_empresa=nome_empresa,
        tipo="modulo",
        data_criacao=datetime.now(timezone.utc),
        status="nova",
        id_favorecido=id_favorecido,
        contexto=contexto,
    )

    try:
        Session.add(nova_impl)
        Session.commit()
        implantacao_id = nova_impl.id
    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        Session.rollback()
        raise DatabaseError(f"Falha ao salvar nova implantação de módulo: {e}")

    modulo_label = MODULO_OPCOES.get(modulo_tipo, modulo_tipo)
    try:
        logar_timeline(
            implantacao_id,
            usuario_criador,
            "implantacao_criada",
            f'Implantação de Módulo "{nome_empresa}" (módulo: {modulo_label}) criada e atribuída a {usuario_atribuido}. Contexto: {contexto}.',
        )
    except Exception as e:
        current_app.logger.warning(f"Falha ao registrar timeline para implantação {implantacao_id}: {e}", exc_info=True)

    # Criar checklist de finalização automaticamente
    try:
        from ....modules.checklist.application.checklist_finalizacao_service import criar_checklist_para_implantacao

        criar_checklist_para_implantacao(implantacao_id)
        current_app.logger.info(
            f"Checklist de finalização criado automaticamente para implantação de módulo {implantacao_id}"
        )
    except Exception as e:
        current_app.logger.warning(
            f"Não foi possível criar checklist de finalização para implantação de módulo {implantacao_id}: {e}"
        )

    # Limpar cache do usuário atribuído
    with contextlib.suppress(Exception):
        clear_user_cache(usuario_atribuido)

    return implantacao_id


def transferir_implantacao_service(implantacao_id, usuario_cs_email, novo_usuario_cs):
    """
    Transfere a responsabilidade de uma implantação para outro usuário.
    """
    if not novo_usuario_cs or not implantacao_id:
        raise ValidationError("Dados inválidos para transferência.")

    from ....db import Session
    from ....models import Implantacao

    impl = Session.query(Implantacao).get(implantacao_id)
    if not impl:
        raise BusinessRuleError("Implantação não encontrada.", details={"implantacao_id": implantacao_id})

    antigo_usuario_cs = impl.usuario_cs or "Ninguém"
    
    try:
        impl.usuario_cs = novo_usuario_cs
        Session.commit()
    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        Session.rollback()
        raise DatabaseError(f"Falha ao transferir implantação: {e}")

    try:
        logar_timeline(
            implantacao_id,
            usuario_cs_email,
            "detalhes_alterados",
            f'Implantação "{impl.nome_empresa}" transferida de {antigo_usuario_cs} para {novo_usuario_cs} por {usuario_cs_email}.',
        )
    except Exception as e:
        current_app.logger.warning(f"Falha ao registrar timeline para implantação {implantacao_id}: {e}", exc_info=True)

    # Limpar caches
    try:
        clear_implantacao_cache(implantacao_id)
        clear_user_cache(antigo_usuario_cs)
        clear_user_cache(novo_usuario_cs)
        if usuario_cs_email not in [antigo_usuario_cs, novo_usuario_cs]:
            clear_user_cache(usuario_cs_email)
    except Exception as e:
        current_app.logger.warning(f"Falha ao limpar cache após transferência da implantação {implantacao_id}: {e}", exc_info=True)

    # Emitir evento de domínio
    try:
        from ....core.events import ImplantacaoTransferida, event_bus

        event_bus.emit(ImplantacaoTransferida(
            implantacao_id=implantacao_id,
            de_usuario=antigo_usuario_cs,
            para_usuario=novo_usuario_cs,
        ))
    except Exception as e:
        current_app.logger.warning(f"Falha ao emitir evento ImplantacaoTransferida para implantação {implantacao_id}: {e}", exc_info=True)

    return antigo_usuario_cs


def excluir_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso):
    """
    Exclui permanentemente uma implantação e seus dados associados.
    """
    from sqlalchemy import text

    from ....db import Session
    from ....models import Implantacao

    impl = Session.query(Implantacao).get(implantacao_id)
    if not impl:
        return

    is_owner = impl.usuario_cs == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise ValueError("Permissão negada.")

    # Buscar imagens de comentários para exclusão (R2)
    # Mantendo query_db parcial para tabelas complexas ainda não totalmente mapeadas para ORM se necessário
    comentarios_img = (
        Session.execute(
            text(
                """
                SELECT DISTINCT c.imagem_url
                FROM comentarios_h c
                WHERE EXISTS (
                    SELECT 1 FROM checklist_items ci
                    WHERE c.checklist_item_id = ci.id
                    AND ci.implantacao_id = :implantacao_id
                )
                AND c.imagem_url IS NOT NULL AND c.imagem_url != ''
                """
            ),
            {"implantacao_id": implantacao_id},
        )
        .mappings()
        .all()
    )

    from ....core.extensions import r2_client

    public_url_base = current_app.config.get("CLOUDFLARE_PUBLIC_URL")
    bucket_name = current_app.config.get("CLOUDFLARE_BUCKET_NAME")

    if r2_client and public_url_base and bucket_name:
        for c in comentarios_img:
            imagem_url = c.get("imagem_url")
            if imagem_url and imagem_url.startswith(public_url_base):
                try:
                    object_key = imagem_url.replace(f"{public_url_base}/", "")
                    if object_key:
                        r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                except Exception as e:
                    current_app.logger.warning(f"Falha ao excluir R2 (key: {object_key}): {e}", exc_info=True)

    # A exclusão via ORM agora cuida das cascatas configuradas no modelo para:
    # - checklist_items (checklists)
    # - timeline_log (timeline)
    # - planos_sucesso (plano_sucesso_rel)
    
    usuario_cs = impl.usuario_cs
    
    try:
        # Remover dependências legadas não mapeadas no ORM se existirem.
        try:
            Session.execute(
                text("DELETE FROM implantacao_planos WHERE implantacao_id = :implantacao_id"),
                {"implantacao_id": implantacao_id},
            )
        except Exception as exc:
            logger.exception(
                "Falha ao remover planos legados da implantaÃ§Ã£o %s",
                implantacao_id,
                exc_info=True,
            )
            Session.rollback()
            raise DatabaseError(
                f"Falha ao remover dependÃªncias antes de excluir implantaÃ§Ã£o: {exc}"
            ) from exc

        Session.delete(impl)
        Session.commit()
    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        Session.rollback()
        raise DatabaseError(f"Falha ao excluir implantação: {e}")

    # Limpar caches
    try:
        clear_user_cache(usuario_cs)
        clear_implantacao_cache(implantacao_id)
        if usuario_cs_email != usuario_cs:
            clear_user_cache(usuario_cs_email)
    except Exception as e:
        current_app.logger.warning(f"Falha ao limpar cache após excluir implantação {implantacao_id}: {e}", exc_info=True)


def cancelar_implantacao_service(
    implantacao_id, usuario_cs_email, user_perfil_acesso, data_cancelamento_iso, motivo, comprovante_url
):
    """
    Cancela uma implantação.
    """
    from ....db import Session
    from ....models import Implantacao

    impl = Session.query(Implantacao).get(implantacao_id)
    if not impl:
        raise BusinessRuleError("Implantação não encontrada.", details={"implantacao_id": implantacao_id})

    is_owner = impl.usuario_cs == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise AuthorizationError("Permissão negada para cancelar esta implantação.")

    if impl.status in ["finalizada", "cancelada"]:
        raise BusinessRuleError(f"Implantação já está {impl.status}.", details={"status": impl.status})

    if impl.status == "nova":
        raise BusinessRuleError(
            'Ações indisponíveis para implantações "Nova". Inicie a implantação para habilitar cancelamento.'
        )

    try:
        impl.status = "cancelada"
        impl.data_cancelamento = data_cancelamento_iso
        impl.motivo_cancelamento = motivo
        impl.comprovante_cancelamento_url = comprovante_url
        impl.data_finalizacao = datetime.now(timezone.utc)
        Session.commit()
    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        Session.rollback()
        raise DatabaseError(f"Falha ao cancelar implantação: {e}")

    try:
        logar_timeline(
            implantacao_id,
            usuario_cs_email,
            "status_alterado",
            f"Implantação CANCELADA.\nMotivo: {motivo}\nData inf.: {format_date_br(data_cancelamento_iso)}",
        )
    except Exception as e:
        current_app.logger.warning(f"Falha ao registrar timeline para implantação {implantacao_id}: {e}", exc_info=True)

    # Limpar caches
    try:
        clear_implantacao_cache(implantacao_id)
        clear_user_cache(impl.usuario_cs)
        if usuario_cs_email != impl.usuario_cs:
            clear_user_cache(usuario_cs_email)
    except Exception as e:
        current_app.logger.warning(f"Falha ao limpar cache após cancelar implantação {implantacao_id}: {e}", exc_info=True)


def remover_plano_implantacao_service(implantacao_id: int, usuario_cs_email: str, user_perfil_acesso: str) -> None:
    """
    Remove o plano de sucesso de uma implantação, limpando todas as fases/ações/tarefas associadas.
    """
    from ....db import Session
    from ....models import Implantacao

    impl = Session.query(Implantacao).get(implantacao_id)
    if not impl:
        raise BusinessRuleError("Implantação não encontrada.", details={"implantacao_id": implantacao_id})

    is_owner = impl.usuario_cs == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise AuthorizationError("Permissão negada.")

    try:
        total_removed = len(impl.checklists)
        # Limpar checklists (delete-orphan cuidará da exclusão no DB)
        impl.checklists = []
        
        # Limpar campos de plano
        # Note: no banco real os nomes podem variar, o modelo usa plano_sucesso_rel ou campos diretos
        # No DB vi: plano_sucesso_id
        if hasattr(impl, "plano_sucesso_id"):
            impl.plano_sucesso_id = None
        
        impl.data_atribuicao_plano = None
        impl.data_previsao_termino = None
        
        Session.commit()
    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        Session.rollback()
        raise DatabaseError(f"Falha ao remover plano da implantação: {e}")

    detalhe = f"Plano de sucesso removido da implantação por {usuario_cs_email}."
    if total_removed > 0:
        detalhe += f" Itens removidos: {total_removed}."

    try:
        logar_timeline(implantacao_id, usuario_cs_email, "plano_removido", detalhe)
    except Exception as e:
        current_app.logger.warning(f"Falha ao registrar timeline para implantação {implantacao_id}: {e}", exc_info=True)

    clear_implantacao_cache(implantacao_id)
    clear_user_cache(usuario_cs_email)
