/**
 * Utilitário para limpar modais do Bootstrap e prevenir bugs de backdrop/congelamento
 * Este script deve ser carregado após o Bootstrap
 */

(function () {
    'use strict';

    console.log('[ModalCleanup] 🧹 Inicializando limpeza automática de modais...');

    /**
     * Limpa todos os backdrops e restaura o estado do body
     */
    function cleanupModalBackdrops() {
        // Remover todos os backdrops órfãos
        const backdrops = document.querySelectorAll('.modal-backdrop');
        if (backdrops.length > 0) {
            console.log(`[ModalCleanup] Removendo ${backdrops.length} backdrop(s) órfão(s)`);
            backdrops.forEach(backdrop => backdrop.remove());
        }

        // Verificar se ainda há modais abertos
        const openModals = document.querySelectorAll('.modal.show');

        // Se não há modais abertos, restaurar o body
        if (openModals.length === 0) {
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
            console.log('[ModalCleanup] ✅ Estado do body restaurado');
        }
    }

    /**
     * Adiciona listeners de limpeza a todos os modais existentes
     */
    function attachCleanupListeners() {
        const modals = document.querySelectorAll('.modal');

        modals.forEach(modal => {
            // Verificar se já tem o listener (para não duplicar)
            if (!modal.hasAttribute('data-cleanup-attached')) {
                modal.setAttribute('data-cleanup-attached', 'true');

                // Listener para quando o modal é fechado
                modal.addEventListener('hidden.bs.modal', function () {
                    console.log('[ModalCleanup] Modal fechado:', modal.id || 'sem ID');
                    cleanupModalBackdrops();
                });

                // Listener para quando o modal é destruído
                modal.addEventListener('dispose.bs.modal', function () {
                    console.log('[ModalCleanup] Modal destruído:', modal.id || 'sem ID');
                    cleanupModalBackdrops();
                });
            }
        });
    }

    /**
     * Observer para detectar novos modais adicionados ao DOM
     */
    const observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            mutation.addedNodes.forEach(function (node) {
                if (node.nodeType === 1) { // Element node
                    // Verificar se o nó adicionado é um modal
                    if (node.classList && node.classList.contains('modal')) {
                        console.log('[ModalCleanup] Novo modal detectado:', node.id || 'sem ID');
                        attachCleanupListeners();
                    }
                    // Verificar se o nó contém modais
                    else if (node.querySelectorAll) {
                        const modals = node.querySelectorAll('.modal');
                        if (modals.length > 0) {
                            console.log(`[ModalCleanup] ${modals.length} modal(is) detectado(s) em novo elemento`);
                            attachCleanupListeners();
                        }
                    }
                }
            });
        });
    });

    /**
     * Inicializa o sistema de limpeza
     */
    function init() {
        // Anexar listeners aos modais existentes
        attachCleanupListeners();

        // Observar mudanças no DOM para novos modais
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Limpeza preventiva a cada 5 segundos (fallback)
        setInterval(function () {
            const backdrops = document.querySelectorAll('.modal-backdrop');
            const openModals = document.querySelectorAll('.modal.show');

            // Se há backdrops mas nenhum modal aberto, limpar
            if (backdrops.length > 0 && openModals.length === 0) {
                console.log('[ModalCleanup] ⚠️ Detectados backdrops órfãos, limpando...');
                cleanupModalBackdrops();
            }
        }, 5000);

        console.log('[ModalCleanup] ✅ Sistema de limpeza inicializado');
    }

    // Inicializar quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expor função de limpeza globalmente para uso manual se necessário
    window.cleanupModals = cleanupModalBackdrops;

})();
