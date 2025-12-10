"""
API v1 - Endpoints versionados

Esta é a primeira versão estável da API.
Mudanças breaking devem ser feitas em uma nova versão (v2, v3, etc).

Endpoints disponíveis:
- GET  /api/v1/implantacoes - Lista implantações
- GET  /api/v1/implantacoes/<id> - Detalhes de uma implantação
- POST /api/v1/implantacoes/<id>/tarefas/<tarefa_id>/toggle - Toggle tarefa
- POST /api/v1/implantacoes/<id>/tarefas/<tarefa_id>/comentarios - Adicionar comentário
"""


from flask import Blueprint, g, jsonify, request
from flask_limiter.util import get_remote_address

from ..blueprints.auth import login_required
from ..config.logging_config import api_logger
from ..constants import PERFIS_COM_GESTAO
from ..core.extensions import limiter
from ..db import query_db
from ..domain.hierarquia_service import get_hierarquia_implantacao
from ..security.api_security import validate_api_origin
from ..database.external_db import query_external_db

api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')


@api_v1_bp.before_request
def _api_v1_origin_guard():
    return validate_api_origin(lambda: None)()


@api_v1_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint para API v1."""
    return jsonify({
        'status': 'ok',
        'version': 'v1',
        'api': 'CSAPP API v1'
    })


@api_v1_bp.route('/implantacoes', methods=['GET'])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def list_implantacoes():
    """
    Lista implantações do usuário.

    Query params:
        - status: Filtrar por status (opcional)
        - page: Número da página (opcional, padrão 1)
        - per_page: Itens por página (opcional, padrão 50)

    Returns:
        JSON com lista de implantações
    """
    try:
        user_email = g.user_email
        status_filter = request.args.get('status')

        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 50))
            per_page = min(per_page, 200)
        except (TypeError, ValueError):
            page = 1
            per_page = 50

        offset = (page - 1) * per_page

        query = """
            SELECT i.*, p.nome as cs_nome
            FROM implantacoes i
            LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
            WHERE i.usuario_cs = %s
        """
        args = [user_email]

        if status_filter:
            query += " AND i.status = %s"
            args.append(status_filter)

        query += " ORDER BY i.data_criacao DESC LIMIT %s OFFSET %s"
        args.extend([per_page, offset])

        implantacoes = query_db(query, tuple(args)) or []

        count_query = "SELECT COUNT(*) as total FROM implantacoes WHERE usuario_cs = %s"
        count_args = [user_email]
        if status_filter:
            count_query += " AND status = %s"
            count_args.append(status_filter)

        total_result = query_db(count_query, tuple(count_args), one=True)
        total = total_result.get('total', 0) if total_result else 0

        return jsonify({
            'ok': True,
            'data': implantacoes,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        api_logger.error(f"Error listing implantacoes: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@api_v1_bp.route('/implantacoes/<int:impl_id>', methods=['GET'])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def get_implantacao(impl_id):
    """
    Retorna detalhes de uma implantação.

    Args:
        impl_id: ID da implantação

    Returns:
        JSON com detalhes da implantação
    """
    try:
        user_email = g.user_email

        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        if is_manager:
            impl = query_db(
                """SELECT i.*, p.nome as cs_nome
                   FROM implantacoes i
                   LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
                   WHERE i.id = %s""",
                (impl_id,),
                one=True
            )
        else:
            impl = query_db(
                """SELECT i.*, p.nome as cs_nome
                   FROM implantacoes i
                   LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
                   WHERE i.id = %s AND i.usuario_cs = %s""",
                (impl_id, user_email),
                one=True
            )

        if not impl:
            return jsonify({'ok': False, 'error': 'Implantação não encontrada'}), 404

        # Normalizar datas para strings ISO (YYYY-MM-DD) no payload
        def iso_date(val):
            try:
                from ..common.utils import format_date_iso_for_json
                return format_date_iso_for_json(val, only_date=True)
            except Exception:
                return None

        impl['data_criacao'] = iso_date(impl.get('data_criacao'))
        impl['data_inicio_efetivo'] = iso_date(impl.get('data_inicio_efetivo'))
        impl['data_inicio_producao'] = iso_date(impl.get('data_inicio_producao'))
        impl['data_final_implantacao'] = iso_date(impl.get('data_final_implantacao'))

        hierarquia = get_hierarquia_implantacao(impl_id)

        return jsonify({
            'ok': True,
            'data': {
                'implantacao': impl,
                'hierarquia': hierarquia
            }
        })

    except Exception as e:
        api_logger.error(f"Error getting implantacao {impl_id}: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@api_v1_bp.route('/oamd/implantacoes/<int:impl_id>/consulta', methods=['GET'])
@login_required
@limiter.limit("60 per minute", key_func=lambda: g.user_email or get_remote_address())
def consultar_oamd_implantacao(impl_id):
    try:
        impl = query_db("SELECT id, id_favorecido, chave_oamd FROM implantacoes WHERE id = %s", (impl_id,), one=True)
        if not impl:
            return jsonify({'ok': False, 'error': 'Implantação não encontrada'}), 404
        fav = impl.get('id_favorecido')
        key = impl.get('chave_oamd')
        cnpj = None
        where = []
        params = {}
        if fav:
            where.append("ef.codigo = :codigo")
            params['codigo'] = int(fav)
        if key:
            where.append("ef.chavezw = :chavezw")
            params['chavezw'] = key
        if cnpj:
            where.append("ef.cnpj = :cnpj")
            params['cnpj'] = cnpj
        if not where:
            return jsonify({'ok': False, 'error': 'Implantação sem chave de correlação (ID Favorecido/Chave ZW/CNPJ)'}), 400
        q = (
            "SELECT ef.codigo AS ef_codigo, ef.cnpj, ef.endereco, ef.estado, ef.nomefantasia, ef.razaosocial, ef.chavezw, ef.datacadastro, ef.ativazw, ef.dataexpiracaozw, ef.datadesativacao, ef.datasuspensaoempresazw, ef.ultimaatualizacao, ef.nomeempresazw, ef.tipoempresa, ef.nicho, ef.bairro, ef.cidade, ef.urlcontatoresponsavelpacto, ef.detalheempresa_codigo, "
            "ef.empresazw, "
            "de.inicioimplantacao, de.finalimplantacao, de.tipocliente, de.inicioproducao, de.condicaoespecial, de.nivelreceitamensal, de.categoria, de.nivelatendimento, de.statusimplantacao, de.customersuccess_codigo, de.implantador_codigo, de.responsavelpacto_codigo, "
            "cs.nome AS cs_nome, cs.telefone AS cs_telefone, cs.url AS cs_url "
            "FROM empresafinanceiro ef "
            "LEFT JOIN detalheempresa de ON ef.detalheempresa_codigo = de.codigo "
            "LEFT JOIN customersuccess cs ON de.customersuccess_codigo = cs.codigo "
            "WHERE " + " OR ".join(where)
        )
        rows = query_external_db(q, params) or []
        if not rows:
            return jsonify({'ok': True, 'data': {'persistibles': {}, 'extras': {}, 'derived': {}, 'found': False}})
        r = rows[0]
        def to_iso_date(val):
            try:
                import datetime
                if isinstance(val, datetime.date):
                    return val.isoformat()
                if isinstance(val, datetime.datetime):
                    return val.date().isoformat()
                return None
            except Exception:
                return None
        persistibles = {
            'id_favorecido': r.get('ef_codigo'),
            'chave_oamd': r.get('chavezw'),
            'cnpj': (r.get('cnpj') or ''),
            'data_cadastro': to_iso_date(r.get('datacadastro')),
            'status_implantacao': r.get('statusimplantacao'),
            'tipo_do_cliente': r.get('tipocliente'),
            'inicio_implantacao': to_iso_date(r.get('inicioimplantacao')),
            'final_implantacao': to_iso_date(r.get('finalimplantacao')),
            'inicio_producao': to_iso_date(r.get('inicioproducao')),
            'nivel_receita_do_cliente': r.get('nivelreceitamensal'),
            'categorias': r.get('categoria'),
            'nivel_atendimento': r.get('nivelatendimento'),
            'condicao_especial': r.get('condicaoespecial'),
            'analista_cs_responsavel': r.get('cs_nome'),
            'link_agendamento_cs': r.get('cs_url'),
            'telefone_cs': r.get('cs_telefone')
        }
        derived = {}
        # Extrair código da infra (ZW_###) e URL de integração
        infra_code = None
        # 1) Preferir coluna numerica empresazw
        if r.get('empresazw') is not None:
            try:
                code_int = int(r.get('empresazw'))
                if code_int > 0:
                    infra_code = f"ZW_{code_int}"
            except Exception:
                pass
        # 2) Tentar extrair do nomeempresazw (ex.: "ZW_804" ou "zw804")
        if not infra_code and r.get('nomeempresazw'):
            namezw = str(r.get('nomeempresazw')).strip()
            import re
            m = re.search(r"zw[_\-]?(\d+)", namezw, re.IGNORECASE)
            if m:
                infra_code = f"ZW_{m.group(1)}"
        # 3) Se ainda não tiver, montar informacao_infra com tipo/estado
        if infra_code:
            derived['informacao_infra'] = infra_code
            # host para URL integração é sempre "zw<codigo>"
            try:
                digits = ''.join([c for c in infra_code if c.isdigit()])
                if digits:
                    host = f"zw{digits}"
                    derived['tela_apoio_link'] = f"http://{host}.pactosolucoes.com.br/app"
            except Exception:
                pass
        else:
            infra_parts = []
            if r.get('tipoempresa'): infra_parts.append(str(r.get('tipoempresa')).strip())
            if r.get('ativazw') is not None: infra_parts.append('ATIVA' if r.get('ativazw') else 'INATIVA')
            if r.get('dataexpiracaozw'): infra_parts.append(f"Expira {to_iso_date(r.get('dataexpiracaozw'))}")
            if r.get('datadesativacao'): infra_parts.append(f"Desativada {to_iso_date(r.get('datadesativacao'))}")
            if r.get('datasuspensaoempresazw'): infra_parts.append(f"Suspensa {to_iso_date(r.get('datasuspensaoempresazw'))}")
            if infra_parts:
                derived['informacao_infra'] = ' | '.join([p for p in infra_parts if p])
        extras = {
            'nome_fantasia': r.get('nomefantasia'),
            'razao_social': r.get('razaosocial'),
            'endereco': r.get('endereco'),
            'bairro': r.get('bairro'),
            'cidade': r.get('cidade'),
            'estado': r.get('estado'),
            'nicho': r.get('nicho'),
            'ultima_atualizacao': r.get('ultimaatualizacao')
        }
        return jsonify({'ok': True, 'data': {'persistibles': persistibles, 'derived': derived, 'extras': extras, 'found': True}})
    except Exception as e:
        api_logger.error(f"Erro ao consultar OAMD para implantação {impl_id}: {e}")
        return jsonify({'ok': False, 'error': 'Erro interno na consulta ao OAMD'}), 500


