"""
Planos de Sucesso Service - Módulo de Compatibilidade
Este arquivo re-exporta todas as funções do novo pacote domain/planos/
para manter compatibilidade com código existente.

REFATORAÇÃO SOLID: As funções foram movidas para módulos especializados:
- crud.py       -> Criar, listar, atualizar, excluir planos
- estrutura.py  -> Criação de estrutura do plano
- aplicar.py    -> Aplicar/remover plano de implantação
- validacao.py  -> Validações de estrutura
"""

# Re-exportar todas as funções do novo pacote para compatibilidade
from .planos import (
    _clonar_plano_para_implantacao,
    _clonar_plano_para_implantacao_checklist,
    _converter_items_para_plano,
    _criar_estrutura_plano,
    _criar_estrutura_plano_checklist,
    _criar_items_recursivo,
    _plano_usa_checklist_items,
    _validar_items_recursivo,
    # Aplicar
    aplicar_plano_a_implantacao,
    aplicar_plano_a_implantacao_checklist,
    # CRUD
    concluir_plano_sucesso,
    contar_planos_em_andamento,
    contar_planos_por_status,
    # Estrutura
    atualizar_estrutura_plano,
    atualizar_plano_sucesso,
    clonar_plano_sucesso,
    converter_estrutura_editor_para_checklist,
    # CRUD
    criar_plano_sucesso,
    criar_plano_sucesso_checklist,
    excluir_plano_sucesso,
    get_valid_tags,
    listar_planos_sucesso,
    obter_plano_completo,
    obter_plano_completo_checklist,
    obter_plano_da_implantacao,
    remover_plano_de_implantacao,
    validar_estrutura_checklist,
    # Validação
    validar_estrutura_hierarquica,
)

# Manter __all__ para compatibilidade com imports *
__all__ = [
    "_clonar_plano_para_implantacao",
    "_clonar_plano_para_implantacao_checklist",
    "_converter_items_para_plano",
    "_criar_estrutura_plano",
    "_criar_estrutura_plano_checklist",
    "_criar_items_recursivo",
    "_plano_usa_checklist_items",
    "_validar_items_recursivo",
    # Aplicar
    "aplicar_plano_a_implantacao",
    "aplicar_plano_a_implantacao_checklist",
    # CRUD
    "concluir_plano_sucesso",
    "contar_planos_em_andamento",
    "contar_planos_por_status",
    # Estrutura
    "atualizar_estrutura_plano",
    "atualizar_plano_sucesso",
    "clonar_plano_sucesso",
    "converter_estrutura_editor_para_checklist",
    # CRUD
    "criar_plano_sucesso",
    "criar_plano_sucesso_checklist",
    "excluir_plano_sucesso",
    "get_valid_tags",
    "listar_planos_sucesso",
    "obter_plano_completo",
    "obter_plano_completo_checklist",
    "obter_plano_da_implantacao",
    "remover_plano_de_implantacao",
    "validar_estrutura_checklist",
    # Validação
    "validar_estrutura_hierarquica",
]
