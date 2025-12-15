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
        this.csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
        this.previsaoTermino = this.container?.dataset?.previsaoTermino || '';
        if (!this.csrfToken) {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) this.csrfToken = meta.getAttribute('content') || '';
            if (!this.csrfToken) {
                try {
                    const m = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
                    if (m) this.csrfToken = decodeURIComponent(m[1]);
                } catch(e) {}
            }
        }
        this._toggleThrottle = new Map();
        
        if (!this.container) {
            return;
        }
        
        this.init();
    }
    
    init() {
        if (!this.data || this.data.length === 0) {
            this.renderEmpty();
            return;
        }
        
        this.buildFlatData(this.data);
        
        this.render();
        this.attachEventListeners();
        
        // Render com todas as tarefas minimizadas por padrão (sem expandir nós inicialmente)
        
        this.updateProgressFromLocalData();
    }
    
    /**
     * Constrói estrutura plana (flatData) para acesso rápido durante propagação
     * Limita a 7 filhos por tarefa pai
     */
    buildFlatData(nodes, parentId = null) {
        nodes.forEach(node => {
            const limitedChildren = node.children && node.children.length > 0 ? node.children.slice(0, 7) : [];
            
            this.flatData[node.id] = {
                ...node,
                parentId: parentId,
                childrenIds: limitedChildren.map(c => c.id)
            };
            
            if (limitedChildren.length > 0) {
                this.buildFlatData(limitedChildren, node.id);
            }
        });
    }
    
    render() {
        const treeRoot = this.container.querySelector('#checklist-tree-root');
        if (!treeRoot) return;
        
        treeRoot.innerHTML = this.renderTree(this.data);
    }
    
    renderTree(items) {
        if (!items || items.length === 0) {
            return '<div class="text-muted text-center py-4">Nenhum item encontrado</div>';
        }
        
        return items.map(item => this.renderItem(item)).join('');
    }
    
    renderItem(item) {
        const limitedChildren = item.children && item.children.length > 0 ? item.children.slice(0, 7) : [];
        const hasChildren = limitedChildren.length > 0;
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
        
        return `
            <div id="checklist-item-${item.id}" class="checklist-item" data-item-id="${item.id}" data-level="${item.level || 0}">
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
                            <i class="bi ${iconClass} ${iconColor}" style="font-size: 1.1rem;"></i>
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
                        <span class="col-status">
                            <span class="badge badge-truncate ${statusClass}" id="status-badge-${item.id}" title="Status: ${statusText}" aria-label="Status: ${statusText}">
                                <i class="bi ${statusIcon} me-1" aria-hidden="true"></i>${statusText}
                                ${item.atrasada ? '<i class="bi bi-exclamation-triangle-fill" aria-hidden="true"></i>' : ''}
                            </span>
                        </span>
                        
                        <span class="col-comment">
                        <button class="btn-icon btn-comment-toggle p-1 border-0 bg-transparent" 
                                data-item-id="${item.id}" 
                                title="Comentários">
                            <i class="bi bi-chat-left-text ${hasComment ? 'text-primary' : 'text-muted'} position-relative">
                                ${hasComment ? '<span class="position-absolute top-0 start-100 translate-middle p-1 bg-danger border border-light rounded-circle" style="font-size: 0.4rem;"></span>' : ''}
                            </i>
                        </button>
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
                        ${this.renderTree(limitedChildren)}
                        ${item.children && item.children.length > 7 ? `
                            <div class="text-muted text-center py-2 px-3 small" style="font-style: italic;">
                                <i class="bi bi-info-circle me-1"></i>
                                Limite de 7 tarefas por camada. ${item.children.length - 7} tarefa(s) não exibida(s).
                            </div>
                        ` : ''}
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
                        <div class="d-flex align-items-center justify-content-between gap-2 mt-2">
                            <select class="form-select form-select-sm" id="comment-visibility-${item.id}" style="max-width: 140px;">
                                <option value="interno" selected>Interno</option>
                                <option value="externo">Externo</option>
                            </select>
                            <div class="d-flex gap-2">
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
                    <h6 class="text-muted mt-3">Nenhum plano aplicado</h6>
                    <p class="small text-muted mb-3">Selecione um plano de sucesso para visualizar a estrutura.</p>
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
        
        if (this.flatData[itemId]) {
            this.flatData[itemId].completed = completed;
            this.flatData[itemId].data_conclusao = completed ? new Date().toISOString() : null;
        }
        
        this.propagateDown(itemId, completed);
        this.propagateUp(itemId);
        this.updateAllItemsUI();
        this.updateProgressFromLocalData();
        
        try {
            const response = await fetch(`/api/checklist/toggle/${itemId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ completed })
            });
            
            const data = await response.json();
            
            if (data.ok) {
                const serverProgress = Math.round(data.progress || 0);
                this.updateProgressDisplay(serverProgress);
                
                if (window.updateProgressBar && typeof window.updateProgressBar === 'function') {
                    window.updateProgressBar(serverProgress);
                }
                try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) {}
                try { if (typeof window.appendTimelineEvent === 'function') window.appendTimelineEvent('tarefa_alterada', `Status: ${completed ? 'Concluída' : 'Pendente'} — ${(this.flatData[itemId] && this.flatData[itemId].title) || ''}`); } catch (_) {}
            } else {
                throw new Error(data.error || 'Erro ao alterar status');
            }
        } catch (error) {
            
            if (this.flatData[itemId]) {
                this.flatData[itemId].completed = !completed;
            }
            this.propagateDown(itemId, !completed);
            this.propagateUp(itemId);
            this.updateAllItemsUI();
            this.updateProgressFromLocalData();
            
            if (typeof this.showToast === 'function') this.showToast(`Erro: ${error.message}`, 'error'); else alert(`Erro: ${error.message}`);
        } finally {
            this.isLoading = false;
        }
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
                prevNova.classList.remove('bg-warning','text-dark');
                prevNova.classList.add('bg-danger','text-white');
                prevNova.setAttribute('title', `Nova previsão: ${node.nova_previsao}`);
                prevNova.textContent = this.formatDate(node.nova_previsao);
            } else {
                prevNova.classList.remove('d-none');
                prevNova.classList.remove('bg-danger','text-white');
                prevNova.classList.add('bg-warning','text-dark');
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
                concl.textContent = `Concl.: ${this.formatDate(node.data_conclusao)}`;
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
        
        try {
            const response = await fetch(`/api/checklist/comments/${itemId}`);
            const data = await response.json();
            
            if (data.ok) {
                this.renderCommentsHistory(itemId, data.comentarios, data.email_responsavel);
            } else {
                historyContainer.innerHTML = `<div class="text-danger small">${data.error || 'Erro ao carregar comentários'}</div>`;
            }
        } catch (error) {
            historyContainer.innerHTML = '<div class="text-danger small">Erro ao carregar comentários</div>';
        }
    }

    formatDate(dataStr) {
        if (!dataStr) return '';
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
            const csrf = this.csrfToken;
            try {
                const res = await fetch(`/api/checklist/item/${itemId}/responsavel`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                    body: JSON.stringify({ responsavel: novo })
                });
                const data = await res.json();
                if (data.ok) {
                    if (this.flatData[itemId]) this.flatData[itemId].responsavel = data.responsavel;
                    this.updateItemUI(itemId);
                    const m = bootstrap.Modal.getInstance(modal) || new bootstrap.Modal(modal);
                    m.hide();
                    if (typeof this.showToast === 'function') this.showToast('Responsável atualizado', 'success');
                    try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) {}
                    try { if (typeof window.appendTimelineEvent === 'function') window.appendTimelineEvent('responsavel_alterado', `Responsável: ${(current || '')} → ${data.responsavel} — ${(this.flatData[itemId] && this.flatData[itemId].title) || ''}`); } catch (_) {}
                } else {
                    if (typeof this.showToast === 'function') this.showToast(data.error || 'Erro ao atualizar responsável', 'error'); else alert(data.error || 'Erro ao atualizar responsável');
                }
            } catch (e) {
                if (typeof this.showToast === 'function') this.showToast('Erro ao atualizar responsável', 'error'); else alert('Erro ao atualizar responsável');
            }
        };
        const m = new bootstrap.Modal(modal);
        m.show();
        setTimeout(()=>input.focus(),100);
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
        input.value = current ? String(current).slice(0,10) : (this.flatData[itemId]?.previsao_original ? String(this.flatData[itemId].previsao_original).slice(0,10) : '');
        if (window.flatpickr) {
            if (input._flatpickr) input._flatpickr.destroy();
            window.flatpickr(input, { dateFormat: 'Y-m-d', altInput: true, altFormat: 'd/m/Y' });
        }
        const saveBtn = modal.querySelector('#prev-edit-save');
        saveBtn.onclick = async () => {
            const novo = input.value.trim();
            if (!novo) return;
            const csrf = this.csrfToken;
            const prevOld = this.flatData[itemId]?.nova_previsao || null;
            this.flatData[itemId] = this.flatData[itemId] || {};
            this.flatData[itemId].nova_previsao = novo;
            this.updateItemUI(itemId);
            const originalText = saveBtn.innerHTML;
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvando...';
            try {
                const res = await fetch(`/api/checklist/item/${itemId}/prazos`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                    body: JSON.stringify({ nova_previsao: novo })
                });
                const data = await res.json();
                if (data.ok) {
                    if (this.flatData[itemId]) {
                        this.flatData[itemId].nova_previsao = data.nova_previsao;
                        this.flatData[itemId].previsao_original = data.previsao_original || this.flatData[itemId].previsao_original;
                    }
                    this.updateItemUI(itemId);
                    const m = bootstrap.Modal.getInstance(modal) || new bootstrap.Modal(modal);
                    m.hide();
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = originalText;
                    if (typeof this.showToast === 'function') this.showToast('Prazo atualizado', 'success');
                    try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) {}
                    try { if (typeof window.appendTimelineEvent === 'function') window.appendTimelineEvent('prazo_alterado', `Nova previsão: ${data.nova_previsao} — ${(this.flatData[itemId] && this.flatData[itemId].title) || ''}`); } catch (_) {}
                } else {
                    this.flatData[itemId].nova_previsao = prevOld;
                    this.updateItemUI(itemId);
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = originalText;
                    if (typeof this.showToast === 'function') this.showToast(data.error || 'Erro ao atualizar prazo', 'error'); else alert(data.error || 'Erro ao atualizar prazo');
                }
            } catch (e) {
                this.flatData[itemId].nova_previsao = prevOld;
                this.updateItemUI(itemId);
                saveBtn.disabled = false;
                saveBtn.innerHTML = originalText;
                if (typeof this.showToast === 'function') this.showToast('Erro ao atualizar prazo', 'error'); else alert('Erro ao atualizar prazo');
            }
        };
        const m = new bootstrap.Modal(modal);
        m.show();
        setTimeout(()=>input.focus(),100);
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
            const csrf = this.csrfToken;
            const prev = this.flatData[itemId]?.tag || '';
            this.flatData[itemId] = this.flatData[itemId] || {};
            this.flatData[itemId].tag = novo;
            this.updateItemUI(itemId);
            const originalText = saveBtn.innerHTML;
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvando...';
            try {
                const res = await fetch(`/api/checklist/item/${itemId}/tag`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                    body: JSON.stringify({ tag: novo })
                });
                const data = await res.json();
                if (data.ok) {
                    if (this.flatData[itemId]) this.flatData[itemId].tag = data.tag;
                    this.updateItemUI(itemId);
                    const m = bootstrap.Modal.getInstance(modal) || new bootstrap.Modal(modal);
                    m.hide();
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = originalText;
                    if (typeof this.showToast === 'function') this.showToast('Tag atualizada', 'success');
                    try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) {}
                    try { if (typeof window.appendTimelineEvent === 'function') window.appendTimelineEvent('tag_alterada', `Tag: ${(prev||'')} → ${novo} — ${(this.flatData[itemId] && this.flatData[itemId].title) || ''}`); } catch (_) {}
                } else {
                    this.flatData[itemId].tag = prev;
                    this.updateItemUI(itemId);
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = originalText;
                    if (typeof this.showToast === 'function') this.showToast(data.error || 'Erro ao atualizar tag', 'error'); else alert(data.error || 'Erro ao atualizar tag');
                }
            } catch (e) {
                this.flatData[itemId].tag = prev;
                this.updateItemUI(itemId);
                saveBtn.disabled = false;
                saveBtn.innerHTML = originalText;
                if (typeof this.showToast === 'function') this.showToast('Erro ao atualizar tag', 'error'); else alert('Erro ao atualizar tag');
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
            const dataFormatada = c.data_criacao ? new Date(c.data_criacao).toLocaleString('pt-BR') : '';
            const visibilidadeClass = c.visibilidade === 'interno' ? 'bg-secondary' : 'bg-info text-dark';
            const isExterno = c.visibilidade === 'externo';
            const temEmailResponsavel = emailResponsavel && emailResponsavel.trim() !== '';
            
            return `
                <div class="comment-item border rounded p-2 mb-2 bg-white" data-comment-id="${c.id}">
                    <div class="d-flex justify-content-between align-items-start mb-1">
                        <div class="d-flex align-items-center gap-2">
                            <strong class="small"><i class="bi bi-person-fill me-1"></i>${this.escapeHtml(c.usuario_nome || c.usuario_cs)}</strong>
                            <span class="badge rounded-pill small ${visibilidadeClass}">${c.visibilidade}</span>
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
        const visibilitySelect = this.container.querySelector(`#comment-visibility-${itemId}`);
        if (!textarea) return;
        
        const texto = textarea.value.trim();
        const visibilidade = visibilitySelect ? visibilitySelect.value : 'interno';
        
        if (!texto) {
            if (typeof this.showToast === 'function') this.showToast('O texto do comentário é obrigatório', 'warning'); else alert('O texto do comentário é obrigatório');
            return;
        }
        
        try {
            const response = await fetch(`/api/checklist/comment/${itemId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ texto, visibilidade })
            });
            
            const data = await response.json();
            
            if (data.ok) {
                textarea.value = '';
                if (visibilitySelect) visibilitySelect.value = 'interno';
                
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
                
                await this.loadComments(itemId);
                try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) {}
                try { if (typeof window.appendTimelineEvent === 'function') window.appendTimelineEvent('novo_comentario', `Comentário criado — ${(this.flatData[itemId] && this.flatData[itemId].title) || ''}`); } catch (_) {}
                
            } else {
                throw new Error(data.error || 'Erro ao salvar comentário');
            }
        } catch (error) {
            if (typeof this.showToast === 'function') this.showToast(`Erro: ${error.message}`, 'error'); else alert(`Erro: ${error.message}`);
        }
    }
    
    async sendCommentEmail(comentarioId) {
        const proceed = window.confirmWithModal ? await window.confirmWithModal('Deseja enviar este comentário por e-mail ao responsável?') : confirm('Deseja enviar este comentário por e-mail ao responsável?');
        if (!proceed) {
            return;
        }
        
        try {
            const response = await fetch(`/api/checklist/comment/${comentarioId}/email`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                }
            });
            
            const data = await response.json();
            
            if (data.ok) {
                if (typeof this.showToast === 'function') this.showToast('Email enviado com sucesso!', 'success'); else alert('Email enviado com sucesso!');
            } else {
                throw new Error(data.error || 'Erro ao enviar email');
            }
        } catch (error) {
            if (typeof this.showToast === 'function') this.showToast(`Erro: ${error.message}`, 'error'); else alert(`Erro: ${error.message}`);
        }
    }
    
    async deleteComment(comentarioId, itemId) {
        const proceedDel = window.confirmWithModal ? await window.confirmWithModal('Deseja excluir este comentário?') : confirm('Deseja excluir este comentário?');
        if (!proceedDel) {
            return;
        }
        
        try {
            const response = await fetch(`/api/checklist/comment/${comentarioId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                }
            });
            
            const data = await response.json();
            
            if (data.ok) {
                await this.loadComments(itemId);
                try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) {}
                try { if (typeof window.appendTimelineEvent === 'function') window.appendTimelineEvent('comentario_excluido', `Comentário excluído — ${(this.flatData[itemId] && this.flatData[itemId].title) || ''}`); } catch (_) {}
            } else {
                throw new Error(data.error || 'Erro ao excluir comentário');
            }
        } catch (error) {
            if (typeof this.showToast === 'function') this.showToast(`Erro: ${error.message}`, 'error'); else alert(`Erro: ${error.message}`);
        }
    }

    async deleteItem(itemId) {
        let confirmed = false;
        if (window.confirmWithModal) {
            confirmed = await window.confirmWithModal('Tem certeza que deseja excluir esta tarefa e todos os seus subitens? Esta ação não pode ser desfeita.');
        } else {
            confirmed = confirm('Tem certeza que deseja excluir esta tarefa e todos os seus subitens? Esta ação não pode ser desfeita.');
        }
        
        if (!confirmed) return;
        
        // Mostrar loading ou desabilitar botão?
        const itemEl = this.container.querySelector(`.checklist-item[data-item-id="${itemId}"]`);
        if (itemEl) {
            itemEl.style.opacity = '0.5';
            itemEl.style.pointerEvents = 'none';
        }
        
        try {
            const response = await fetch(`/api/checklist/delete/${itemId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                }
            });
            
            const data = await response.json();
            
            if (data.ok) {
                // Remover o item da DOM
                if (itemEl) {
                    itemEl.remove();
                }
                
                // Remover do flatData
                if (this.flatData[itemId]) {
                    const parentId = this.flatData[itemId].parentId;
                    delete this.flatData[itemId];
                    
                    // Atualizar lista de filhos do pai
                    if (parentId && this.flatData[parentId]) {
                        this.flatData[parentId].childrenIds = this.flatData[parentId].childrenIds.filter(id => id !== itemId);
                        
                        // Se o pai ficou sem filhos, atualizar UI do pai (remover ícone de expandir)
                        if (this.flatData[parentId].childrenIds.length === 0) {
                            const parentEl = this.container.querySelector(`.checklist-item[data-item-id="${parentId}"]`);
                            if (parentEl) {
                                // Forçar re-render do pai ou atualizar classes manualmente
                                // Simplificando: Recarregar checklist se estrutura mudou muito
                                // Mas vamos tentar atualizar manualmente primeiro
                                const expandBtn = parentEl.querySelector('.btn-expand');
                                if (expandBtn) expandBtn.remove(); // Remove botão expandir
                                
                                const childrenContainer = parentEl.querySelector('.checklist-item-children');
                                if (childrenContainer) childrenContainer.remove();
                            }
                        }
                    }
                }
                
                // Atualizar progresso
                if (data.progress !== undefined) {
                    this.updateProgressDisplay(data.progress);
                } else {
                    this.updateProgressFromLocalData();
                }
                
                try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) {}
                try { if (typeof window.appendTimelineEvent === 'function') window.appendTimelineEvent('tarefa_excluida', `Tarefa excluída — ${(this.flatData[itemId] && this.flatData[itemId].title) || ''}`); } catch (_) {}
                
            } else {
                throw new Error(data.error || 'Erro ao excluir tarefa');
            }
        } catch (error) {
            if (typeof this.showToast === 'function') this.showToast(`Erro: ${error.message}`, 'error'); else alert(`Erro: ${error.message}`);
            if (itemEl) {
                itemEl.style.opacity = '1';
                itemEl.style.pointerEvents = 'auto';
            }
        }
    }

    showToast(message, type='info', duration=3000) {
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
     * @param {boolean} fetchFromServer - Se true, busca do servidor (mais lento mas preciso)
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
