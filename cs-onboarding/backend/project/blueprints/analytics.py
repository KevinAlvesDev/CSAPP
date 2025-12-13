from flask import Blueprint, flash, g, jsonify, make_response, redirect, render_template, request, url_for

from ..blueprints.auth import permission_required
from ..common.validation import ValidationError, sanitize_string, validate_date, validate_email
from ..constants import PERFIS_COM_ANALYTICS, PERFIS_COM_GESTAO
from ..domain.analytics_service import (
    get_analytics_data,
    get_cancelamentos_data,
    get_funnel_counts,
    get_gamification_rank,
    get_implants_by_day,
)
from ..domain.management_service import listar_todos_cs_com_cache

analytics_bp = Blueprint('analytics', __name__)



@analytics_bp.route('/analytics')
@permission_required(PERFIS_COM_ANALYTICS)
def analytics_dashboard():
    """Rota para o dashboard gerencial de métricas e relatórios, com filtros."""

    user_perfil = g.perfil.get('perfil_acesso')

    cs_email = None
    status_filter = 'todas'
    start_date = None
    end_date = None
    sort_impl_date = None

    try:
        cs_email_param = request.args.get('cs_email')
        if cs_email_param:
            try:
                cs_email = validate_email(cs_email_param)
            except ValidationError:
                cs_email = None
                flash('Erro nos filtros: Email inválido — ignorado', 'warning')
        status_filter_param = request.args.get('status_filter', 'todas')
        try:
            status_filter = sanitize_string(status_filter_param, max_length=20)
        except ValidationError:
            status_filter = 'todas'
            flash('Erro nos filtros: Status inválido — ignorado', 'warning')
        sort_param = request.args.get('sort_impl_date')
        if sort_param:
            try:
                sort_impl_date = sanitize_string(sort_param, max_length=4)
            except ValidationError:
                sort_impl_date = None
        start_date_param = request.args.get('start_date')
        if start_date_param:
            try:
                start_date = validate_date(start_date_param)
            except ValidationError:
                start_date = None
                flash('Erro nos filtros: Data inicial inválida — ignorada', 'warning')
        end_date_param = request.args.get('end_date')
        if end_date_param:
            try:
                end_date = validate_date(end_date_param)
            except ValidationError:
                end_date = None
                flash('Erro nos filtros: Data final inválida — ignorada', 'warning')
    except Exception as e:
        flash(f'Erro nos filtros: {str(e)}', 'warning')
        cs_email = None
        status_filter = 'todas'
        start_date = None
        end_date = None

    task_cs_email = None
    task_start_date = None
    task_end_date = None

    try:
        task_cs_email_param = request.args.get('task_cs_email')
        if task_cs_email_param:
            try:
                task_cs_email = validate_email(task_cs_email_param)
            except ValidationError:
                task_cs_email = None
        task_start_date_param = request.args.get('task_start_date')
        if task_start_date_param:
            try:
                task_start_date = validate_date(task_start_date_param)
            except ValidationError:
                task_start_date = None
        task_end_date_param = request.args.get('task_end_date')
        if task_end_date_param:
            try:
                task_end_date = validate_date(task_end_date_param)
            except ValidationError:
                task_end_date = None
    except Exception:
        task_cs_email = None
        task_start_date = None
        task_end_date = None

    if user_perfil not in PERFIS_COM_GESTAO:
        cs_email = g.user_email
        task_cs_email = g.user_email

    try:

        analytics_data = get_analytics_data(
            target_cs_email=cs_email,
            target_status=status_filter,
            start_date=start_date,
            end_date=end_date,
            target_tag=None,
            task_cs_email=task_cs_email,
            task_start_date=task_start_date,
            task_end_date=task_end_date,
            sort_impl_date=sort_impl_date
        )

        all_cs = listar_todos_cs_com_cache()

        status_options = [
            {'value': 'todas', 'label': 'Todas as Implantações'},
            {'value': 'nova', 'label': 'Novas'},
            {'value': 'andamento', 'label': 'Em Andamento'},
            {'value': 'futura', 'label': 'Futuras'},
            {'value': 'finalizada', 'label': 'Finalizadas'},
            {'value': 'parada', 'label': 'Paradas'},
            {'value': 'cancelada', 'label': 'Canceladas'}
        ]

        current_task_cs_email = task_cs_email
        current_task_start_date = task_start_date or analytics_data.get('default_task_start_date')
        current_task_end_date = task_end_date or analytics_data.get('default_task_end_date')

        return render_template(
            'analytics.html',
            kpi_cards=analytics_data.get('kpi_cards', {}),
            implantacoes_lista_detalhada=analytics_data.get('implantacoes_lista_detalhada', []),
            modules_implantacao_lista=analytics_data.get('modules_implantacao_lista', []),
            chart_data=analytics_data.get('chart_data', {}),
            implantacoes_paradas_lista=analytics_data.get('implantacoes_paradas_lista', []),
            implantacoes_canceladas_lista=analytics_data.get('implantacoes_canceladas_lista', []),
            task_summary_data=analytics_data.get('task_summary_data', []),
            current_task_cs_email=current_task_cs_email,
            current_task_start_date=current_task_start_date,
            current_task_end_date=current_task_end_date,
            all_cs=all_cs,
            status_options=status_options,
            current_cs_email=cs_email,
            current_status_filter=status_filter,
            current_start_date=start_date,
            current_end_date=end_date,
            current_sort_impl_date=sort_impl_date,
            user_info=g.user,
            user_perfil=user_perfil
        )

    except Exception as e:
        from ..config.logging_config import get_logger
        logger = get_logger('analytics')
        logger.error(f"Erro ao carregar dashboard de analytics: {e}", exc_info=True)
        flash(f"Erro interno ao carregar os dados de relatórios: {e}", "error")
        return redirect(url_for('main.dashboard'))


@analytics_bp.route('/analytics/implants_by_day')
@permission_required(PERFIS_COM_ANALYTICS)
def api_implants_by_day():
    """Retorna contagem de implantações finalizadas por dia no período."""
    try:
        cs_email = request.args.get('cs_email')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if cs_email:
            cs_email = validate_email(cs_email)
        if start_date:
            start_date = validate_date(start_date)
        if end_date:
            end_date = validate_date(end_date)

        if g.perfil.get('perfil_acesso') not in PERFIS_COM_GESTAO:
            cs_email = g.user_email

        payload = get_implants_by_day(start_date=start_date, end_date=end_date, cs_email=cs_email)
        return jsonify({'ok': True, **payload})
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'Parâmetro inválido: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Erro interno: {str(e)}'}), 500


@analytics_bp.route('/cancelamentos')
@permission_required(PERFIS_COM_ANALYTICS)
def cancelamentos_dashboard():
    """Página analítica de cancelamentos com filtros e gráficos."""
    try:
        cs_email = request.args.get('cs_email')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if cs_email:
            try:
                cs_email = validate_email(cs_email)
            except ValidationError:
                cs_email = None
        if start_date:
            try:
                start_date = validate_date(start_date)
            except ValidationError:
                start_date = None
        if end_date:
            try:
                end_date = validate_date(end_date)
            except ValidationError:
                end_date = None

        if g.perfil.get('perfil_acesso') not in PERFIS_COM_GESTAO:
            cs_email = g.user_email

        payload = get_cancelamentos_data(cs_email=cs_email, start_date=start_date, end_date=end_date)
        return render_template('cancelamentos.html', **payload,
                               current_cs_email=cs_email,
                               current_start_date=start_date,
                               current_end_date=end_date,
                               user_info=g.user,
                               user_perfil=g.perfil.get('perfil_acesso'))
    except Exception as e:
        flash(f'Erro ao carregar cancelamentos: {e}', 'error')
        return redirect(url_for('analytics.analytics_dashboard'))


@analytics_bp.route('/cancelamentos/export/csv')
@permission_required(PERFIS_COM_ANALYTICS)
def export_cancelamentos_csv():
    """Exporta dataset de cancelamentos em CSV (compatível com Excel)."""
    try:
        cs_email = request.args.get('cs_email')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if cs_email:
            cs_email = validate_email(cs_email)
        if start_date:
            start_date = validate_date(start_date)
        if end_date:
            end_date = validate_date(end_date)
        if g.perfil.get('perfil_acesso') not in PERFIS_COM_GESTAO:
            cs_email = g.user_email

        payload = get_cancelamentos_data(cs_email=cs_email, start_date=start_date, end_date=end_date)
        rows = payload.get('dataset', [])
        headers = ['id', 'nome_empresa', 'usuario_cs', 'data_criacao', 'data_cancelamento', 'motivo_cancelamento', 'seguimento', 'tipos_planos', 'alunos_ativos', 'nivel_receita', 'valor_atribuido', 'tempo_permanencia_dias']
        out = ','.join(headers) + '\n'
        for r in rows:
            vals = [str(r.get(h, '')).replace(',', ';') for h in headers]
            out += ','.join(vals) + '\n'
        resp = make_response(out)
        resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
        resp.headers['Content-Disposition'] = 'attachment; filename=cancelamentos.csv'
        return resp
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Falha ao exportar CSV: {e}'}), 500


@analytics_bp.route('/analytics/funnel')
@permission_required(PERFIS_COM_ANALYTICS)
def api_funnel():
    """Retorna contagem por status para funil em período opcional."""
    try:
        cs_email = request.args.get('cs_email')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if cs_email:
            cs_email = validate_email(cs_email)
        if start_date:
            start_date = validate_date(start_date)
        if end_date:
            end_date = validate_date(end_date)

        if g.perfil.get('perfil_acesso') not in PERFIS_COM_GESTAO:
            cs_email = g.user_email

        payload = get_funnel_counts(start_date=start_date, end_date=end_date, cs_email=cs_email)
        return jsonify({'ok': True, **payload})
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'Parâmetro inválido: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Erro interno: {str(e)}'}), 500


@analytics_bp.route('/analytics/gamification_rank')
@permission_required(PERFIS_COM_ANALYTICS)
def api_gamification_rank():
    """Retorna ranking de gamificação por mês/ano."""
    try:
        month = request.args.get('month')
        year = request.args.get('year')

        if month:
            month = int(sanitize_string(month, max_length=2))
        if year:
            year = int(sanitize_string(year, max_length=4))

        payload = get_gamification_rank(month=month, year=year)
        return jsonify({'ok': True, **payload})
    except ValueError:
        return jsonify({'ok': False, 'error': 'Parâmetros month/year devem ser inteiros.'}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Erro interno: {str(e)}'}), 500
