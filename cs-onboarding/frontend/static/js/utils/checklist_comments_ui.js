/**
 * Melhorias de UX para Comentários do Checklist
 * Solução para o problema de identificação quando múltiplas caixas de comentários estão abertas
 */

(function () {
    'use strict';

    // Contador de comentários abertos
    let openCommentsCount = 0;
    const openCommentsSections = new Set();

    /**
     * Atualiza o cabeçalho da seção de comentários com o título da tarefa
     */
    function updateCommentSectionHeader(itemId) {
        const commentsSection = document.getElementById(`comments-${itemId}`);
        if (!commentsSection) return;

        const commentForm = commentsSection.querySelector('.checklist-comment-form');
        if (!commentForm) return;

        // Verificar se já existe o cabeçalho
        if (commentForm.querySelector('.comment-task-header')) return;

        // Obter o título da tarefa
        const itemElement = document.getElementById(`checklist-item-${itemId}`);
        if (!itemElement) return;

        const titleElement = itemElement.querySelector('.checklist-item-title');
        if (!titleElement) return;

        const taskTitle = titleElement.textContent.trim();

        // Criar o cabeçalho
        const header = document.createElement('div');
        header.className = 'comment-task-header mb-3 pb-2';
        header.innerHTML = `
            <div class="task-title-label">
                <i class="bi bi-chat-left-text text-primary"></i>
                <strong>Comentários da tarefa:</strong>
            </div>
            <div class="task-title-text">${escapeHtml(taskTitle)}</div>
        `;

        // Inserir no início do formulário
        commentForm.insertBefore(header, commentForm.firstChild);
    }

    /**
     * Adiciona destaque visual à tarefa quando a seção de comentários está aberta
     */
    function highlightTaskWithOpenComments(itemId, isOpen) {
        const itemElement = document.getElementById(`checklist-item-${itemId}`);
        if (!itemElement) return;

        if (isOpen) {
            itemElement.classList.add('comment-section-open');
            openCommentsSections.add(itemId);
        } else {
            itemElement.classList.remove('comment-section-open');
            openCommentsSections.delete(itemId);
        }

        updateOpenCommentsCounter();
    }

    /**
     * Scroll suave até a seção de comentários aberta
     */
    function scrollToCommentSection(itemId) {
        const commentsSection = document.getElementById(`comments-${itemId}`);
        if (!commentsSection) return;

        // Aguardar a animação de abertura
        setTimeout(() => {
            const rect = commentsSection.getBoundingClientRect();
            const isVisible = rect.top >= 0 && rect.bottom <= window.innerHeight;

            if (!isVisible) {
                commentsSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'nearest'
                });

                // Adicionar highlight temporário
                const itemElement = document.getElementById(`checklist-item-${itemId}`);
                if (itemElement) {
                    itemElement.classList.add('scroll-highlight');
                    setTimeout(() => {
                        itemElement.classList.remove('scroll-highlight');
                    }, 1500);
                }
            }
        }, 350); // Tempo da animação de collapse
    }

    /**
     * Atualiza o contador de comentários abertos
     */
    function updateOpenCommentsCounter() {
        const count = openCommentsSections.size;
        let badge = document.getElementById('comments-open-badge');

        if (count > 1) {
            if (!badge) {
                badge = document.createElement('div');
                badge.id = 'comments-open-badge';
                badge.className = 'comments-open-badge';
                document.body.appendChild(badge);
            }

            badge.innerHTML = `
                <i class="bi bi-chat-dots-fill"></i>
                <span><span class="badge-count">${count}</span> caixas de comentários abertas</span>
                <button class="btn btn-sm btn-light ms-2" onclick="window.closeAllCommentSections()" title="Fechar todas">
                    <i class="bi bi-x-lg"></i>
                </button>
            `;
            badge.classList.add('visible');
        } else {
            if (badge) {
                badge.classList.remove('visible');
                setTimeout(() => {
                    if (openCommentsSections.size <= 1 && badge.parentNode) {
                        badge.remove();
                    }
                }, 300);
            }
        }
    }

    /**
     * Fecha todas as seções de comentários abertas
     */
    window.closeAllCommentSections = function () {
        openCommentsSections.forEach(itemId => {
            const commentsSection = document.getElementById(`comments-${itemId}`);
            if (commentsSection && commentsSection.classList.contains('show')) {
                const bsCollapse = window.bootstrap?.Collapse.getInstance(commentsSection);
                if (bsCollapse) {
                    bsCollapse.hide();
                } else {
                    commentsSection.classList.remove('show');
                }
            }
        });
        openCommentsSections.clear();
        updateOpenCommentsCounter();
    };

    /**
     * Escape HTML para prevenir XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Intercepta a abertura/fechamento de seções de comentários
     */
    function setupCommentSectionObserver() {
        // Observer para detectar mudanças nas classes dos elementos
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    const element = mutation.target;
                    if (element.classList.contains('checklist-comments-section')) {
                        const itemId = element.id.replace('comments-', '');
                        const isOpen = element.classList.contains('show');

                        highlightTaskWithOpenComments(itemId, isOpen);

                        if (isOpen) {
                            updateCommentSectionHeader(itemId);
                            scrollToCommentSection(itemId);
                        }
                    }
                }
            });
        });

        // Observar todas as seções de comentários
        const commentsSections = document.querySelectorAll('.checklist-comments-section');
        commentsSections.forEach(section => {
            observer.observe(section, {
                attributes: true,
                attributeFilter: ['class']
            });
        });

        // Também observar novos elementos adicionados ao DOM
        const containerObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1 && node.classList?.contains('checklist-comments-section')) {
                        observer.observe(node, {
                            attributes: true,
                            attributeFilter: ['class']
                        });
                    }
                });
            });
        });

        const container = document.getElementById('checklist-tree-root');
        if (container) {
            containerObserver.observe(container, {
                childList: true,
                subtree: true
            });
        }
    }

    /**
     * Adiciona atalho de teclado para fechar todas as caixas
     */
    function setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // ESC para fechar todas as caixas de comentários
            if (e.key === 'Escape' && openCommentsSections.size > 0) {
                window.closeAllCommentSections();
            }
        });
    }

    /**
     * Inicialização
     */
    function init() {
        // Aguardar o DOM estar pronto
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setupCommentSectionObserver();
                setupKeyboardShortcuts();
            });
        } else {
            setupCommentSectionObserver();
            setupKeyboardShortcuts();
        }

        // Também inicializar quando o checklist for renderizado
        if (window.checklistRenderer) {
            const originalRender = window.checklistRenderer.render;
            if (originalRender) {
                window.checklistRenderer.render = function () {
                    originalRender.call(this);
                    setTimeout(() => {
                        setupCommentSectionObserver();
                    }, 100);
                };
            }
        }
    }

    // Exportar funções úteis
    window.ChecklistCommentsUI = {
        updateCommentSectionHeader,
        highlightTaskWithOpenComments,
        scrollToCommentSection,
        updateOpenCommentsCounter,
        closeAllCommentSections: window.closeAllCommentSections
    };

    // Inicializar
    init();

    console.log('[ChecklistCommentsUI] Melhorias de UI para comentários carregadas');
})();
