/**
 * Checklist Hierárquico Infinito - Renderizador e Gerenciador
 * Baseado no exemplo com melhorias de performance e integração com backend
 * 
 * Funcionalidades:
 * - Propagação de status (cascata e bolha)
 * - Sistema de comentários
 * - Barras de progresso por item
 * - Atualização incremental (sem re-render completo)
 */

class ChecklistRenderer {
    constructor(containerId, implantacaoId) {
        this.container = document.getElementById(containerId);
        this.implantacaoId = implantacaoId;
        this.data = window.CHECKLIST_DATA || [];
        this.expandedItems = new Set();
        this.flatData = {};
        this.isLoading = false;
        this.previsaoTermino = this.container?.dataset?.previsaoTermino || '';
        this._toggleThrottle = new Map();

        // Dependency Injection - Usa Service Container
        if (window.appContainer && window.appContainer.has('checklistService')) {
            this.service = window.appContainer.resolve('checklistService');
        } else {
            // Fallback para compatibilidade (se container não estiver disponível)
            this.service = window.$checklistService || null;
        }

        // Log warning se service não estiver disponível
        if (!this.service) {
            console.warn('[ChecklistRenderer] ChecklistService não disponível. Funcionalidades de comentários e edição estarão limitadas.');
        }

        // CSRF ainda necessário para código legado (será removido gradualmente)
        this.csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
        if (!this.csrfToken) {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) this.csrfToken = meta.getAttribute('content') || '';
            if (!this.csrfToken) {
                try {
                    const m = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
                    if (m) this.csrfToken = decodeURIComponent(m[1]);
                } catch (e) { }
            }
        }

        if (!this.container) {
            return;
        }

        this.init();
    }

    /**
     * Verifica se o service está disponível para operações
     */
    hasService() {
        return this.service && typeof this.service.loadComments === 'function';
    }

    init() {
        if (!this.data || this.data.length === 0) {
            this.renderEmpty();
            return;
        }

        this.buildFlatData(this.data);

        this.render();
        this.attachEventListeners();
        this.setupImageUploadHandlers();

        // Render com todas as tarefas minimizadas por padrão (sem expandir nós inicialmente)

        this.updateProgressFromLocalData();
        this.updateAllItemsUI();
    }

    /**
     * Constrói estrutura plana (flatData) para acesso rápido durante propagação
     * Processa todas as tarefas filhas sem limite
     */
    buildFlatData(nodes, parentId = null) {
        nodes.forEach(node => {
            const allChildren = node.children && node.children.length > 0 ? node.children : [];

            this.flatData[node.id] = {
                ...node,
                parentId: parentId,
                childrenIds: allChildren.map(c => c.id)
            };

            if (allChildren.length > 0) {
                this.buildFlatData(allChildren, node.id);
            }
        });
    }

    render() {
        const treeRoot = this.container.querySelector('#checklist-tree-root');
        if (!treeRoot) return;

        treeRoot.innerHTML = this.renderTree(this.data);
        this.updateConclusionHeaderVisibility();
    }

    renderTree(items) {
        if (!items || items.length === 0) {
            return '<div class="text-muted text-center py-4">Nenhum item encontrado</div>';
        }

        return items.map(item => this.renderItem(item)).join('');
    }

    renderItem(item) {
        const allChildren = item.children && item.children.length > 0 ? item.children : [];
        const hasChildren = allChildren.length > 0;
        const isExpanded = this.expandedItems.has(item.id);
        const hasComment = item.comment && item.comment.trim().length > 0;
        const progressLabel = item.progress_label || null;

        let iconClass = 'bi-list-ul text-secondary';
        let iconColor = '';
        if (item.level === 0) {
            iconClass = 'bi-flag-fill';
            iconColor = 'text-primary';
        } else if (item.level === 1) {
            iconClass = 'bi-folder2-fill';
            iconColor = 'text-info';
        } else if (item.level === 2) {
            iconClass = 'bi-file-text-fill';
            iconColor = 'text-success';
        } else {
            iconClass = 'bi-list-ul';
            iconColor = 'text-muted';
        }

        const statusClass = item.completed ? 'bg-success' : 'bg-warning';
        const statusText = item.completed ? 'Concluído' : 'Pendente';
        const statusIcon = item.completed ? 'bi-check-circle-fill' : 'bi-clock-fill';

        const indentPx = Math.max(0, (item.level || 0) * 14);

        // UX: Adiciona animação de entrada
        // Adicionamos um delay leve baseado no índice se possível, mas aqui usamos genérico
        return `
            <div id="checklist-item-${item.id}" class="checklist-item animate-fade-in" data-item-id="${item.id}" data-level="${item.level || 0}" style="animation-duration: 0.3s;">
                <div class="checklist-item-header position-relative level-${item.level || 0}" style="padding-left: 0;">
                    ${hasChildren ? `
                        <div class="position-absolute bottom-0 left-0 h-1 progress-bar-item" 
                             style="width: 0%; background-color: #28a745; opacity: 0; transition: all 0.3s;"
                             id="progress-bar-${item.id}"></div>
                    ` : ''}
                    
                    <div class="checklist-item-grid py-1 px-2 hover-bg" 
                         style="cursor: pointer;"
                         onclick="if(event.target.closest('.btn-expand, .btn-comment-toggle, .checklist-checkbox')) return; if(window.checklistRenderer && ${hasChildren}) { window.checklistRenderer.toggleExpand(${item.id}); }">
                        <span class="col-empty d-flex align-items-center justify-content-center">
                            ${hasChildren ? `
                                <button class="btn-icon btn-expand p-1 border-0 bg-transparent" 
                                        data-item-id="${item.id}" 
                                        title="${isExpanded ? 'Colapsar' : 'Expandir'}"
                                        style="cursor: pointer; z-index: 10; position: relative;">
                                    <i class="bi ${isExpanded ? 'bi-chevron-down' : 'bi-chevron-right'} text-muted" style="pointer-events: none;"></i>
                                </button>
                            ` : '<span class="btn-icon-placeholder" style="width: 24px;"></span>'}
                        </span>
                        <span class="col-checkbox d-flex align-items-center justify-content-center">
                            <input type="checkbox" 
                                   class="checklist-checkbox form-check-input" 
                                   id="checklist-${item.id}"
                                   data-item-id="${item.id}"
                                   ${item.completed ? 'checked' : ''}
                                   style="cursor: pointer; width: 18px; height: 18px;">
                        </span>
                        <span class="col-title d-flex align-items-center gap-2">
                            <span class="indent-spacer" style="display:inline-block; width: ${indentPx}px;"></span>
                            <span class="checklist-item-title mb-0" 
                                   style="${item.completed ? 'text-decoration: line-through; color: #6c757d;' : ''}">
                                ${this.escapeHtml(item.title)}
                            </span>
                        </span>

                        <span class="col-spacer"></span>

                        <span class="col-tag d-flex align-items-center" style="overflow:hidden; white-space:nowrap;">
                            ${item.tag ? `
                                <span class="badge badge-truncate ${this.getTagClass(item.tag)} js-edit-tag" id="badge-tag-${item.id}" data-item-id="${item.id}" style="font-size: 0.75rem; cursor: pointer; display:inline-block; max-width:100%;" title="Editar tag">
                                    ${this.escapeHtml(item.tag)}
                                </span>
                            ` : `
                                <span class="badge badge-truncate bg-light text-dark js-edit-tag" id="badge-tag-${item.id}" data-item-id="${item.id}" style="font-size: 0.75rem; cursor: pointer; display:inline-block; max-width:100%;" title="Definir tag">
                                    Definir tag
                                </span>
                            `}
                        </span>

                        <span class="col-qtd d-flex align-items-center justify-content-center" style="overflow:hidden">
                            ${progressLabel ? `
                                <span class="checklist-progress-badge badge badge-truncate bg-light text-dark" style="font-size: 0.75rem;">
                                    ${progressLabel}
                                </span>
                            ` : ''}
                        </span>

                        <span class="col-responsavel d-flex align-items-center" style="overflow:hidden; white-space:nowrap;">
                            ${item.responsavel ? `<span class="badge bg-primary js-edit-resp badge-resp-ellipsis badge-truncate" data-item-id="${item.id}" style="font-size: 0.75rem;" title="${this.escapeHtml(item.responsavel)}">${this.escapeHtml(this.abbrevResponsavel(item.responsavel))}</span>` : `<span class="badge bg-primary js-edit-resp badge-resp-ellipsis badge-truncate" data-item-id="${item.id}" style="font-size: 0.75rem;">Definir responsável</span>`}
                        </span>

                        <span class="col-prev-orig">
                            ${item.previsao_original ? `<span class="badge badge-truncate bg-warning text-dark" id="badge-prev-orig-${item.id}" style="font-size: 0.75rem;" title="Previsão original: ${item.previsao_original}" aria-label="Previsão original: ${this.formatDate(item.previsao_original)}">${this.formatDate(item.previsao_original)}</span>` : `<span class="badge bg-warning text-dark d-none" id="badge-prev-orig-${item.id}" style="font-size: 0.75rem;" aria-hidden="true"></span>`}
                        </span>
                        <span class="col-prev-atual">
                            ${item.nova_previsao ? `<span class="badge badge-truncate bg-danger text-white js-edit-prev" id="badge-prev-nova-${item.id}" data-item-id="${item.id}" style="font-size: 0.75rem;" title="Nova previsão: ${item.nova_previsao}" aria-label="Nova previsão: ${this.formatDate(item.nova_previsao)}">${this.formatDate(item.nova_previsao)}</span>` : ((item.previsao_original || this.previsaoTermino) ? `<span class="badge badge-truncate bg-warning text-dark js-edit-prev" id="badge-prev-nova-${item.id}" data-item-id="${item.id}" style="font-size: 0.75rem;" title="Nova previsão: ${item.previsao_original || this.previsaoTermino}" aria-label="Nova previsão: ${this.formatDate(item.previsao_original || this.previsaoTermino)}">${this.formatDate(item.previsao_original || this.previsaoTermino)}</span>` : `<span class="badge badge-truncate bg-warning text-dark js-edit-prev" id="badge-prev-nova-${item.id}" data-item-id="${item.id}" style="font-size: 0.75rem;" aria-label="Definir nova previsão">Definir nova previsão</span>`)}
                        </span>
                        <span class="col-conclusao">
                            <span class="badge badge-truncate bg-success text-white d-none" id="badge-concl-${item.id}" style="font-size: 0.75rem;"></span>
                        </span>
                        <span class="col-status">
                            <span class="badge badge-truncate ${statusClass}" id="status-badge-${item.id}" title="Status: ${statusText}" aria-label="Status: ${statusText}">
                                <i class="bi ${statusIcon} me-1" aria-hidden="true"></i>${statusText}
                                ${item.atrasada ? '<i class="bi bi-exclamation-triangle-fill" aria-hidden="true"></i>' : ''}
                            </span>
                        </span>
                        
                        <span class="col-comment">
                        ${item.level === 0 ? `
                        <button class="btn-icon btn-comment-toggle p-1 border-0 bg-transparent" 
                                data-item-id="${item.id}" 
                                title="Comentários">
                            <i class="bi bi-chat-left-text ${hasComment ? 'text-primary' : 'text-muted'} position-relative">
                                ${hasComment ? '<span class="position-absolute top-0 start-100 translate-middle p-1 bg-danger border border-light rounded-circle" style="font-size: 0.4rem;"></span>' : ''}
                            </i>
                        </button>
                        ` : ''}
                        </span>
                        <span class="col-delete">
                         <button class="btn-icon btn-delete-item p-1 border-0 bg-transparent" 
                                 data-item-id="${item.id}" 
                                 title="Excluir tarefa">
                             <i class="bi bi-trash text-danger"></i>
                         </button>
                         </span>
                    </div>
                </div>
                
                ${hasChildren ? `
                    <div class="checklist-item-children ${isExpanded ? '' : 'd-none'}" 
                         data-item-id="${item.id}"
                         style="transition: all 0.3s ease; ${isExpanded ? 'display: block;' : 'display: none;'}">
                        ${this.renderTree(allChildren)}
                    </div>
                ` : ''}
                
                <!-- Seção de Comentários (Collapse Bootstrap) -->
                <div class="checklist-comments-section collapse" id="comments-${item.id}">
                    <div class="checklist-comment-form p-3 bg-light border-top">
                        <label class="form-label small text-muted mb-1">Adicionar Comentário</label>
                        <textarea class="form-control form-control-sm" 
                                  id="comment-input-${item.id}" 
                                  rows="2"
                                  placeholder="Escreva um comentário para esta tarefa..."></textarea>
                        
                        <!-- Preview de imagem -->
                        <div class="image-preview-container d-none mt-2 p-2 bg-white border rounded" id="image-preview-${item.id}">
                            <div class="d-flex align-items-center gap-2">
                                <img class="image-preview" style="max-height: 80px; max-width: 120px; border-radius: 4px; border: 1px solid #dee2e6;">
                                <button type="button" class="btn btn-sm btn-outline-danger" 
                                        onclick="window.checklistRenderer.removeImagePreview(${item.id})"
                                        title="Remover imagem">
                                    <i class="bi bi-trash"></i> Remover
                                </button>
                            </div>
                        </div>
                        
                        <div class="d-flex align-items-center justify-content-between gap-2 mt-2">
                            <div class="d-flex align-items-center gap-2 flex-wrap">
                                <span class="comentario-tipo-tag interno active" 
                                      data-tipo="interno"
                                      data-item-id="${item.id}">
                                    <i class="bi bi-lock-fill"></i> Interno
                                </span>
                                <span class="comentario-tipo-tag externo" 
                                      data-tipo="externo"
                                      data-item-id="${item.id}">
                                    <i class="bi bi-globe"></i> Externo
                                </span>
                                <span class="comentario-tipo-tag tag-option acao-interna" 
                                      data-item-id="${item.id}"
                                      data-tag="Ação interna">
                                    <i class="bi bi-briefcase"></i> Ação interna
                                </span>
                                <span class="comentario-tipo-tag tag-option reuniao" 
                                      data-item-id="${item.id}"
                                      data-tag="Reunião">
                                    <i class="bi bi-calendar-event"></i> Reunião
                                </span>
                                <span class="comentario-tipo-tag tag-option noshow" 
                                      id="comment-noshow-${item.id}"
                                      data-item-id="${item.id}"
                                      data-tag="No Show">
                                    <i class="bi bi-calendar-x"></i> No show
                                </span>
                                <span class="comentario-tipo-tag tag-option simples-registro" 
                                      id="comment-simples-registro-${item.id}"
                                      data-item-id="${item.id}"
                                      data-tag="Simples registro">
                                    <i class="bi bi-pencil-square"></i> Simples registro
                                </span>
                            </div>
                            <div class="d-flex gap-2">
                                <label class="btn btn-sm btn-outline-secondary mb-0" title="Anexar imagem ou print">
                                    <i class="bi bi-paperclip"></i>
                                    <input type="file" 
                                           class="d-none comentario-imagem-input" 
                                           data-item-id="${item.id}"
                                           accept="image/*">
                                </label>
                                <button class="btn btn-sm btn-secondary btn-cancel-comment" data-item-id="${item.id}">
                                    Cancelar
                                </button>
                                <button class="btn btn-sm btn-primary btn-save-comment" data-item-id="${item.id}">
                                    <i class="bi bi-send me-1"></i>Salvar
                                </button>
                            </div>
                        </div>
                        
                        <div class="comments-history mt-3" id="comments-history-${item.id}">
                            <div class="text-center py-2">
                                <div class="spinner-border spinner-border-sm text-secondary" role="status">
                                    <span class="visually-hidden">Carregando...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderEmpty() {
        const treeRoot = this.container.querySelector('#checklist-tree-root');
        if (treeRoot) {
            treeRoot.innerHTML = `
                <div class="empty-state text-center py-5">
                    <i class="bi bi-diagram-3" style="font-size: 3rem; color: #ccc;"></i>
                    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#modalSelecionarPlano">
                        <i class="bi bi-plus-circle me-2"></i>Selecionar Plano
                    </button>
                </div>
            `;
        }
    }

    attachEventListeners() {
        document.addEventListener('click', (e) => {
            const button = e.target.closest('.btn-expand');
            if (button && this.container.contains(button)) {
                e.preventDefault();
                e.stopPropagation();
                const itemId = parseInt(button.dataset.itemId);
                if (!isNaN(itemId)) {
                    this.toggleExpand(itemId);
                }
            }
        });

        this.container.addEventListener('change', (e) => {
            if (e.target.classList.contains('checklist-checkbox')) {
                const itemId = parseInt(e.target.dataset.itemId);
                const checked = e.target.checked;
                this.handleCheck(itemId, checked);
            }
        });

        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.btn-comment-toggle')) {
                const button = e.target.closest('.btn-comment-toggle');
                const itemId = parseInt(button.dataset.itemId);
                this.toggleComments(itemId);
            }
        });
        this.container.addEventListener('click', (e) => {
            const respBadge = e.target.closest('.js-edit-resp');
            if (respBadge) {
                const itemId = parseInt(respBadge.dataset.itemId);
                this.openRespModal(itemId);
                return;
            }
            const prevBadge = e.target.closest('.js-edit-prev');
            if (prevBadge) {
                const itemId = parseInt(prevBadge.dataset.itemId);
                const node = this.flatData[itemId] || {};
                if (node.completed || node.data_conclusao) {
                    if (typeof this.showToast === 'function') this.showToast('Tarefa concluída: não é possível adicionar nova previsão', 'warning'); else alert('Tarefa concluída: não é possível adicionar nova previsão');
                    return;
                }
                this.openPrevModal(itemId);
                return;
            }
            const tagBadge = e.target.closest('.js-edit-tag');
            if (tagBadge) {
                const itemId = parseInt(tagBadge.dataset.itemId);
                this.openTagModal(itemId);
                return;
            }
        });

        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.btn-save-comment')) {
                const button = e.target.closest('.btn-save-comment');
                const itemId = parseInt(button.dataset.itemId);
                this.saveComment(itemId);
            }

            if (e.target.closest('.btn-cancel-comment')) {
                const button = e.target.closest('.btn-cancel-comment');
                const itemId = parseInt(button.dataset.itemId);
                this.cancelComment(itemId);
            }

            if (e.target.closest('.btn-send-email-comment')) {
                const button = e.target.closest('.btn-send-email-comment');
                const comentarioId = parseInt(button.dataset.commentId);
                this.sendCommentEmail(comentarioId);
            }

            if (e.target.closest('.btn-delete-comment')) {
                const button = e.target.closest('.btn-delete-comment');
                const comentarioId = parseInt(button.dataset.commentId);
                const itemId = parseInt(button.dataset.itemId);
                this.deleteComment(comentarioId, itemId);
            }

            if (e.target.closest('.btn-delete-item')) {
                const button = e.target.closest('.btn-delete-item');
                const itemId = parseInt(button.dataset.itemId);
                this.deleteItem(itemId);
            }

            // Handle visibility tags (Interno/Externo) - mutually exclusive
            const visibilityTag = e.target.closest('.comentario-tipo-tag.interno, .comentario-tipo-tag.externo');
            if (visibilityTag) {
                const container = visibilityTag.closest('.d-flex');
                if (container) {
                    // Remove active from Interno and Externo only (not noshow)
                    container.querySelectorAll('.comentario-tipo-tag.interno, .comentario-tipo-tag.externo').forEach(t => t.classList.remove('active'));
                }
                visibilityTag.classList.add('active');
            }

            // Handle tag options (Ação interna, Reunião, No Show, Simples registro) - mutually exclusive
            const tagOption = e.target.closest('.comentario-tipo-tag.tag-option');
            if (tagOption) {
                const itemId = tagOption.dataset.itemId;
                const tagName = tagOption.dataset.tag;
                const container = tagOption.closest('.d-flex');

                // Check if already active - if so, deselect it
                if (tagOption.classList.contains('active')) {
                    tagOption.classList.remove('active');
                } else {
                    // Remove active from all tag-options in this container
                    if (container) {
                        container.querySelectorAll('.comentario-tipo-tag.tag-option').forEach(t => t.classList.remove('active'));
                    }
                    // Activate clicked tag
                    tagOption.classList.add('active');
                }
            }
        });
    }

    updateElementState(children, button, itemId) {
        const isExpanded = this.expandedItems.has(itemId);
        if (isExpanded) {
            children.classList.remove('d-none');
            children.style.display = 'block';
            if (button) {
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = 'bi bi-chevron-down text-muted';
                }
                button.setAttribute('title', 'Colapsar');
            }
        } else {
            children.classList.add('d-none');
            if (button) {
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = 'bi bi-chevron-right text-muted';
                }
                button.setAttribute('title', 'Expandir');
            }
        }
    }

    toggleExpand(itemId, animate = true) {
        const wasExpanded = this.expandedItems.has(itemId);
        if (wasExpanded) {
            this.expandedItems.delete(itemId);
        } else {
            this.expandedItems.add(itemId);
        }
        this.updateExpandedState(itemId, animate);
    }

    updateExpandedState(itemId = null, animate = true) {
        if (itemId) {
            const children = this.container.querySelector(`.checklist-item-children[data-item-id="${itemId}"]`);
            const button = this.container.querySelector(`.btn-expand[data-item-id="${itemId}"]`);

            if (children) {
                this.updateElementState(children, button, itemId);
            }
        } else {
            this.expandedItems.forEach(id => {
                const children = this.container.querySelector(`.checklist-item-children[data-item-id="${id}"]`);
                const button = this.container.querySelector(`.btn-expand[data-item-id="${id}"]`);
                if (children) {
                    this.updateElementState(children, button, id);
                }
            });
        }
    }

    ensureItemVisible(itemId) {
        if (!itemId) return;
        let current = itemId;
        const visited = new Set();
        while (this.flatData[current] && this.flatData[current].parentId && !visited.has(current)) {
            visited.add(current);
            const parentId = this.flatData[current].parentId;
            this.expandedItems.add(parentId);
            current = parentId;
        }
        this.expandedItems.add(itemId);
        this.updateExpandedState();
    }

    /**
     * Manipula mudança de checkbox com propagação (cascata e bolha)
     * OTIMIZADO: Atualiza UI imediatamente (otimista) e sincroniza com backend em paralelo
     */
    async handleCheck(itemId, completed) {
        if (this.isLoading) return;
        const now = Date.now();
        const last = this._toggleThrottle.get(itemId) || 0;
        if (now - last < 300) return;
        this._toggleThrottle.set(itemId, now);

        const checkbox = this.container.querySelector(`#checklist-${itemId}`);
        if (!checkbox) return;

        // Marcar como loading mas NÃO desabilitar o checkbox para UX mais fluida
        this.isLoading = true;

        // Atualiza UI otimisticamente
        if (this.flatData[itemId]) {
            this.flatData[itemId].completed = completed;
            this.flatData[itemId].data_conclusao = completed ? new Date().toISOString() : null;
        }

        this.propagateDown(itemId, completed);
        this.propagateUp(itemId);
        this.updateAllItemsUI();
        this.updateProgressFromLocalData();

        // Delega para o service
        if (!this.hasService()) {
            console.warn('[ChecklistRenderer] Service não disponível para toggleItem');
            this.isLoading = false;
            return;
        }
        const result = await this.service.toggleItem(itemId, completed);

        if (result.success) {
            // Atualiza progresso do servidor
            const serverProgress = Math.round(result.progress || 0);
            this.updateProgressDisplay(serverProgress);

            if (window.updateProgressBar && typeof window.updateProgressBar === 'function') {
                window.updateProgressBar(serverProgress);
            }

            // Atualiza timeline
            try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) { }
            try {
                if (typeof window.appendTimelineEvent === 'function') {
                    const status = completed ? 'Concluída' : 'Pendente';
                    const title = (this.flatData[itemId] && this.flatData[itemId].title) || '';
                    window.appendTimelineEvent('tarefa_alterada', `Status: ${status} — ${title}`);
                }
            } catch (_) { }
        } else {
            // Reverte UI em caso de erro
            if (this.flatData[itemId]) {
                this.flatData[itemId].completed = !completed;
            }
            this.propagateDown(itemId, !completed);
            this.propagateUp(itemId);
            this.updateAllItemsUI();
            this.updateProgressFromLocalData();
        }

        this.isLoading = false;
    }

    updateAllItemsUI() {
        Object.keys(this.flatData).forEach(id => {
            this.updateItemUI(parseInt(id));
        });
    }

    updateProgressFromLocalData() {
        let total = 0;
        let completed = 0;

        Object.values(this.flatData).forEach(item => {
            const isLeaf = !item.childrenIds || item.childrenIds.length === 0;
            if (isLeaf) {
                total++;
                if (item.completed) {
                    completed++;
                }
            }
        });

        const progress = total > 0 ? Math.round((completed / total) * 100) : 100;
        this.updateProgressDisplay(progress);
    }

    updateProgressDisplay(progress) {
        if (window.updateProgressBar) window.updateProgressBar(progress);
        this.updateConclusionHeaderVisibility();
    }

    updateConclusionHeaderVisibility() {
        const headerEl = this.container.querySelector('.checklist-grid .col-conclusao');
        if (!headerEl) return;
        const hasConclusion = Object.values(this.flatData || {}).some(item => !!item.data_conclusao);
        if (hasConclusion) {
            headerEl.classList.remove('d-none');
        } else {
            headerEl.classList.add('d-none');
        }
    }

    /**
     * Propaga status para baixo (cascata) - todos os filhos recebem o mesmo status
     */
    propagateDown(parentId, status) {
        const node = this.flatData[parentId];
        if (!node || !node.childrenIds || node.childrenIds.length === 0) return;

        node.childrenIds.forEach(childId => {
            if (this.flatData[childId]) {
                this.flatData[childId].completed = status;
                this.flatData[childId].data_conclusao = status ? new Date().toISOString() : null;
                this.propagateDown(childId, status);
            }
        });
    }

    propagateUp(itemId, visited = new Set()) {
        if (!itemId || visited.has(itemId)) return;

        visited.add(itemId);

        const node = this.flatData[itemId];
        if (!node || !node.parentId) return;

        const parentNode = this.flatData[node.parentId];
        if (!parentNode || !parentNode.childrenIds || parentNode.childrenIds.length === 0) return;

        const children = parentNode.childrenIds
            .map(id => this.flatData[id])
            .filter(c => c !== undefined);

        if (children.length === 0) return;

        const allChecked = children.every(c => c.completed === true);
        const someChecked = children.some(c => c.completed === true);

        const oldStatus = parentNode.completed;
        parentNode.completed = allChecked;
        parentNode.data_conclusao = allChecked ? new Date().toISOString() : null;

        if (oldStatus !== allChecked) {
            this.propagateUp(node.parentId, visited);
        }
    }

    updateItemUI(itemId) {
        const node = this.flatData[itemId];
        if (!node) return;

        const itemElement = this.container.querySelector(`.checklist-item[data-item-id="${itemId}"]`);
        if (!itemElement) return;

        const checkbox = itemElement.querySelector(`#checklist-${itemId}`);
        if (checkbox && checkbox.checked !== node.completed) {
            checkbox.checked = node.completed;
        }

        const title = itemElement.querySelector('.checklist-item-title');
        if (title) {
            if (node.completed) {
                title.style.textDecoration = 'line-through';
                title.style.color = '#6c757d';
            } else {
                title.style.textDecoration = 'none';
                title.style.color = '';
            }
        }

        const badge = itemElement.querySelector(`#status-badge-${itemId}`);
        if (badge) {
            const statusClass = node.completed ? 'bg-success' : 'bg-warning';
            const statusText = node.completed ? 'Concluído' : 'Pendente';
            const statusIcon = node.completed ? 'bi-check-circle-fill' : 'bi-clock-fill';
            badge.className = `badge badge-truncate ${statusClass}`;
            badge.innerHTML = `<i class="bi ${statusIcon} me-1"></i>${statusText}`;
        }

        const progressBadge = itemElement.querySelector('.checklist-progress-badge');
        if (progressBadge && node.childrenIds && node.childrenIds.length > 0) {
            const total = node.childrenIds.length;
            const completed = node.childrenIds.filter(id => this.flatData[id]?.completed).length;
            progressBadge.textContent = `${completed}/${total}`;
        }

        const tagBadge = itemElement.querySelector(`#badge-tag-${itemId}`);
        if (tagBadge) {
            const val = (this.flatData[itemId]?.tag || '').trim();
            if (val) {
                tagBadge.className = `badge badge-truncate ${this.getTagClass(val)} js-edit-tag`;
                tagBadge.textContent = val;
                tagBadge.setAttribute('title', 'Editar tag');
            } else {
                tagBadge.className = `badge badge-truncate bg-light text-dark js-edit-tag`;
                tagBadge.textContent = 'Definir tag';
                tagBadge.setAttribute('title', 'Definir tag');
            }
        }

        const respBadge = itemElement.querySelector('.js-edit-resp');
        if (respBadge) {
            if (node.responsavel) {
                respBadge.classList.remove('d-none');
                respBadge.textContent = this.abbrevResponsavel(node.responsavel);
                respBadge.setAttribute('title', node.responsavel);
            } else {
                respBadge.classList.remove('d-none');
                respBadge.innerHTML = 'Definir responsável';
                respBadge.removeAttribute('title');
            }
        }

        const prevOrig = itemElement.querySelector(`#badge-prev-orig-${itemId}`);
        if (prevOrig) {
            if (node.previsao_original) {
                prevOrig.classList.remove('d-none');
                prevOrig.setAttribute('title', `Previsão original: ${node.previsao_original}`);
                prevOrig.textContent = this.formatDate(node.previsao_original);
            } else {
                prevOrig.classList.add('d-none');
            }
        }

        const prevNova = itemElement.querySelector(`#badge-prev-nova-${itemId}`);
        if (prevNova) {
            if (node.nova_previsao) {
                prevNova.classList.remove('d-none');
                prevNova.classList.remove('bg-warning', 'text-dark');
                prevNova.classList.add('bg-danger', 'text-white');
                prevNova.setAttribute('title', `Nova previsão: ${node.nova_previsao}`);
                prevNova.textContent = this.formatDate(node.nova_previsao);
            } else {
                prevNova.classList.remove('d-none');
                prevNova.classList.remove('bg-danger', 'text-white');
                prevNova.classList.add('bg-warning', 'text-dark');
                const fallbackPrev = node.previsao_original || this.previsaoTermino;
                if (fallbackPrev) {
                    prevNova.setAttribute('title', `Nova previsão: ${fallbackPrev}`);
                    prevNova.textContent = this.formatDate(fallbackPrev);
                } else {
                    prevNova.textContent = 'Definir nova previsão';
                }
            }
        }

        const concl = itemElement.querySelector(`#badge-concl-${itemId}`);
        if (concl) {
            if (node.data_conclusao) {
                concl.classList.remove('d-none');
                concl.setAttribute('title', `Concluída em: ${node.data_conclusao}`);
                concl.textContent = this.formatDate(node.data_conclusao);
            } else {
                concl.classList.add('d-none');
            }
        }

        const atrasoBadge = itemElement.querySelector(`#badge-atrasada-${itemId}`);
        if (atrasoBadge) {
            const ref = node.nova_previsao || node.previsao_original;
            const atrasada = !!(ref && !node.completed && new Date(ref) < new Date());
            if (atrasada) atrasoBadge.classList.remove('d-none'); else atrasoBadge.classList.add('d-none');
        }
    }

    updateChildrenUI(itemId) {
        const node = this.flatData[itemId];
        if (!node || !node.childrenIds) return;

        node.childrenIds.forEach(childId => {
            this.updateItemUI(childId);
            this.updateChildrenUI(childId);
        });
    }

    updateParentUI(itemId) {
        const node = this.flatData[itemId];
        if (!node || !node.parentId) return;

        this.updateItemUI(node.parentId);
        this.updateParentUI(node.parentId);
    }

    toggleComments(itemId) {
        const commentsSection = this.container.querySelector(`#comments-${itemId}`);
        if (!commentsSection) return;

        const isOpening = !commentsSection.classList.contains('show');

        if (window.bootstrap && bootstrap.Collapse) {
            const bsCollapse = new bootstrap.Collapse(commentsSection, {
                toggle: true
            });
        } else {
            commentsSection.classList.toggle('show');
        }

        if (isOpening) {
            this.loadComments(itemId);
        }
    }

    async loadComments(itemId) {
        const historyContainer = this.container.querySelector(`#comments-history-${itemId}`);
        if (!historyContainer) return;

        // Verifica se service está disponível
        if (!this.service || typeof this.service.loadComments !== 'function') {
            console.warn('[ChecklistRenderer] Service não disponível para loadComments');
            historyContainer.innerHTML = `<div class="text-muted small">Serviço de comentários não disponível.</div>`;
            return;
        }

        // Delega para o service
        const result = await this.service.loadComments(itemId);

        if (result.success) {
            this.renderCommentsHistory(itemId, result.comentarios, result.emailResponsavel);
        } else {
            historyContainer.innerHTML = `<div class="text-danger small">${result.error || 'Erro ao carregar comentários'}</div>`;
        }
    }

    formatDate(dataStr) {
        if (!dataStr) return '';
        // Se já for do tipo YYYY-MM-DD, faz split manual para evitar timezone
        if (typeof dataStr === 'string' && /^\d{4}-\d{2}-\d{2}/.test(dataStr)) {
            // Pega apenas a parte da data (antes de T ou espaço)
            const dateOnly = dataStr.split(/[T ]/)[0];
            const parts = dateOnly.split('-');
            if (parts.length === 3) {
                const yyyy = parts[0];
                const mm = parts[1];
                const dd = parts[2];
                return `${dd}/${mm}/${yyyy}`;
            }
        }

        // Fallback para datas ISO com hora ou outros formatos
        const d = new Date(dataStr);
        if (isNaN(d.getTime())) return dataStr;
        const dd = String(d.getDate()).padStart(2, '0');
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const yyyy = d.getFullYear();
        return `${dd}/${mm}/${yyyy}`;
    }

    openRespModal(itemId) {
        const current = this.flatData[itemId]?.responsavel || '';
        let modal = document.getElementById('resp-edit-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'resp-edit-modal';
            modal.className = 'modal fade';
            modal.innerHTML = `
            <div class="modal-dialog">
              <div class="modal-content">
                <div class="modal-header">
                  <h5 class="modal-title">Editar Responsável</h5>
                  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                  <input type="text" class="form-control" id="resp-edit-input" placeholder="Nome" />
                </div>
                <div class="modal-footer">
                  <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                  <button type="button" class="btn btn-primary" id="resp-edit-save">Salvar</button>
                </div>
              </div>
            </div>`;
            document.body.appendChild(modal);
        }
        const input = modal.querySelector('#resp-edit-input');
        input.value = current || '';
        const saveBtn = modal.querySelector('#resp-edit-save');
        saveBtn.onclick = async () => {
            const novo = input.value.trim();
            if (!novo) return;

            // Delega para o service
            const result = await this.service.updateResponsavel(itemId, novo);

            if (result.success) {
                if (this.flatData[itemId]) this.flatData[itemId].responsavel = novo;
                this.updateItemUI(itemId);
                const m = bootstrap.Modal.getInstance(modal) || new bootstrap.Modal(modal);
                m.hide();
                try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) { }
                try {
                    if (typeof window.appendTimelineEvent === 'function') {
                        const title = (this.flatData[itemId] && this.flatData[itemId].title) || '';
                        window.appendTimelineEvent('responsavel_alterado', `Responsável: ${current || ''} → ${novo} — ${title}`);
                    }
                } catch (_) { }
            }
        };
        const m = new bootstrap.Modal(modal);
        m.show();
        setTimeout(() => input.focus(), 100);
    }

    openPrevModal(itemId) {
        const current = this.flatData[itemId]?.nova_previsao || '';
        let modal = document.getElementById('prev-edit-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'prev-edit-modal';
            modal.className = 'modal fade';
            modal.innerHTML = `
            <div class="modal-dialog">
              <div class="modal-content">
                <div class="modal-header">
                  <h5 class="modal-title">Editar Prazo da Tarefa</h5>
                  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                  <div class="mb-2">
                    <label class="form-label small text-muted">Previsão Original</label>
                    <input type="text" class="form-control" id="prev-orig-view" readonly />
                  </div>
                  <div class="mb-2">
                    <label class="form-label small">Nova Previsão</label>
                    <input type="text" class="form-control" id="prev-edit-input" placeholder="YYYY-MM-DD" />
                  </div>
                </div>
                <div class="modal-footer">
                  <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                  <button type="button" class="btn btn-primary" id="prev-edit-save">Salvar</button>
                </div>
              </div>
            </div>`;
            document.body.appendChild(modal);
        }
        const input = modal.querySelector('#prev-edit-input');
        const origView = modal.querySelector('#prev-orig-view');
        if (origView) origView.value = this.formatDate(this.flatData[itemId]?.previsao_original) || '';
        input.value = current ? String(current).slice(0, 10) : (this.flatData[itemId]?.previsao_original ? String(this.flatData[itemId].previsao_original).slice(0, 10) : '');
        if (window.flatpickr) {
            if (input._flatpickr) input._flatpickr.destroy();
            window.flatpickr(input, { dateFormat: 'Y-m-d', altInput: true, altFormat: 'd/m/Y' });
        }
        const saveBtn = modal.querySelector('#prev-edit-save');
        saveBtn.onclick = async () => {
            const novo = input.value.trim();
            if (!novo) return;

            const prevOld = this.flatData[itemId]?.nova_previsao || '';
            const isCompleted = this.flatData[itemId]?.completed || false;

            // Show loading
            const originalText = saveBtn.innerHTML;
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvando...';

            // Optimistic UI update
            this.flatData[itemId] = this.flatData[itemId] || {};
            this.flatData[itemId].nova_previsao = novo;
            this.updateItemUI(itemId);

            // Delega para o service
            const result = await this.service.updatePrevisao(itemId, novo, isCompleted);

            if (result.success) {
                if (this.flatData[itemId]) {
                    this.flatData[itemId].nova_previsao = novo;
                }
                this.updateItemUI(itemId);
                const m = bootstrap.Modal.getInstance(modal) || new bootstrap.Modal(modal);
                m.hide();
                try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) { }
                try {
                    if (typeof window.appendTimelineEvent === 'function') {
                        const title = (this.flatData[itemId] && this.flatData[itemId].title) || '';
                        window.appendTimelineEvent('prazo_alterado', `Nova previsão: ${novo} — ${title}`);
                    }
                } catch (_) { }
            } else {
                // Rollback UI
                this.flatData[itemId].nova_previsao = prevOld;
                this.updateItemUI(itemId);
            }

            saveBtn.disabled = false;
            saveBtn.innerHTML = originalText;
        };
        const m = new bootstrap.Modal(modal);
        m.show();
        setTimeout(() => input.focus(), 100);
    }

    getTagClass(tag) {
        if (tag === 'Ação interna') return 'bg-secondary';
        if (tag === 'Reunião') return 'bg-info text-dark';
        if (tag === 'Cliente') return 'bg-warning text-dark';
        if (tag === 'Rede') return 'bg-primary';
        if (tag === 'No Show') return 'bg-danger';
        return 'bg-light text-dark';
    }

    openTagModal(itemId) {
        const current = (this.flatData[itemId]?.tag || '').trim();
        let modal = document.getElementById('tag-edit-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'tag-edit-modal';
            modal.className = 'modal fade';
            modal.innerHTML = `
            <div class="modal-dialog">
              <div class="modal-content">
                <div class="modal-header">
                  <h5 class="modal-title">Editar Tag</h5>
                  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                  <div class="mb-2">
                    <label class="form-label small">Selecione a tag</label>
                    <select class="form-select" id="tag-edit-select">
                      <option value="">Definir tag</option>
                      <option value="Ação interna">Ação interna</option>
                      <option value="Reunião">Reunião</option>
                      <option value="Cliente">Cliente</option>
                      <option value="Rede">Rede</option>
                      <option value="No Show">No Show</option>
                    </select>
                  </div>
                </div>
                <div class="modal-footer">
                  <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                  <button type="button" class="btn btn-primary" id="tag-edit-save">Salvar</button>
                </div>
              </div>
            </div>`;
            document.body.appendChild(modal);
        }
        const select = modal.querySelector('#tag-edit-select');
        select.value = current || '';
        const saveBtn = modal.querySelector('#tag-edit-save');
        saveBtn.onclick = async () => {
            const novo = (select.value || '').trim();
            const prev = this.flatData[itemId]?.tag || ''; // Keep prev for rollback and timeline event

            // Show loading state
            const originalText = saveBtn.innerHTML;
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvando...';

            // Optimistic UI update
            this.flatData[itemId] = this.flatData[itemId] || {};
            this.flatData[itemId].tag = novo;
            this.updateItemUI(itemId);

            // Delega para o service
            const result = await this.service.updateTag(itemId, novo);

            if (result.success) {
                if (this.flatData[itemId]) this.flatData[itemId].tag = result.tag;
                this.updateItemUI(itemId);
                const m = bootstrap.Modal.getInstance(modal) || new bootstrap.Modal(modal);
                m.hide();
                if (typeof this.showToast === 'function') this.showToast('Tag atualizada', 'success');
                try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) { }
                try { if (typeof window.appendTimelineEvent === 'function') window.appendTimelineEvent('tag_alterada', `Tag: ${(prev || '')} → ${novo} — ${(this.flatData[itemId] && this.flatData[itemId].title) || ''}`); } catch (_) { }
            } else {
                // Rollback UI
                this.flatData[itemId].tag = prev;
                this.updateItemUI(itemId);
            }
        };
        const m = new bootstrap.Modal(modal);
        m.show();
    }

    renderCommentsHistory(itemId, comentarios, emailResponsavel) {
        const historyContainer = this.container.querySelector(`#comments-history-${itemId}`);
        if (!historyContainer) return;

        if (!comentarios || comentarios.length === 0) {
            historyContainer.innerHTML = '<div class="text-muted small fst-italic py-2">Nenhum comentário ainda.</div>';
            return;
        }

        const html = comentarios.map(c => {
            const dataFormatada = c.data_criacao || '';
            const visibilidadeClass = c.visibilidade === 'interno' ? 'bg-secondary' : 'bg-info text-dark';
            const isExterno = c.visibilidade === 'externo';
            const temEmailResponsavel = emailResponsavel && emailResponsavel.trim() !== '';

            return `
                <div class="comment-item border rounded p-2 mb-2 bg-white" data-comment-id="${c.id}">
                    <div class="d-flex justify-content-between align-items-start mb-1">
                        <div class="d-flex align-items-center gap-2">
                            <strong class="small"><i class="bi bi-person-fill me-1"></i>${this.escapeHtml(c.usuario_nome || c.usuario_cs)}</strong>
                            <span class="badge rounded-pill small ${visibilidadeClass}">${c.visibilidade}</span>
                            ${c.tag === 'Ação interna' ? '<span class="badge rounded-pill small bg-primary"><i class="bi bi-briefcase"></i> Ação interna</span>' : ''}
                            ${c.tag === 'Reunião' ? '<span class="badge rounded-pill small bg-danger"><i class="bi bi-calendar-event"></i> Reunião</span>' : ''}
                            ${(c.tag === 'No Show' || c.noshow) ? '<span class="badge rounded-pill small bg-warning text-dark"><i class="bi bi-calendar-x"></i> No show</span>' : ''}
                            ${c.tag === 'Simples registro' ? '<span class="badge rounded-pill small bg-secondary"><i class="bi bi-pencil-square"></i> Simples registro</span>' : ''}
                        </div>
                        <small class="text-muted">${dataFormatada}</small>
                    </div>
                    <p class="mb-1 small">${this.escapeHtml(c.texto)}</p>
                    ${c.imagem_url ? `<a href="${c.imagem_url}" target="_blank"><img src="${c.imagem_url}" class="img-fluid rounded mt-1" style="max-height: 100px;"></a>` : ''}
                    <div class="d-flex gap-2 mt-1">
                        ${isExterno && temEmailResponsavel ? `
                            <button class="btn btn-sm btn-link text-primary p-0 small btn-send-email-comment" 
                                    data-comment-id="${c.id}" 
                                    title="Enviar para ${emailResponsavel}">
                                <i class="bi bi-envelope me-1"></i>Enviar email ao responsável
                            </button>
                        ` : ''}
                        <button class="btn btn-sm btn-link text-danger p-0 small btn-delete-comment" 
                                data-comment-id="${c.id}"
                                data-item-id="${itemId}">
                            <i class="bi bi-trash me-1"></i>Excluir
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        historyContainer.innerHTML = `
            <label class="form-label small text-muted mb-2">Histórico de Comentários</label>
            <div class="comments-list" style="max-height: 250px; overflow-y: auto;">
                ${html}
            </div>
        `;
    }

    async saveComment(itemId) {
        const textarea = this.container.querySelector(`#comment-input-${itemId}`);
        const commentsSection = this.container.querySelector(`#comments-${itemId}`);

        // Coleta dados do formulário
        const activeVisibilityTag = commentsSection?.querySelector('.comentario-tipo-tag.interno.active, .comentario-tipo-tag.externo.active');
        const visibilidade = activeVisibilityTag?.classList.contains('externo') ? 'externo' : 'interno';

        const activeTagOption = commentsSection?.querySelector('.comentario-tipo-tag.tag-option.active');
        const tag = activeTagOption ? activeTagOption.dataset.tag : null;
        const noshow = tag === 'No Show';

        if (!textarea) return;

        const texto = textarea.value.trim();

        // Verifica se service está disponível
        if (!this.hasService()) {
            console.warn('[ChecklistRenderer] Service não disponível para saveComment');
            if (window.showToast) window.showToast('Serviço de comentários não disponível', 'error');
            return;
        }

        // Delega para o service (validação + API call)
        const result = await this.service.saveComment(itemId, { texto, visibilidade, noshow, tag });

        if (result.success) {
            // Limpa formulário
            textarea.value = '';

            // Reset visibility tags - set Interno as active
            if (commentsSection) {
                commentsSection.querySelectorAll('.comentario-tipo-tag.interno, .comentario-tipo-tag.externo').forEach(t => t.classList.remove('active'));
                const internoTag = commentsSection.querySelector('.comentario-tipo-tag.interno');
                if (internoTag) internoTag.classList.add('active');
            }

            // Reset all tag options
            if (commentsSection) {
                commentsSection.querySelectorAll('.comentario-tipo-tag.tag-option').forEach(t => t.classList.remove('active'));
            }

            // Atualiza ícone de comentário
            const commentButton = this.container.querySelector(`.btn-comment-toggle[data-item-id="${itemId}"]`);
            if (commentButton) {
                const icon = commentButton.querySelector('i');
                if (icon) {
                    icon.className = 'bi bi-chat-left-text text-primary position-relative';
                    if (!icon.querySelector('.position-absolute')) {
                        icon.innerHTML += '<span class="position-absolute top-0 start-100 translate-middle p-1 bg-danger border border-light rounded-circle" style="font-size: 0.4rem;"></span>';
                    }
                }
            }

            // Recarrega comentários e timeline
            await this.loadComments(itemId);
            try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) { }
            try { if (typeof window.appendTimelineEvent === 'function') window.appendTimelineEvent('comentario_adicionado', `Comentário adicionado`); } catch (_) { }
        }
    }

    async sendCommentEmail(comentarioId) {
        // Delega para o service (confirmação + API call + notificação)
        await this.service.sendCommentEmail(comentarioId);
    }

    async deleteComment(comentarioId, itemId) {
        // Delega para o service (confirmação + API call)
        const result = await this.service.deleteComment(comentarioId);

        if (result.success) {
            // Recarrega comentários e atualiza timeline
            await this.loadComments(itemId);

            // Atualiza o indicador visual do botão de comentários
            this.updateCommentIndicator(itemId);

            try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) { }
            try { if (typeof window.appendTimelineEvent === 'function') window.appendTimelineEvent('comentario_excluido', `Comentário excluído`); } catch (_) { }
        }
    }

    updateCommentIndicator(itemId) {
        // Verifica se ainda há comentários no histórico
        const historyContainer = this.container.querySelector(`#comments-history-${itemId}`);
        const hasComments = historyContainer &&
            historyContainer.querySelectorAll('.comment-item').length > 0;

        // Atualiza o ícone do botão
        const button = this.container.querySelector(`.btn-comment-toggle[data-item-id="${itemId}"]`);
        if (button) {
            const icon = button.querySelector('i');
            if (icon) {
                // Atualiza classe de cor
                icon.classList.remove('text-primary', 'text-muted');
                icon.classList.add(hasComments ? 'text-primary' : 'text-muted');

                // Atualiza/remove indicador vermelho
                const indicator = icon.querySelector('.bg-danger');
                if (hasComments && !indicator) {
                    // Adiciona indicador
                    icon.innerHTML += '<span class="position-absolute top-0 start-100 translate-middle p-1 bg-danger border border-light rounded-circle" style="font-size: 0.4rem;"></span>';
                } else if (!hasComments && indicator) {
                    // Remove indicador
                    indicator.remove();
                }
            }
        }

        // Atualiza também o flatData para manter consistência
        if (this.flatData[itemId]) {
            this.flatData[itemId].comment = hasComments ? 'has_comment' : '';
        }
    }

    async deleteItem(itemId) {
        // Obtém título para confirmação
        const itemTitle = this.flatData[itemId]?.title || 'este item';

        // Mostra loading
        const itemEl = this.container.querySelector(`.checklist-item[data-item-id="${itemId}"]`);
        if (itemEl) {
            itemEl.style.opacity = '0.5';
            itemEl.style.pointerEvents = 'none';
        }

        // Delega para o service (confirmação + API call)
        const result = await this.service.deleteItem(itemId, itemTitle);

        if (result.success) {
            // Remove da DOM
            if (itemEl) {
                itemEl.remove();
            }

            // Remove do flatData
            if (this.flatData[itemId]) {
                const parentId = this.flatData[itemId].parentId;
                delete this.flatData[itemId];

                // Atualiza lista de filhos do pai
                if (parentId && this.flatData[parentId]) {
                    this.flatData[parentId].childrenIds = this.flatData[parentId].childrenIds.filter(id => id !== itemId);

                    // Se o pai ficou sem filhos, remove botão de expandir
                    if (this.flatData[parentId].childrenIds.length === 0) {
                        const parentEl = this.container.querySelector(`.checklist-item[data-item-id="${parentId}"]`);
                        if (parentEl) {
                            const expandBtn = parentEl.querySelector('.btn-expand');
                            if (expandBtn) expandBtn.remove();

                            const childrenContainer = parentEl.querySelector('.checklist-item-children');
                            if (childrenContainer) childrenContainer.remove();
                        }
                    }
                }
            }

            // Atualiza progresso
            if (result.progress !== undefined) {
                this.updateProgressDisplay(result.progress);
            } else {
                this.updateProgressFromLocalData();
            }

            // Atualiza timeline
            try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) { }
            try { if (typeof window.appendTimelineEvent === 'function') window.appendTimelineEvent('tarefa_excluida', `Tarefa excluída — ${itemTitle}`); } catch (_) { }

        } else if (!result.cancelled) {
            // Reverte UI se houve erro (não se foi cancelado)
            if (itemEl) {
                itemEl.style.opacity = '1';
                itemEl.style.pointerEvents = 'auto';
            }
        } else {
            // Cancelado - apenas reverte UI
            if (itemEl) {
                itemEl.style.opacity = '1';
                itemEl.style.pointerEvents = 'auto';
            }
        }
    }

    showToast(message, type = 'info', duration = 3000) {
        if (window.showToast) {
            window.showToast(message, type, duration);
        } else {
            alert(message);
        }
    }

    cancelComment(itemId) {
        const textarea = this.container.querySelector(`#comment-input-${itemId}`);
        if (textarea && this.flatData[itemId]) {
            textarea.value = this.flatData[itemId].comment || '';
        }

        const commentsSection = this.container.querySelector(`#comments-${itemId}`);
        if (commentsSection && window.bootstrap && bootstrap.Collapse) {
            const bsCollapse = bootstrap.Collapse.getInstance(commentsSection);
            if (bsCollapse) bsCollapse.hide();
        }
    }

    async reloadChecklist() {
        try {
            const response = await fetch(`/api/checklist/tree?implantacao_id=${this.implantacaoId}&format=nested`);
            const data = await response.json();

            if (data.ok && data.items) {
                const expandedIds = Array.from(this.expandedItems);

                this.data = data.items;

                this.flatData = {};
                this.buildFlatData(this.data);

                this.render();

                expandedIds.forEach(id => this.expandedItems.add(id));
                this.updateExpandedState();
            }
        } catch (error) {
        }
    }

    /**
     * Atualiza progresso global - usa dados locais para resposta imediata
     * @param {boolean} fetchFromServer - Se true, busca do servidor (mais lento but preciso)
     */
    async updateGlobalProgress(fetchFromServer = false) {
        // Primeiro, atualiza imediatamente com dados locais
        this.updateProgressFromLocalData();

        // Se solicitado, busca do servidor para garantir precisão
        if (fetchFromServer) {
            try {
                const response = await fetch(`/api/checklist/tree?implantacao_id=${this.implantacaoId}&format=flat`);
                const data = await response.json();

                if (data.ok && data.global_progress !== undefined) {
                    const progress = Math.round(data.global_progress);
                    this.updateProgressDisplay(progress);

                    if (data.items) {
                        data.items.forEach(item => {
                            if (item.progress_label) {
                                const progressBadge = this.container.querySelector(`[data-item-id="${item.id}"] .checklist-progress-badge`);
                                if (progressBadge) {
                                    progressBadge.textContent = item.progress_label;
                                }

                                // Atualizar barra de progresso do item
                                const progressBarItem = this.container.querySelector(`#progress-bar-${item.id}`);
                                if (progressBarItem && item.progress) {
                                    const percent = item.progress.completed / item.progress.total * 100;
                                    progressBarItem.style.width = `${percent}%`;
                                    progressBarItem.style.opacity = percent > 0 && percent < 100 ? '1' : '0';
                                }
                            }
                        });
                    }
                }
            } catch (error) {
            }
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Salva comentário com imagem (se houver)
     */
    async saveComment(itemId) {
        const textarea = document.getElementById(`comment-input-${itemId}`);
        const texto = textarea?.value?.trim();

        if (!texto) {
            this.notifier.warning('Digite um comentário');
            return;
        }

        // Pegar visibilidade (interno/externo)
        const visibilityTag = document.querySelector(`.comentario-tipo-tag.interno.active[data-item-id="${itemId}"], .comentario-tipo-tag.externo.active[data-item-id="${itemId}"]`);
        const visibilidade = visibilityTag?.dataset?.tipo || 'interno';

        // Pegar tag opcional (Ação interna, Reunião, No Show, Simples registro)
        const tagOption = document.querySelector(`.comentario-tipo-tag.tag-option.active[data-item-id="${itemId}"]`);
        const tag = tagOption?.dataset?.tag || null;

        // Pegar arquivo de imagem (se houver)
        const fileInput = document.querySelector(`.comentario-imagem-input[data-item-id="${itemId}"]`);
        const imageFile = fileInput?.files?.[0] || null;

        const commentData = {
            texto,
            visibilidade,
            tag,
            noshow: tag === 'No Show'
        };

        // Salvar via service (que vai converter imagem para base64)
        const result = await this.service.saveComment(itemId, commentData, imageFile);

        if (result.success) {
            // Limpar formulário
            textarea.value = '';
            this.removeImagePreview(itemId);

            // Recarregar comentários
            await this.loadComments(itemId);
        }
    }

    /**
     * Cancela edição de comentário
     */
    cancelComment(itemId) {
        const textarea = document.getElementById(`comment-input-${itemId}`);
        if (textarea) textarea.value = '';
        this.removeImagePreview(itemId);
    }

    /**
     * Carrega e exibe comentários de um item
     */
    async loadComments(itemId) {
        const historyContainer = document.getElementById(`comments-history-${itemId}`);
        if (!historyContainer) return;

        // Mostrar loading
        historyContainer.innerHTML = `
            <div class="text-center py-2">
                <div class="spinner-border spinner-border-sm text-secondary" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
            </div>
        `;

        const result = await this.service.loadComments(itemId);

        if (result.success) {
            const comentarios = result.comentarios || [];

            if (comentarios.length === 0) {
                historyContainer.innerHTML = `
                    <div class="text-center py-3 text-muted small">
                        <i class="bi bi-chat-dots"></i> Nenhum comentário ainda
                    </div>
                `;
                return;
            }

            // Renderizar comentários
            historyContainer.innerHTML = comentarios.map(c => this.renderComment(c)).join('');
        } else {
            historyContainer.innerHTML = `
                <div class="text-center py-2 text-danger small">
                    Erro ao carregar comentários
                </div>
            `;
        }
    }

    /**
     * Renderiza um comentário
     */
    renderComment(c) {
        const isInterno = c.visibilidade === 'interno';
        const badgeClass = isInterno ? 'bg-primary' : 'bg-info';
        const badgeIcon = isInterno ? 'lock-fill' : 'globe';
        const badgeText = isInterno ? 'Interno' : 'Externo';

        return `
            <div class="comment-item border-start border-3 ${isInterno ? 'border-primary' : 'border-info'} ps-2 mb-2">
                <div class="d-flex justify-content-between align-items-start mb-1">
                    <div>
                        <strong class="small">${this.escapeHtml(c.usuario_nome || 'Usuário')}</strong>
                        <span class="badge rounded-pill small ${badgeClass} ms-1">
                            <i class="bi bi-${badgeIcon}"></i> ${badgeText}
                        </span>
                        ${c.tag === 'Ação interna' ? '<span class="badge rounded-pill small bg-primary"><i class="bi bi-briefcase"></i> Ação interna</span>' : ''}
                        ${c.tag === 'Reunião' ? '<span class="badge rounded-pill small bg-danger"><i class="bi bi-calendar-event"></i> Reunião</span>' : ''}
                        ${(c.tag === 'No Show' || c.noshow) ? '<span class="badge rounded-pill small bg-warning text-dark"><i class="bi bi-calendar-x"></i> No show</span>' : ''}
                        ${c.tag === 'Simples registro' ? '<span class="badge rounded-pill small bg-secondary"><i class="bi bi-pencil-square"></i> Simples registro</span>' : ''}
                    </div>
                    <small class="text-muted">${c.data_criacao || ''}</small>
                </div>
                <p class="mb-1 small">${this.escapeHtml(c.texto)}</p>
                ${c.imagem_url ? `
                    <div class="mt-2">
                        <img src="${c.imagem_url}" 
                             class="img-thumbnail comment-image-thumbnail" 
                             style="max-width: 200px; max-height: 150px; cursor: pointer;"
                             onclick="window.checklistRenderer.openImageModal(\'${c.imagem_url}\')"
                             title="Clique para ampliar">
                    </div>
                ` : ''}
                <div class="d-flex gap-2 mt-1">
                    <button class="btn btn-sm btn-link text-danger p-0 btn-delete-comment" 
                            data-comment-id="${c.id}" 
                            data-item-id="${c.checklist_item_id || c.tarefa_id}">
                        <i class="bi bi-trash"></i> Excluir
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Deleta comentário
     */
    async deleteComment(comentarioId, itemId) {
        const result = await this.service.deleteComment(comentarioId);

        if (result.success) {
            // Recarregar comentários
            await this.loadComments(itemId);
        }
    }

    /**
     * Envia comentário por email
     */
    async sendCommentEmail(comentarioId) {
        await this.service.sendCommentEmail(comentarioId);
    }

    /**
     * Deleta comentário e recarrega lista
     */
    async deleteComment(comentarioId, itemId) {
        const result = await this.service.deleteComment(comentarioId);

        if (result.success) {
            // Recarregar comentários imediatamente
            await this.loadComments(itemId);
        }
    }

    /**
     * Envia comentário por email
     */
    async sendCommentEmail(comentarioId) {
        await this.service.sendCommentEmail(comentarioId);
    }

    /**
     * Abre modal com imagem ampliada
     */
    openImageModal(imageUrl, caption = '') {
        // Criar modal dinamicamente se não existir
        let modal = document.getElementById('imageModal');
        if (!modal) {
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

            // Adicionar event listener para limpar o modal quando fechado
            modal.addEventListener('hidden.bs.modal', function () {
                // Remover backdrop manualmente se ainda existir
                const backdrops = document.querySelectorAll('.modal-backdrop');
                backdrops.forEach(backdrop => backdrop.remove());

                // Restaurar scroll do body
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';

                // Limpar a imagem para liberar memória
                const img = document.getElementById('modalImage');
                if (img) img.src = '';
            });
        }

        // Atualizar imagem
        const img = document.getElementById('modalImage');
        if (img) img.src = imageUrl;

        // Abrir modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }

    /**
     * Remove preview de imagem
     */
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

    /**
     * Configura handlers de upload de imagem
     */
    setupImageUploadHandlers() {
        // Delegar evento para inputs de imagem
        this.container.addEventListener('change', (e) => {
            if (e.target.classList.contains('comentario-imagem-input')) {
                const itemId = e.target.dataset.itemId;
                const file = e.target.files[0];

                if (file && file.type.startsWith('image/')) {
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
                    };
                    reader.readAsDataURL(file);
                }
            }
        });

        // Suporte para colar imagens (Ctrl+V)
        this.container.addEventListener('paste', (e) => {
            const target = e.target;
            if (target.id && target.id.startsWith('comment-input-')) {
                const itemId = target.id.replace('comment-input-', '');
                const items = e.clipboardData?.items;

                if (items) {
                    for (let i = 0; i < items.length; i++) {
                        if (items[i].type.indexOf('image') !== -1) {
                            e.preventDefault();
                            const blob = items[i].getAsFile();

                            // Criar um FileReader para ler a imagem
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

                                // Simular que o arquivo foi selecionado
                                const fileInput = document.querySelector(`.comentario-imagem-input[data-item-id="${itemId}"]`);
                                if (fileInput) {
                                    // Criar um DataTransfer para adicionar o arquivo ao input
                                    const dataTransfer = new DataTransfer();
                                    dataTransfer.items.add(blob);
                                    fileInput.files = dataTransfer.files;
                                }
                            };
                            reader.readAsDataURL(blob);
                            break;
                        }
                    }
                }
            }
        });

        // Carregar comentários quando a seção é aberta
        this.container.addEventListener('shown.bs.collapse', (e) => {
            if (e.target.id && e.target.id.startsWith('comments-')) {
                const itemId = parseInt(e.target.id.replace('comments-', ''));
                if (itemId) {
                    this.loadComments(itemId);

                    // Abrir modal ao clicar em imagens de comentários
                    this.container.addEventListener('click', (e) => {
                        if (e.target.classList.contains('comment-image-thumbnail')) {
                            const imageUrl = e.target.getAttribute('src');
                            if (imageUrl) {
                                this.openImageModal(imageUrl);
                            }
                        }
                    });
                }
            }
        });
    }

    abbrevResponsavel(str) {
        if (!str) return '';
        const s = String(str);
        if (s.includes('@')) {
            const [local, domain] = s.split('@');
            const baseDomain = (domain || '').split('.')[0] || domain || '';
            const shortDomain = baseDomain.length > 5 ? baseDomain.slice(0, 5) + '...' : baseDomain + (baseDomain ? '' : '');
            return `${local}@${shortDomain}`;
        }
        return s;
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('checklist-container');
    if (container && window.IMPLANTACAO_ID) {
        window.checklistRenderer = new ChecklistRenderer('checklist-container', window.IMPLANTACAO_ID);
    }
});



