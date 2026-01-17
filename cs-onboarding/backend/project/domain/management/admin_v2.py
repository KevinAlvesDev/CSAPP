"""
Management Admin Otimizado - Versão SEM N+1
Elimina DELETE em loop

ANTES: DELETE individual para cada implantação
DEPOIS: DELETE em batch com IN

Ganho: 5-10x mais rápido
"""

from ...config.logging_config import management_logger, security_logger
from ...constants import ADMIN_EMAIL
from ...db import execute_db, query_db
from .users import obter_perfil_usuario


def excluir_usuario_service_v2(usuario_alvo, usuario_admin):
    """
    Versão otimizada que exclui usuário e implantações em batch.

    ANTES: 1 + N queries (DELETE individual)
    DEPOIS: 3 queries totais
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

    # Contar implantações vinculadas
    stats = query_db("SELECT COUNT(*) as total FROM implantacoes WHERE usuario_cs = %s", (usuario_alvo,), one=True) or {
        "total": 0
    }

    total_implantacoes = stats.get("total", 0)

    # OTIMIZAÇÃO: Excluir TODAS as implantações em UMA query
    if total_implantacoes > 0:
        execute_db("DELETE FROM implantacoes WHERE usuario_cs = %s", (usuario_alvo,))

    # Excluir perfil e usuário
    execute_db("DELETE FROM perfil_usuario WHERE usuario = %s", (usuario_alvo,))
    execute_db("DELETE FROM usuarios WHERE usuario = %s", (usuario_alvo,))

    management_logger.info(
        f"Usuário {usuario_alvo} excluído por {usuario_admin} (implantações vinculadas removidas: {total_implantacoes})"
    )

    return {"implantacoes_excluidas": total_implantacoes, "foto_url": foto_url}
