# project/blueprints/gamification.py
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, g, jsonify
)
from datetime import datetime, date
import calendar
from ..blueprints.auth import login_required, permission_required
from ..db import query_db, execute_db
from ..services import calcular_pontuacao_gamificacao # Importa a função criada
from ..constants import PERFIS_COM_GESTAO # Apenas gestão pode ver/editar

gamification_bp = Blueprint('gamification', __name__, url_prefix='/gamification')

def get_all_cs_users():
    """Busca todos os usuários com perfil que podem ser avaliados."""
    # Adiciona filtro para perfil_acesso não ser nulo ou vazio e ordena
    return query_db("SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome")

@gamification_bp.route('/report', methods=['GET'])
@login_required
@permission_required(PERFIS_COM_GESTAO)
def gamification_report():
    """Exibe o relatório de pontuação da gamificação."""
    now = datetime.now()
    current_year = now.year
    # Default para o mês anterior se for início do mês (até dia 5), senão mês atual
    current_month = now.month - 1 if now.day <= 5 and now.month > 1 else now.month
    if current_month == 0: # Ajuste para Dezembro do ano anterior
        current_month = 12
        current_year -= 1

    try:
        selected_month = request.args.get('mes', default=current_month, type=int)
        selected_year = request.args.get('ano', default=current_year, type=int)
        # Validação básica
        if not (1 <= selected_month <= 12 and 1900 < selected_year < 3000):
            flash("Mês ou ano inválido selecionado.", "warning")
            selected_month=current_month
            selected_year=current_year
    except ValueError:
        flash("Mês ou ano inválido.", "warning")
        selected_month=current_month
        selected_year=current_year


    all_cs = get_all_cs_users()
    report_data = []
    calculation_errors = {}

    # Garante que all_cs é uma lista antes de iterar
    if all_cs is None:
        all_cs = []
        flash("Não foi possível buscar a lista de colaboradores.", "error")


    for cs in all_cs:
        # Garante que cs é um dicionário e tem 'usuario'
        if not isinstance(cs, dict) or 'usuario' not in cs:
            continue
        # Pula o cálculo se o usuário não tiver um nome (pode ser conta inativa/inválida)
        if not cs.get('nome'):
            continue
        try:
            # Chama a função de serviço para calcular a pontuação
            score_details = calcular_pontuacao_gamificacao(cs['usuario'], selected_month, selected_year)
            report_data.append({
                'usuario_cs': cs['usuario'],
                'nome': cs.get('nome') or cs['usuario'], # Usa get com fallback
                **score_details # Adiciona todos os detalhes retornados pelo cálculo
            })
        except ValueError as ve: # Erros esperados (ex: perfil não encontrado)
            print(f"Aviso ao calcular gamificação para {cs['usuario']} ({selected_month}/{selected_year}): {ve}")
            # Não adiciona ao erro crítico, apenas pula este usuário no relatório
        except Exception as e:
            print(f"Erro CRÍTICO ao calcular gamificação para {cs['usuario']} ({selected_month}/{selected_year}): {e}")
            calculation_errors[cs['usuario']] = f"Erro interno ao processar. Verifique os logs." # Mensagem genérica

    # Ordena por pontuação (maior primeiro), tratando inelegíveis
    report_data.sort(key=lambda x: x.get('pontuacao_final', -999) if x.get('elegivel', False) else -999, reverse=True)


    return render_template(
        'gamification_report.html',
        report_data=report_data,
        all_cs=all_cs, # Para filtros futuros, se necessário
        selected_month=selected_month,
        selected_year=selected_year,
        current_year=now.year, # Usa o ano atual real para o seletor
        calculation_errors=calculation_errors,
        user_info=g.user, # Passa user_info para o base.html
        g=g # Passa g para acesso ao g.perfil no template
    )

@gamification_bp.route('/metrics', methods=['GET', 'POST'])
@login_required
@permission_required(PERFIS_COM_GESTAO)
def manage_gamification_metrics():
    """Página para inserir/editar as métricas manuais da gamificação."""
    all_cs = get_all_cs_users()
    # Garante que all_cs é uma lista
    if all_cs is None: all_cs = []

    now = datetime.now()
    current_year = now.year
    # Default para o mês anterior se for início do mês (até dia 5), senão mês atual
    current_month = now.month - 1 if now.day <= 5 and now.month > 1 else now.month
    if current_month == 0: # Ajuste para Dezembro do ano anterior
        current_month = 12
        current_year -= 1


    # --- Lógica GET (Exibir formulário) ---
    if request.method == 'GET':
        selected_cs = request.args.get('usuario_cs')

        try:
            selected_month = request.args.get('mes', default=current_month, type=int)
            selected_year = request.args.get('ano', default=current_year, type=int)
            # Validação básica
            if not (1 <= selected_month <= 12 and 1900 < selected_year < 3000):
                flash("Mês ou Ano inválido selecionado.", "warning")
                selected_month = current_month
                selected_year = current_year
        except ValueError:
            flash("Mês ou ano inválido.", "warning")
            selected_month=current_month
            selected_year=current_year

        metrics = None
        if selected_cs:
            try:
                metrics = query_db(
                    "SELECT * FROM gamificacao_metricas_mensais WHERE usuario_cs = %s AND mes = %s AND ano = %s",
                    (selected_cs, selected_month, selected_year),
                    one=True
                )
                # Converte para dicionário padrão se for DictRow ou Row
                if metrics and not isinstance(metrics, dict):
                    metrics = dict(metrics)

                if not metrics:
                     # Se não existe, cria um dicionário vazio para o template não falhar
                     metrics = {'usuario_cs': selected_cs, 'mes': selected_month, 'ano': selected_year}

                # --- CORREÇÃO: Chamar o cálculo para exibir os pontos ---
                # Garante que o cálculo seja executado se o usuário e o período forem válidos
                score_details = calcular_pontuacao_gamificacao(selected_cs, selected_month, selected_year)
                
                # Atualiza o dicionário 'metrics' com os detalhes do score
                metrics.update(score_details)
                
            except Exception as e:
                flash(f"Erro ao buscar métricas existentes: {e}", "error")
                print(f"Erro GET /gamification/metrics (query/calc): {e}")
                metrics = {'usuario_cs': selected_cs, 'mes': selected_month, 'ano': selected_year} # Fallback


        return render_template(
            'gamification_metrics_form.html',
            all_cs=all_cs,
            selected_cs=selected_cs,
            selected_month=selected_month,
            selected_year=selected_year,
            current_year=now.year, # Ano atual real para o seletor
            metrics=metrics,
            user_info=g.user, # Passa user_info para o base.html
            g=g # Passa g para acesso ao g.perfil no template
        )

    # --- Lógica POST (Salvar formulário) ---
    elif request.method == 'POST':
        usuario_cs = request.form.get('usuario_cs')
        mes_str = request.form.get('mes')
        ano_str = request.form.get('ano')

        try:
            mes = int(mes_str) if mes_str else None
            ano = int(ano_str) if ano_str else None
            registrado_por = g.user_email # Quem está salvando

            if not all([usuario_cs, mes, ano, 1 <= mes <= 12, 1900 < ano < 3000]):
                raise ValueError("Usuário, Mês e Ano válidos são obrigatórios.")

            # Função helper para converter form para int ou None
            def form_to_int_or_none(field_name):
                value = request.form.get(field_name)
                if value is None or value == '':
                    return None
                try:
                    # Garante que seja um número inteiro não negativo onde aplicável
                    int_val = int(value)
                    # Adiciona validação de intervalo se necessário (ex: 0-100 para percentuais)
                    if field_name in ['nota_qualidade', 'assiduidade', 'planos_sucesso_perc', 'satisfacao_processo']:
                        if not (0 <= int_val <= 100):
                             raise ValueError(f"Valor para {field_name} deve estar entre 0 e 100.")
                    elif int_val < 0:
                         # Para contagens, não permitir negativos
                          raise ValueError(f"Valor para {field_name} não pode ser negativo.")
                    return int_val
                except (ValueError, TypeError):
                    # Se não for um inteiro válido, retorna None (ou lança erro?)
                    # Retornar None permite salvar campos vazios como NULL
                    # Lançar erro força o preenchimento correto
                    raise ValueError(f"Valor inválido para {field_name}: '{value}'. Use apenas números inteiros.")


            # Coleta todos os campos manuais do formulário
            manual_metrics = {
                'nota_qualidade': form_to_int_or_none('nota_qualidade'),
                'assiduidade': form_to_int_or_none('assiduidade'),
                'planos_sucesso_perc': form_to_int_or_none('planos_sucesso_perc'),
                'satisfacao_processo': form_to_int_or_none('satisfacao_processo'),
                'reclamacoes': form_to_int_or_none('reclamacoes') or 0, # Default 0 se None
                'perda_prazo': form_to_int_or_none('perda_prazo') or 0,
                'nao_preenchimento': form_to_int_or_none('nao_preenchimento') or 0,
                'elogios': form_to_int_or_none('elogios') or 0,
                'recomendacoes': form_to_int_or_none('recomendacoes') or 0,
                'certificacoes': form_to_int_or_none('certificacoes') or 0,
                'treinamentos_pacto_part': form_to_int_or_none('treinamentos_pacto_part') or 0,
                'treinamentos_pacto_aplic': form_to_int_or_none('treinamentos_pacto_aplic') or 0,
                'reunioes_presenciais': form_to_int_or_none('reunioes_presenciais') or 0,
                'cancelamentos_resp': form_to_int_or_none('cancelamentos_resp') or 0,
                'nao_envolvimento': form_to_int_or_none('nao_envolvimento') or 0,
                'desc_incompreensivel': form_to_int_or_none('desc_incompreensivel') or 0,
                'hora_extra': form_to_int_or_none('hora_extra') or 0,
                 # Adicionar aqui 'perda_sla_grupo' e 'finalizacao_incompleta' se os campos forem criados
                 'perda_sla_grupo': form_to_int_or_none('perda_sla_grupo') or 0,
                 'finalizacao_incompleta': form_to_int_or_none('finalizacao_incompleta') or 0,
            }

            # Verifica se já existe um registro para UPSERT
            existing_record = query_db(
                "SELECT id FROM gamificacao_metricas_mensais WHERE usuario_cs = %s AND mes = %s AND ano = %s",
                (usuario_cs, mes, ano), one=True
            )

            current_timestamp = datetime.now() # Usar timestamp consistente

            if existing_record:
                # UPDATE
                set_clauses = [f"{key} = %s" for key in manual_metrics.keys()]
                sql = f"""
                    UPDATE gamificacao_metricas_mensais
                    SET {', '.join(set_clauses)}, registrado_por = %s, data_registro = %s
                    WHERE id = %s
                """
                args = list(manual_metrics.values()) + [registrado_por, current_timestamp, existing_record['id']]
                execute_db(sql, tuple(args))
                flash(f"Métricas manuais de {usuario_cs} para {mes:02d}/{ano} atualizadas com sucesso. A pontuação foi recalculada.", "success")
            else:
                # INSERT
                columns = ['usuario_cs', 'mes', 'ano', 'registrado_por', 'data_registro'] + list(manual_metrics.keys())
                values_placeholders = ['%s'] * len(columns)
                sql = f"INSERT INTO gamificacao_metricas_mensais ({', '.join(columns)}) VALUES ({', '.join(values_placeholders)})"
                args = [usuario_cs, mes, ano, registrado_por, current_timestamp] + list(manual_metrics.values())
                execute_db(sql, tuple(args))
                flash(f"Métricas manuais de {usuario_cs} para {mes:02d}/{ano} salvas com sucesso. A pontuação foi calculada.", "success")

            # CORREÇÃO: Recalcula e redireciona para a visualização atualizada (que chamará o GET com os pontos)
            return redirect(url_for('gamification.manage_gamification_metrics', usuario_cs=usuario_cs, mes=mes, ano=ano))

        except ValueError as ve:
             flash(f"Erro nos dados do formulário: {ve}", "error")
        except Exception as e:
            flash(f"Erro CRÍTICO ao salvar métricas: {e}. Verifique os logs do servidor.", "error")
            print(f"Erro POST /gamification/metrics: {e}") # Log detalhado no servidor

        # Em caso de erro, recarrega a página GET com os parâmetros originais (se possível)
        usuario_cs_fallback = request.form.get('usuario_cs', '')
        mes_fallback = request.form.get('mes', current_month)
        ano_fallback = request.form.get('ano', current_year)
        # Garante que os fallbacks sejam válidos antes de redirecionar
        try:
             mes_fallback = int(mes_fallback)
             ano_fallback = int(ano_fallback)
             if not (1 <= mes_fallback <= 12): mes_fallback = current_month
             if not (1900 < ano_fallback < 3000): ano_fallback = current_year
        except:
             mes_fallback = current_month
             ano_fallback = current_year

        return redirect(url_for('gamification.manage_gamification_metrics', usuario_cs=usuario_cs_fallback, mes=mes_fallback, ano=ano_fallback))