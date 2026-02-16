"""
Helpers de acesso para implantações.
Centraliza validação de acesso para evitar divergências entre camadas.
"""

from __future__ import annotations

from typing import Any

from ....constants import PERFIS_COM_GESTAO
from ....db import query_db

ImplantacaoDict = dict[str, Any]
UserProfile = dict[str, Any]


def _get_implantacao_and_validate_access(
    impl_id: int, usuario_cs_email: str, user_perfil: UserProfile | None
) -> tuple[ImplantacaoDict, bool]:
    user_perfil_acesso = user_perfil.get("perfil_acesso") if user_perfil else None
    implantacao = query_db("SELECT * FROM implantacoes WHERE id = %s", (impl_id,), one=True)

    if not implantacao:
        raise ValueError("Implantação não encontrada.")

    is_owner = implantacao.get("usuario_cs") == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not is_owner and not is_manager:
        if implantacao.get("status") == "nova":
            raise ValueError("Esta implantação ainda não foi iniciada.")
        raise ValueError("Implantação não encontrada ou não pertence a você.")

    # Regra removida: permitir acesso a detalhes mesmo sem iniciar a implantação
    # (anteriormente bloqueava implantações com status "nova" para o dono)

    return implantacao, is_manager
