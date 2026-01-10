/**
 * CS Onboarding - HTML Utilities
 * Extracted from common.js for better maintainability.
 * 
 * @module utils/html-utils
 * @description Safe HTML manipulation and escaping functions.
 */

(function (global) {
    'use strict';

    // ========================================
    // HTML ESCAPING
    // ========================================

    /**
     * Escapes HTML special characters to prevent XSS attacks.
     * Also converts newlines to <br> tags.
     * 
     * @param {string} text - Text to escape
     * @returns {string} - Escaped HTML string
     */
    function escapeHtml(text) {
        if (!text) return '';
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;")
            .replace(/\n/g, '<br>');
    }

    /**
     * Escapes HTML without converting newlines.
     * 
     * @param {string} text - Text to escape
     * @returns {string} - Escaped HTML string
     */
    function escapeHtmlStrict(text) {
        if (!text) return '';
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    /**
     * Sanitizes a string for use in HTML attributes.
     * 
     * @param {string} text - Text to sanitize
     * @returns {string} - Sanitized string
     */
    function sanitizeAttr(text) {
        if (!text) return '';
        return String(text)
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    // ========================================
    // PROGRESS BAR
    // ========================================

    /**
     * Updates the global checklist progress bar.
     * 
     * @param {number} percent - Progress percentage (0-100)
     */
    function updateProgressBar(percent) {
        var p = Math.max(0, Math.min(100, Number(percent) || 0));
        var labelEl = document.querySelector('#checklist-global-progress-percent');
        var barEl = document.querySelector('#checklist-global-progress-bar');
        if (labelEl) labelEl.textContent = p + '%';
        if (barEl) {
            barEl.style.width = p + '%';
            barEl.setAttribute('aria-valuenow', String(p));
            if (!barEl.getAttribute('aria-valuemax')) barEl.setAttribute('aria-valuemax', '100');
            if (!barEl.getAttribute('aria-valuemin')) barEl.setAttribute('aria-valuemin', '0');
        }
    }

    // ========================================
    // MULTIPLE SELECT HELPER
    // ========================================

    /**
     * Sets multiple values in a select element.
     * 
     * @param {HTMLSelectElement} selectElement - The select element
     * @param {string} dataValue - Comma-separated values to select
     */
    function setMultipleSelect(selectElement, dataValue) {
        if (!selectElement) return;
        Array.from(selectElement.options).forEach(opt => opt.selected = false);
        const values = (typeof dataValue === 'string' && dataValue)
            ? dataValue.split(',').map(s => s.trim()).filter(s => s.length > 0)
            : [];
        if (values.length > 0) {
            let hasSelection = false;
            Array.from(selectElement.options).forEach(opt => {
                if (values.includes(opt.value)) {
                    opt.selected = true;
                    hasSelection = true;
                }
            });
            if (!hasSelection && selectElement.options.length > 0 && selectElement.options[0].value === "") {
                selectElement.options[0].selected = true;
            }
        } else {
            if (selectElement.options.length > 0 && selectElement.options[0].value === "") {
                selectElement.options[0].selected = true;
            }
        }
    }

    // ========================================
    // EXPORTS
    // ========================================

    // Create HtmlUtils namespace
    var HtmlUtils = {
        escapeHtml: escapeHtml,
        escapeHtmlStrict: escapeHtmlStrict,
        sanitizeAttr: sanitizeAttr,
        updateProgressBar: updateProgressBar,
        setMultipleSelect: setMultipleSelect
    };

    // Expose to global scope for backward compatibility
    global.HtmlUtils = HtmlUtils;
    global.escapeHtml = escapeHtml;
    global.updateProgressBar = updateProgressBar;
    global.setMultipleSelect = setMultipleSelect;

    console.log('✅ HtmlUtils module loaded');

})(typeof window !== 'undefined' ? window : this);
