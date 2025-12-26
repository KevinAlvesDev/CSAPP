"""
Módulo de CRUD de Implantação
Responsável por criar, excluir, transferir e cancelar implantações.
Princípio SOLID: Single Responsibility
"""
from datetime import datetime

from flask import current_app

from ...common.utils import format_date_br
from ...constants import MODULO_OPCOES, PERFIS_COM_GESTAO
from ...db import execute_and_fetch_one, execute_db, logar_timeline, query_db


def criar_implantacao_service(nome_empresa, usuario_atribuido, usuario_criador, id_favorecido=None):
    """
    Cria uma nova implantação completa.
    """
    if not nome_empresa:
        raise ValueError('Nome da empresa é obrigatório.')
    if not usuario_atribuido:
        raise ValueError('Usuário a ser atribuído é obrigatório.')

    existente = query_db(
        """
        SELECT id, status
        FROM implantacoes
        WHERE LOWER(nome_empresa) = LOWER(%s)
          AND status IN ('nova','futura','andamento','parada')
        LIMIT 1
        """,
        (nome_empresa,), one=True
    )
    if existente:
        status_existente = existente.get('status')
        raise ValueError(f'Já existe uma implantação ativa para "{nome_empresa}" (status: {status_existente}).')

    tipo = 'completa'
    status = 'nova'
    agora = datetime.now()

    result = execute_and_fetch_one(
        "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status, data_inicio_previsto, data_inicio_efetivo, id_favorecido) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (usuario_atribuido, nome_empresa, tipo, agora, status, None, None, id_favorecido)
    )

    implantacao_id = result.get('id') if result else None
    if not implantacao_id:
        raise Exception("Falha ao obter ID da nova implantação.")

    logar_timeline(implantacao_id, usuario_criador, 'implantacao_criada', f'Implantação "{nome_empresa}" ({tipo.capitalize()}) criada e atribuída a {usuario_atribuido}.')
    
    return implantacao_id


def criar_implantacao_modulo_service(nome_empresa, usuario_atribuido, usuario_criador, modulo_tipo, id_favorecido=None):
    """
    Cria uma nova implantação de módulo.
    """
    if not nome_empresa:
        raise ValueError('Nome da empresa é obrigatório.')
    if not usuario_atribuido:
        raise ValueError('Usuário a ser atribuído é obrigatório.')
    
    modulo_opcoes = {
        'nota_fiscal': 'Nota fiscal',
        'vendas_online': 'Vendas Online',
        'app_treino': 'App Treino',
        'recorrencia': 'Recorrência'
    }
    if modulo_tipo not in modulo_opcoes:
        raise ValueError('Módulo inválido.')

    existente = query_db(
        """
        SELECT id, status
        FROM implantacoes
        WHERE LOWER(nome_empresa) = LOWER(%s)
          AND status IN ('nova','futura','andamento','parada')
        LIMIT 1
        """,
        (nome_empresa,), one=True
    )
    if existente:
        status_existente = existente.get('status')
        raise ValueError(f'Já existe uma implantação ativa para "{nome_empresa}" (status: {status_existente}).')

    tipo = 'modulo'
    status = 'nova'
    agora = datetime.now()

    result = execute_and_fetch_one(
        "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status, data_inicio_previsto, data_inicio_efetivo, id_favorecido) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (usuario_atribuido, nome_empresa, tipo, agora, status, None, None, id_favorecido)
    )

    implantacao_id = result.get('id') if result else None
    if not implantacao_id:
        raise Exception("Falha ao obter ID da nova implantação de módulo.")

    modulo_label = MODULO_OPCOES.get(modulo_tipo, modulo_tipo)
    logar_timeline(implantacao_id, usuario_criador, 'implantacao_criada', f'Implantação de Módulo "{nome_empresa}" (módulo: {modulo_label}) criada e atribuída a {usuario_atribuido}.')

    return implantacao_id


def transferir_implantacao_service(implantacao_id, usuario_cs_email, novo_usuario_cs):
    """
    Transfere a responsabilidade de uma implantação para outro usuário.
    """
    if not novo_usuario_cs or not implantacao_id:
        raise ValueError('Dados inválidos para transferência.')

    impl = query_db("SELECT nome_empresa, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    if not impl:
        raise ValueError('Implantação não encontrada.')

    antigo_usuario_cs = impl.get('usuario_cs', 'Ninguém')
    execute_db("UPDATE implantacoes SET usuario_cs = %s WHERE id = %s", (novo_usuario_cs, implantacao_id))
    
    logar_timeline(implantacao_id, usuario_cs_email, 'detalhes_alterados', f'Implantação "{impl.get("nome_empresa")}" transferida de {antigo_usuario_cs} para {novo_usuario_cs} por {usuario_cs_email}.')
    
    return antigo_usuario_cs


def excluir_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso):
    """
    Exclui permanentemente uma implantação e seus dados associados.
    """
    impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO
    
    if not (is_owner or is_manager):
        raise ValueError('Permissão negada.')

    # Buscar imagens de comentários para exclusão (R2)
    comentarios_img = query_db(
        """ SELECT DISTINCT c.imagem_url 
            FROM comentarios_h c 
            WHERE EXISTS (
                SELECT 1 FROM checklist_items ci 
                WHERE c.checklist_item_id = ci.id
                AND ci.implantacao_id = %s
            )
            AND c.imagem_url IS NOT NULL AND c.imagem_url != '' """,
        (implantacao_id,)
    )
    
    from ...core.extensions import r2_client
    
    public_url_base = current_app.config.get('CLOUDFLARE_PUBLIC_URL')
    bucket_name = current_app.config.get('CLOUDFLARE_BUCKET_NAME')
    
    if r2_client and public_url_base and bucket_name:
        for c in comentarios_img:
            imagem_url = c.get('imagem_url')
            if imagem_url and imagem_url.startswith(public_url_base):
                try:
                    object_key = imagem_url.replace(f"{public_url_base}/", "")
                    if object_key:
                        r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                except Exception as e:
                    current_app.logger.warning(f"Falha ao excluir R2 (key: {object_key}): {e}")

    execute_db("DELETE FROM implantacoes WHERE id = %s", (implantacao_id,))


def cancelar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso, data_cancelamento_iso, motivo, comprovante_url):
    """
    Cancela uma implantação.
    """
    impl = query_db("SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)

    is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        raise ValueError('Permissão negada para cancelar esta implantação.')

    if impl.get('status') in ['finalizada', 'cancelada']:
        raise ValueError(f'Implantação já está {impl.get("status")}.')

    if impl.get('status') == 'nova':
        raise ValueError('Ações indisponíveis para implantações "Nova". Inicie a implantação para habilitar cancelamento.')

    execute_db(
        "UPDATE implantacoes SET status = 'cancelada', data_cancelamento = %s, motivo_cancelamento = %s, comprovante_cancelamento_url = %s, data_finalizacao = CURRENT_TIMESTAMP WHERE id = %s",
        (data_cancelamento_iso, motivo, comprovante_url, implantacao_id)
    )

    logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação CANCELADA.\nMotivo: {motivo}\nData inf.: {format_date_br(data_cancelamento_iso)}')
