/**
 * CS Onboarding - Toast Notification System
 * Extracted from common.js for better maintainability.
 * 
 * @module ui/toast
 * @description Premium toast notifications with dark mode support.
 */

(function (global) {
    'use strict';

    // ========================================
    // TOAST CONFIGURATION
    // ========================================

    const TOAST_TYPES = {
        success: {
            icon: 'bi-check-lg',
            color: '#10b981', // Emerald 500
            bgIcon: 'rgba(16, 185, 129, 0.1)',
            title: 'Sucesso'
        },
        error: {
            icon: 'bi-x-lg',
            color: '#ef4444', // Red 500
            bgIcon: 'rgba(239, 68, 68, 0.1)',
            title: 'Erro'
        },
        warning: {
            icon: 'bi-exclamation-lg',
            color: '#f59e0b', // Amber 500
            bgIcon: 'rgba(245, 158, 11, 0.1)',
            title: 'Atenção'
        },
        info: {
            icon: 'bi-info-lg',
            color: '#3b82f6', // Blue 500
            bgIcon: 'rgba(59, 130, 246, 0.1)',
            title: 'Informação'
        },
        default: {
            icon: 'bi-bell-fill',
            color: '#6366f1', // Indigo 500
            bgIcon: 'rgba(99, 102, 241, 0.1)',
            title: 'Notificação'
        }
    };

    // ========================================
    // TOAST CONTAINER MANAGEMENT
    // ========================================

    /**
     * Gets or creates the toast container element.
     * 
     * @returns {HTMLElement} The toast container
     */
    function getToastContainer() {
        let container = document.getElementById('toastContainer');

        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999'; // Above modals (1055)
            document.body.appendChild(container);
        }

        return container;
    }

    // ========================================
    // DARK MODE DETECTION
    // ========================================

    /**
     * Checks if dark mode is currently active.
     * 
     * @returns {boolean} true if dark mode is active
     */
    function isDarkMode() {
        return document.body.classList.contains('dark-mode') ||
            document.documentElement.getAttribute('data-bs-theme') === 'dark';
    }

    // ========================================
    // SHOW TOAST FUNCTION
    // ========================================

    /**
     * Shows a premium toast notification.
     * 
     * @param {string} message - The message to display
     * @param {string} [type='info'] - Type: 'success', 'error', 'warning', 'info'
     * @param {number} [duration=5000] - Duration in milliseconds
     */
    function showToast(message, type = 'info', duration = 5000) {
        const toastContainer = getToastContainer();
        const toastId = 'toast-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        const config = TOAST_TYPES[type] || TOAST_TYPES.default;

        // Dark Mode Styles
        const isDark = isDarkMode();
        const bgColor = isDark ? 'rgba(30, 30, 35, 0.95)' : 'rgba(255, 255, 255, 0.98)';
        const textColor = isDark ? '#e2e8f0' : '#1e293b';
        const borderColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)';
        const shadow = isDark ? '0 10px 30px -5px rgba(0, 0, 0, 0.5)' : '0 10px 30px -5px rgba(0, 0, 0, 0.1)';

        const toastHTML = `
        <div id="${toastId}" class="toast border-0 mb-3" role="alert" aria-live="assertive" aria-atomic="true"
             style="
                background: ${bgColor};
                backdrop-filter: blur(10px);
                border: 1px solid ${borderColor};
                border-left: 4px solid ${config.color};
                box-shadow: ${shadow};
                border-radius: 12px;
                min-width: 320px;
                max-width: 400px;
                overflow: hidden;
                transform: translateX(100%);
                transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
             ">
             
             <div class="d-flex p-3 align-items-start">
                <!-- Circular Icon -->
                <div class="d-flex align-items-center justify-content-center rounded-circle flex-shrink-0 me-3"
                     style="width: 38px; height: 38px; background: ${config.bgIcon}; color: ${config.color};">
                    <i class="bi ${config.icon} fs-5"></i>
                </div>

                <!-- Content -->
                <div class="flex-grow-1">
                    <h6 class="mb-1 fw-bold" style="color: ${textColor}; font-size: 0.95rem;">${config.title}</h6>
                    <p class="mb-0 text-muted" style="font-size: 0.85rem; line-height: 1.4;">${message}</p>
                </div>

                <!-- Close Button -->
                <button type="button" class="btn-close ms-2" data-bs-dismiss="toast" aria-label="Close" 
                        style="opacity: 0.5; font-size: 0.8rem;"></button>
             </div>

             <!-- Progress Bar -->
             <div class="toast-progress" style="height: 3px; background: ${config.bgIcon}; width: 100%;">
                <div style="height: 100%; background: ${config.color}; width: 100%; transition: width ${duration}ms linear;"></div>
             </div>
        </div>
        `;

        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        const toastElement = document.getElementById(toastId);

        // Activate entrance animation
        requestAnimationFrame(() => {
            toastElement.style.transform = 'translateX(0)';
        });

        // Activate progress bar animation
        setTimeout(() => {
            const progressBar = toastElement.querySelector('.toast-progress > div');
            if (progressBar) progressBar.style.width = '0%';
        }, 50);

        // Use Bootstrap Toast if available
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            const toast = new bootstrap.Toast(toastElement, {
                autohide: true,
                delay: duration
            });
            toast.show();

            // Exit animation
            toastElement.addEventListener('hide.bs.toast', function () {
                toastElement.style.transform = 'translateX(120%)';
                toastElement.style.opacity = '0';
            });

            toastElement.addEventListener('hidden.bs.toast', function () {
                toastElement.remove();
            });
        } else {
            // Fallback: manual removal after duration
            setTimeout(() => {
                toastElement.style.transform = 'translateX(120%)';
                toastElement.style.opacity = '0';
                setTimeout(() => toastElement.remove(), 400);
            }, duration);
        }
    }

    // ========================================
    // EXPORTS
    // ========================================

    // Create Toast namespace
    var Toast = {
        show: showToast,
        success: (msg, duration) => showToast(msg, 'success', duration),
        error: (msg, duration) => showToast(msg, 'error', duration),
        warning: (msg, duration) => showToast(msg, 'warning', duration),
        info: (msg, duration) => showToast(msg, 'info', duration)
    };

    // Expose to global scope for backward compatibility
    global.Toast = Toast;
    global.showToast = showToast;

    console.log('✅ Toast module loaded');

})(typeof window !== 'undefined' ? window : this);
