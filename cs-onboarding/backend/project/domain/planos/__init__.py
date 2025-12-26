"""
Módulo de Planos de Sucesso - Pacote SOLID
Re-exporta todas as funções para manter compatibilidade com código existente.

Estrutura:
- crud.py       -> Criar, listar, atualizar, excluir planos
- estrutura.py  -> Criação de estrutura do plano
- aplicar.py    -> Aplicar/remover plano de implantação
- validacao.py  -> Validações de estrutura
"""

# Importações de crud.py
from .crud import (
    criar_plano_sucesso,
    criar_plano_sucesso_checklist,
    atualizar_plano_sucesso,
    excluir_plano_sucesso,
    listar_planos_sucesso,
    obter_plano_completo,
    obter_plano_completo_checklist,
    obter_plano_da_implantacao,
    _plano_usa_checklist_items,
)

# Importações de estrutura.py
from .estrutura import (
    atualizar_estrutura_plano,
    _criar_estrutura_plano,
    _criar_estrutura_plano_checklist,
    _criar_items_recursivo,
    converter_estrutura_editor_para_checklist,
    _converter_items_para_plano,
)

# Importações de aplicar.py
from .aplicar import (
    aplicar_plano_a_implantacao,
    aplicar_plano_a_implantacao_checklist,
    remover_plano_de_implantacao,
    _clonar_plano_para_implantacao,
    _clonar_plano_para_implantacao_checklist,
)

# Importações de validacao.py
from .validacao import (
    validar_estrutura_hierarquica,
    validar_estrutura_checklist,
    _validar_items_recursivo,
    VALID_TAGS,
)

# Exports públicos
__all__ = [
    # CRUD
    'criar_plano_sucesso',
    'criar_plano_sucesso_checklist',
    'atualizar_plano_sucesso',
    'excluir_plano_sucesso',
    'listar_planos_sucesso',
    'obter_plano_completo',
    'obter_plano_completo_checklist',
    'obter_plano_da_implantacao',
    '_plano_usa_checklist_items',
    # Estrutura
    'atualizar_estrutura_plano',
    '_criar_estrutura_plano',
    '_criar_estrutura_plano_checklist',
    '_criar_items_recursivo',
    'converter_estrutura_editor_para_checklist',
    '_converter_items_para_plano',
    # Aplicar
    'aplicar_plano_a_implantacao',
    'aplicar_plano_a_implantacao_checklist',
    'remover_plano_de_implantacao',
    '_clonar_plano_para_implantacao',
    '_clonar_plano_para_implantacao_checklist',
    # Validação
    'validar_estrutura_hierarquica',
    'validar_estrutura_checklist',
    '_validar_items_recursivo',
    'VALID_TAGS',
]
