import os
import time
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, g, current_app
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from botocore.exceptions import ClientError, NoCredentialsError

from ..blueprints.auth import login_required
from ..db import execute_db, query_db
from ..extensions import r2_client
from ..utils import allowed_file
from ..constants import CARGOS_LIST, PERFIL_IMPLANTADOR # <-- ALTERADO

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    usuario_cs_email = g.user_email
    current_perfil = g.perfil # Perfil carregado pelo @login_required

    if request.method == 'POST':
        # Verifica se o R2 está configurado antes de tentar o upload
        if not r2_client or not current_app.config['CLOUDFLARE_PUBLIC_URL']:
            flash("Erro: Serviço de armazenamento (R2) não configurado. Não é possível alterar a foto.", "error")
            return redirect(url_for('profile.perfil'))
            
        try:
            # Pega os dados do formulário
            form_nome = request.form.get('nome', '').strip()
            form_cargo = request.form.get('cargo', '').strip()
            
            # --- Lógica de Restrição ATUALIZADA ---
            is_implantador = current_perfil.get('perfil_acesso') == PERFIL_IMPLANTADOR # <-- ALTERADO
            
            # DEFINE nome_to_save: Se não for implantador, usa o valor do form.
            if not is_implantador:
                 nome_to_save = form_nome if form_nome else None
            else:
                 nome_to_save = current_perfil.get('nome')
            
            # Cargo só é salvo se não for implantador.
            cargo_to_save = current_perfil.get('cargo') # Mantém o atual por padrão
            if not is_implantador:
                if not form_cargo: 
                    cargo_to_save = None
                elif form_cargo in CARGOS_LIST:
                    cargo_to_save = form_cargo
                else:
                    cargo_to_save = current_perfil.get('cargo') 
            # --------------------------
            
            foto_url_atual = current_perfil.get('foto_url')

            # --- Lógica de Upload para R2 (original) ---
            if 'foto_perfil' in request.files:
                file = request.files['foto_perfil']
                if file and file.filename and allowed_file(file.filename):
                    try:
                        # Cria um nome de arquivo único
                        nome_base, extensao = os.path.splitext(secure_filename(file.filename))
                        email_hash = generate_password_hash(usuario_cs_email).split('$')[-1][:8]
                        object_name = f"profile_pics/perfil_{email_hash}_{int(time.time())}{extensao}"

                        # Faz o upload para o R2
                        file.seek(0)
                        r2_client.upload_fileobj(
                            file,
                            current_app.config['CLOUDFLARE_BUCKET_NAME'],
                            object_name,
                            ExtraArgs={'ContentType': file.content_type}
                        )
                        
                        # Constrói a URL pública
                        nova_foto_url = f"{current_app.config['CLOUDFLARE_PUBLIC_URL']}/{object_name}"
                        print(f"Upload R2 concluído: {nova_foto_url}")

                        # --- Excluir foto ANTIGA do R2 ---
                        if foto_url_atual and foto_url_atual != nova_foto_url:
                            try:
                                old_object_key = foto_url_atual.replace(f"{current_app.config['CLOUDFLARE_PUBLIC_URL']}/", "")
                                if old_object_key and old_object_key != foto_url_atual:
                                    print(f"Tentando excluir objeto R2 antigo: {old_object_key}")
                                    r2_client.delete_object(
                                        Bucket=current_app.config['CLOUDFLARE_BUCKET_NAME'], 
                                        Key=old_object_key
                                    )
                                    print(f"Objeto R2 antigo excluído.")
                            except Exception as e_delete:
                                print(f"Aviso: Falha ao excluir foto antiga do R2. {e_delete}")
                        
                        foto_url_atual = nova_foto_url

                    except (ClientError, NoCredentialsError) as e_upload:
                        print(f"ERRO upload R2: {e_upload}")
                        flash("Erro ao fazer upload da nova foto (credenciais/conexão R2?).", "error")
                    except Exception as e_upload:
                        print(f"ERRO upload R2: {e_upload}")
                        flash("Erro ao fazer upload da nova foto.", "error")

            # Atualiza o banco de dados com os valores corretos (respeitando a restrição)
            execute_db(
                """
                UPDATE perfil_usuario 
                SET nome = %s, cargo = %s, foto_url = %s 
                WHERE usuario = %s
                """,
                (nome_to_save, cargo_to_save, foto_url_atual, usuario_cs_email)
            )
            
            if is_implantador and (request.form.get('nome', '').strip() != current_perfil.get('nome') or request.form.get('cargo', '').strip() != current_perfil.get('cargo')):
                 # Verifica se a intenção era mudar (o form submetido é diferente do valor inicial)
                 flash(f'Perfil atualizado. Nome e Cargo não podem ser alterados pelo perfil {PERFIL_IMPLANTADOR}.', 'warning') # <-- ALTERADO
            else:
                 flash('Perfil atualizado com sucesso!', 'success')
            
            # Recarrega o perfil para refletir a mudança no request atual
            g.perfil = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (usuario_cs_email,), one=True)
            
            return redirect(url_for('profile.perfil'))
            
        except Exception as e:
            print(f"ERRO GERAL ao atualizar perfil para {usuario_cs_email}: {e}")
            flash(f'Erro ao atualizar perfil: {e}', 'error')
            return redirect(url_for('profile.perfil'))

    # Método GET
    return render_template('perfil.html', user_info=g.user, perfil=current_perfil, cargos_list=CARGOS_LIST)