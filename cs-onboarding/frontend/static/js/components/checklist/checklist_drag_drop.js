/**
 * CS Onboarding - Checklist Drag & Drop Component (Enhanced UX)
 * Handles all drag and drop interactions for checklist items with improved visual feedback.
 * 
 * @module components/checklist/ChecklistDragDrop
 */

class ChecklistDragDrop {
    constructor(renderer, container) {
        this.renderer = renderer;
        this.container = container;
        this.draggedItem = null;
        this.dragOverItem = null;
        this.dropIndicator = null;
        this.dropHint = null; // New: Textual hint tooltip
        this.dropPosition = null;

        this.init();
    }

    init() {
        // Create drop indicator element (Line)
        this.dropIndicator = document.createElement('div');
        this.dropIndicator.className = 'drop-indicator';
        this.dropIndicator.style.display = 'none';

        // Create drop hint element (Tooltip)
        this.dropHint = document.createElement('div');
        this.dropHint.className = 'drop-hint-tooltip';
        this.dropHint.style.display = 'none';

        // Ensure container is relative
        if (getComputedStyle(this.container).position === 'static') {
            this.container.style.position = 'relative';
        }

        this.container.appendChild(this.dropIndicator);
        document.body.appendChild(this.dropHint); // Body apppend to avoid overflow clipping

        // Bind events
        this.container.addEventListener('dragstart', this.handleDragStart.bind(this));
        this.container.addEventListener('dragend', this.handleDragEnd.bind(this));
        this.container.addEventListener('dragover', this.handleDragOver.bind(this));
        this.container.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.container.addEventListener('drop', this.handleDrop.bind(this));

        // Activate draggable only when pressing handle
        this.container.addEventListener('mousedown', (e) => {
            const handle = e.target.closest('.drag-handle');
            if (handle) {
                const item = handle.closest('.checklist-item');
                if (item) item.setAttribute('draggable', 'true');
            }
        });

        this.container.addEventListener('mouseup', (e) => {
            const item = e.target.closest('.checklist-item');
            if (item) item.setAttribute('draggable', 'false');
        });

        // Improve styling injection
        this.injectStyles();
    }

    injectStyles() {
        if (document.getElementById('checklist-dnd-styles-v2')) return;
        const style = document.createElement('style');
        style.id = 'checklist-dnd-styles-v2';
        style.textContent = `
            .drop-indicator {
                position: absolute;
                height: 4px;
                background-color: #0d6efd;
                border-radius: 4px;
                pointer-events: none;
                z-index: 1050;
                box-shadow: 0 0 4px rgba(13, 110, 253, 0.5);
                transition: top 0.1s ease, left 0.1s ease;
            }
            .drop-indicator::before, .drop-indicator::after {
                content: '';
                position: absolute;
                width: 10px;
                height: 10px;
                background-color: #0d6efd;
                border-radius: 50%;
                top: 50%;
                transform: translateY(-50%);
                box-shadow: 0 0 2px rgba(255,255,255,0.8);
            }
            .drop-indicator::before { left: -4px; }
            .drop-indicator::after { right: -4px; }

            .drop-hint-tooltip {
                position: fixed;
                background-color: #212529;
                color: #fff;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 0.85rem;
                font-weight: 500;
                z-index: 9999;
                pointer-events: none;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                max-width: 300px;
                white-space: normal;
                border: 1px solid rgba(255,255,255,0.1);
            }
            .drop-hint-tooltip strong { color: #6ea8fe; }

            .drag-over-inside > .checklist-item-header {
                background-color: rgba(13, 110, 253, 0.15) !important;
                border: 2px dashed #0d6efd !important;
                border-radius: 6px;
            }
            
            .checklist-item.dragging {
                background-color: #fff3cd !important;
                opacity: 0.6;
                border: 1px dashed #ffc107;
            }
            .drag-handle { cursor: grab; }
            .drag-handle:active { cursor: grabbing; }
        `;
        document.head.appendChild(style);
    }

    handleDragStart(e) {
        const item = e.target.closest('.checklist-item');
        if (!item || item.getAttribute('draggable') !== 'true') {
            e.preventDefault();
            return;
        }

        this.draggedItem = item;
        item.classList.add('dragging');

        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', item.dataset.itemId);

        // Hide standard drag image if possible to use our custom feedback, 
        // but for now keeping default ghost as fallback is safer cross-browser.
    }

    handleDragEnd(e) {
        if (this.draggedItem) {
            this.draggedItem.classList.remove('dragging');
            this.draggedItem.setAttribute('draggable', 'false');
        }

        // Clean up classes and elements
        this.container.querySelectorAll('.checklist-item').forEach(item => {
            item.classList.remove('drag-over-inside');
        });

        this.dropIndicator.style.display = 'none';
        this.dropHint.style.display = 'none';
        this.draggedItem = null;
        this.dragOverItem = null;
    }

    handleDragOver(e) {
        e.preventDefault(); // Necessary to allow dropping
        e.dataTransfer.dropEffect = 'move';

        const targetItem = e.target.closest('.checklist-item');

        // Safety checks
        if (!targetItem || targetItem === this.draggedItem) {
            this.hideIndicators();
            return;
        }

        // Prevent dropping onto a descendant (infinite loop)
        if (this.isDescendant(this.draggedItem, targetItem)) {
            e.dataTransfer.dropEffect = 'none';
            this.showHint(e, '🚫 Não pode mover para dentro do próprio filho', 'danger');
            this.dropIndicator.style.display = 'none';
            return;
        }

        this.dragOverItem = targetItem;

        // Calculate geometry
        const rect = targetItem.getBoundingClientRect();
        const y = e.clientY - rect.top;
        const header = targetItem.querySelector('.checklist-item-header');
        const headerHeight = header ? header.offsetHeight : 40;

        // Get Item Title for Hint
        const targetTitle = targetItem.querySelector('.checklist-item-title')?.textContent.trim() || 'item';
        const formattedTitle = targetTitle.length > 30 ? targetTitle.substring(0, 30) + '...' : targetTitle;

        // Clean previous state
        targetItem.classList.remove('drag-over-inside');

        const containerRect = this.container.getBoundingClientRect();
        const relativeTop = rect.top - containerRect.top;
        const relativeLeft = rect.left - containerRect.left;

        // Zones: Top 25% (Before), Bottom 25% (After), Middle 50% (Inside/Child)
        // Adjusted to make "Inside" easier to hit but not accidental
        const thresholdTop = headerHeight * 0.25;
        const thresholdBottom = headerHeight * 0.75;

        // Logic
        if (y < thresholdTop) {
            // BEFORE
            this.dropPosition = 'before';
            this.dropIndicator.className = 'drop-indicator';
            this.dropIndicator.style.top = `${relativeTop - 2}px`;
            this.dropIndicator.style.left = `${relativeLeft}px`;
            this.dropIndicator.style.width = `${rect.width}px`;
            this.dropIndicator.style.display = 'block';

            this.showHint(e, `⬆ Mover para <strong>ANTES</strong> de:<br>"${formattedTitle}"`);

        } else if (y > thresholdBottom) {
            // AFTER
            this.dropPosition = 'after';
            this.dropIndicator.className = 'drop-indicator';

            // Should account for children if expanded? 
            // If item is expanded, "After" visually means after all children.
            // But conceptually we are dropping as a sibling.
            // Visually let's put the bar at the bottom of the header.

            const childrenContainer = targetItem.querySelector('.checklist-item-children');
            const isExpanded = childrenContainer && !childrenContainer.classList.contains('d-none');
            const visualBottom = isExpanded ? headerHeight : rect.height; // Not actually used in calculation below but logic corrected

            // Correction: If we drop AFTER an expanded item, we usually mean "Use as next sibling of parent".
            // To drop as first child, use "Inside".
            // To drop as next sibling of this item (skipping children), visual cue should be at bottom of block.

            this.dropIndicator.style.top = `${relativeTop + rect.height - 2}px`;
            this.dropIndicator.style.left = `${relativeLeft}px`;
            this.dropIndicator.style.width = `${rect.width}px`;
            this.dropIndicator.style.display = 'block';

            this.showHint(e, `⬇ Mover para <strong>DEPOIS</strong> de:<br>"${formattedTitle}"`);

        } else {
            // INSIDE (Subtask)
            this.dropPosition = 'inside';
            this.dropIndicator.style.display = 'none';
            targetItem.classList.add('drag-over-inside');

            this.showHint(e, `↳ Transformar em <strong>SUBTAREFA</strong> de:<br>"${formattedTitle}"`);
        }
    }

    handleDragLeave(e) {
        // Only hide if we really left the item, not just entered a child
        const targetItem = e.target.closest('.checklist-item');
        if (targetItem && !targetItem.contains(e.relatedTarget)) {
            targetItem.classList.remove('drag-over-inside');
            // Don't hide hint immediately, handleDragOver of next item will update it
        }
    }

    hideIndicators() {
        this.dropIndicator.style.display = 'none';
        this.dropHint.style.display = 'none';
    }

    showHint(e, html, type = 'info') {
        this.dropHint.innerHTML = html;
        this.dropHint.style.display = 'block';

        // Better positioning to avoid clipping
        const tooltipWidth = this.dropHint.offsetWidth;
        const viewportWidth = window.innerWidth;
        const margin = 20;

        let x = e.clientX + 15;
        let y = e.clientY + 15;

        // If tooltip goes off-screen to the right, flip it to the left of the cursor
        if (x + tooltipWidth > viewportWidth - margin) {
            x = e.clientX - tooltipWidth - 15;
        }

        // If tooltip goes off-screen to the bottom, flip it above the cursor
        const tooltipHeight = this.dropHint.offsetHeight;
        if (y + tooltipHeight > window.innerHeight - margin) {
            y = e.clientY - tooltipHeight - 15;
        }

        this.dropHint.style.left = `${x}px`;
        this.dropHint.style.top = `${y}px`;

        this.dropHint.style.borderColor = type === 'danger' ? '#dc3545' : 'rgba(255,255,255,0.1)';
        this.dropHint.style.backgroundColor = type === 'danger' ? '#dc3545' : '#212529';
    }

    async handleDrop(e) {
        e.preventDefault();
        this.hideIndicators();

        const targetItem = e.target.closest('.checklist-item');
        if (!targetItem || targetItem === this.draggedItem || !this.draggedItem) {
            return;
        }

        if (this.isDescendant(this.draggedItem, targetItem)) {
            if (this.renderer.showToast) this.renderer.showToast('Não é possível mover para dentro de um item filho', 'warning');
            return;
        }

        const draggedId = parseInt(this.draggedItem.dataset.itemId);
        const targetId = parseInt(targetItem.dataset.itemId);
        const targetParentId = targetItem.dataset.parentId ? parseInt(targetItem.dataset.parentId) : null;

        let newParentId, newOrder;

        if (this.dropPosition === 'inside') {
            // Move inside target
            newParentId = targetId;
            newOrder = 0; // First child
        } else {
            // Move as sibling
            newParentId = targetParentId;

            const siblings = this.getSiblings(targetItem);
            const targetIndex = siblings.indexOf(targetItem);

            if (this.dropPosition === 'before') {
                newOrder = targetIndex;
            } else {
                newOrder = targetIndex + 1;
            }
        }

        // Call API
        await this.moveItem(draggedId, newParentId, newOrder);
    }

    isDescendant(parent, child) {
        if (!parent || !child) return false;
        if (parent.contains(child)) return true;
        return false;
    }

    getSiblings(item) {
        const parentId = item.dataset.parentId || '';
        let container;

        if (parentId) {
            const parent = this.container.querySelector(`[data-item-id="${parentId}"]`);
            container = parent ? parent.querySelector('.checklist-item-children') : null;
        } else {
            container = this.container.querySelector('#checklist-tree-root');
        }

        if (!container) return [];
        return Array.from(container.querySelectorAll(':scope > .checklist-item'));
    }

    async moveItem(itemId, newParentId, newOrder) {
        if (!this.renderer.service) {
            if (this.renderer.showToast) this.renderer.showToast('Serviço não disponível', 'error');
            return;
        }

        try {
            // Show loading
            const item = this.container.querySelector(`[data-item-id="${itemId}"]`);
            if (item) item.style.opacity = '0.5';

            // Show toast processing
            if (window.Notifier) window.Notifier.loading('Movendo item...');

            // Use the renderer's service API which we fixed to include moveItem
            const result = await this.renderer.service.moveItem(itemId, newParentId, newOrder);

            if (result.success) {
                if (window.Notifier) window.Notifier.success('Item movido com sucesso!');
                // Reload checklist
                if (this.renderer.reloadChecklist) await this.renderer.reloadChecklist();
            } else {
                throw new Error(result.error || 'Erro desconhecido');
            }
        } catch (error) {
            console.error('[MoveItem] Error:', error);
            if (window.Notifier) window.Notifier.error('Erro ao mover: ' + error.message);
            else if (this.renderer.showToast) this.renderer.showToast('Erro ao mover: ' + error.message, 'error');

            // Restore opacity
            const item = this.container.querySelector(`[data-item-id="${itemId}"]`);
            if (item) item.style.opacity = '';
        }
    }
}

window.ChecklistDragDrop = ChecklistDragDrop;
