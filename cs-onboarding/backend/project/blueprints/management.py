import csv
import io
import os
import shutil
import zipfile
from datetime import datetime

from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, url_for

from ..blueprints.auth import admin_required
from ..config.logging_config import management_logger, security_logger
from ..constants import ADMIN_EMAIL, PERFIL_ADMIN
from ..core.extensions import r2_client
from ..db import db_connection, execute_db
from ..domain.management_service import (
    listar_usuarios_service,
    atualizar_perfil_usuario_service,
    excluir_usuario_service,
    limpar_implantacoes_orfas_service,
    obter_perfis_disponiveis,
    verificar_usuario_existe
)

management_bp = Blueprint('management', __name__, url_prefix='/management')


@management_bp.before_request
@admin_required
def before_request():
    """Protege todas as rotas de gerenciamento."""
    pass


@management_bp.route('/users')
def manage_users():
    """Renderiza a página principal de gerenciamento de usuários."""
    try:
        users_data = listar_usuarios_service()
        perfis_disponiveis = obter_perfis_disponiveis()

        return render_template(
            'manage_users.html',
            users=users_data,
            perfis_list=perfis_disponiveis
        )
    except Exception as e:
        management_logger.error(f"Erro ao carregar a lista de usuários: {e}")
        return ("Erro ao carregar a lista de usuários", 500)


@management_bp.route('/users/modal')
def manage_users_modal():
    """Renderiza somente o conteúdo do modal de gerenciamento de usuários (sem coluna 'Implantações')."""
    try:
        users_data = listar_usuarios_service()
        perfis_disponiveis = obter_perfis_disponiveis()

        return render_template(
            '_manage_users_content.html',
            users=users_data,
            perfis_list=perfis_disponiveis
        )
    except Exception as e:
        management_logger.error(f"Erro ao carregar conteúdo do modal de usuários: {e}")
        return ("Erro ao carregar usuários", 500)


@management_bp.route('/backup/db', methods=['POST'])
def backup_database():
    """Gera um backup do banco de dados atual.
    - SQLite: copia o arquivo .db para backend/backups com timestamp
    - PostgreSQL: exporta tabelas principais para CSV dentro de um ZIP
    Retorna JSON com caminho relativo do backup.
    """
    try:
        result = perform_backup()
        return jsonify({'ok': True, **result})
    except Exception as e:
        management_logger.error(f"Erro ao gerar backup do banco: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


def perform_backup():
    """Executa o backup do banco e retorna dict com tipo e caminho do arquivo."""

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    backup_dir = os.path.join(base_dir, 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    ts = datetime.now().strftime('%Y%m%d-%H%M%S')

    with db_connection() as (conn, db_type):
        if db_type == 'sqlite':

            sqlite_base = os.path.abspath(os.path.dirname(base_dir))
            is_testing = current_app.config.get('TESTING', False)
            db_filename = 'dashboard_simples_test.db' if is_testing else 'dashboard_simples.db'
            db_path = os.path.join(sqlite_base, db_filename)
            if not os.path.exists(db_path):
                raise FileNotFoundError(f"Arquivo SQLite não encontrado: {db_path}")

            target = os.path.join(backup_dir, f'db-sqlite-{ts}.sqlite')
            shutil.copy2(db_path, target)
            management_logger.info(f"SQLite backup criado: {target}")
            return {'type': 'sqlite', 'backup_file': target.replace(base_dir + os.sep, '')}

        elif db_type == 'postgres':
            tables = [
                'usuarios', 'perfil_usuario', 'implantacoes', 'tarefas', 'comentarios',
                'timeline_log', 'gamificacao_regras', 'gamificacao_metricas_mensais'
            ]
            zip_path = os.path.join(backup_dir, f'db-postgres-{ts}.zip')
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                cur = conn.cursor()
                for tbl in tables:
                    try:
                        cur.execute(f'SELECT * FROM {tbl}')
                        rows = cur.fetchall() or []
                        if hasattr(cur, 'description') and cur.description:
                            headers = [col.name if hasattr(col, 'name') else col[0] for col in cur.description]
                        else:
                            headers = []
                        buf = io.StringIO()
                        writer = csv.writer(buf)
                        if headers:
                            writer.writerow(headers)
                        for r in rows:
                            writer.writerow(list(r))
                        zf.writestr(f'{tbl}.csv', buf.getvalue())
                    except Exception as te:
                        management_logger.error(f"Falha ao exportar tabela {tbl}: {te}")
                cur.close()
            management_logger.info(f"PostgreSQL backup criado: {zip_path}")
            return {'type': 'postgres', 'backup_file': zip_path.replace(base_dir + os.sep, '')}
        else:
            raise RuntimeError(f"Tipo de banco desconhecido: {db_type}")


@management_bp.route('/users/update_profile', methods=['POST'])
def update_user_profile():
    """Atualiza o perfil de acesso de um usuário."""
    data = request.get_json()
    if not data or 'usuario' not in data or 'perfil' not in data:
        return jsonify({'ok': False, 'error': 'Dados incompletos'}), 400

    usuario_alvo = data['usuario']
    novo_perfil = data['perfil']

    try:
        atualizar_perfil_usuario_service(usuario_alvo, novo_perfil, g.user_email)
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400 if 'não encontrado' in str(e) else 403
    except Exception as e:
        management_logger.error(f"Erro ao atualizar perfil de {usuario_alvo} por {g.user_email}: {e}")
        return jsonify({'ok': False, 'error': f'Erro de banco de dados: {e}'}), 500


@management_bp.route('/users/update_perfil', methods=['POST'])
def update_user_perfil():
    """Atualiza o perfil via formulário HTML (compatível com manage_users.html)."""

    usuario_alvo = request.form.get('usuario_email')
    novo_perfil = request.form.get('new_perfil')

    def render_users_list():
        """Helper para renderizar lista de usuários."""
        users_data = listar_usuarios_service()
        perfis_disponiveis = obter_perfis_disponiveis()
        return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)

    if usuario_alvo is None:
        flash('Usuário não especificado.', 'error')
        if request.headers.get('HX-Request') == 'true':
            return render_users_list()
        return redirect(url_for('management.manage_users'))

    if novo_perfil == "":
        novo_perfil = None

    try:
        atualizar_perfil_usuario_service(usuario_alvo, novo_perfil, g.user_email)
        flash('Perfil atualizado com sucesso.', 'success')
        if request.headers.get('HX-Request') == 'true':
            return render_users_list()
        return redirect(url_for('management.manage_users'))

    except ValueError as e:
        flash(str(e), 'warning' if 'próprio perfil' in str(e) or 'administrador' in str(e) else 'error')
        if request.headers.get('HX-Request') == 'true':
            return render_users_list()
        return redirect(url_for('management.manage_users'))
    except Exception as e:
        management_logger.error(f"Erro ao atualizar perfil de {usuario_alvo} por {g.user_email}: {e}")
        flash(f'Erro de banco de dados: {e}', 'error')
        if request.headers.get('HX-Request') == 'true':
            return render_users_list()
        return redirect(url_for('management.manage_users'))


@management_bp.route('/users/delete', methods=['POST'])
def delete_user():
    """Exclui um usuário via formulário, com redirecionamento e logs (compatível com testes)."""
    usuario_alvo = request.form.get('usuario_email')

    def render_users_list():
        """Helper para renderizar lista de usuários."""
        users_data = listar_usuarios_service()
        perfis_disponiveis = obter_perfis_disponiveis()
        return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)

    if not usuario_alvo:
        flash('Usuário não especificado.', 'error')
        if request.headers.get('HX-Request') == 'true':
            return render_users_list()
        return redirect(url_for('management.manage_users'))

    try:
        result = excluir_usuario_service(usuario_alvo, g.user_email)

        # Deletar foto do R2 se houver
        foto_url = result.get('foto_url')
        if foto_url:
            public_base = current_app.config.get('CLOUDFLARE_PUBLIC_URL')
            bucket = current_app.config.get('CLOUDFLARE_BUCKET_NAME')
            if public_base and bucket and r2_client and foto_url.startswith(public_base):
                key = foto_url[len(public_base):].lstrip('/')
                try:
                    r2_client.delete_object(Bucket=bucket, Key=key)
                except Exception:
                    pass

        flash(f"Usuário e {result['implantacoes_excluidas']} implantações vinculadas excluídos.", 'success')
        if request.headers.get('HX-Request') == 'true':
            return render_users_list()
        return redirect(url_for('management.manage_users'))

    except ValueError as e:
        flash(str(e), 'warning')
        if request.headers.get('HX-Request') == 'true':
            return render_users_list()
        return redirect(url_for('management.manage_users'))
    except Exception as e:
        management_logger.error(f"Erro ao excluir usuário {usuario_alvo} por {g.user_email}: {e}")
        flash(f'Erro de banco de dados: {e}', 'error')
        if request.headers.get('HX-Request') == 'true':
            return render_users_list()
        return redirect(url_for('management.manage_users'))


@management_bp.route('/cleanup/orphan-implantacoes', methods=['POST'])
def cleanup_orphan_implantacoes():
    """Remove implantações órfãs (sem usuário proprietário). Admin-only."""
    try:
        count = limpar_implantacoes_orfas_service(g.user_email)
        flash(f"{count} implantações órfãs removidas.", 'success')
        return redirect(url_for('management.manage_users'))
    except Exception as e:
        management_logger.error(f"Erro ao remover implantações órfãs por {g.user_email}: {e}")
        flash(f"Erro ao remover implantações órfãs: {e}", 'error')
        return redirect(url_for('management.manage_users'))
