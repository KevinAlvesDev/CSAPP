from flask import (
    Blueprint, request, g, jsonify
)
from ..db import query_db, execute_db
from ..blueprints.auth import login_required, permission_required
from ..constants import PERFIS_COM_GESTAO
from ..services import get_analytics_data 

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics_dashboard', methods=['GET'])
@login_required
@permission_required(PERFIS_COM_GESTAO)
def analytics_dashboard():
    """Retorna dados de analytics para o dashboard gerencial (agora como JSON)."""
    
    try:
        target_cs_email = request.args.get('cs_filter') or None
        target_status = request.args.get('status_filter') or 'todas'
        start_date = request.args.get('start_date') or None
        end_date = request.args.get('end_date') or None
        
        if target_cs_email == 'todos': target_cs_email = None

        global_metrics, cs_metrics_list, implantacoes_paradas_detalhadas = get_analytics_data(
            target_cs_email=target_cs_email,
            target_status=target_status,
            start_date=start_date,
            end_date=end_date
        )
        
        all_cs_users = query_db(
            "SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IN %s ORDER BY nome", 
            (tuple(PERFIS_COM_GESTAO),)
        )
        
        status_options = [
            {'value': 'todas', 'label': 'Todas as Implantações'},
            {'value': 'andamento', 'label': 'Em Andamento'},
            {'value': 'atrasadas_status', 'label': 'Atrasadas (> 25d)'},
            {'value': 'futura', 'label': 'Futuras'},
            {'value': 'finalizada', 'label': 'Finalizadas'},
            {'value': 'parada', 'label': 'Paradas'}
        ]

        return jsonify(
            success=True,
            global_metrics=global_metrics,
            cs_metrics=cs_metrics_list,
            implantacoes_paradas_detalhadas=implantacoes_paradas_detalhadas,
            all_cs_users=all_cs_users,
            status_options=status_options,
            current_filters={
                'cs_filter': target_cs_email or 'todos',
                'status_filter': target_status,
                'start_date': start_date,
                'end_date': end_date
            }
        )

    except Exception as e:
        print(f"Erro ao carregar dados de analytics: {e}")
        return jsonify(success=False, error=f"Erro ao carregar dados de analytics: {e}"), 500