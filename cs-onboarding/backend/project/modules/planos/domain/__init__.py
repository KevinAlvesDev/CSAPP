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
# Importações de aplicar.py
from .aplicar import (
    _clonar_plano_para_implantacao,
    _clonar_plano_para_implantacao_checklist,
    aplicar_plano_a_implantacao,
    aplicar_plano_a_implantacao_checklist,
    remover_plano_de_implantacao,
)
from .crud import (
    _plano_usa_checklist_items,
    atualizar_plano_sucesso,
    clonar_plano_sucesso,
    concluir_plano_sucesso,
    contar_planos_em_andamento,
    contar_planos_por_status,
    criar_plano_sucesso,
    criar_plano_sucesso_checklist,
    excluir_plano_sucesso,
    listar_planos_sucesso,
    obter_plano_completo,
    obter_plano_completo_checklist,
    obter_plano_da_implantacao,
)

# Importações de estrutura.py
from .estrutura import (
    _converter_items_para_plano,
    _criar_estrutura_plano,
    _criar_estrutura_plano_checklist,
    _criar_items_recursivo,
    atualizar_estrutura_plano,
    converter_estrutura_editor_para_checklist,
)

# Importações de validacao.py
from .validacao import (
    _validar_items_recursivo,
    get_valid_tags,
    validar_estrutura_checklist,
    validar_estrutura_hierarquica,
)

# Exports públicos
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
    # Estrutura
    "atualizar_estrutura_plano",
    "atualizar_plano_sucesso",
    "clonar_plano_sucesso",
    "concluir_plano_sucesso",
    "contar_planos_em_andamento",
    "contar_planos_por_status",
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
