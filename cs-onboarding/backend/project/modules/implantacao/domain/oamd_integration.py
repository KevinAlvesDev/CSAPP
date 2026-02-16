"""
Módulo de Integração OAMD para Implantações
Funções para consultar e aplicar dados do sistema externo OAMD.
Princípio SOLID: Single Responsibility
"""

import re

from ....db import db_transaction_with_lock, query_db


def consultar_dados_oamd(impl_id=None, user_email=None, id_favorecido_direto=None):
    """
    Consulta dados externos (OAMD) para uma implantação.
    Substitui a lógica de GET /api/v1/oamd/implantacoes/<id>/consulta.

    Args:
        impl_id: ID da implantação (opcional se id_favorecido_direto for fornecido)
        user_email: Email do usuário
        id_favorecido_direto: ID Favorecido direto (opcional, usado quando implantação não existe)

    Returns:
        dict: Dados do OAMD categorizados em persistibles, derived, extras
    """
    from ..infra.external_service import consultar_empresa_oamd as svc_consultar_empresa

    # Inicializar variáveis
    id_favorecido = id_favorecido_direto
    infra_req = None

    # Se impl_id foi fornecido, tentar buscar dados locais
    if impl_id:
        impl = query_db(
            "SELECT id, id_favorecido, chave_oamd, informacao_infra, tela_apoio_link FROM implantacoes WHERE id = %s",
            (impl_id,),
            one=True,
        )

        if impl:
            # Usar id_favorecido da implantação se não foi fornecido diretamente
            if not id_favorecido:
                id_favorecido = impl.get("id_favorecido")
            infra_req = impl.get("informacao_infra")

    # Se não temos id_favorecido de nenhuma fonte, erro
    if not id_favorecido and not infra_req:
        raise ValueError("Implantação não encontrada e nenhum ID Favorecido fornecido")

    # Extract numeric part from infra if possible as fallback
    infra_digits = None
    if infra_req:
        m = re.search(r"(\d+)", str(infra_req))
        if m:
            infra_digits = m.group(1)

    # Call external service
    result = svc_consultar_empresa(id_favorecido=id_favorecido, infra_req=infra_digits if not id_favorecido else None)

    if not result.get("ok") or not result.get("mapped"):
        # Construir link de apoio
        link = f"https://app.pactosolucoes.com.br/apoio/apoio/{id_favorecido}" if id_favorecido else ""

        return {"persistibles": {}, "extras": {}, "derived": {"tela_apoio_link": link}, "found": False}

    mapped = result.get("mapped", {})
    empresa = result.get("empresa", {})

    # Construir persistibles (dados que podem ser salvos na tabela implantacoes)
    persistibles = _build_persistibles(mapped, empresa, id_favorecido)

    # Derived (dados calculados)
    derived = _build_derived(mapped)

    # Extras (dados informativos)
    extras = _build_extras(empresa)

    return {"persistibles": persistibles, "derived": derived, "extras": extras, "found": True}


def _build_persistibles(mapped, empresa, id_favorecido):
    """
    Constrói dicionário de dados persistíveis na tabela implantacoes.
    """
    persistibles = {
        "id_favorecido": empresa.get("codigofinanceiro") or id_favorecido,
        "chave_oamd": mapped.get("chave_oamd"),
        "cnpj": mapped.get("cnpj"),
        "data_cadastro": mapped.get("data_cadastro"),
        "status_implantacao": mapped.get("status_implantacao"),
    }

    # Refinando com dados crus da empresa se mapped não tiver tudo
    field_mapping = {
        "tipocliente": "tipo_do_cliente",
        "inicioimplantacao": "inicio_implantacao",
        "finalimplantacao": "final_implantacao",
        "inicioproducao": "inicio_producao",
        "nivelreceitamensal": "nivel_receita_do_cliente",
        "categoria": "categorias",
        "nivelatendimento": "nivel_atendimento",
        "condicaoespecial": "condicao_especial",
        "cs_nome": "analista_cs_responsavel",
        "cs_url": "link_agendamento_cs",
        "cs_telefone": "telefone_cs",
    }

    for empresa_field, impl_field in field_mapping.items():
        if empresa_field in empresa:
            persistibles[impl_field] = empresa[empresa_field]

    return persistibles


def _build_derived(mapped):
    """
    Constrói dicionário de dados derivados/calculados.
    """
    derived = {}

    if mapped.get("informacao_infra"):
        derived["informacao_infra"] = mapped["informacao_infra"]
    if mapped.get("tela_apoio_link"):
        derived["tela_apoio_link"] = mapped["tela_apoio_link"]

    return derived


def _build_extras(empresa):
    """
    Constrói dicionário de dados extras/informativos.
    """
    return {
        "nome_fantasia": empresa.get("nomefantasia"),
        "razao_social": empresa.get("razaosocial"),
        "endereco": empresa.get("endereco"),
        "bairro": empresa.get("bairro"),
        "cidade": empresa.get("cidade"),
        "estado": empresa.get("estado"),
        "nicho": empresa.get("nicho"),
        "ultima_atualizacao": empresa.get("ultimaatualizacao"),
    }


def aplicar_dados_oamd(impl_id, user_email, updates_dict):
    """
    Aplica atualizações OAMD na implantação.
    Substitui POST /api/v1/oamd/implantacoes/<id>/aplicar

    Args:
        impl_id: ID da implantação
        user_email: Email do usuário
        updates_dict: Dicionário com campos a atualizar

    Returns:
        dict: Resultado da operação
    """

    # Validar implantação
    impl = query_db("SELECT id FROM implantacoes WHERE id = %s", (impl_id,), one=True)
    if not impl:
        raise ValueError("Implantação não encontrada")

    allowed_fields = [
        "id_favorecido",
        "chave_oamd",
        "informacao_infra",
        "tela_apoio_link",
        "status_implantacao_oamd",
        "nivel_atendimento",
        "cnpj",
        "data_cadastro",
        "valor_atribuido",
    ]
    filtered_updates = {k: v for k, v in updates_dict.items() if k in allowed_fields}

    if not filtered_updates:
        return {"updated": False}

    set_clauses = []
    values = []
    for k, v in filtered_updates.items():
        set_clauses.append(f"{k} = %s")
        values.append(v)

    values.append(impl_id)

    with db_transaction_with_lock() as (conn, cursor, db_type):
        sql = f"UPDATE implantacoes SET {', '.join(set_clauses)} WHERE id = %s"
        if db_type == "sqlite":
            sql = sql.replace("%s", "?")
        cursor.execute(sql, tuple(values))
        conn.commit()

    return {"updated": True, "fields": filtered_updates}
