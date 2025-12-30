"""
Endpoint temporário de debug para investigar schema OAMD
REMOVER APÓS USO!
"""
from flask import Blueprint, jsonify
from ..blueprints.auth import login_required
from ..constants import PERFIL_ADMIN
from ..database.external_db import query_external_db
from flask import g

debug_bp = Blueprint('debug', __name__, url_prefix='/api/debug')

@debug_bp.route('/schema-oamd', methods=['GET'])
@login_required
def schema_oamd():
    """
    Endpoint temporário para investigar schema do banco OAMD
    ATENÇÃO: Remover após uso!
    """
    # Verificar se é admin (CORRIGIDO: usar PERFIL_ADMIN)
    perfil_acesso = g.perfil.get('perfil_acesso') if g.get('perfil') else None
    if perfil_acesso != PERFIL_ADMIN:
        return jsonify({'ok': False, 'error': 'Acesso negado'}), 403
    
    try:
        result = {}
        
        # 1. Listar tabelas
        tables = query_external_db("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        result['tables'] = [t['table_name'] for t in tables] if tables else []
        
        # 2. Campos da tabela empresafinanceiro
        columns = query_external_db("""
            SELECT 
                column_name, 
                data_type,
                character_maximum_length,
                is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'empresafinanceiro'
            ORDER BY ordinal_position
        """)
        result['empresafinanceiro_columns'] = columns if columns else []
        
        # 3. Campos relacionados a datas/implantação
        date_fields = [c for c in columns if any(x in c['column_name'].lower() for x in 
                      ['data', 'inicio', 'final', 'producao', 'implantacao', 'cadastro', 
                       'status', 'nivel', 'receita', 'atendimento'])] if columns else []
        result['date_related_fields'] = date_fields
        
        # 4. Teste com ID Favorecido 11350
        test_result = query_external_db("""
            SELECT *
            FROM empresafinanceiro
            WHERE codigofinanceiro = %s
        """, (11350,))
        
        if test_result:
            empresa = test_result[0]
            result['test_id_11350'] = {
                'found': True,
                'nome': empresa.get('nomefantasia'),
                'all_fields': {k: str(v) for k, v in empresa.items()}
            }
        else:
            result['test_id_11350'] = {'found': False}
        
        # 5. Tabelas relacionadas a implantação
        impl_tables = [t for t in result['tables'] if any(x in t.lower() for x in 
                      ['implant', 'cliente', 'contrato', 'atendimento', 'producao'])]
        result['implantation_related_tables'] = impl_tables
        
        # Para cada tabela relacionada, buscar campos
        impl_tables_details = {}
        for table in impl_tables[:5]:  # Limitar a 5 tabelas
            # CORRIGIDO: usar parametrização para evitar SQL injection
            cols = query_external_db("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            impl_tables_details[table] = [{'name': c['column_name'], 'type': c['data_type']} for c in cols] if cols else []
        
        result['implantation_tables_details'] = impl_tables_details
        
        return jsonify({'ok': True, 'data': result})
        
    except Exception as e:
        import traceback
        return jsonify({
            'ok': False, 
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@debug_bp.route('/last-comment/<int:impl_id>', methods=['GET'])
@login_required
def check_last_comment(impl_id):
    """
    Debug endpoint para verificar o último comentário de uma implantação
    """
    from ..db import query_db
    from datetime import datetime
    
    try:
        # Buscar último comentário
        result = query_db("""
            SELECT 
                ci.implantacao_id,
                MAX(ch.data_criacao) as ultima_atividade,
                COUNT(ch.id) as total_comentarios
            FROM comentarios_h ch
            INNER JOIN checklist_items ci ON ch.checklist_item_id = ci.id
            WHERE ci.implantacao_id = %s
            GROUP BY ci.implantacao_id
        """, (impl_id,), one=True)
        
        # Buscar todos os comentários recentes
        all_comments = query_db("""
            SELECT 
                ch.id,
                ch.data_criacao,
                ch.texto,
                ch.usuario_cs,
                ci.nome as tarefa_nome
            FROM comentarios_h ch
            INNER JOIN checklist_items ci ON ch.checklist_item_id = ci.id
            WHERE ci.implantacao_id = %s
            ORDER BY ch.data_criacao DESC
            LIMIT 10
        """, (impl_id,))
        
        now = datetime.now()
        
        return jsonify({
            'ok': True,
            'impl_id': impl_id,
            'current_time': now.isoformat(),
            'last_activity_query': {
                'ultima_atividade': str(result.get('ultima_atividade')) if result else None,
                'total_comentarios': result.get('total_comentarios') if result else 0
            },
            'recent_comments': [
                {
                    'id': c['id'],
                    'data_criacao': str(c['data_criacao']),
                    'texto': c['texto'][:50] + '...' if len(c['texto']) > 50 else c['texto'],
                    'usuario': c['usuario_cs'],
                    'tarefa': c['tarefa_nome']
                }
                for c in (all_comments or [])
            ]
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'ok': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@debug_bp.route('/clear-cache', methods=['POST'])
@login_required
def clear_cache():
    """
    Limpa o cache do dashboard
    """
    try:
        from ..config.cache_config import cache
        if cache:
            cache.clear()
            return jsonify({'ok': True, 'message': 'Cache limpo com sucesso'})
        else:
            return jsonify({'ok': False, 'message': 'Cache não configurado'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

