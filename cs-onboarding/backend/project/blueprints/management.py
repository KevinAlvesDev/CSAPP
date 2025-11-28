
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, g, jsonify, current_app
)
from ..blueprints.auth import admin_required
from ..db import query_db, execute_db
from ..config.logging_config import management_logger, security_logger
from ..constants import ADMIN_EMAIL, PERFIL_ADMIN
from ..core.extensions import r2_client
from ..database import get_db_connection
from ..db import db_connection
import os
import io
import csv
import zipfile
import shutil
from datetime import datetime

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

        users_data = query_db(
            "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
        ) or []

        perfis_disponiveis = current_app.config.get(
            'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
        )

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
        users_data = query_db(
            "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
        ) or []

        perfis_disponiveis = current_app.config.get(
            'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
        )

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
            return {'type': 'sqlite', 'backup_file': target.replace(base_dir+os.sep, '')}

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
            return {'type': 'postgres', 'backup_file': zip_path.replace(base_dir+os.sep, '')}
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

    perfis_disponiveis = current_app.config.get('PERFIS_DE_ACESSO', [])
    if novo_perfil not in perfis_disponiveis:
        security_logger.warning(f"Tentativa de atribuir perfil inválido '{novo_perfil}' para {usuario_alvo} por {g.user_email}")
        return jsonify({'ok': False, 'error': 'Perfil de acesso inválido'}), 400

    if usuario_alvo == g.user_email:
        security_logger.warning(f"Admin {g.user_email} tentou alterar o próprio perfil via 'update_user_profile'")
        return jsonify({'ok': False, 'error': 'Não pode alterar o seu próprio perfil por esta interface.'}), 403

    try:

        user_exists = query_db("SELECT 1 FROM perfil_usuario WHERE usuario = %s", (usuario_alvo,), one=True)
        if not user_exists:
            return jsonify({'ok': False, 'error': 'Usuário não encontrado'}), 404

        execute_db(
            "UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s",
            (novo_perfil, usuario_alvo)
        )
        management_logger.info(f"Admin {g.user_email} atualizou o perfil de {usuario_alvo} para {novo_perfil}")
        return jsonify({'ok': True})

    except Exception as e:
        management_logger.error(f"Erro ao atualizar perfil de {usuario_alvo} por {g.user_email}: {e}")
        return jsonify({'ok': False, 'error': f'Erro de banco de dados: {e}'}), 500

@management_bp.route('/users/update_perfil', methods=['POST'])
def update_user_perfil():
    """Atualiza o perfil via formulário HTML (compatível com manage_users.html)."""

    usuario_alvo = request.form.get('usuario_email')
    novo_perfil = request.form.get('new_perfil')

    if usuario_alvo is None:
        flash('Usuário não especificado.', 'error')
        if request.headers.get('HX-Request') == 'true':
            users_data = query_db(
                "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
            ) or []
            perfis_disponiveis = current_app.config.get(
                'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
            )
            return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)
        return redirect(url_for('management.manage_users'))

    if novo_perfil == "":
        novo_perfil = None

    if usuario_alvo == g.user_email:
        security_logger.warning(f"Admin {g.user_email} tentou alterar o próprio perfil via 'update_user_perfil'")
        flash('Você não pode alterar o seu próprio perfil por esta interface.', 'warning')
        if request.headers.get('HX-Request') == 'true':
            users_data = query_db(
                "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
            ) or []
            perfis_disponiveis = current_app.config.get(
                'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
            )
            return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)
        return redirect(url_for('management.manage_users'))

    if usuario_alvo == ADMIN_EMAIL and (novo_perfil is None or novo_perfil != PERFIL_ADMIN):
        security_logger.warning("Tentativa de rebaixar administrador detectada por " + str(g.user_email))
        flash('Não é permitido alterar o perfil do administrador principal.', 'warning')
        if request.headers.get('HX-Request') == 'true':
            users_data = query_db(
                "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
            ) or []
            perfis_disponiveis = current_app.config.get(
                'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
            )
            return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)
        return redirect(url_for('management.manage_users'))

    perfis_disponiveis = current_app.config.get('PERFIS_DE_ACESSO', [])
    if novo_perfil is not None and novo_perfil not in perfis_disponiveis:
        security_logger.warning(
            f"Tentativa de atribuir perfil inválido '{novo_perfil}' para {usuario_alvo} por {g.user_email}"
        )
        flash('Perfil de acesso inválido.', 'error')
        if request.headers.get('HX-Request') == 'true':
            users_data = query_db(
                "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
            ) or []
            perfis_disponiveis = current_app.config.get(
                'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
            )
            return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)
        return redirect(url_for('management.manage_users'))

    try:

        user_exists = query_db("SELECT 1 FROM perfil_usuario WHERE usuario = %s", (usuario_alvo,), one=True)
        if not user_exists:
            flash('Usuário não encontrado.', 'error')
            if request.headers.get('HX-Request') == 'true':
                users_data = query_db(
                    "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
                ) or []
                perfis_disponiveis = current_app.config.get(
                    'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
                )
                return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)
            return redirect(url_for('management.manage_users'))

        from ..blueprints.auth import security_logger as auth_security_logger                               
        try:
            target_is_admin = query_db(
                "SELECT perfil_acesso FROM perfil_usuario WHERE usuario = %s",
                (usuario_alvo,), one=True
            )
            target_is_admin = target_is_admin and target_is_admin.get('perfil_acesso') == PERFIL_ADMIN
        except Exception:
            target_is_admin = False

        if target_is_admin and (g.perfil or {}).get('perfil_acesso') != PERFIL_ADMIN:
            auth_security_logger.warning("Tentativa de rebaixar administrador detectada por " + str(g.user_email))
            flash('Apenas Administradores podem alterar perfis de Administradores.', 'warning')
            if request.headers.get('HX-Request') == 'true':
                users_data = query_db(
                    "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
                ) or []
                perfis_disponiveis = current_app.config.get(
                    'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
                )
                return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)
            return redirect(url_for('management.manage_users'))

        execute_db(
            "UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s",
            (novo_perfil, usuario_alvo)
        )
        management_logger.info(f"Admin {g.user_email} atualizou o perfil de {usuario_alvo} para {novo_perfil}")
        flash('Perfil atualizado com sucesso.', 'success')
        if request.headers.get('HX-Request') == 'true':
            users_data = query_db(
                "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
            ) or []
            perfis_disponiveis = current_app.config.get(
                'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
            )
            return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)
        return redirect(url_for('management.manage_users'))

    except Exception as e:
        management_logger.error(f"Erro ao atualizar perfil de {usuario_alvo} por {g.user_email}: {e}")
        flash(f'Erro de banco de dados: {e}', 'error')
        if request.headers.get('HX-Request') == 'true':
            users_data = query_db(
                "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
            ) or []
            perfis_disponiveis = current_app.config.get(
                'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
            )
            return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)
        return redirect(url_for('management.manage_users'))

@management_bp.route('/users/delete', methods=['POST'])
def delete_user():
    """Exclui um usuário via formulário, com redirecionamento e logs (compatível com testes)."""
    usuario_alvo = request.form.get('usuario_email')
    if not usuario_alvo:
        flash('Usuário não especificado.', 'error')

        if request.headers.get('HX-Request') == 'true':
            users_data = query_db(
                "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
            ) or []
            perfis_disponiveis = current_app.config.get(
                'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
            )
            return render_template(
                '_manage_users_content.html',
                users=users_data,
                perfis_list=perfis_disponiveis
            )
        return redirect(url_for('management.manage_users'))

    if usuario_alvo == g.user_email:
        security_logger.warning(f"Tentativa de exclusão do próprio usuário por {g.user_email}")
        flash('Você não pode excluir a si mesmo.', 'warning')
        if request.headers.get('HX-Request') == 'true':
            users_data = query_db(
                "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
            ) or []
            perfis_disponiveis = current_app.config.get(
                'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
            )
            return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)
        return redirect(url_for('management.manage_users'))

    if usuario_alvo == ADMIN_EMAIL:
        security_logger.warning("Tentativa de exclusão do administrador principal detectada por " + str(g.user_email))
        flash('Não é permitido excluir o administrador principal.', 'warning')
        if request.headers.get('HX-Request') == 'true':
            users_data = query_db(
                "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
            ) or []
            perfis_disponiveis = current_app.config.get(
                'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
            )
            return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)
        return redirect(url_for('management.manage_users'))

    try:

        perfil = query_db("SELECT foto_url FROM perfil_usuario WHERE usuario = %s", (usuario_alvo,), one=True)
        public_base = current_app.config.get('CLOUDFLARE_PUBLIC_URL')
        bucket = current_app.config.get('CLOUDFLARE_BUCKET_NAME')
        if perfil and perfil.get('foto_url') and public_base and bucket and r2_client:
            foto_url = perfil['foto_url']
            if foto_url.startswith(public_base):
                key = foto_url[len(public_base):].lstrip('/')
                try:
                    r2_client.delete_object(Bucket=bucket, Key=key)
                except Exception:

                    pass

        implantacoes_ids = query_db("SELECT id FROM implantacoes WHERE usuario_cs = %s", (usuario_alvo,)) or []
        for impl in implantacoes_ids:
            execute_db("DELETE FROM implantacoes WHERE id = %s", (impl['id'],))

        execute_db("DELETE FROM perfil_usuario WHERE usuario = %s", (usuario_alvo,))
        execute_db("DELETE FROM usuarios WHERE usuario = %s", (usuario_alvo,))

        management_logger.info(f"Usuário {usuario_alvo} excluído por {g.user_email} (implantações vinculadas removidas: {len(implantacoes_ids)})")
        flash(f"Usuário e {len(implantacoes_ids)} implantações vinculadas excluídos.", 'success')
        if request.headers.get('HX-Request') == 'true':
            users_data = query_db(
                "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
            ) or []
            perfis_disponiveis = current_app.config.get(
                'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
            )
            return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)
        return redirect(url_for('management.manage_users'))

    except Exception as e:
        management_logger.error(f"Erro ao excluir usuário {usuario_alvo} por {g.user_email}: {e}")
        flash(f'Erro de banco de dados: {e}', 'error')
        if request.headers.get('HX-Request') == 'true':
            users_data = query_db(
                "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
            ) or []
            perfis_disponiveis = current_app.config.get(
                'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
            )
            return render_template('_manage_users_content.html', users=users_data, perfis_list=perfis_disponiveis)
        return redirect(url_for('management.manage_users'))

@management_bp.route('/cleanup/orphan-implantacoes', methods=['POST'])
def cleanup_orphan_implantacoes():
    """Remove implantações órfãs (sem usuário proprietário). Admin-only."""
    try:
        stats = query_db("SELECT COUNT(*) as c FROM implantacoes WHERE usuario_cs IS NULL", (), one=True) or {'c': 0}
        execute_db("DELETE FROM implantacoes WHERE usuario_cs IS NULL")
        count = stats.get('c', 0)
        management_logger.info(f"Admin {g.user_email} removeu {count} implantações órfãs")
        flash(f"{count} implantações órfãs removidas.", 'success')
        return redirect(url_for('management.manage_users'))
    except Exception as e:
        management_logger.error(f"Erro ao remover implantações órfãs por {g.user_email}: {e}")
        flash(f"Erro ao remover implantações órfãs: {e}", 'error')
        return redirect(url_for('management.manage_users'))
