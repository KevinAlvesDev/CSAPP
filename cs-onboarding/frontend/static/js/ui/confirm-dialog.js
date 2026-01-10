/**
 * CS Onboarding - Confirm Dialog System
 * Extracted from common.js for better maintainability.
 * 
 * @module ui/confirm-dialog
 * @description Promise-based confirmation dialogs using Bootstrap modals.
 */

(function (global) {
    'use strict';

    // ========================================
    // CONFIRM DIALOG FUNCTION
    // ========================================

    /**
     * Shows a confirmation dialog and returns a Promise.
     * 
     * @param {Object} options - Configuration options
     * @param {string} [options.title='Confirmar ação'] - Dialog title
     * @param {string} [options.message='Tem certeza que deseja continuar?'] - Dialog message
     * @param {string} [options.confirmText='Confirmar'] - Confirm button text
     * @param {string} [options.cancelText='Cancelar'] - Cancel button text
     * @param {string} [options.type='warning'] - Type: 'warning', 'danger', 'info', 'success'
     * @param {string} [options.icon='bi-exclamation-triangle-fill'] - Bootstrap icon class
     * @returns {Promise<boolean>} - Resolves to true if confirmed, false if cancelled
     */
    function showConfirm(options) {
        return new Promise((resolve) => {
            const {
                title = 'Confirmar ação',
                message = 'Tem certeza que deseja continuar?',
                confirmText = 'Confirmar',
                cancelText = 'Cancelar',
                type = 'warning',
                icon = 'bi-exclamation-triangle-fill'
            } = options || {};

            const modalId = 'confirmModal-' + Date.now();

            // Determine button color based on type
            const btnClass = type === 'danger' ? 'btn-danger' : 'btn-primary';

            const modalHTML = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header border-0 pb-0">
                            <h5 class="modal-title" id="${modalId}Label">
                                <i class="bi ${icon} text-${type} me-2"></i>${title}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <p>${message}</p>
                        </div>
                        <div class="modal-footer border-0">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${cancelText}</button>
                            <button type="button" class="btn ${btnClass}" id="${modalId}Confirm">${confirmText}</button>
                        </div>
                    </div>
                </div>
            </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHTML);
            const modalElement = document.getElementById(modalId);

            // Check if Bootstrap is available
            if (typeof bootstrap === 'undefined' || !bootstrap.Modal) {
                console.error('Bootstrap Modal not available');
                modalElement.remove();
                resolve(false);
                return;
            }

            const modal = new bootstrap.Modal(modalElement);
            let resolved = false;

            // Handle confirm button click
            const confirmBtn = document.getElementById(modalId + 'Confirm');
            confirmBtn.addEventListener('click', () => {
                resolved = true;
                modal.hide();
            });

            // Handle modal hidden event (close, cancel, or confirm)
            modalElement.addEventListener('hidden.bs.modal', () => {
                modalElement.remove();
                resolve(resolved);
            }, { once: true });

            modal.show();
        });
    }

    /**
     * Shows a delete confirmation dialog.
     * 
     * @param {string} [itemName='este item'] - Name of item to delete
     * @returns {Promise<boolean>} - Resolves to true if confirmed
     */
    function confirmDelete(itemName = 'este item') {
        return showConfirm({
            title: 'Confirmar Exclusão',
            message: `Tem certeza que deseja excluir ${itemName}? Esta ação não pode ser desfeita.`,
            confirmText: 'Excluir',
            cancelText: 'Cancelar',
            type: 'danger',
            icon: 'bi-trash-fill'
        });
    }

    /**
     * Shows a discard changes confirmation dialog.
     * 
     * @returns {Promise<boolean>} - Resolves to true if user wants to discard
     */
    function confirmDiscard() {
        return showConfirm({
            title: 'Alterações não salvas',
            message: 'Você tem alterações não salvas. Deseja descartá-las?',
            confirmText: 'Descartar',
            cancelText: 'Continuar editando',
            type: 'warning',
            icon: 'bi-exclamation-triangle-fill'
        });
    }

    /**
     * Shows a save confirmation dialog.
     * 
     * @returns {Promise<boolean>} - Resolves to true if confirmed
     */
    function confirmSave() {
        return showConfirm({
            title: 'Salvar alterações',
            message: 'Deseja salvar as alterações realizadas?',
            confirmText: 'Salvar',
            cancelText: 'Cancelar',
            type: 'info',
            icon: 'bi-floppy-fill'
        });
    }

    // ========================================
    // EXPORTS
    // ========================================

    // Create ConfirmDialog namespace
    var ConfirmDialog = {
        show: showConfirm,
        delete: confirmDelete,
        discard: confirmDiscard,
        save: confirmSave
    };

    // Expose to global scope for backward compatibility
    global.ConfirmDialog = ConfirmDialog;
    global.showConfirm = showConfirm;

    console.log('✅ ConfirmDialog module loaded');

})(typeof window !== 'undefined' ? window : this);
