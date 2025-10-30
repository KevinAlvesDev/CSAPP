from flask import (
    Blueprint, request, g, jsonify
)
from ..db import query_db, execute_db
from ..blueprints.auth import login_required, permission_required
from ..constants import PERFIS_COM_GESTAO

gamification_bp = Blueprint('gamification', __name__)

@gamification_bp.route('/gamification/metrics', methods=['GET', 'POST'])
@login_required
@permission_required(PERFIS_COM_GESTAO)
def manage_gamification_metrics():
    """Gerencia (GET/POST) as métricas de gamificação."""
    
    if request.method == 'POST':
        try:
            data = request.json
            metrics = data.get('metrics', [])
            
            execute_db("DELETE FROM gamification_metrics")
            
            if metrics:
                query_args = []
                for m in metrics:
                    if m.get('nome') and m.get('pontos') is not None:
                        query_args.append((
                            m['nome'],
                            m.get('condicao'),
                            m.get('valor_condicao'),
                            int(m['pontos']),
                            m.get('tipo', 'bonus')
                        ))
                
                if query_args:
                    execute_db(
                        "INSERT INTO gamification_metrics (nome, condicao, valor_condicao, pontos, tipo) VALUES (%s, %s, %s, %s, %s)",
                        query_args,
                        many=True
                    )
            
            novas_metricas = query_db("SELECT * FROM gamification_metrics ORDER BY tipo, nome")
            return jsonify(success=True, message="Métricas de gamificação salvas com sucesso!", metrics=novas_metricas)
            
        except Exception as e:
            print(f"Erro ao salvar métricas de gamificação: {e}")
            return jsonify(success=False, error=f"Erro ao salvar métricas: {e}"), 500

    # --- Método GET ---
    try:
        metrics = query_db("SELECT * FROM gamification_metrics ORDER BY tipo, nome")
        return jsonify(success=True, metrics=metrics)
    except Exception as e:
        print(f"Erro ao carregar métricas de gamificação: {e}")
        return jsonify(success=False, error=f"Erro ao carregar métricas: {e}"), 500


@gamification_bp.route('/gamification/report', methods=['GET'])
@login_required
@permission_required(PERFIS_COM_GESTAO)
def gamification_report():
    """Exibe o relatório de gamificação (agora como JSON)."""
    
    try:
        # (Lógica de geração de relatório deve ser implementada aqui)
        report_data = [
            {"usuario": "usuario1@exemplo.com", "nome": "Usuário 1", "pontos_totais": 150, "bonus": 50, "penalidades": -10},
            {"usuario": "usuario2@exemplo.com", "nome": "Usuário 2", "pontos_totais": 120, "bonus": 20, "penalidades": 0},
        ]
        
        users = query_db("SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IN %s", (tuple(PERFIS_COM_GESTAO),))

        return jsonify(
            success=True,
            report_title="Relatório de Gamificação (Exemplo)",
            report_data=report_data,
            available_users=users
        )
        
    except Exception as e:
        print(f"Erro ao gerar relatório de gamificação: {e}")
        return jsonify(success=False, error=f"Erro ao gerar relatório: {e}"), 500