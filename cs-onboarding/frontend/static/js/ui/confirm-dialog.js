/**
 * CS Onboarding - Confirm Dialog System
 * Extracted from common.js for better maintainability.
 * 
 * @module ui/confirm-dialog
 * @description Promise-based confirmation dialogs using Bootstrap modals.
 */

(function (global) {
    'use strict';

    // Referências ao modal
    let modalElement = null;
    let modalInstance = null;
    let currentResolve = null;

    /**
     * Inicializa o modal de confirmação
     */
    function initModal() {
        if (modalElement) return;

        modalElement = document.getElementById('modalConfirmacao');
        if (!modalElement) {
            console.warn('⚠️ Modal de confirmação não encontrado no DOM');
            return;
        }

        modalInstance = new bootstrap.Modal(modalElement);

        // Configurar eventos
        const btnConfirmar = document.getElementById('modalConfirmacaoConfirmar');
        const btnCancelar = document.getElementById('modalConfirmacaoCancelar');
        const btnClose = modalElement.querySelector('.btn-close');

        btnConfirmar.addEventListener('click', () => {
            if (currentResolve) currentResolve(true);
            modalInstance.hide();
        });

        btnCancelar.addEventListener('click', () => {
            if (currentResolve) currentResolve(false);
            modalInstance.hide();
        });

        btnClose.addEventListener('click', () => {
            if (currentResolve) currentResolve(false);
        });

        // Evento quando o modal é fechado por qualquer motivo
        modalElement.addEventListener('hidden.bs.modal', () => {
            if (currentResolve) {
                currentResolve(false);
                currentResolve = null;
            }
        });
    }

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
     * @param {string} [options.alertLabel] - Label do alerta (ex: "Atenção! Irreversível!")
     * @param {string} [options.detail] - Detalhe adicional em texto menor
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
                alertLabel = '',
                detail = ''
            } = options || {};

            // Inicializar modal se necessário
            initModal();

            // Fallback para native confirm se o modal não estiver disponível
            if (!modalInstance) {
                const confirmed = confirm(message);
                resolve(confirmed);
                return;
            }

            // Configurar título
            const tituloEl = document.getElementById('modalConfirmacaoTitulo');
            tituloEl.textContent = title;
            tituloEl.className = 'modal-title';
            if (type === 'danger') {
                tituloEl.classList.add('text-danger');
            }

            // Configurar mensagem
            document.getElementById('modalConfirmacaoMensagem').textContent = message;

            // Configurar alerta (se houver)
            const alertaEl = document.getElementById('modalConfirmacaoAlerta');
            const alertaTextoEl = document.getElementById('modalConfirmacaoAlertaTexto');
            const alertaLabelEl = document.getElementById('modalConfirmacaoAlertaLabel');
            const iconeEl = document.getElementById('modalConfirmacaoIcone');

            if (alertLabel) {
                alertaEl.classList.remove('d-none');
                alertaLabelEl.textContent = alertLabel;

                // Configurar cor e ícone baseado no tipo
                alertaTextoEl.className = 'fw-bold';
                if (type === 'danger') {
                    alertaTextoEl.classList.add('text-danger');
                    iconeEl.className = 'bi bi-exclamation-octagon-fill me-2';
                } else if (type === 'warning') {
                    alertaTextoEl.classList.add('text-warning');
                    iconeEl.className = 'bi bi-exclamation-triangle-fill me-2';
                } else if (type === 'info') {
                    alertaTextoEl.classList.add('text-info');
                    iconeEl.className = 'bi bi-info-circle-fill me-2';
                } else {
                    alertaTextoEl.classList.add('text-primary');
                    iconeEl.className = 'bi bi-question-circle-fill me-2';
                }
            } else {
                alertaEl.classList.add('d-none');
            }

            // Configurar detalhe
            const detalheEl = document.getElementById('modalConfirmacaoDetalhe');
            if (detail) {
                detalheEl.textContent = detail;
                detalheEl.classList.remove('d-none');
            } else {
                detalheEl.classList.add('d-none');
            }

            // Configurar botões
            const btnConfirmar = document.getElementById('modalConfirmacaoConfirmar');
            const btnCancelar = document.getElementById('modalConfirmacaoCancelar');

            btnConfirmar.textContent = confirmText;
            btnCancelar.textContent = cancelText;

            // Configurar cor do botão baseado no tipo
            btnConfirmar.className = 'btn';
            if (type === 'danger') {
                btnConfirmar.classList.add('btn-danger');
            } else if (type === 'warning') {
                btnConfirmar.classList.add('btn-warning');
            } else if (type === 'success') {
                btnConfirmar.classList.add('btn-success');
            } else {
                btnConfirmar.classList.add('btn-primary');
            }

            // Guardar a promise resolve
            currentResolve = resolve;

            // Mostrar modal
            modalInstance.show();
        });
    }

    // Interceptar confirmações do HTMX para usar o modal
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
            message: `Tem certeza que deseja excluir ${itemName}?`,
            confirmText: 'Excluir',
            cancelText: 'Cancelar',
            type: 'danger',
            alertLabel: 'Atenção! Esta ação não pode ser desfeita.',
            detail: 'Todos os dados relacionados serão perdidos.'
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
            alertLabel: 'Atenção!'
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
            type: 'info'
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

    // Inicializar quando o DOM estiver pronto
    document.addEventListener('DOMContentLoaded', initModal);

    console.log('✅ ConfirmDialog module loaded (Bootstrap Modal)');

})(typeof window !== 'undefined' ? window : this);
