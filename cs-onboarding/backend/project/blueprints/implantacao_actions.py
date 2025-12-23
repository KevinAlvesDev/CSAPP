import os
import re
import time
from datetime import date, datetime

from botocore.exceptions import ClientError
from flask import Blueprint, current_app, flash, g, redirect, request, url_for
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename

from ..blueprints.auth import login_required, permission_required
from ..common import utils
from ..common.validation import ValidationError, sanitize_string, validate_date, validate_integer
from ..config.cache_config import clear_implantacao_cache, clear_user_cache
from ..config.logging_config import app_logger
from ..constants import NAO_DEFINIDO_BOOL, PERFIS_COM_CRIACAO, PERFIS_COM_GESTAO
from ..core.extensions import limiter, r2_client
from ..db import execute_and_fetch_one, execute_db, logar_timeline
from ..domain.task_definitions import MODULO_PENDENCIAS

implantacao_actions_bp = Blueprint('actions', __name__)


@implantacao_actions_bp.route('/criar_implantacao', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def criar_implantacao():
    usuario_criador = g.user_email

    try:
        nome_empresa = sanitize_string(request.form.get('nome_empresa', ''), max_length=200)
        usuario_atribuido = sanitize_string(request.form.get('usuario_atribuido_cs', ''), max_length=100)
        usuario_atribuido = usuario_atribuido or usuario_criador

        id_favorecido_raw = request.form.get('id_favorecido')
        id_favorecido = None
        if id_favorecido_raw:
            try:
                import re as _re
                digits_only = ''.join(_re.findall(r"\d+", str(id_favorecido_raw)))
                if digits_only:
                    id_favorecido = validate_integer(digits_only, min_value=1)
            except Exception:
                id_favorecido = None

        from ..domain.implantacao_service import criar_implantacao_service
        implantacao_id = criar_implantacao_service(nome_empresa, usuario_atribuido, usuario_criador, id_favorecido)

        flash(f'Implantação "{nome_empresa}" criada com sucesso. Aplique um plano de sucesso para criar as tarefas.', 'success')

        try:
            clear_user_cache(usuario_criador)
            if usuario_atribuido and usuario_atribuido != usuario_criador:
                clear_user_cache(usuario_atribuido)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass
        return redirect(url_for('main.dashboard'))

    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        app_logger.error(f"ERRO ao criar implantação por {usuario_criador}: {e}")
        flash(f'Erro ao criar implantação: {e}.', 'error')
        return redirect(url_for('main.dashboard'))


@implantacao_actions_bp.route('/criar_implantacao_modulo', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def criar_implantacao_modulo():
    usuario_criador = g.user_email

    try:
        nome_empresa = sanitize_string(request.form.get('nome_empresa_modulo', ''), max_length=200)
        usuario_atribuido = sanitize_string(request.form.get('usuario_atribuido_cs_modulo', ''), max_length=100)
        modulo_tipo = sanitize_string(request.form.get('modulo_tipo', ''), max_length=50)

        id_favorecido_raw = request.form.get('id_favorecido')
        id_favorecido = None
        if id_favorecido_raw:
            try:
                digits_only = ''.join(re.findall(r"\d+", str(id_favorecido_raw)))
                if digits_only:
                    id_favorecido = validate_integer(digits_only, min_value=1)
            except Exception:
                id_favorecido = None

        from ..domain.implantacao_service import criar_implantacao_modulo_service
        implantacao_id = criar_implantacao_modulo_service(nome_empresa, usuario_atribuido, usuario_criador, modulo_tipo, id_favorecido)

        try:
            clear_user_cache(usuario_criador)
            if usuario_atribuido and usuario_atribuido != usuario_criador:
                clear_user_cache(usuario_atribuido)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

        flash(f'Implantação de Módulo "{nome_empresa}" criada e atribuída a {usuario_atribuido}.', 'success')
        return redirect(url_for('main.dashboard'))

    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        app_logger.error(f"ERRO ao criar implantação de módulo por {usuario_criador}: {e}")
        flash(f'Erro ao criar implantação de módulo: {e}.', 'error')
        return redirect(url_for('main.dashboard'))


@implantacao_actions_bp.route('/iniciar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def iniciar_implantacao():
    usuario_cs_email = g.user_email

    try:
        implantacao_id = validate_integer(request.form.get('implantacao_id'), min_value=1)
    except ValidationError as e:
        flash(f'ID de implantação inválido: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

    redirect_to_fallback = request.form.get('redirect_to', 'dashboard')
    dest_url_fallback = url_for('main.dashboard')
    if redirect_to_fallback == 'detalhes':
        dest_url_fallback = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        from ..domain.implantacao_service import iniciar_implantacao_service
        iniciar_implantacao_service(implantacao_id, usuario_cs_email)

        flash('Implantação iniciada com sucesso!', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    except ValueError as e:
        flash(str(e), 'error')
        return redirect(request.referrer or dest_url_fallback)
    except Exception as e:
        app_logger.error(f"Erro ao iniciar implantação ID {implantacao_id}: {e}")
        flash('Erro ao iniciar implantação.', 'error')
        return redirect(url_for('main.dashboard'))


@implantacao_actions_bp.route('/agendar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def agendar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    data_prevista = request.form.get('data_inicio_previsto')

    if not data_prevista:
        flash('A data de início previsto é obrigatória.', 'error')
        return redirect(url_for('main.dashboard'))
    try:
        data_prevista_iso = validate_date(data_prevista)
    except ValidationError:
        flash('Data de início inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        from ..domain.implantacao_service import agendar_implantacao_service
        nome_empresa = agendar_implantacao_service(implantacao_id, usuario_cs_email, data_prevista_iso)

        flash(f'Implantação "{nome_empresa}" movida para "Futuras" com início em {data_prevista}.', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        app_logger.error(f"Erro ao agendar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao agendar implantação: {e}', 'error')

    return redirect(url_for('main.dashboard', refresh='1'))


@implantacao_actions_bp.route('/marcar_sem_previsao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def marcar_sem_previsao():
    usuario_cs_email = g.user_email
    implantacao_id_raw = request.form.get('implantacao_id')
    try:
        implantacao_id = validate_integer(int(implantacao_id_raw), min_value=1)
    except Exception:
        flash('ID da implantação inválido.', 'error')
        return redirect(url_for('main.dashboard', refresh='1'))

    try:
        from ..domain.implantacao_service import marcar_sem_previsao_service
        nome_empresa = marcar_sem_previsao_service(implantacao_id, usuario_cs_email)

        flash(f'Implantação "{nome_empresa}" marcada como "Sem previsão".', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        app_logger.error(f"Erro ao marcar sem previsão implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao marcar sem previsão: {e}', 'error')

    return redirect(url_for('main.dashboard', refresh='1'))


@implantacao_actions_bp.route('/finalizar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def finalizar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_target = request.form.get('redirect_to', 'dashboard')
    dest_url = url_for('main.dashboard')
    if redirect_target == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        data_finalizacao = request.form.get('data_finalizacao')
        if not data_finalizacao:
            flash('A data da finalização é obrigatória.', 'error')
            return redirect(dest_url)
        try:
            data_final_iso = validate_date(data_finalizacao)
        except ValidationError:
            flash('Data da finalização inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.', 'error')
            return redirect(dest_url)

        from ..domain.implantacao_service import finalizar_implantacao_service
        finalizar_implantacao_service(implantacao_id, usuario_cs_email, data_final_iso)

        flash('Implantação finalizada com sucesso!', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        app_logger.error(f"Erro ao finalizar implantação id={implantacao_id} user={usuario_cs_email}: {e}")
        flash('Erro ao finalizar implantação.', 'error')

    return redirect(dest_url)


@implantacao_actions_bp.route('/parar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def parar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    motivo = request.form.get('motivo_parada', '').strip()
    data_parada = request.form.get('data_parada')
    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    if not motivo:
        flash('O motivo da parada é obrigatório.', 'error')
        return redirect(dest_url)
    if not data_parada:
        flash('A data da parada é obrigatória.', 'error')
        return redirect(dest_url)
    try:
        data_parada_iso = validate_date(data_parada)
    except ValidationError:
        flash('Data da parada inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.', 'error')
        return redirect(dest_url)

    try:
        user_perfil_acesso = g.perfil.get('perfil_acesso') if getattr(g, 'perfil', None) else None
        
        from ..domain.implantacao_service import parar_implantacao_service
        parar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso, data_parada_iso, motivo)

        flash('Implantação marcada como "Parada" com data retroativa.', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        app_logger.error(f"Erro ao parar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao parar implantação: {e}', 'error')

    return redirect(dest_url)


@implantacao_actions_bp.route('/retomar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def retomar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard')
    dest_url = url_for('main.dashboard')
    if redirect_to == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        user_perfil_acesso = g.perfil.get('perfil_acesso') if getattr(g, 'perfil', None) else None
        
        from ..domain.implantacao_service import retomar_implantacao_service
        retomar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso)

        flash('Implantação retomada e movida para "Em Andamento".', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except ValueError as e:
        flash(str(e), 'error')
        return redirect(request.referrer or dest_url)
    except Exception as e:
        app_logger.error(f"Erro ao retomar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao retomar implantação: {e}', 'error')

    return redirect(dest_url)


@implantacao_actions_bp.route('/reabrir_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def reabrir_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard')
    dest_url = url_for('main.dashboard')
    if redirect_to == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        from ..domain.implantacao_service import reabrir_implantacao_service
        reabrir_implantacao_service(implantacao_id, usuario_cs_email)

        flash('Implantação reaberta com sucesso e movida para "Em Andamento".', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except ValueError as e:
        flash(str(e), 'error')
        return redirect(request.referrer or url_for('main.dashboard'))
    except Exception as e:
        app_logger.error(f"Erro ao reabrir implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao reabrir implantação: {e}', 'error')

    return redirect(dest_url)


@implantacao_actions_bp.route('/atualizar_detalhes_empresa', methods=['POST'])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def atualizar_detalhes_empresa():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard')
    user_perfil_acesso = g.perfil.get('perfil_acesso') if g.perfil else None

    dest_url = url_for('main.dashboard')
    if redirect_to == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)


    def get_form_value(key):
        value = request.form.get(key, '').strip()
        if value == "":
            return None
        return value

    def get_boolean_value(key):
        value = request.form.get(key, NAO_DEFINIDO_BOOL).strip()
        if value == NAO_DEFINIDO_BOOL or value == "":
            return None
        return value

    try:
        alunos_ativos_str = request.form.get('alunos_ativos', '0').strip()
        alunos_ativos = int(alunos_ativos_str) if alunos_ativos_str else 0
    except (ValueError, TypeError):
        alunos_ativos = 0

    def get_multiple_value(key):
        """Retorna valores de seleção múltipla como string separada por vírgula."""
        values = request.form.getlist(key)
        # Remover valores vazios e "Selecione..."
        values = [v.strip() for v in values if v and v.strip() and v.strip() != "Selecione..."]
        return ','.join(values) if values else None

    seguimento_val = get_multiple_value('seguimento')
    tipos_planos_val = get_multiple_value('tipos_planos')
    modalidades_val = get_multiple_value('modalidades')
    horarios_val = get_multiple_value('horarios_func')
    formas_pagamento_val = get_multiple_value('formas_pagamento')

    cargo_responsavel_val = get_form_value('cargo_responsavel')
    nivel_receita_val = get_form_value('nivel_receita')
    sistema_anterior_val = get_form_value('sistema_anterior')
    recorrencia_usa_val = get_form_value('recorrencia_usa')

    try:
        def normalize_date_str(s):
            """Converte DD/MM/AAAA para YYYY-MM-DD ou retorna None"""
            try:
                if not s:
                    return None

                s = str(s).strip()
                if not s or s == '':
                    return None

                if len(s) == 10 and s[4] == '-' and s[7] == '-':
                    try:
                        datetime.strptime(s, "%Y-%m-%d")
                        return s
                    except Exception as e:
                        app_logger.debug(f"Falha no parse de data YYYY-MM-DD: {e}")
                        pass

                if '/' in s:
                    parts = s.split('/')
                    if len(parts) == 3:
                        day = parts[0].strip().zfill(2)
                        month = parts[1].strip().zfill(2)
                        year = parts[2].strip()

                        result = f"{year}-{month}-{day}"

                        try:
                            datetime.strptime(result, "%Y-%m-%d")
                            return result
                        except Exception as e:
                            app_logger.debug(f"Falha no parse de data DD/MM/YYYY: {e}")
                            return None

                return None

            except Exception as e:
                app_logger.error(f"ERRO ao normalizar data '{s}': {e}")
                return None

        valor_raw = get_form_value('valor_monetario')
        if valor_raw is not None:
            v = valor_raw.replace('R$', '').strip()
            try:
                # Tenta converter direto (formato padrão do input type="number": 1234.56)
                v_float = float(v)
                valor_raw = f"{v_float:.2f}"
            except ValueError:
                # Fallback para formato BR (1.234,56) caso venha como texto
                try:
                    v_br = v.replace('.', '').replace(',', '.')
                    v_float = float(v_br)
                    valor_raw = f"{v_float:.2f}"
                except ValueError:
                    pass

        data_inicio_producao = normalize_date_str(get_form_value('data_inicio_producao'))
        data_final_implantacao = normalize_date_str(get_form_value('data_final_implantacao'))
        data_inicio_efetivo = normalize_date_str(get_form_value('data_inicio_efetivo'))

        data_inicio_efetivo_iso = data_inicio_efetivo or None

        telefone_raw = get_form_value('telefone_responsavel')
        telefone_validado = None
        if telefone_raw:
            # Remove caracteres não numéricos
            telefone_numeros = ''.join(filter(str.isdigit, telefone_raw))
            # Valida: deve ter 10 ou 11 dígitos
            if len(telefone_numeros) >= 10 and len(telefone_numeros) <= 11:
                # Formata: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX
                if len(telefone_numeros) == 11:
                    telefone_validado = f"({telefone_numeros[:2]}) {telefone_numeros[2:7]}-{telefone_numeros[7:]}"
                else:
                    telefone_validado = f"({telefone_numeros[:2]}) {telefone_numeros[2:6]}-{telefone_numeros[6:]}"
            else:
                flash('Telefone inválido. Use o formato (XX) XXXXX-XXXX ou (XX) XXXX-XXXX', 'warning')
                return redirect(dest_url)

        campos = {
            'responsavel_cliente': get_form_value('responsavel_cliente'),
            'cargo_responsavel': cargo_responsavel_val,
            'telefone_responsavel': telefone_validado,
            'email_responsavel': get_form_value('email_responsavel'),
            'data_inicio_producao': data_inicio_producao,
            'data_final_implantacao': data_final_implantacao,
            'data_inicio_efetivo': data_inicio_efetivo_iso,
            'id_favorecido': get_form_value('id_favorecido'),
            'nivel_receita': nivel_receita_val,
            'chave_oamd': get_form_value('chave_oamd'),
            'tela_apoio_link': get_form_value('tela_apoio_link'),
            'informacao_infra': get_form_value('informacao_infra'),
            'seguimento': seguimento_val,
            'tipos_planos': tipos_planos_val,
            'modalidades': modalidades_val,
            'horarios_func': horarios_val,
            'formas_pagamento': formas_pagamento_val,
            'diaria': get_boolean_value('diaria'),
            'freepass': get_boolean_value('freepass'),
            'alunos_ativos': alunos_ativos,
            'sistema_anterior': sistema_anterior_val,
            'importacao': get_boolean_value('importacao'),
            'recorrencia_usa': recorrencia_usa_val,
            'boleto': get_boolean_value('boleto'),
            'nota_fiscal': get_boolean_value('nota_fiscal'),
            'catraca': get_boolean_value('catraca'),
            'modelo_catraca': get_form_value('modelo_catraca') if get_boolean_value('catraca') == 'Sim' else None,
            'facial': get_boolean_value('facial'),
            'modelo_facial': get_form_value('modelo_facial') if get_boolean_value('facial') == 'Sim' else None,
            'wellhub': get_boolean_value('wellhub'),
            'totalpass': get_boolean_value('totalpass'),
            'cnpj': get_form_value('cnpj'),
            'status_implantacao_oamd': get_form_value('status_implantacao_oamd'),
            'nivel_atendimento': get_form_value('nivel_atendimento'),
            'valor_monetario': valor_raw,
            'resp_estrategico_nome': get_form_value('resp_estrategico_nome'),
            'resp_onb_nome': get_form_value('resp_onb_nome'),
            'resp_estrategico_obs': get_form_value('resp_estrategico_obs'),
            'contatos': get_form_value('contatos'),
        }
        
        
        # Chave OAMD pode ser: hash MD5, formato ZW_123, ou número puro
        # Não fazemos validação restritiva aqui, apenas limpeza básica
        try:
            co = campos.get('chave_oamd')
            if co and isinstance(co, str):
                # Remove espaços em branco
                campos['chave_oamd'] = co.strip() if co.strip() else None
        except Exception as e:
            app_logger.warning(f"Erro ao processar chave OAMD: {e}")
            pass


        # Prepare fields for service
        final_campos = {}
        for k, v in campos.items():
            if v is None:
                final_campos[k] = None
            elif isinstance(v, str):
                final_campos[k] = v
            elif isinstance(v, (datetime, date)):
                try:
                    final_campos[k] = v.strftime('%Y-%m-%d')
                except Exception:
                    final_campos[k] = str(v)
            else:
                final_campos[k] = v

        from ..domain.implantacao_service import atualizar_detalhes_empresa_service
        atualizar_detalhes_empresa_service(implantacao_id, usuario_cs_email, user_perfil_acesso, final_campos)

        try:
            logar_timeline(implantacao_id, usuario_cs_email, 'detalhes_alterados', 'Detalhes da empresa/cliente foram atualizados.')
        except Exception as e:
            app_logger.error(f"ERRO NO logar_timeline: {e}")
            pass

        flash('Detalhes da implantação atualizados com sucesso!', 'success')
        
        # Force cache clear - call twice to ensure it's cleared
        try:
            clear_implantacao_cache(implantacao_id)
            clear_user_cache(usuario_cs_email)
            # Clear again to be absolutely sure
            clear_implantacao_cache(implantacao_id)
        except Exception as ex:
            app_logger.error(f"Erro ao limpar cache: {ex}")
            pass

    except AttributeError as e:
        if 'isoformat' in str(e):
            app_logger.error(f"ERRO: Tentativa de chamar .isoformat() em string: {e}")
            flash('❌ Erro ao processar data. Verifique o formato (DD/MM/AAAA).', 'error')
        else:
            app_logger.error(f"ERRO AttributeError: {e}")
            flash('❌ Erro ao processar dados. Tente novamente.', 'error')
    except ValueError as e:
        # ValueError is used for validation errors - show specific message
        error_msg = str(e)
        app_logger.warning(f"Validation error: {error_msg}")
        flash(error_msg if error_msg else '❌ Dados inválidos. Verifique os campos.', 'error')
    except PermissionError as e:
        app_logger.warning(f"Permission denied: {e}")
        flash('❌ Você não tem permissão para realizar esta ação.', 'error')
    except TimeoutError as e:
        app_logger.error(f"Timeout error: {e}")
        flash('❌ Operação demorou muito tempo. Verifique sua conexão e tente novamente.', 'error')
    except Exception as e:
        # Log full error for debugging
        app_logger.error(f"ERRO COMPLETO ao atualizar detalhes (Impl. ID {implantacao_id}): {e}", exc_info=True)
        
        # Check if it's a database error
        error_str = str(e).lower()
        if 'database' in error_str or 'connection' in error_str:
            flash('❌ Erro de conexão com o banco de dados. Tente novamente em alguns segundos.', 'error')
        elif 'timeout' in error_str:
            flash('❌ Tempo de espera esgotado. Tente novamente.', 'error')
        else:
            flash('❌ Erro inesperado ao atualizar detalhes. Nossa equipe foi notificada.', 'error')

    try:
        wants_json = 'application/json' in (request.headers.get('Accept') or '')
        is_modal = (request.form.get('redirect_to') or '').lower() == 'modal'
        if wants_json or is_modal:
            from flask import jsonify
            return jsonify({'ok': True, 'implantacao_id': implantacao_id})
    except Exception:
        pass
    return redirect(dest_url)


@implantacao_actions_bp.route('/remover_plano_implantacao', methods=['POST'])
@login_required
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def remover_plano_implantacao():
    """Remove o plano de sucesso de uma implantação, limpando todas as fases/ações/tarefas associadas."""
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    user_perfil_acesso = g.perfil.get('perfil_acesso') if g.perfil else None

    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        from ..domain.implantacao_service import remover_plano_implantacao_service
        remover_plano_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso)

        flash('Plano de sucesso removido com sucesso!', 'success')
        try:
            clear_implantacao_cache(implantacao_id)
        except Exception as e:
            app_logger.warning(f"Erro ao limpar cache após remover plano: {e}")
            pass

    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        app_logger.error(f"Erro ao remover plano da implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao remover plano: {e}', 'error')

    return redirect(dest_url)


@implantacao_actions_bp.route('/transferir_implantacao', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_GESTAO)
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def transferir_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    novo_usuario_cs = request.form.get('novo_usuario_cs')
    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        from ..domain.implantacao_service import transferir_implantacao_service
        antigo_usuario_cs = transferir_implantacao_service(implantacao_id, usuario_cs_email, novo_usuario_cs)
        
        flash(f'Implantação transferida para {novo_usuario_cs} com sucesso!', 'success')
        if antigo_usuario_cs == usuario_cs_email:
            return redirect(url_for('main.dashboard'))
            
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        app_logger.error(f"Erro ao transferir implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao transferir implantação: {e}', 'error')
        
    return redirect(dest_url)


@implantacao_actions_bp.route('/excluir_implantacao', methods=['POST'])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def excluir_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    user_perfil_acesso = g.perfil.get('perfil_acesso') if g.perfil else None

    try:
        from ..domain.implantacao_service import excluir_implantacao_service
        excluir_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso)
        
        flash('Implantação e todos os dados associados foram excluídos com sucesso.', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        app_logger.error(f"Erro ao excluir implantação ID {implantacao_id}: {e}")
        flash('Erro ao excluir implantação.', 'error')
        
    return redirect(url_for('main.dashboard'))





@implantacao_actions_bp.route('/cancelar_implantacao', methods=['POST'])
@login_required
def cancelar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    data_cancelamento = request.form.get('data_cancelamento')
    motivo = request.form.get('motivo_cancelamento', '').strip()
    user_perfil_acesso = g.perfil.get('perfil_acesso') if g.perfil else None

    if not r2_client:
        flash('Erro: Serviço de armazenamento R2 não configurado. Não é possível fazer upload do comprovante obrigatório.', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    if not all([implantacao_id, data_cancelamento, motivo]):
        flash('Todos os campos (Data, Motivo Resumo) são obrigatórios para cancelar.', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    try:
        data_cancel_iso = validate_date(data_cancelamento)
    except ValidationError:
        flash('Data do cancelamento inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    file = request.files.get('comprovante_cancelamento')
    if not file or file.filename == '':
        flash('O upload do print do e-mail de cancelamento é obrigatório.', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    try:
        comprovante_url = None
        if file and utils.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            _, extensao = os.path.splitext(filename)
            nome_unico = f"cancel_proof_{implantacao_id}_{int(time.time())}{extensao}"
            object_name = f"comprovantes_cancelamento/{nome_unico}"

            bucket_name = current_app.config.get('CLOUDFLARE_BUCKET_NAME')
            public_url = current_app.config.get('CLOUDFLARE_PUBLIC_URL')
            r2_ok = bool(r2_client) and bool(bucket_name) and bool(public_url) and bool(current_app.config.get('R2_CONFIGURADO')) and bool(re.match(r'^[a-zA-Z0-9.\-_]{1,255}$', bucket_name))

            if r2_ok:
                r2_client.upload_fileobj(
                    file,
                    bucket_name,
                    object_name,
                    ExtraArgs={'ContentType': file.content_type}
                )
                comprovante_url = f"{public_url}/{object_name}"
            else:
                base_dir = os.path.join(os.path.dirname(current_app.root_path), 'uploads')
                target_dir = os.path.join(base_dir, 'comprovantes_cancelamento')
                try:
                    os.makedirs(target_dir, exist_ok=True)
                except Exception:
                    pass
                local_path = os.path.join(target_dir, nome_unico)
                file.stream.seek(0)
                with open(local_path, 'wb') as f_out:
                    f_out.write(file.stream.read())
                comprovante_url = url_for('main.serve_upload', filename=f'comprovantes_cancelamento/{nome_unico}')
        else:
            flash('Tipo de arquivo inválido para o comprovante.', 'error')
            return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

        from ..domain.implantacao_service import cancelar_implantacao_service
        cancelar_implantacao_service(implantacao_id, usuario_cs_email, user_perfil_acesso, data_cancel_iso, motivo, comprovante_url)

        flash('Implantação cancelada com sucesso.', 'success')
        return redirect(url_for('main.dashboard'))

    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))
    except Exception as e:
        app_logger.error(f"Erro ao cancelar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao cancelar implantação: {e}', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))
