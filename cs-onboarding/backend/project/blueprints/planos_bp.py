from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, g
from functools import wraps
from ..domain import planos_sucesso_service
from ..db import logar_timeline
from ..__init__ import csrf
from ..common.exceptions import ValidationError
from ..blueprints.auth import login_required
from ..config.logging_config import planos_logger

planos_bp = Blueprint('planos', __name__, url_prefix='/planos')


def get_current_user():
    if hasattr(g, 'perfil') and g.perfil:
        return g.perfil
    return None


def requires_permission(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.is_json:
                    return jsonify({'error': 'Não autenticado'}), 401
                flash('Você precisa estar logado para acessar esta página.', 'error')
                return redirect(url_for('auth.login'))

            perfil = user.get('perfil_acesso', '').lower()
            if perfil not in allowed_roles:
                if request.is_json:
                    return jsonify({'error': 'Permissão negada'}), 403
                flash('Você não tem permissão para acessar esta funcionalidade.', 'error')
                return redirect(url_for('main.dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


@planos_bp.route('/', methods=['GET'])
@login_required
def listar_planos():
    try:
        ativo_apenas = request.args.get('ativo', 'true').lower() == 'true'
        busca = request.args.get('busca', '').strip()

        planos = planos_sucesso_service.listar_planos_sucesso(
            ativo_apenas=ativo_apenas,
            busca=busca if busca else None
        )

        pode_editar = True
        pode_excluir = True

        wants_json = request.is_json or request.headers.get('Accept', '').startswith('application/json')

        if wants_json:
            return jsonify({
                'success': True,
                'planos': planos,
                'permissoes': {
                    'pode_editar': pode_editar,
                    'pode_excluir': pode_excluir
                }
            }), 200

        return render_template(
            'planos_sucesso.html',
            planos=planos,
            pode_editar=pode_editar,
            pode_excluir=pode_excluir,
            ativo_apenas=ativo_apenas,
            busca=busca
        )

    except Exception as e:
        planos_logger.error(f"Erro ao listar planos: {str(e)}", exc_info=True)
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Erro ao listar planos: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))


@planos_bp.route('/<int:plano_id>', methods=['GET'])
@login_required
def obter_plano(plano_id):
    try:
        plano = planos_sucesso_service.obter_plano_completo(plano_id)

        wants_json = request.is_json or request.headers.get('Accept', '').startswith('application/json')

        if not plano:
            if wants_json:
                return jsonify({'error': 'Plano não encontrado'}), 404
            flash('Plano não encontrado.', 'error')
            return redirect(url_for('planos.listar_planos'))

        if wants_json:
            return jsonify({'success': True, 'plano': plano}), 200

        pode_editar = True

        default_mode = 'editar' if pode_editar else 'visualizar'
        modo_req = request.args.get('modo', default_mode).strip().lower()
        if modo_req not in ['visualizar', 'editar']:
            modo_req = 'visualizar'

        return render_template(
            'plano_sucesso_editor.html',
            plano=plano,
            modo=modo_req,
            pode_editar=pode_editar
        )

    except Exception as e:
        planos_logger.error(f"Erro ao obter plano {plano_id}: {str(e)}", exc_info=True)
        wants_json = request.is_json or request.headers.get('Accept', '').startswith('application/json')
        if wants_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Erro ao obter plano: {str(e)}', 'error')
        return redirect(url_for('planos.listar_planos'))


@planos_bp.route('/novo', methods=['GET'])
@login_required
def novo_plano():
    return render_template('plano_sucesso_editor.html', modo='criar', pode_editar=True)


@planos_bp.route('/', methods=['POST'])
@login_required
@csrf.exempt
def criar_plano():
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()

        nome = data.get('nome', '').strip()
        descricao = data.get('descricao', '').strip()
        estrutura = data.get('estrutura', {})
        dias_duracao_str = data.get('dias_duracao', '')

        dias_duracao = None
        if dias_duracao_str:
            try:
                dias_duracao = int(dias_duracao_str)
                if dias_duracao < 1 or dias_duracao > 365:
                    raise ValidationError("Dias de duração deve ser entre 1 e 365")
            except ValueError:
                raise ValidationError("Dias de duração deve ser um número válido")

        if not nome:
            raise ValidationError("Nome do plano é obrigatório")

        if isinstance(estrutura, str):
            import json
            estrutura = json.loads(estrutura)

        user = get_current_user()
        criado_por = user.get('usuario') if user else 'sistema'

        plano_id = planos_sucesso_service.criar_plano_sucesso_checklist(
            nome=nome,
            descricao=descricao,
            criado_por=criado_por,
            estrutura=estrutura,
            dias_duracao=dias_duracao
        )

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Plano criado com sucesso',
                'plano_id': plano_id
            }), 201

        flash(f'Plano "{nome}" criado com sucesso!', 'success')
        return redirect(url_for('planos.obter_plano', plano_id=plano_id))

    except ValidationError as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(str(e), 'error')
        return redirect(url_for('planos.novo_plano'))

    except Exception as e:
        planos_logger.error(f"Erro ao criar plano: {str(e)}", exc_info=True)
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Erro ao criar plano: {str(e)}', 'error')
        return redirect(url_for('planos.novo_plano'))


@planos_bp.route('/<int:plano_id>', methods=['PUT', 'POST'])
@login_required
@csrf.exempt
def atualizar_plano(plano_id):
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            ativo_values = request.form.getlist('ativo')
            if ativo_values:
                data['ativo'] = 'true' in ativo_values or 'on' in ativo_values
            else:
                data['ativo'] = False

        if request.method == 'POST' and '_method' in data:
            if data['_method'].upper() != 'PUT':
                return jsonify({'error': 'Método não permitido'}), 405

        dados_atualizacao = {}

        if 'nome' in data:
            dados_atualizacao['nome'] = data['nome']

        if 'descricao' in data:
            dados_atualizacao['descricao'] = data['descricao']

        if 'ativo' in data:
            ativo_val = data.get('ativo')
            dados_atualizacao['ativo'] = ativo_val in [True, 'true', '1', 1, 'on']

        if 'dias_duracao' in data:
            dias_val = data['dias_duracao']
            if dias_val:
                try:
                    dias_int = int(dias_val)
                    if dias_int < 1 or dias_int > 365:
                        raise ValidationError("Dias de duração deve ser entre 1 e 365")
                    dados_atualizacao['dias_duracao'] = dias_int
                except ValueError:
                    raise ValidationError("Dias de duração deve ser um número válido")
            else:
                dados_atualizacao['dias_duracao'] = None

        estrutura = data.get('estrutura', {})
        if estrutura:
            if isinstance(estrutura, str):
                import json
                try:
                    estrutura = json.loads(estrutura)
                except json.JSONDecodeError:
                    planos_logger.error(f"Erro ao fazer parse da estrutura JSON: {estrutura[:200]}")
                    raise ValidationError("Estrutura inválida: JSON malformado")
            
            if estrutura and (estrutura.get('items') or estrutura.get('fases')):
                planos_sucesso_service.atualizar_estrutura_plano(plano_id, estrutura)

        planos_sucesso_service.atualizar_plano_sucesso(plano_id, dados_atualizacao)

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Plano atualizado com sucesso'
            }), 200

        flash('Plano atualizado com sucesso!', 'success')
        return redirect(url_for('planos.obter_plano', plano_id=plano_id))

    except ValidationError as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(str(e), 'error')
        return redirect(url_for('planos.obter_plano', plano_id=plano_id))

    except Exception as e:
        planos_logger.error(f"Erro ao atualizar plano {plano_id}: {str(e)}", exc_info=True)
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Erro ao atualizar plano: {str(e)}', 'error')
        return redirect(url_for('planos.obter_plano', plano_id=plano_id))


@planos_bp.route('/<int:plano_id>', methods=['DELETE'])
@login_required
def excluir_plano(plano_id):
    try:
        planos_sucesso_service.excluir_plano_sucesso(plano_id)

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Plano excluído com sucesso'
            }), 200

        flash('Plano excluído com sucesso!', 'success')
        return redirect(url_for('planos.listar_planos'))

    except ValidationError as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(str(e), 'error')
        return redirect(url_for('planos.listar_planos'))

    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Erro ao excluir plano: {str(e)}', 'error')
        return redirect(url_for('planos.listar_planos'))


@planos_bp.route('/<int:plano_id>/preview', methods=['GET'])
@login_required
def preview_plano(plano_id):
    try:
        plano = planos_sucesso_service.obter_plano_completo(plano_id)
        wants_json = request.is_json or request.headers.get('Accept', '').startswith('application/json')

        if not plano:
            if wants_json:
                return jsonify({'error': 'Plano não encontrado'}), 404
            return render_template('partials/_plano_preview.html', plano=None)

        if wants_json:
            return jsonify({'success': True, 'plano': plano}), 200

        return render_template('partials/_plano_preview.html', plano=plano)

    except Exception as e:
        wants_json = request.is_json or request.headers.get('Accept', '').startswith('application/json')
        if wants_json:
            return jsonify({'error': str(e)}), 500
        return render_template('partials/_plano_preview.html', plano=None, erro=str(e))


@planos_bp.route('/implantacao/<int:implantacao_id>/aplicar', methods=['POST'])
@login_required
@csrf.exempt
def aplicar_plano_implantacao(implantacao_id):
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        plano_id = data.get('plano_id')

        if not plano_id:
            raise ValidationError("ID do plano é obrigatório")

        plano_id = int(plano_id)

        user = get_current_user()
        usuario = user.get('usuario') if user else 'sistema'
        responsavel_nome = None
        if user:
            responsavel_nome = user.get('nome') or None
            try:
                if not responsavel_nome and hasattr(g, 'user') and g.user:
                    responsavel_nome = g.user.get('name')
            except Exception:
                pass

        planos_sucesso_service.aplicar_plano_a_implantacao_checklist(
            implantacao_id=implantacao_id,
            plano_id=plano_id,
            usuario=usuario,
            responsavel_nome=responsavel_nome
        )

        try:
            logar_timeline(
                implantacao_id,
                usuario,
                'plano_aplicado',
                f'Plano {plano_id} aplicado à implantação {implantacao_id} por {usuario}'
            )
        except Exception:
            pass

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Plano aplicado com sucesso à implantação'
            }), 200

        flash('Plano aplicado com sucesso!', 'success')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    except ValidationError as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(str(e), 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    except Exception as e:
        planos_logger.error(f"Erro ao aplicar plano {plano_id} à implantação {implantacao_id}: {str(e)}", exc_info=True)
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Erro ao aplicar plano: {str(e)}', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))


@planos_bp.route('/implantacao/<int:implantacao_id>/plano', methods=['GET'])
@login_required
def obter_plano_implantacao(implantacao_id):
    try:
        plano = planos_sucesso_service.obter_plano_da_implantacao(implantacao_id)
        wants_json = request.is_json or request.headers.get('Accept', '').startswith('application/json')

        if wants_json:
            return jsonify({
                'success': True,
                'plano': plano
            }), 200

        return render_template('partials/_plano_preview.html', plano=plano)

    except Exception as e:
        wants_json = request.is_json or request.headers.get('Accept', '').startswith('application/json')
        if wants_json:
            return jsonify({'error': str(e)}), 500
        return render_template('partials/_plano_preview.html', plano=None, erro=str(e))


@planos_bp.route('/implantacao/<int:implantacao_id>/plano', methods=['DELETE'])
@login_required
def remover_plano_implantacao(implantacao_id):
    try:
        user = get_current_user()
        usuario = user.get('usuario') if user else 'sistema'

        planos_sucesso_service.remover_plano_de_implantacao(
            implantacao_id=implantacao_id,
            usuario=usuario
        )

        try:
            logar_timeline(
                implantacao_id,
                usuario,
                'plano_removido',
                f'Plano removido da implantação {implantacao_id} por {usuario}'
            )
        except Exception:
            pass

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Plano removido da implantação'
            }), 200

        flash('Plano removido da implantação!', 'success')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    except ValidationError as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(str(e), 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Erro ao remover plano: {str(e)}', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))
