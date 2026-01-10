/**
 * CS Onboarding - Phone Utilities
 * Extracted from common.js for better maintainability.
 * 
 * @module utils/phone-utils
 * @description Handles Brazilian phone number formatting and validation.
 */

(function (global) {
    'use strict';

    // ========================================
    // PHONE FORMATTING
    // ========================================

    /**
     * Formats a phone input field with Brazilian mask.
     * Supports both landline (XX) XXXX-XXXX and mobile (XX) XXXXX-XXXX formats.
     * Also applies visual validation (is-valid/is-invalid classes).
     * 
     * @param {HTMLInputElement} input - The input element to format
     */
    function formatarTelefone(input) {
        if (!input) return;

        // Remove everything except digits
        let v = input.value.replace(/\D/g, '').substring(0, 11);

        // Apply mask based on length
        if (v.length > 10) {
            // Mobile: (XX) XXXXX-XXXX
            v = v.replace(/^(\d{2})(\d{5})(\d{4}).*/, '($1) $2-$3');
        } else if (v.length > 6) {
            // Landline: (XX) XXXX-XXXX
            v = v.replace(/^(\d{2})(\d{4})(\d{0,4}).*/, '($1) $2-$3');
        } else if (v.length > 2) {
            // DDD + start: (XX) XXXX
            v = v.replace(/^(\d{2})(\d{0,5}).*/, '($1) $2');
        } else if (v.length > 0) {
            // Just DDD: (XX
            v = v.replace(/^(\d{0,2}).*/, '($1');
        }

        input.value = v;

        // Visual validation
        const telefoneNumeros = v.replace(/\D/g, '');
        const isValid = telefoneNumeros.length >= 10 && telefoneNumeros.length <= 11;

        // Remove previous classes
        input.classList.remove('is-valid', 'is-invalid');

        // Add validation class
        if (telefoneNumeros.length > 0) {
            if (isValid) {
                input.classList.add('is-valid');
                input.setCustomValidity('');
            } else {
                input.classList.add('is-invalid');
                input.setCustomValidity('Telefone deve ter 10 ou 11 dígitos');
            }
        } else {
            input.setCustomValidity('');
        }
    }

    // ========================================
    // PHONE VALIDATION
    // ========================================

    /**
     * Validates a phone number string.
     * 
     * @param {string} telefone - Phone number to validate (can include formatting)
     * @returns {boolean} - true if valid (10-11 digits) or empty (optional field)
     */
    function validarTelefone(telefone) {
        if (!telefone) return true; // Optional field
        const numeros = telefone.replace(/\D/g, '');
        return numeros.length >= 10 && numeros.length <= 11;
    }

    /**
     * Validates a phone input field and applies visual feedback.
     * 
     * @param {HTMLInputElement} input - The input element to validate
     * @returns {boolean} - true if valid or empty
     */
    function validarTelefoneCompleto(input) {
        if (!input) return true;

        const telefone = input.value.trim();

        // Remove previous classes
        input.classList.remove('is-valid', 'is-invalid');

        if (telefone.length === 0) {
            // Empty field is valid (optional)
            input.setCustomValidity('');
            return true;
        }

        const numeros = telefone.replace(/\D/g, '');
        const isValid = numeros.length >= 10 && numeros.length <= 11;

        if (isValid) {
            input.classList.add('is-valid');
            input.setCustomValidity('');
            return true;
        } else {
            input.classList.add('is-invalid');
            input.setCustomValidity('Telefone deve ter 10 ou 11 dígitos');
            return false;
        }
    }

    /**
     * Extracts only digits from a phone number string.
     * 
     * @param {string} telefone - Phone number with formatting
     * @returns {string} - Only digits
     */
    function extrairDigitos(telefone) {
        if (!telefone) return '';
        return String(telefone).replace(/\D/g, '');
    }

    /**
     * Formats a raw phone number string (digits only) to Brazilian format.
     * 
     * @param {string} digits - Phone digits only (10 or 11 digits)
     * @returns {string} - Formatted phone number
     */
    function formatarDigitos(digits) {
        if (!digits) return '';
        const d = String(digits).replace(/\D/g, '');

        if (d.length === 11) {
            return d.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
        } else if (d.length === 10) {
            return d.replace(/^(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3');
        }

        return digits;
    }

    // ========================================
    // EXPORTS
    // ========================================

    // Create PhoneUtils namespace
    var PhoneUtils = {
        formatarTelefone: formatarTelefone,
        validarTelefone: validarTelefone,
        validarTelefoneCompleto: validarTelefoneCompleto,
        extrairDigitos: extrairDigitos,
        formatarDigitos: formatarDigitos
    };

    // Expose to global scope for backward compatibility
    global.PhoneUtils = PhoneUtils;
    global.formatarTelefone = formatarTelefone;
    global.validarTelefone = validarTelefone;
    global.validarTelefoneCompleto = validarTelefoneCompleto;

    console.log('✅ PhoneUtils module loaded');

})(typeof window !== 'undefined' ? window : this);
