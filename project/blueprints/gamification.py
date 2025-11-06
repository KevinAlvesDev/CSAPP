from flask import Blueprint, render_template, request, flash, redirect, url_for, g
from ..blueprints.auth import permission_required
from ..db import query_db, execute_db

# --- INÍCIO DA CORREÇÃO (Refatoração) ---
# Importa as funções de serviço/domínio no topo do arquivo.
# Isto é seguro agora que a lógica não está mais neste arquivo.
from ..domain.gamification_service import (
    _get_all_gamification_rules_grouped,
    get_gamification_report_data, 
    _get_gamification_automatic_data_bulk
)
# --- FIM DA CORREÇÃO ---

from ..constants import PERFIS_COM_GESTAO
from datetime import datetime, timedelta 
from collections import OrderedDict 
import calendar 

gamification_bp = Blueprint('gamification', __name__, url_prefix='/gamification')

def _get_all_cs_users_for_gamification():
    """Busca todos os usuários com nome e e-mail para o filtro de gamificação."""
    result = query_db("SELECT usuario, nome, cargo FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome", ())
    return result if result is not None else []

# --- FUNÇÃO REMOVIDA ---
# A função _get_all_gamification_rules_grouped() foi movida 
# para project/domain/gamification_service.py
# --- FIM DA REMOÇÃO ---

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
    
    # A importação de _get_gamification_automatic_data_bulk foi movida para o topo.
    
    all_cs_users = _get_all_cs_users_for_gamification()
    
    # --- Busca as regras para a UI ---
    # Agora usa a função importada do serviço
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
    metricas_automaticas = {}
    
    if target_cs_email:
        # 1. Busca métricas manuais (existente)
        metricas_atuais = query_db(
            "SELECT * FROM gamificacao_metricas_mensais WHERE usuario_cs = %s AND mes = %s AND ano = %s",
            (target_cs_email, target_mes, target_ano),
            one=True
        )
        
        # (Buscar métricas automáticas para visualização)
        try:
            # Definir Período
            primeiro_dia = datetime(target_ano, target_mes, 1)
            dias_no_mes = calendar.monthrange(target_ano, target_mes)[1]
            ultimo_dia = datetime(target_ano, target_mes, dias_no_mes)
            fim_ultimo_dia = datetime.combine(ultimo_dia, datetime.max.time())
            
            primeiro_dia_str = primeiro_dia.isoformat()
            fim_ultimo_dia_str = fim_ultimo_dia.isoformat()

            # Chamar a função bulk (filtrando para 1 user)
            tma_data_map, iniciadas_map, tarefas_map = _get_gamification_automatic_data_bulk(
                target_mes, target_ano, primeiro_dia_str, fim_ultimo_dia_str, target_cs_email
            )
            
            # Processar os resultados para este user
            dados_tma = tma_data_map.get(target_cs_email, {})
            count_iniciadas = iniciadas_map.get(target_cs_email, 0)
            dados_tarefas = tarefas_map.get(target_cs_email, {})

            # Calcular valores
            count_finalizadas = dados_tma.get('count', 0)
            tma_total_dias = dados_tma.get('total_dias', 0)
            tma_medio = round(tma_total_dias / count_finalizadas, 1) if count_finalizadas > 0 else 0.0

            count_acao_interna = dados_tarefas.get('Ação interna', 0)
            count_reuniao = dados_tarefas.get('Reunião', 0)
            
            media_reunioes_dia = round(count_reuniao / dias_no_mes, 2) if dias_no_mes > 0 else 0.0
            media_acoes_dia = round(count_acao_interna / dias_no_mes, 2) if dias_no_mes > 0 else 0.0

            metricas_automaticas = {
                'tma_medio_mes': f"{tma_medio} dias" if tma_medio > 0 else "N/A",
                'impl_iniciadas_mes': count_iniciadas,
                'reunioes_concluidas_dia_media': f"{media_reunioes_dia:.2f}",
                'acoes_concluidas_dia_media': f"{media_acoes_dia:.2f}"
            }
            
        except Exception as e_auto:
            print(f"Erro ao calcular métricas automáticas para {target_cs_email}: {e_auto}")
            flash(f"Erro ao buscar dados automáticos: {e_auto}", "warning")


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
        metricas_automaticas=metricas_automaticas,
        current_year=hoje.year,
        regras_agrupadas=regras_agrupadas
    )

@gamification_bp.route('/report')
@permission_required(PERFIS_COM_GESTAO)
def gamification_report():
    """Rota para exibir o relatório de pontuação da gamificação."""
    
    # A importação de get_gamification_report_data foi movida para o topo.
    
    all_cs_users = _get_all_cs_users_for_gamification()
    
    hoje = datetime.now()
    
    default_mes = int(request.args.get('mes', hoje.month))
    default_ano = int(request.args.get('ano', hoje.year))
    
    target_cs_email = request.args.get('cs_email')
    
    try:
        report_data_sorted = get_gamification_report_data(
            default_mes, 
            default_ano, 
            target_cs_email,
            all_cs_users_list=all_cs_users 
        )
    except Exception as e:
        print(f"ERRO CRÍTICO ao gerar relatório de gamificação: {e}")
        flash(f"Erro ao gerar relatório: {e}", "error")
        report_data_sorted = []

    return render_template(
        'gamification_report.html',
        report_data=report_data_sorted,
        all_cs_users=all_cs_users,
        current_cs_email=target_cs_email,
        selected_month=default_mes,
        selected_year=default_ano,
        current_year=hoje.year 
    )