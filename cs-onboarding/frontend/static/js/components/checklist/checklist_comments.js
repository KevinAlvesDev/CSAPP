/**
 * CS Onboarding - Checklist Comments Component
 * Handles comment rendering, submission, deletion and image uploads.
 * 
 * @module components/checklist/ChecklistComments
 */

class ChecklistComments {
    constructor(renderer, container) {
        this.renderer = renderer;
        this.container = container;
        this.init();
    }

    init() {
        this.setupImageUploadHandlers();
    }

    /**
     * Toggles the visibility of the comments section for an item.
     * Loads comments if opening.
     */
    toggleComments(itemId) {
        const commentsSection = this.container.querySelector(`#comments-${itemId}`);
        if (!commentsSection) return;

        const isOpening = !commentsSection.classList.contains('show');

        if (window.bootstrap && window.bootstrap.Collapse) {
            // Use Bootstrap Collapse if available
            const bsCollapse = window.bootstrap.Collapse.getOrCreateInstance(commentsSection, { toggle: false });
            if (isOpening) bsCollapse.show(); else bsCollapse.hide();
        } else {
            // Fallback
            commentsSection.classList.toggle('show');
        }

        if (isOpening) {
            this.loadComments(itemId);
        }
    }

    /**
     * Loads and displays comments for an item.
     */
    async loadComments(itemId) {
        const historyContainer = this.container.querySelector(`#comments-history-${itemId}`);
        if (!historyContainer) return;

        // Show loading state
        historyContainer.innerHTML = `
            <div class="text-center py-2">
                <div class="spinner-border spinner-border-sm text-secondary" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
            </div>
        `;

        if (!this.renderer.service) {
            historyContainer.innerHTML = `<div class="text-muted small">Serviço indisponível.</div>`;
            return;
        }

        const result = await this.renderer.service.loadComments(itemId);

        if (result.success) {
            this.renderCommentsHistory(itemId, result.comentarios, result.emailResponsavel);
        } else {
            historyContainer.innerHTML = `<div class="text-danger small">${result.error || 'Erro ao carregar comentários'}</div>`;
        }
    }

    /**
     * Renders the list of comments into the history container.
     */
    renderCommentsHistory(itemId, comentarios, emailResponsavel) {
        const historyContainer = this.container.querySelector(`#comments-history-${itemId}`);
        if (!historyContainer) return;

        if (!comentarios || comentarios.length === 0) {
            historyContainer.innerHTML = '<div class="text-muted small fst-italic py-2">Nenhum comentário ainda.</div>';
            return;
        }

        const html = comentarios.map(c => this.renderSingleComment(c, itemId, emailResponsavel)).join('');

        historyContainer.innerHTML = `
            <label class="form-label small text-muted mb-2">Histórico de Comentários</label>
            <div class="comments-list" style="max-height: 250px; overflow-y: auto;">
                ${html}
            </div>
        `;
    }

    getCurrentUser() {
        const main = document.getElementById('main-content');
        return {
            email: main ? main.dataset.emailUsuarioLogado : '',
            isManager: main ? main.dataset.isManager === 'true' : false
        };
    }

    checkTimeLimit(dateStr) {
        if (!dateStr) return false;
        // Tentar parsear data. Se for formato DD/MM/YYYY HH:mm, converter (fallback)
        let date = new Date(dateStr);
        if (isNaN(date.getTime())) {
            // Fallback simples para DD/MM/YYYY HH:MM (pt-BR)
            const parts = dateStr.split(/[\/\s:]/); // separa por / espaço ou :
            if (parts.length >= 5) {
                // new Date(year, monthIndex, day, hours, minutes)
                date = new Date(parts[2], parts[1] - 1, parts[0], parts[3], parts[4]);
            }
        }

        if (isNaN(date.getTime())) return false; // Fail safe

        const now = new Date();
        const diffMs = now - date;
        const diffHours = diffMs / (1000 * 60 * 60);
        return diffHours < 3;
    }

    renderSingleComment(c, itemId, emailResponsavel) {
        const escape = window.HtmlUtils ? window.HtmlUtils.escapeHtml : (t) => t;
        const isInterno = c.visibilidade === 'interno';
        const isExterno = c.visibilidade === 'externo';
        const badgeClass = isInterno ? 'bg-secondary' : 'bg-info text-dark';
        const temEmailResponsavel = emailResponsavel && emailResponsavel.trim() !== '';

        const user = this.getCurrentUser();
        // Use ISO se houver, senão data_criacao (que pode ser string formatada)
        const dateForCheck = c.created_at_iso || c.data_criacao;

        const isOwner = user.email === c.usuario_cs;
        const withinTimeLimit = this.checkTimeLimit(dateForCheck);

        // Pode editar se for gestor OU (dono E dentro do prazo)
        const canEditOrDelete = user.isManager || (isOwner && withinTimeLimit);
        // Mostra desabilitado se for dono MAS o prazo expirou (e não é gestor)
        const showDisabled = isOwner && !withinTimeLimit && !user.isManager;

        // Se pode editar ou deve mostrar desabilitado, renderizamos os botões
        const shouldRenderButtons = canEditOrDelete || showDisabled;

        return `
            <div class="comment-item border rounded p-2 mb-2 bg-white" data-comment-id="${c.id}">
                <div class="d-flex justify-content-between align-items-start mb-1">
                    <div class="d-flex align-items-center gap-2">
                        <strong class="small"><i class="bi bi-person-fill me-1"></i>${escape(c.usuario_nome || c.usuario_cs)}</strong>
                        <span class="badge rounded-pill small ${badgeClass}">${c.visibilidade}</span>
                        ${c.tag === 'Ação interna' ? '<span class="badge rounded-pill small bg-primary"><i class="bi bi-briefcase"></i> Ação interna</span>' : ''}
                        ${c.tag === 'Reunião' ? '<span class="badge rounded-pill small bg-danger"><i class="bi bi-calendar-event"></i> Reunião</span>' : ''}
                        ${(c.tag === 'No Show' || c.noshow) ? '<span class="badge rounded-pill small bg-warning text-dark"><i class="bi bi-calendar-x"></i> No show</span>' : ''}
                        ${c.tag === 'Simples registro' ? '<span class="badge rounded-pill small bg-secondary"><i class="bi bi-pencil-square"></i> Simples registro</span>' : ''}
                    </div>
                </div>
                <div class="d-flex justify-content-between align-items-center">
                     <small class="text-muted" style="font-size: 0.7em;">${c.data_criacao || ''}</small>
                </div>
                
                <p class="mb-1 small mt-2" style="white-space: pre-wrap; word-wrap: break-word;">${escape(c.texto)}</p>
                ${c.imagem_url ? `
                    <div class="mt-1">
                         <img src="${c.imagem_url}" class="img-fluid rounded comment-image-thumbnail" style="max-height: 100px; cursor: pointer;" title="Clique para ampliar">
                    </div>
                ` : ''}
                <div class="d-flex gap-2 mt-2 justify-content-end action-buttons">
                    ${isExterno && temEmailResponsavel ? `
                        <button class="btn btn-sm btn-link text-primary p-0 small btn-send-email-comment me-auto" 
                                data-comment-id="${c.id}" 
                                title="Enviar para ${emailResponsavel}">
                            <i class="bi bi-envelope me-1"></i>Enviar email
                        </button>
                    ` : ''}
                    
                    ${shouldRenderButtons ? `
                        <button class="btn btn-sm btn-link ${canEditOrDelete ? 'text-secondary' : 'text-muted'} p-0 small btn-edit-comment" 
                                data-comment-id="${c.id}"
                                data-item-id="${itemId}"
                                ${!canEditOrDelete ? 'disabled title="Prazo de 3h para edição expirado"' : ''}>
                            <i class="bi bi-pencil me-1"></i>Editar
                        </button>
                        <div class="vr"></div>
                        <button class="btn btn-sm btn-link ${canEditOrDelete ? 'text-danger' : 'text-muted'} p-0 small btn-delete-comment" 
                                data-comment-id="${c.id}"
                                data-item-id="${itemId}"
                                ${!canEditOrDelete ? 'disabled title="Prazo de 3h para exclusão expirado"' : ''}>
                            <i class="bi bi-trash me-1"></i>Excluir
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Saves a new comment.
     */
    async saveComment(itemId) {
        const textarea = this.container.querySelector(`#comment-input-${itemId}`);
        const commentsSection = this.container.querySelector(`#comments-${itemId}`);
        if (!textarea) return;

        const texto = textarea.value.trim();

        // Get visibility
        const activeVisibilityTag = commentsSection?.querySelector('.comentario-tipo-tag.interno.active, .comentario-tipo-tag.externo.active');
        const visibilidade = activeVisibilityTag?.classList.contains('externo') ? 'externo' : 'interno';

        // Get tag
        const activeTagOption = commentsSection?.querySelector('.comentario-tipo-tag.tag-option.active');
        const tag = activeTagOption ? activeTagOption.dataset.tag : null;
        const noshow = tag === 'No Show';

        // Get image
        const fileInput = commentsSection?.querySelector(`.comentario-imagem-input`);
        const imageFile = fileInput?.files?.[0] || null;

        // Get email notification
        const checkboxEmail = commentsSection?.querySelector(`#check-email-${itemId}`);
        const send_email = checkboxEmail ? checkboxEmail.checked : false;

        if (!texto && !imageFile) {
            if (this.renderer.showToast) this.renderer.showToast('Digite um comentário ou anexe uma imagem', 'warning');
            return;
        }

        if (!this.renderer.service) return;

        // Delegate to service
        const data = { texto, visibilidade, noshow, tag, send_email };
        const result = await this.renderer.service.saveComment(itemId, data, imageFile);

        if (result.success) {
            // Clear form
            textarea.value = '';
            this.removeImagePreview(itemId);
            this.resetTags(commentsSection);

            // Update indicator
            this.updateCommentIndicator(itemId, true);

            // Reload
            await this.loadComments(itemId);

            // Trigger global events
            try { if (window.reloadTimeline) window.reloadTimeline(); } catch (_) { }
        }
    }

    resetTags(commentsSection) {
        if (!commentsSection) return;
        // Reset visibility to Interno
        commentsSection.querySelectorAll('.comentario-tipo-tag.interno, .comentario-tipo-tag.externo').forEach(t => t.classList.remove('active'));
        const internoTag = commentsSection.querySelector('.comentario-tipo-tag.interno');
        if (internoTag) internoTag.classList.add('active');

        // Reset tags
        commentsSection.querySelectorAll('.comentario-tipo-tag.tag-option').forEach(t => t.classList.remove('active'));
    }

    cancelComment(itemId) {
        const textarea = this.container.querySelector(`#comment-input-${itemId}`);
        if (textarea) textarea.value = ''; // Or restore original if editing
        this.removeImagePreview(itemId);

        const commentsSection = this.container.querySelector(`#comments-${itemId}`);
        if (commentsSection && window.bootstrap && window.bootstrap.Collapse) {
            const bsCollapse = window.bootstrap.Collapse.getInstance(commentsSection);
            if (bsCollapse) bsCollapse.hide();
        }
    }

    async deleteComment(comentarioId, itemId) {
        if (!this.renderer.service) return;

        const result = await this.renderer.service.deleteComment(comentarioId);

        if (result.success) {
            await this.loadComments(itemId);
            // Check if there are any comments left to update indicator
            const historyContainer = this.container.querySelector(`#comments-history-${itemId}`);
            const hasComments = historyContainer && historyContainer.querySelectorAll('.comment-item').length > 0;
            this.updateCommentIndicator(itemId, hasComments);
        }
    }

    updateCommentIndicator(itemId, hasComments) {
        const button = this.container.querySelector(`.btn-comment-toggle[data-item-id="${itemId}"]`);
        if (!button) return;

        const icon = button.querySelector('i');
        if (!icon) return;

        // Update colors
        if (hasComments) {
            icon.classList.remove('text-muted');
            icon.classList.add('text-primary');
            // Add red dot if missing
            if (!icon.querySelector('.position-absolute')) {
                icon.innerHTML += '<span class="position-absolute top-0 start-100 translate-middle p-1 bg-danger border border-light rounded-circle" style="font-size: 0.4rem;"></span>';
            }
        } else {
            icon.classList.remove('text-primary');
            icon.classList.add('text-muted');
            // Remove red dot
            const dot = icon.querySelector('.position-absolute');
            if (dot) dot.remove();
        }

        // Update flatData if accessible
        if (this.renderer.flatData && this.renderer.flatData[itemId]) {
            this.renderer.flatData[itemId].comment = hasComments ? 'has_comment' : '';
        }
    }

    // ========================================
    // IMAGE HANDLING
    // ========================================

    setupImageUploadHandlers() {
        this._handlers = {
            change: (e) => {
                if (e.target.classList.contains('comentario-imagem-input')) {
                    const itemId = e.target.dataset.itemId;
                    const file = e.target.files[0];
                    this.handleImageSelect(itemId, file);
                }
            },
            paste: (e) => {
                const target = e.target;
                if (target.id && target.id.startsWith('comment-input-')) {
                    const itemId = target.id.replace('comment-input-', '');
                    const items = e.clipboardData?.items;
                    if (items) {
                        for (let i = 0; i < items.length; i++) {
                            if (items[i].type.indexOf('image') !== -1) {
                                e.preventDefault();
                                const blob = items[i].getAsFile();
                                this.handleImageSelect(itemId, blob);
                                break;
                            }
                        }
                    }
                }
            },
            click: (e) => {
                if (e.target.classList.contains('comment-image-thumbnail')) {
                    const src = e.target.getAttribute('src');
                    if (src) this.openImageModal(src);
                }
            }
        };

        this.container.addEventListener('change', this._handlers.change);
        this.container.addEventListener('paste', this._handlers.paste);
        this.container.addEventListener('click', this._handlers.click);
    }

    destroy() {
        if (this._handlers) {
            this.container.removeEventListener('change', this._handlers.change);
            this.container.removeEventListener('paste', this._handlers.paste);
            this.container.removeEventListener('click', this._handlers.click);
            this._handlers = null;
        }
    }

    handleImageSelect(itemId, file) {
        if (!file || !file.type.startsWith('image/')) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            const previewContainer = document.getElementById(`image-preview-${itemId}`);
            if (previewContainer) {
                const img = previewContainer.querySelector('.image-preview');
                if (img) {
                    img.src = event.target.result;
                    previewContainer.classList.remove('d-none');
                }
            }

            // Update file input if it wasn't the source (e.g. pasted)
            const fileInput = document.querySelector(`.comentario-imagem-input[data-item-id="${itemId}"]`);
            if (fileInput && fileInput.files[0] !== file) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
            }
        };
        reader.readAsDataURL(file);
    }

    removeImagePreview(itemId) {
        const previewContainer = document.getElementById(`image-preview-${itemId}`);
        const fileInput = document.querySelector(`.comentario-imagem-input[data-item-id="${itemId}"]`);

        if (previewContainer) {
            previewContainer.classList.add('d-none');
            const img = previewContainer.querySelector('.image-preview');
            if (img) img.src = '';
        }

        if (fileInput) {
            fileInput.value = '';
        }
    }

    openImageModal(imageUrl) {
        let modal = document.getElementById('imageModal');
        if (!modal) {
            // Create modal if missing
            const modalHtml = `
                <div class="modal fade" id="imageModal" tabindex="-1">
                    <div class="modal-dialog modal-xl modal-dialog-centered" style="max-width: 90vw;">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Imagem do Comentário</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body text-center p-2">
                                <img id="modalImage" src="" class="img-fluid" style="max-height: 85vh; width: auto;">
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            modal = document.getElementById('imageModal');
        }

        const img = document.getElementById('modalImage');
        if (img) img.src = imageUrl;

        if (window.bootstrap && window.bootstrap.Modal) {
            const bsModal = new window.bootstrap.Modal(modal);
            bsModal.show();
        }
    }

    startEditComment(commentId, itemId) {
        const commentEl = this.container.querySelector(`.comment-item[data-comment-id="${commentId}"]`);
        if (!commentEl) return;

        // Save current HTML to restore on cancel
        if (!commentEl.dataset.originalHtml) {
            commentEl.dataset.originalHtml = commentEl.innerHTML;
        }

        const p = commentEl.querySelector('p.small');
        const currentText = p ? p.innerText : '';

        // Replace content with edit form
        // We use innerHTML but be careful not to break event delegation.
        // The delegation is on the container, so replacing innerHTML of a child is fine.
        commentEl.innerHTML = `
            <div class="edit-mode-wrapper p-1">
                <textarea class="form-control form-control-sm mb-2" rows="3">${this.escapeHtml(currentText)}</textarea>
                <div class="d-flex justify-content-end gap-2">
                    <button class="btn btn-sm btn-secondary btn-cancel-edit" data-comment-id="${commentId}" data-item-id="${itemId}">Cancelar</button>
                    <button class="btn btn-sm btn-primary btn-save-edit" data-comment-id="${commentId}" data-item-id="${itemId}">Salvar</button>
                </div>
            </div>
        `;
    }

    cancelEditComment(commentId, itemId) {
        const commentEl = this.container.querySelector(`.comment-item[data-comment-id="${commentId}"]`);
        if (commentEl && commentEl.dataset.originalHtml) {
            commentEl.innerHTML = commentEl.dataset.originalHtml;
            delete commentEl.dataset.originalHtml;
        }
    }

    async saveEditedComment(commentId, itemId) {
        const commentEl = this.container.querySelector(`.comment-item[data-comment-id="${commentId}"]`);
        const textarea = commentEl.querySelector('textarea');
        const newText = textarea.value.trim();

        if (!newText) {
            if (this.renderer.showToast) this.renderer.showToast('Digite um texto', 'warning');
            return;
        }

        if (this.renderer.service) {
            const result = await this.renderer.service.updateComment(commentId, newText);
            if (result.success) {
                await this.loadComments(itemId);
                // Trigger global updates if needed, though comments don't affect progress usually
            } else {
                if (this.renderer.showToast) this.renderer.showToast(result.error || 'Erro ao editar', 'error');
            }
        }
    }

    async sendEmail(commentId) {
        if (!this.renderer.service) return;

        // Service already handles confirmation/toasts
        await this.renderer.service.sendCommentEmail(commentId);
    }

    escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

window.ChecklistComments = ChecklistComments;
