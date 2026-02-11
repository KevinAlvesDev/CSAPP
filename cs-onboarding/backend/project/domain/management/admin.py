"""
Módulo de Administração do Gerenciamento
Operações administrativas de usuários.
Princípio SOLID: Single Responsibility
"""

from flask import current_app

from ...config.logging_config import management_logger, security_logger
from ...constants import ADMIN_EMAIL, PERFIL_ADMIN
from ...db import execute_db, query_db
from .users import obter_perfil_usuario, verificar_usuario_existe


def atualizar_perfil_usuario_service(usuario_alvo, novo_perfil, usuario_admin):
    """
    Atualiza o perfil de acesso de um usuário.

    Args:
        usuario_alvo: Email do usuário a ser atualizado
        novo_perfil: Novo perfil de acesso
        usuario_admin: Email do admin que está fazendo a alteração

    Raises:
        ValueError: Se a operação não for permitida
    """
    # Validações de segurança
    if usuario_alvo == usuario_admin:
        raise ValueError("Não pode alterar o seu próprio perfil por esta interface.")

    from ...constants import MASTER_ADMIN_EMAIL

    if usuario_alvo == MASTER_ADMIN_EMAIL and novo_perfil != PERFIL_ADMIN:
        raise ValueError("Não é permitido alterar o perfil do Master Admin.")

    # Se for o ADMIN_EMAIL antigo (env), permitir alteração desde que exista o Master garantindo acesso
    if usuario_alvo == ADMIN_EMAIL and novo_perfil != PERFIL_ADMIN and usuario_alvo != MASTER_ADMIN_EMAIL:
        pass  # Permitido pois temos backup

    # Verificar se usuário existe
    if not verificar_usuario_existe(usuario_alvo):
        raise ValueError("Usuário não encontrado.")

    # Validar perfil
    perfis_disponiveis = current_app.config.get("PERFIS_DE_ACESSO", [])
    if novo_perfil and novo_perfil not in perfis_disponiveis:
        security_logger.warning(
            f"Tentativa de atribuir perfil inválido '{novo_perfil}' para {usuario_alvo} por {usuario_admin}"
        )
        raise ValueError("Perfil de acesso inválido.")

    # Verificar se está tentando alterar um admin (apenas admin pode)
    perfil_atual = obter_perfil_usuario(usuario_alvo)
    if perfil_atual and perfil_atual.get("perfil_acesso") == PERFIL_ADMIN:
        # Esta validação deveria verificar se usuario_admin é admin, mas assumimos que sim
        # pois a rota já tem @admin_required
        pass

    # Executar atualização
    execute_db("UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s", (novo_perfil, usuario_alvo))

    # Invalidar cache do perfil do usuário para refletir mudanças imediatamente
    try:
        from ...config.cache_config import cache

        if cache:
            cache_key = f"user_profile_{usuario_alvo}"
            cache.delete(cache_key)
            management_logger.debug(f"Cache de perfil invalidado para {usuario_alvo}")
    except Exception as e:
        management_logger.warning(f"Falha ao invalidar cache de perfil para {usuario_alvo}: {e}")

    management_logger.info(f"Admin {usuario_admin} atualizou o perfil de {usuario_alvo} para {novo_perfil}")
    return True


def excluir_usuario_service(usuario_alvo, usuario_admin):
    """
    Exclui um usuário e todas as suas implantações.

    Args:
        usuario_alvo: Email do usuário a ser excluído
        usuario_admin: Email do admin que está fazendo a exclusão

    Returns:
        int: Número de implantações excluídas junto com o usuário

    Raises:
        ValueError: Se a operação não for permitida
    """
    # Validações de segurança
    if usuario_alvo == usuario_admin:
        raise ValueError("Você não pode excluir a si mesmo.")

    if usuario_alvo == ADMIN_EMAIL:
        security_logger.warning(f"Tentativa de exclusão do administrador principal por {usuario_admin}")
        raise ValueError("Não é permitido excluir o administrador principal.")

    # Obter foto do perfil para deletar do R2 (se houver)
    perfil = obter_perfil_usuario(usuario_alvo)
    foto_url = perfil.get("foto_url") if perfil else None

    # Buscar implantações vinculadas
    implantacoes_ids = query_db("SELECT id FROM implantacoes WHERE usuario_cs = %s", (usuario_alvo,)) or []

    # Excluir implantações
    for impl in implantacoes_ids:
        execute_db("DELETE FROM implantacoes WHERE id = %s", (impl["id"],))

    # Excluir perfil e usuário
    execute_db("DELETE FROM perfil_usuario WHERE usuario = %s", (usuario_alvo,))
    execute_db("DELETE FROM usuarios WHERE usuario = %s", (usuario_alvo,))

    # Invalidar cache do perfil do usuário excluído
    try:
        from ...config.cache_config import cache

        if cache:
            cache_key = f"user_profile_{usuario_alvo}"
            cache.delete(cache_key)
    except Exception:
        pass  # Ignorar erros de cache na exclusão

    management_logger.info(
        f"Usuário {usuario_alvo} excluído por {usuario_admin} "
        f"(implantações vinculadas removidas: {len(implantacoes_ids)})"
    )

    return {"implantacoes_excluidas": len(implantacoes_ids), "foto_url": foto_url}


def limpar_implantacoes_orfas_service(usuario_admin):
    """
    Remove implantações órfãs (sem usuário proprietário).

    Args:
        usuario_admin: Email do admin que está executando a limpeza

    Returns:
        int: Número de implantações removidas
    """
    stats = query_db("SELECT COUNT(*) as c FROM implantacoes WHERE usuario_cs IS NULL", (), one=True) or {"c": 0}

    count = stats.get("c", 0)

    if count > 0:
        execute_db("DELETE FROM implantacoes WHERE usuario_cs IS NULL")
        management_logger.info(f"Admin {usuario_admin} removeu {count} implantações órfãs")

    return count
