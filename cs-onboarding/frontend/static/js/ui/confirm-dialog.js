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

            // Mapeamento de type para icons do SweetAlert2
            // warning, error, success, info, question
            const swalType = type === 'danger' ? 'error' : (type === 'primary' ? 'question' : type);

            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: title,
                    text: message,
                    icon: swalType,
                    showCancelButton: true,
                    confirmButtonText: confirmText,
                    cancelButtonText: cancelText,
                    confirmButtonColor: type === 'danger' ? '#dc3545' : '#0d6efd',
                    cancelButtonColor: '#6c757d',
                    reverseButtons: true
                }).then((result) => {
                    resolve(result.isConfirmed);
                });
            } else {
                // Fallback para native confirm se Swal falhar
                const confirmed = confirm(message);
                resolve(confirmed);
            }
        });
    }

    // Interceptar confirmações do HTMX para usar o modal bonito
    document.addEventListener('htmx:load', function () {
        if (!document.body.dataset.htmxConfirmAttached) {
            document.body.addEventListener('htmx:confirm', function (evt) {
                evt.preventDefault();
                showConfirm({
                    message: evt.detail.question,
                    title: 'Confirmação',
                    type: 'warning',
                    confirmText: 'Sim',
                    cancelText: 'Não'
                }).then(confirmed => {
                    if (confirmed) evt.detail.issueRequest();
                });
            });
            document.body.dataset.htmxConfirmAttached = 'true';
        }
    });

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
