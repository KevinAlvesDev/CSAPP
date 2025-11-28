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
        this.flatData = {}; // Cache de dados planos para propagação rápida
        this.isLoading = false;
        
        if (!this.container) {
            console.error(`Container #${containerId} não encontrado`);
            return;
        }
        
        this.init();
    }
    
    init() {
        if (!this.data || this.data.length === 0) {
            this.renderEmpty();
            return;
        }
        
        // Construir estrutura plana para propagação rápida
        this.buildFlatData(this.data);
        
        this.render();
        this.updateGlobalProgress();
        this.attachEventListeners();
        
        // Expandir primeira fase por padrão
        if (this.data.length > 0 && this.data[0]) {
            this.toggleExpand(this.data[0].id, false);
        }
    }
    
    /**
     * Constrói estrutura plana (flatData) para acesso rápido durante propagação
     */
    buildFlatData(nodes, parentId = null) {
        nodes.forEach(node => {
            this.flatData[node.id] = {
                ...node,
                parentId: parentId,
                childrenIds: node.children ? node.children.map(c => c.id) : []
            };
            
            if (node.children && node.children.length > 0) {
                this.buildFlatData(node.children, node.id);
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
        const hasChildren = item.children && item.children.length > 0;
        const isExpanded = this.expandedItems.has(item.id);
        const hasComment = item.comment && item.comment.trim().length > 0;
        const progressLabel = item.progress_label || null;
        
        // Ícones por nível (similar ao exemplo)
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
        
        // Status badge
        const statusClass = item.completed ? 'bg-success' : 'bg-warning';
        const statusText = item.completed ? 'Concluído' : 'Pendente';
        const statusIcon = item.completed ? 'bi-check-circle-fill' : 'bi-clock-fill';
        
        // Padding esquerdo baseado no nível (similar ao exemplo)
        const paddingLeft = `${(item.level || 0) * 1.5 + 0.5}rem`;
        
        return `
            <div class="checklist-item" data-item-id="${item.id}" data-level="${item.level || 0}">
                <div class="checklist-item-header position-relative" style="padding-left: ${paddingLeft};">
                    <!-- Barra de progresso (se tiver filhos) -->
                    ${hasChildren ? `
                        <div class="position-absolute bottom-0 left-0 h-1 progress-bar-item" 
                             style="width: 0%; background-color: #28a745; opacity: 0; transition: all 0.3s;"
                             id="progress-bar-${item.id}"></div>
                    ` : ''}
                    
                    <div class="d-flex align-items-center gap-2 py-2 px-3 hover-bg">
                        ${hasChildren ? `
                            <button class="btn-icon btn-expand p-1 border-0 bg-transparent" 
                                    data-item-id="${item.id}" 
                                    title="${isExpanded ? 'Colapsar' : 'Expandir'}">
                                <i class="bi ${isExpanded ? 'bi-chevron-down' : 'bi-chevron-right'} text-muted"></i>
                            </button>
                        ` : '<span class="btn-icon-placeholder" style="width: 24px;"></span>'}
                        
                        <input type="checkbox" 
                               class="checklist-checkbox form-check-input" 
                               id="checklist-${item.id}"
                               data-item-id="${item.id}"
                               ${item.completed ? 'checked' : ''}
                               style="cursor: pointer; width: 18px; height: 18px;">
                        
                        <i class="bi ${iconClass} ${iconColor}" style="font-size: 1.1rem;"></i>
                        
                        <label class="checklist-item-title flex-grow-1 mb-0 cursor-pointer" 
                               for="checklist-${item.id}"
                               style="${item.completed ? 'text-decoration: line-through; color: #6c757d;' : ''}">
                            ${this.escapeHtml(item.title)}
                        </label>
                        
                        ${progressLabel ? `
                            <span class="checklist-progress-badge badge bg-light text-dark ms-2" style="font-size: 0.75rem;">
                                ${progressLabel}
                            </span>
                        ` : ''}
                        
                        <span class="badge ${statusClass} ms-2" id="status-badge-${item.id}">
                            <i class="bi ${statusIcon} me-1"></i>${statusText}
                        </span>
                        
                        <button class="btn-icon btn-comment-toggle p-1 border-0 bg-transparent ms-2" 
                                data-item-id="${item.id}" 
                                title="Comentários">
                            <i class="bi bi-chat-left-text ${hasComment ? 'text-primary' : 'text-muted'} position-relative">
                                ${hasComment ? '<span class="position-absolute top-0 start-100 translate-middle p-1 bg-danger border border-light rounded-circle" style="font-size: 0.4rem;"></span>' : ''}
                            </i>
                        </button>
                    </div>
                </div>
                
                ${hasChildren ? `
                    <div class="checklist-item-children ${isExpanded ? '' : 'd-none'}" 
                         data-item-id="${item.id}"
                         style="transition: all 0.3s ease;">
                        ${this.renderTree(item.children)}
                    </div>
                ` : ''}
                
                <!-- Seção de Comentários (Collapse Bootstrap) -->
                <div class="checklist-comments-section collapse" id="comments-${item.id}">
                    <div class="checklist-comment-form p-3 bg-light border-top">
                        <label class="form-label small text-muted mb-1">Comentários / Observações</label>
                        <textarea class="form-control form-control-sm" 
                                  id="comment-input-${item.id}" 
                                  rows="2"
                                  placeholder="Escreva uma observação para este item...">${item.comment || ''}</textarea>
                        <div class="d-flex justify-content-end gap-2 mt-2">
                            <button class="btn btn-sm btn-secondary btn-cancel-comment" data-item-id="${item.id}">
                                Cancelar
                            </button>
                            <button class="btn btn-sm btn-primary btn-save-comment" data-item-id="${item.id}">
                                <i class="bi bi-send me-1"></i>Salvar Nota
                            </button>
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
        // Toggle expand/collapse
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.btn-expand')) {
                const button = e.target.closest('.btn-expand');
                const itemId = parseInt(button.dataset.itemId);
                this.toggleExpand(itemId);
            }
        });
        
        // Toggle checkbox
        this.container.addEventListener('change', (e) => {
            if (e.target.classList.contains('checklist-checkbox')) {
                const itemId = parseInt(e.target.dataset.itemId);
                const checked = e.target.checked;
                this.handleCheck(itemId, checked);
            }
        });
        
        // Toggle comentários
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.btn-comment-toggle')) {
                const button = e.target.closest('.btn-comment-toggle');
                const itemId = parseInt(button.dataset.itemId);
                this.toggleComments(itemId);
            }
        });
        
        // Salvar comentário
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
        });
    }
    
    toggleExpand(itemId, animate = true) {
        if (this.expandedItems.has(itemId)) {
            this.expandedItems.delete(itemId);
        } else {
            this.expandedItems.add(itemId);
        }
        this.updateExpandedState(itemId, animate);
    }
    
    updateExpandedState(itemId = null, animate = true) {
        if (itemId) {
            // Atualizar apenas o item específico (melhor performance)
            const children = this.container.querySelector(`.checklist-item-children[data-item-id="${itemId}"]`);
            const button = this.container.querySelector(`.btn-expand[data-item-id="${itemId}"]`);
            
            if (children) {
                if (this.expandedItems.has(itemId)) {
                    children.classList.remove('d-none');
                    if (button) {
                        const icon = button.querySelector('i');
                        if (icon) icon.className = 'bi bi-chevron-down text-muted';
                    }
                } else {
                    children.classList.add('d-none');
                    if (button) {
                        const icon = button.querySelector('i');
                        if (icon) icon.className = 'bi bi-chevron-right text-muted';
                    }
                }
            }
        } else {
            // Atualizar todos (apenas na inicialização)
            this.expandedItems.forEach(id => {
                const children = this.container.querySelector(`.checklist-item-children[data-item-id="${id}"]`);
                const button = this.container.querySelector(`.btn-expand[data-item-id="${id}"]`);
                if (children) {
                    children.classList.remove('d-none');
                    if (button) {
                        const icon = button.querySelector('i');
                        if (icon) icon.className = 'bi bi-chevron-down text-muted';
                    }
                }
            });
        }
    }
    
    /**
     * Manipula mudança de checkbox com propagação (cascata e bolha)
     */
    async handleCheck(itemId, completed) {
        if (this.isLoading) return;
        
        const checkbox = this.container.querySelector(`#checklist-${itemId}`);
        if (!checkbox) return;
        
        // Desabilitar checkbox durante operação
        checkbox.disabled = true;
        this.isLoading = true;
        
        try {
            // Chamar API para fazer toggle com propagação
            const response = await fetch(`/api/checklist/toggle/${itemId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ completed })
            });
            
            const data = await response.json();
            
            if (data.ok) {
                // Backend já fez toda a propagação via SQL CTE
                // Recarregar dados atualizados do servidor para garantir consistência
                await this.reloadChecklist();
                
                // Atualizar progresso global
                await this.updateGlobalProgress();
                
                // Atualizar progresso global da página principal se houver função externa
                if (window.updateProgressBar && typeof window.updateProgressBar === 'function') {
                    window.updateProgressBar(data.progress || 0);
                }
            } else {
                throw new Error(data.error || 'Erro ao alterar status');
            }
        } catch (error) {
            console.error('Erro ao fazer toggle:', error);
            alert(`Erro: ${error.message}`);
            checkbox.checked = !completed; // Reverter checkbox
        } finally {
            checkbox.disabled = false;
            this.isLoading = false;
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
                this.propagateDown(childId, status);
            }
        });
    }
    
    /**
     * Propaga status para cima (bolha) - pai atualiza baseado nos filhos
     */
    propagateUp(itemId, visited = new Set()) {
        if (!itemId || visited.has(itemId)) return; // Evitar loops
        
        visited.add(itemId);
        
        const node = this.flatData[itemId];
        if (!node || !node.parentId) return;
        
        const parentNode = this.flatData[node.parentId];
        if (!parentNode || !parentNode.childrenIds || parentNode.childrenIds.length === 0) return;
        
        // Verificar status dos filhos
        const children = parentNode.childrenIds
            .map(id => this.flatData[id])
            .filter(c => c !== undefined);
        
        if (children.length === 0) return;
        
        const allChecked = children.every(c => c.completed === true);
        const someChecked = children.some(c => c.completed === true);
        
        // Atualizar pai
        const oldStatus = parentNode.completed;
        parentNode.completed = allChecked;
        
        // Continuar propagação para o avô se o status mudou
        if (oldStatus !== allChecked) {
            this.propagateUp(node.parentId, visited);
        }
    }
    
    /**
     * Atualiza UI de um item específico (sem re-render completo)
     */
    updateItemUI(itemId) {
        const node = this.flatData[itemId];
        if (!node) return;
        
        // Atualizar checkbox
        const checkbox = this.container.querySelector(`#checklist-${itemId}`);
        if (checkbox) {
            checkbox.checked = node.completed;
        }
        
        // Atualizar label (riscado)
        const label = this.container.querySelector(`label[for="checklist-${itemId}"]`);
        if (label) {
            if (node.completed) {
                label.style.textDecoration = 'line-through';
                label.style.color = '#6c757d';
            } else {
                label.style.textDecoration = 'none';
                label.style.color = '';
            }
        }
        
        // Atualizar badge de status
        const badge = this.container.querySelector(`#status-badge-${itemId}`);
        if (badge) {
            const statusClass = node.completed ? 'bg-success' : 'bg-warning';
            const statusText = node.completed ? 'Concluído' : 'Pendente';
            const statusIcon = node.completed ? 'bi-check-circle-fill' : 'bi-clock-fill';
            badge.className = `badge ${statusClass} ms-2`;
            badge.innerHTML = `<i class="bi ${statusIcon} me-1"></i>${statusText}`;
        }
    }
    
    /**
     * Atualiza UI dos filhos recursivamente
     */
    updateChildrenUI(itemId) {
        const node = this.flatData[itemId];
        if (!node || !node.childrenIds) return;
        
        node.childrenIds.forEach(childId => {
            this.updateItemUI(childId);
            this.updateChildrenUI(childId);
        });
    }
    
    /**
     * Atualiza UI do pai
     */
    updateParentUI(itemId) {
        const node = this.flatData[itemId];
        if (!node || !node.parentId) return;
        
        this.updateItemUI(node.parentId);
        this.updateParentUI(node.parentId);
    }
    
    toggleComments(itemId) {
        const commentsSection = this.container.querySelector(`#comments-${itemId}`);
        if (!commentsSection) return;
        
        // Usar Bootstrap Collapse
        if (window.bootstrap && bootstrap.Collapse) {
            const bsCollapse = new bootstrap.Collapse(commentsSection, {
                toggle: true
            });
        } else {
            // Fallback sem Bootstrap
            commentsSection.classList.toggle('show');
        }
    }
    
    async saveComment(itemId) {
        const textarea = this.container.querySelector(`#comment-input-${itemId}`);
        if (!textarea) return;
        
        const comment = textarea.value.trim();
        
        try {
            const response = await fetch(`/api/checklist/comment/${itemId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ comment })
            });
            
            const data = await response.json();
            
            if (data.ok) {
                // Atualizar dados locais
                if (this.flatData[itemId]) {
                    this.flatData[itemId].comment = comment;
                }
                
                // Atualizar ícone de comentário (sem re-render completo)
                const commentButton = this.container.querySelector(`.btn-comment-toggle[data-item-id="${itemId}"]`);
                if (commentButton) {
                    const icon = commentButton.querySelector('i');
                    if (icon) {
                        if (comment) {
                            icon.className = 'bi bi-chat-left-text text-primary position-relative';
                            // Adicionar indicador se não tiver
                            if (!icon.querySelector('.position-absolute')) {
                                icon.innerHTML += '<span class="position-absolute top-0 start-100 translate-middle p-1 bg-danger border border-light rounded-circle" style="font-size: 0.4rem;"></span>';
                            }
                        } else {
                            icon.className = 'bi bi-chat-left-text text-muted';
                            const indicator = icon.querySelector('.position-absolute');
                            if (indicator) indicator.remove();
                        }
                    }
                }
                
                // Colapsar seção de comentários
                const commentsSection = this.container.querySelector(`#comments-${itemId}`);
                if (commentsSection && window.bootstrap && bootstrap.Collapse) {
                    const bsCollapse = bootstrap.Collapse.getInstance(commentsSection);
                    if (bsCollapse) bsCollapse.hide();
                }
            } else {
                throw new Error(data.error || 'Erro ao salvar comentário');
            }
        } catch (error) {
            console.error('Erro ao salvar comentário:', error);
            alert(`Erro: ${error.message}`);
        }
    }
    
    cancelComment(itemId) {
        // Restaurar valor original
        const textarea = this.container.querySelector(`#comment-input-${itemId}`);
        if (textarea && this.flatData[itemId]) {
            textarea.value = this.flatData[itemId].comment || '';
        }
        
        // Colapsar seção
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
                // Preservar estado expandido antes de recarregar
                const expandedIds = Array.from(this.expandedItems);
                
                // Atualizar dados
                this.data = data.items;
                
                // Reconstruir flatData
                this.flatData = {};
                this.buildFlatData(this.data);
                
                // Re-renderizar
                this.render();
                
                // Restaurar estado expandido
                expandedIds.forEach(id => this.expandedItems.add(id));
                this.updateExpandedState();
            }
        } catch (error) {
            console.error('Erro ao recarregar checklist:', error);
        }
    }
    
    async updateGlobalProgress() {
        try {
            const response = await fetch(`/api/checklist/tree?implantacao_id=${this.implantacaoId}&format=flat`);
            const data = await response.json();
            
            if (data.ok && data.global_progress !== undefined) {
                const progress = Math.round(data.global_progress);
                
                // Atualizar UI - buscar dentro do container ou no documento
                const progressPercent = this.container.querySelector('#checklist-global-progress-percent') || 
                                       document.querySelector('#checklist-global-progress-percent');
                const progressBar = this.container.querySelector('#checklist-global-progress-bar') || 
                                   document.querySelector('#checklist-global-progress-bar');
                
                if (progressPercent) {
                    progressPercent.textContent = `${progress}%`;
                }
                
                if (progressBar) {
                    progressBar.style.width = `${progress}%`;
                    progressBar.setAttribute('aria-valuenow', progress);
                    
                    // Mudar cor quando 100%
                    if (progress === 100) {
                        progressBar.classList.remove('bg-primary');
                        progressBar.classList.add('bg-success');
                    } else {
                        progressBar.classList.remove('bg-success');
                        progressBar.classList.add('bg-primary');
                    }
                }
                
                // Atualizar progresso de cada item com filhos
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
            console.error('Erro ao buscar progresso global:', error);
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('checklist-container');
    if (container && window.IMPLANTACAO_ID) {
        window.checklistRenderer = new ChecklistRenderer('checklist-container', window.IMPLANTACAO_ID);
    }
});
