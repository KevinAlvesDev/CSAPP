"""
Test Fixtures — Dados de teste reutilizáveis.

Contém factories e constantes para criar objetos de teste.
"""

from datetime import datetime, timedelta

# ──────────────────────────────────────────────
# Fixtures de Usuários
# ──────────────────────────────────────────────

ADMIN_USER = {
    "email": "admin@admin.com",
    "name": "Administrador",
    "sub": "test|admin",
}

GERENTE_USER = {
    "email": "gerente@company.com",
    "name": "Maria Gerente",
    "sub": "test|gerente",
}

IMPLANTADOR_USER = {
    "email": "implantador@company.com",
    "name": "João Implantador",
    "sub": "test|implantador",
}

COORDENADOR_USER = {
    "email": "coordenador@company.com",
    "name": "Ana Coordenadora",
    "sub": "test|coordenador",
}


# ──────────────────────────────────────────────
# Fixtures de Perfis
# ──────────────────────────────────────────────


def make_perfil(
    usuario: str = "user@test.com",
    nome: str = "Test User",
    perfil_acesso: str = "Implantador",
    cargo: str | None = None,
    foto_url: str | None = None,
) -> dict:
    """Factory para criar perfis de teste."""
    return {
        "usuario": usuario,
        "nome": nome,
        "perfil_acesso": perfil_acesso,
        "cargo": cargo,
        "foto_url": foto_url,
    }


# ──────────────────────────────────────────────
# Fixtures de Implantações
# ──────────────────────────────────────────────


def make_implantacao(
    id: int = 1,
    nome_empresa: str = "Empresa Teste LTDA",
    status: str = "nova",
    usuario_cs: str = "implantador@company.com",
    created_at: str | None = None,
    tipo: str = "onboarding",
    progresso: float = 0.0,
) -> dict:
    """Factory para criar implantações de teste."""
    if created_at is None:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "id": id,
        "nome_empresa": nome_empresa,
        "status": status,
        "usuario_cs": usuario_cs,
        "created_at": created_at,
        "tipo": tipo,
        "progresso": progresso,
    }


# ──────────────────────────────────────────────
# Fixtures de Checklist
# ──────────────────────────────────────────────


def make_checklist_item(
    id: int = 1,
    implantacao_id: int = 1,
    parent_id: int | None = None,
    title: str = "Item de Teste",
    tipo_item: str = "tarefa",
    completed: bool = False,
    ordem: int = 1,
    tag: str = "",
    responsavel: str | None = None,
) -> dict:
    """Factory para criar items de checklist de teste."""
    return {
        "id": id,
        "implantacao_id": implantacao_id,
        "parent_id": parent_id,
        "title": title,
        "tipo_item": tipo_item,
        "completed": completed,
        "ordem": ordem,
        "tag": tag,
        "responsavel": responsavel,
        "prazo_inicio": None,
        "prazo_fim": None,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def make_checklist_tree(implantacao_id: int = 1) -> list[dict]:
    """
    Cria uma árvore de checklist completa para testes.

    Estrutura:
    - Fase 1
      - Grupo A
        - Tarefa 1 (concluída)
        - Tarefa 2
          - Subtarefa 2.1
          - Subtarefa 2.2 (concluída)
      - Grupo B
        - Tarefa 3
    """
    return [
        make_checklist_item(id=1, implantacao_id=implantacao_id, title="Fase 1", tipo_item="fase", ordem=1),
        make_checklist_item(
            id=2, implantacao_id=implantacao_id, parent_id=1, title="Grupo A", tipo_item="grupo", ordem=1
        ),
        make_checklist_item(
            id=3,
            implantacao_id=implantacao_id,
            parent_id=2,
            title="Tarefa 1",
            tipo_item="tarefa",
            completed=True,
            ordem=1,
        ),
        make_checklist_item(
            id=4, implantacao_id=implantacao_id, parent_id=2, title="Tarefa 2", tipo_item="tarefa", ordem=2
        ),
        make_checklist_item(
            id=5, implantacao_id=implantacao_id, parent_id=4, title="Subtarefa 2.1", tipo_item="subtarefa", ordem=1
        ),
        make_checklist_item(
            id=6,
            implantacao_id=implantacao_id,
            parent_id=4,
            title="Subtarefa 2.2",
            tipo_item="subtarefa",
            completed=True,
            ordem=2,
        ),
        make_checklist_item(
            id=7, implantacao_id=implantacao_id, parent_id=1, title="Grupo B", tipo_item="grupo", ordem=2
        ),
        make_checklist_item(
            id=8, implantacao_id=implantacao_id, parent_id=7, title="Tarefa 3", tipo_item="tarefa", ordem=1
        ),
    ]


# ──────────────────────────────────────────────
# Fixtures de Comentários
# ──────────────────────────────────────────────


def make_comentario(
    id: int = 1,
    item_id: int = 1,
    autor: str = "user@test.com",
    texto: str = "Comentário de teste",
    tag: str = "",
    created_at: str | None = None,
) -> dict:
    """Factory para criar comentários de teste."""
    if created_at is None:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "id": id,
        "item_id": item_id,
        "autor": autor,
        "texto": texto,
        "tag": tag,
        "created_at": created_at,
        "editado": False,
        "editado_em": None,
    }


# ──────────────────────────────────────────────
# Fixtures de Planos de Sucesso
# ──────────────────────────────────────────────


def make_plano_sucesso(
    id: int = 1,
    nome: str = "Plano de Sucesso Básico",
    descricao: str = "Plano de onboarding padrão",
    ativo: bool = True,
) -> dict:
    """Factory para criar planos de sucesso de teste."""
    return {
        "id": id,
        "nome": nome,
        "descricao": descricao,
        "ativo": ativo,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
