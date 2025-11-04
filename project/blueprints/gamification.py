from flask import Blueprint, render_template, request, flash, redirect, url_for, g
from ..blueprints.auth import permission_required
from ..db import query_db, execute_db
# --- ALTERAÇÃO ---
# Trocamos a chamada de 'calcular_pontuacao_gamificacao' 
# pela nova função de busca em massa 'get_gamification_report_data'
from ..services import get_gamification_report_data
# --- FIM DA ALTERAÇÃO ---
from ..constants import PERFIS_COM_GESTAO
from datetime import datetime, timedelta 
from collections import OrderedDict 

gamification_bp = Blueprint('gamification', __name__, url_prefix='/gamification')

def _get_all_cs_users_for_gamification():
    """Busca todos os usuários com nome e e-mail para o filtro de gamificação."""
    result = query_db("SELECT usuario, nome, cargo FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome", ())
    return result if result is not None else []

def _get_all_gamification_rules_grouped():
    """Busca todas as regras de gamificação e as agrupa por categoria."""
    regras = query_db("SELECT * FROM gamificacao_regras ORDER BY categoria, id")
    if not regras:
        return {}
    
    regras_agrupadas = OrderedDict()
    for regra in regras:
        categoria = regra['categoria']
        if categoria not in regras_agrupadas:
            regras_agrupadas[categoria] = []
        regras_agrupadas[categoria].append(regra)
    return regras_agrupadas

@gamification_bp.route('/save-rules-modal', methods=['POST'])
@permission_required(PERFIS_COM_GESTAO)
def save_gamification_rules_from_modal():
    """
    Rota (apenas POST) para salvar as regras de gamificação
    enviadas pelo formulário dentro do modal em base.html.
    """
    fallback_redirect = redirect(request.referrer or url_for('main.dashboard'))
    
    try:
        updates_to_make = []
        for key, value in request.form.items():
            if key.startswith('regra-'):
                regra_id = key.replace('regra-', '')
                try:
                    valor_pontos = int(value)
                    updates_to_make.append((valor_pontos, regra_id))
                except (ValueError, TypeError):
                    print(f"AVISO: Valor inválido recebido para {regra_id}: {value}")
        
        if not updates_to_make:
            flash('Nenhum dado válido foi enviado para atualização.', 'warning')
            return fallback_redirect

        total_atualizado = 0
        for valor, regra_id in updates_to_make:
            execute_db(
                "UPDATE gamificacao_regras SET valor_pontos = %s WHERE regra_id = %s",
                (valor, regra_id)
            )
            total_atualizado += 1
        
        flash(f'{total_atualizado} regras de pontuação foram atualizadas com sucesso!', 'success')
    
    except Exception as e:
        print(f"ERRO ao atualizar regras de gamificação (modal): {e}")
        flash(f'Erro ao salvar as regras: {e}', 'error')
    
    return fallback_redirect


@gamification_bp.route('/metrics', methods=['GET', 'POST'])
@permission_required(PERFIS_COM_GESTAO)
def manage_gamification_metrics():
    """Rota para gestores inserirem/atualizarem as métricas manuais de um CS."""
    
    all_cs_users = _get_all_cs_users_for_gamification()
    
    # --- Busca as regras para a UI ---
    regras_agrupadas = _get_all_gamification_rules_grouped()
    
    target_cs_email = request.args.get('cs_email')
    
    hoje = datetime.now()
    default_mes = hoje.month
    default_ano = hoje.year

    try:
        target_mes = int(request.values.get('mes', default_mes))
        target_ano = int(request.values.get('ano', default_ano))
    except ValueError:
        target_mes = default_mes
        target_ano = default_ano

    
    metricas_atuais = None
    if target_cs_email:
        metricas_atuais = query_db(
            "SELECT * FROM gamificacao_metricas_mensais WHERE usuario_cs = %s AND mes = %s AND ano = %s",
            (target_cs_email, target_mes, target_ano),
            one=True
        )
    
    if not metricas_atuais:
        metricas_atuais = {} # Garante que é um dict para o template


    if request.method == 'POST':
        if not target_cs_email:
            flash("É necessário selecionar um usuário para salvar as métricas.", "error")
            return redirect(url_for('gamification.manage_gamification_metrics'))
        
        try:
            data_to_save = {
                'usuario_cs': target_cs_email,
                'mes': target_mes,
                'ano': target_ano,
                'data_registro': datetime.now()
            }
            
            float_fields = ['nota_qualidade', 'assiduidade', 'planos_sucesso_perc', 'satisfacao_processo']
            int_fields = [
                'reclamacoes', 'perda_prazo', 'nao_preenchimento', 'elogios', 
                'recomendacoes', 'certificacoes', 'treinamentos_pacto_part', 
                'treinamentos_pacto_aplic', 'reunioes_presenciais', 'cancelamentos_resp', 
                'nao_envolvimento', 'desc_incompreensivel', 'hora_extra', 
                'perda_sla_grupo', 'finalizacao_incompleta'
            ]

            for field in float_fields:
                value_str = request.form.get(field)
                if value_str:
                    try:
                        data_to_save[field] = float(value_str)
                    except ValueError:
                        data_to_save[field] = None
                else:
                    data_to_save[field] = None 

            for field in int_fields:
                value_str = request.form.get(field)
                try:
                    data_to_save[field] = int(value_str) if value_str else 0
                except ValueError:
                    data_to_save[field] = 0

            existing_record_id = metricas_atuais.get('id') if metricas_atuais else None
            
            if existing_record_id:
                set_clauses = [f"{key} = %s" for key in data_to_save.keys() if key not in ['usuario_cs', 'mes', 'ano']]
                sql_update = f"""
                    UPDATE gamificacao_metricas_mensais
                    SET {', '.join(set_clauses)}
                    WHERE id = %s
                """
                args = list(data_to_save.values())[3:] + [existing_record_id] 
                
                execute_db(sql_update, tuple(args))
                flash("Métricas manuais atualizadas com sucesso!", "success")
                
            else:
                columns = data_to_save.keys()
                values_placeholders = ['%s'] * len(columns)
                sql_insert = f"INSERT INTO gamificacao_metricas_mensais ({', '.join(columns)}) VALUES ({', '.join(values_placeholders)})"
                args = list(data_to_save.values())

                execute_db(sql_insert, tuple(args))
                flash("Métricas manuais salvas com sucesso!", "success")

            return redirect(url_for('gamification.manage_gamification_metrics', cs_email=target_cs_email, mes=target_mes, ano=target_ano))

        except Exception as e:
            print(f"ERRO ao salvar métricas de gamificação: {e}")
            flash(f"Erro ao salvar métricas: {e}", "error")
            
    return render_template(
        'gamification_metrics_form.html',
        all_cs_users=all_cs_users,
        current_cs_email=target_cs_email,
        current_mes=target_mes,
        current_ano=target_ano,
        metricas_atuais=metricas_atuais,
        current_year=hoje.year,
        # Passa as regras para o template
        regras_agrupadas=regras_agrupadas
    )

@gamification_bp.route('/report')
@permission_required(PERFIS_COM_GESTAO)
def gamification_report():
    """Rota para exibir o relatório de pontuação da gamificação."""
    
    all_cs_users = _get_all_cs_users_for_gamification()
    
    hoje = datetime.now()
    
    # --- ALTERAÇÃO (AJUSTE MÊS ATUAL) ---
    default_mes = int(request.args.get('mes', hoje.month))
    default_ano = int(request.args.get('ano', hoje.year))
    # --- FIM DA ALTERAÇÃO ---
    
    target_cs_email = request.args.get('cs_email')
    
    # --- INÍCIO DA ALTERAÇÃO (N+1) ---
    # A lógica de loop foi movida para 'get_gamification_report_data'
    
    try:
        report_data_sorted = get_gamification_report_data(
            default_mes, 
            default_ano, 
            target_cs_email,
            all_cs_users_list=all_cs_users # Passa a lista de usuários para evitar re-query
        )
    except Exception as e:
        print(f"ERRO CRÍTICO ao gerar relatório de gamificação: {e}")
        flash(f"Erro ao gerar relatório: {e}", "error")
        report_data_sorted = []
    # --- FIM DA ALTERAÇÃO (N+1) ---

    return render_template(
        'gamification_report.html',
        report_data=report_data_sorted,
        all_cs_users=all_cs_users,
        current_cs_email=target_cs_email,
        selected_month=default_mes,
        selected_year=default_ano,
        current_year=hoje.year 
    )