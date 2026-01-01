"""
Endpoint de Upload de Imagens para Comentários
"""
from flask import Blueprint, g, jsonify, request, current_app
from flask_limiter.util import get_remote_address
import os
import uuid
import base64
from io import BytesIO
from werkzeug.utils import secure_filename

from ..blueprints.auth import login_required
from ..config.logging_config import api_logger
from ..core.extensions import limiter, r2_client
from ..security.api_security import validate_api_origin

upload_bp = Blueprint('upload', __name__, url_prefix='/api/upload')


@upload_bp.route('/comment-image', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def upload_comment_image():
    """
    Faz upload de uma imagem para anexar em um comentário.
    Aceita arquivo multipart/form-data ou base64.
    
    Returns:
        JSON com URL da imagem ou erro
    """
    try:
        # Verificar se R2 está configurado
        if not r2_client:
            return jsonify({'ok': False, 'error': 'Sistema de upload não configurado'}), 503
        
        bucket_name = current_app.config.get('R2_BUCKET_NAME')
        public_url_base = current_app.config.get('R2_PUBLIC_URL')
        
        if not bucket_name or not public_url_base:
            return jsonify({'ok': False, 'error': 'Configuração de storage incompleta'}), 503
        
        image_data = None
        filename = None
        
        # Verificar se é upload de arquivo
        if 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                return jsonify({'ok': False, 'error': 'Nenhum arquivo selecionado'}), 400
            
            # Validar extensão
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if ext not in allowed_extensions:
                return jsonify({'ok': False, 'error': 'Formato de imagem não suportado. Use PNG, JPG, GIF ou WebP'}), 400
            
            # Validar tamanho (máx 5MB)
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > 5 * 1024 * 1024:  # 5MB
                return jsonify({'ok': False, 'error': 'Imagem muito grande. Máximo 5MB'}), 400
            
            image_data = file.read()
            filename = secure_filename(file.filename)
        
        # Verificar se é base64 (para cola de imagem)
        elif request.is_json:
            data = request.get_json() or {}
            base64_data = data.get('image_base64')
            
            if not base64_data:
                return jsonify({'ok': False, 'error': 'Dados da imagem não fornecidos'}), 400
            
            # Remover prefixo data:image/...;base64, se existir
            if ',' in base64_data:
                base64_data = base64_data.split(',', 1)[1]
            
            try:
                image_data = base64.b64decode(base64_data)
            except Exception:
                return jsonify({'ok': False, 'error': 'Dados base64 inválidos'}), 400
            
            # Validar tamanho
            if len(image_data) > 5 * 1024 * 1024:
                return jsonify({'ok': False, 'error': 'Imagem muito grande. Máximo 5MB'}), 400
            
            filename = f"pasted-image-{uuid.uuid4().hex[:8]}.png"
        
        else:
            return jsonify({'ok': False, 'error': 'Formato de requisição inválido'}), 400
        
        # Gerar nome único para o arquivo
        unique_filename = f"comentarios/{uuid.uuid4().hex}-{filename}"
        
        # Upload para R2
        try:
            r2_client.upload_fileobj(
                BytesIO(image_data),
                bucket_name,
                unique_filename,
                ExtraArgs={'ContentType': 'image/png' if filename.endswith('.png') else 'image/jpeg'}
            )
        except Exception as e:
            api_logger.error(f"Erro ao fazer upload para R2: {e}", exc_info=True)
            return jsonify({'ok': False, 'error': 'Erro ao fazer upload da imagem'}), 500
        
        # Gerar URL pública
        image_url = f"{public_url_base}/{unique_filename}"
        
        return jsonify({
            'ok': True,
            'image_url': image_url,
            'filename': filename
        })
    
    except Exception as e:
        api_logger.error(f"Erro ao processar upload de imagem: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao processar imagem'}), 500
