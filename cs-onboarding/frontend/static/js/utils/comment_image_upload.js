/**
 * Sistema de Upload de Imagens para Comentários - VERSÃO SIMPLIFICADA
 * Suporta: Upload de arquivo + Cola de imagem (Ctrl+V)
 */

(function () {
    'use strict';

    console.log('[ImageUpload] 🚀 Módulo carregando...');

    // Estado global para armazenar imagens pendentes por tarefa
    const pendingImages = new Map();

    /**
     * Inicializa o sistema de upload de imagens
     */
    function initImageUpload() {
        console.log('[ImageUpload] ✅ Inicializando sistema de upload de imagens...');

        // Adicionar listener GLOBAL para QUALQUER textarea
        document.addEventListener('paste', function (e) {
            const target = e.target;

            // Verificar se é um textarea de comentário
            if (target.tagName === 'TEXTAREA' && target.id && target.id.includes('comment-input-')) {
                console.log('[ImageUpload] 🎯 PASTE detectado em textarea de comentário!', target.id);
                const tarefaId = target.id.replace('comment-input-', '');
                handlePaste(e, tarefaId);
            }
        }, true); // useCapture = true para capturar antes

        // Detectar inputs de arquivo
        const imageInputs = document.querySelectorAll('.comentario-imagem-input');
        console.log(`[ImageUpload] 📎 Encontrados ${imageInputs.length} inputs de arquivo`);

        imageInputs.forEach(input => {
            const tarefaId = input.getAttribute('data-tarefa-id');
            if (!tarefaId) return;

            input.addEventListener('change', function (e) {
                handleFileSelect(e, tarefaId);
            });
        });

        console.log('[ImageUpload] ✨ Sistema inicializado com sucesso!');
    }

    /**
     * Manipula seleção de arquivo
     */
    function handleFileSelect(event, tarefaId) {
        const file = event.target.files[0];
        if (!file) return;

        console.log(`[ImageUpload] 📁 Arquivo selecionado para tarefa ${tarefaId}:`, file.name);

        // Validar tipo
        if (!file.type.startsWith('image/')) {
            showError(tarefaId, 'Por favor, selecione apenas arquivos de imagem.');
            event.target.value = '';
            return;
        }

        // Validar tamanho (5MB)
        if (file.size > 5 * 1024 * 1024) {
            showError(tarefaId, 'Imagem muito grande. Máximo 5MB.');
            event.target.value = '';
            return;
        }

        uploadImage(file, tarefaId);
    }

    /**
     * Manipula cola de imagem (Ctrl+V)
     */
    function handlePaste(event, tarefaId) {
        console.log('[ImageUpload] 📋 Processando evento de cola...');

        const items = (event.clipboardData || event.originalEvent.clipboardData).items;
        console.log('[ImageUpload] 📋 Items na área de transferência:', items.length);

        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            console.log(`[ImageUpload] Item ${i}:`, item.type);

            if (item.type.indexOf('image') !== -1) {
                event.preventDefault();

                const file = item.getAsFile();
                console.log('[ImageUpload] 🖼️ Imagem encontrada!', file);

                uploadImage(file, tarefaId);
                return;
            }
        }

        console.log('[ImageUpload] ⚠️ Nenhuma imagem encontrada na área de transferência');
    }

    /**
     * Faz upload da imagem
     */
    function uploadImage(file, tarefaId) {
        console.log(`[ImageUpload] ⬆️ Iniciando upload para tarefa ${tarefaId}...`);

        showLoading(tarefaId, true);

        const formData = new FormData();
        formData.append('image', file);

        fetch('/api/upload/comment-image', {
            method: 'POST',
            body: formData
        })
            .then(response => {
                console.log('[ImageUpload] 📡 Resposta recebida:', response.status);
                return response.json();
            })
            .then(data => {
                showLoading(tarefaId, false);

                console.log('[ImageUpload] 📦 Dados:', data);

                if (data.ok && data.image_url) {
                    console.log(`[ImageUpload] ✅ Upload concluído:`, data.image_url);

                    pendingImages.set(tarefaId, data.image_url);
                    showImagePreview(tarefaId, data.image_url, data.filename);
                    showSuccess(tarefaId, '✅ Imagem anexada! Clique em "Salvar" para enviar o comentário.');
                } else {
                    console.error('[ImageUpload] ❌ Erro no upload:', data.error);
                    showError(tarefaId, data.error || 'Erro ao fazer upload da imagem');
                }
            })
            .catch(error => {
                console.error('[ImageUpload] ❌ Erro no upload:', error);
                showLoading(tarefaId, false);
                showError(tarefaId, 'Erro ao fazer upload. Tente novamente.');
            });
    }

    /**
     * Mostra preview da imagem
     */
    function showImagePreview(tarefaId, imageUrl, filename) {
        const comentarioSection = document.getElementById(`comentarios-tarefa-${tarefaId}`);
        if (!comentarioSection) {
            console.warn('[ImageUpload] ⚠️ Seção de comentários não encontrada:', `comentarios-tarefa-${tarefaId}`);
            return;
        }

        const oldPreview = comentarioSection.querySelector('.image-preview-container');
        if (oldPreview) oldPreview.remove();

        const previewContainer = document.createElement('div');
        previewContainer.className = 'image-preview-container mb-2 p-2 border rounded bg-light';
        previewContainer.innerHTML = `
            <div class="d-flex align-items-center justify-content-between">
                <div class="d-flex align-items-center gap-2">
                    <img src="${imageUrl}" alt="${filename}" class="image-preview-thumb" 
                         style="max-width: 100px; max-height: 100px; object-fit: cover; border-radius: 4px; cursor: pointer;"
                         onclick="window.open('${imageUrl}', '_blank')">
                    <div>
                        <div class="small fw-bold text-success">
                            <i class="bi bi-check-circle-fill me-1"></i>Imagem anexada
                        </div>
                        <div class="small text-muted">${filename || 'imagem.png'}</div>
                    </div>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeImagePreview('${tarefaId}')">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>
        `;

        const comentarioForm = comentarioSection.querySelector('.comentario-form');
        if (comentarioForm) {
            comentarioForm.insertAdjacentElement('afterbegin', previewContainer);
        }
    }

    /**
     * Remove preview da imagem
     */
    window.removeImagePreview = function (tarefaId) {
        const comentarioSection = document.getElementById(`comentarios-tarefa-${tarefaId}`);
        if (!comentarioSection) return;

        const preview = comentarioSection.querySelector('.image-preview-container');
        if (preview) preview.remove();

        pendingImages.delete(tarefaId);

        const fileInput = document.querySelector(`.comentario-imagem-input[data-tarefa-id="${tarefaId}"]`);
        if (fileInput) fileInput.value = '';

        console.log(`[ImageUpload] 🗑️ Preview removido para tarefa ${tarefaId}`);
    };

    /**
     * Mostra/oculta loading
     */
    function showLoading(tarefaId, show) {
        const btnSalvar = document.querySelector(`.btn-salvar-comentario[data-tarefa-id="${tarefaId}"]`);
        if (!btnSalvar) return;

        if (show) {
            btnSalvar.disabled = true;
            btnSalvar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando...';
        } else {
            btnSalvar.disabled = false;
            btnSalvar.innerHTML = '<i class="bi bi-send me-1"></i>Salvar';
        }
    }

    /**
     * Mostra mensagem de erro
     */
    function showError(tarefaId, message) {
        console.error(`[ImageUpload] ❌ Erro na tarefa ${tarefaId}:`, message);

        const comentarioSection = document.getElementById(`comentarios-tarefa-${tarefaId}`);
        if (!comentarioSection) return;

        const oldAlert = comentarioSection.querySelector('.upload-alert');
        if (oldAlert) oldAlert.remove();

        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-sm py-2 mb-2 upload-alert';
        alert.innerHTML = `<i class="bi bi-exclamation-triangle me-1"></i>${message}`;

        const comentarioForm = comentarioSection.querySelector('.comentario-form');
        if (comentarioForm) {
            comentarioForm.insertAdjacentElement('afterbegin', alert);
            setTimeout(() => alert.remove(), 5000);
        }
    }

    /**
     * Mostra mensagem de sucesso
     */
    function showSuccess(tarefaId, message) {
        console.log(`[ImageUpload] ✅ Sucesso na tarefa ${tarefaId}:`, message);

        const comentarioSection = document.getElementById(`comentarios-tarefa-${tarefaId}`);
        if (!comentarioSection) return;

        const oldAlert = comentarioSection.querySelector('.upload-alert');
        if (oldAlert) oldAlert.remove();

        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-sm py-2 mb-2 upload-alert';
        alert.innerHTML = `<i class="bi bi-check-circle me-1"></i>${message}`;

        const comentarioForm = comentarioSection.querySelector('.comentario-form');
        if (comentarioForm) {
            comentarioForm.insertAdjacentElement('afterbegin', alert);
            setTimeout(() => alert.remove(), 5000);
        }
    }

    /**
     * Retorna URL da imagem pendente para uma tarefa
     */
    window.getPendingImageUrl = function (tarefaId) {
        return pendingImages.get(tarefaId) || null;
    };

    /**
     * Limpa imagem pendente após envio bem-sucedido
     */
    window.clearPendingImage = function (tarefaId) {
        pendingImages.delete(tarefaId);
        window.removeImagePreview(tarefaId);
    };

    // Inicializar quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            console.log('[ImageUpload] 📄 DOM carregado, inicializando...');
            initImageUpload();
        });
    } else {
        console.log('[ImageUpload] 📄 DOM já está pronto, inicializando...');
        initImageUpload();
    }

    console.log('[ImageUpload] 🎉 Módulo carregado com sucesso!');
})();
