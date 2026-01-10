/**
 * CS Onboarding - Date Utilities
 * Extracted from common.js for better maintainability.
 * 
 * @module utils/date-utils
 * @description Handles date formatting, validation, masking, and Flatpickr configuration.
 */

(function (global) {
    'use strict';

    // ========================================
    // FLATPICKR LOCALIZATION (PT-BR)
    // ========================================

    /**
     * Configures Flatpickr to use Brazilian Portuguese locale.
     * Call this after Flatpickr is loaded.
     */
    function configureFlatpickrLocale() {
        if (global.flatpickr) {
            flatpickr.localize({
                weekdays: {
                    shorthand: ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'],
                    longhand: ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']
                },
                months: {
                    shorthand: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
                    longhand: ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
                },
                firstDayOfWeek: 1,
                rangeSeparator: ' até ',
                weekAbbreviation: 'Sem',
                scrollTitle: 'Role para aumentar',
                toggleTitle: 'Clique para alternar',
                amPM: ['AM', 'PM'],
                yearAriaLabel: 'Ano',
                monthAriaLabel: 'Mês',
                hourAriaLabel: 'Hora',
                minuteAriaLabel: 'Minuto',
                time_24hr: false
            });
        }
    }

    // ========================================
    // DATE VALIDATION
    // ========================================

    /**
     * Validates a date input field (DD/MM/YYYY format).
     * Adds 'is-valid' or 'is-invalid' classes based on validation result.
     * 
     * @param {HTMLInputElement} input - The input element to validate
     * @returns {boolean|undefined} - true if valid, false if invalid, undefined if empty
     */
    function validateDateInput(input) {
        var value = input.value.trim();
        input.classList.remove('is-invalid', 'is-valid');

        if (!value || value.length === 0) {
            return;
        }

        // Check format DD/MM/YYYY
        var regex = /^(\d{2})\/(\d{2})\/(\d{4})$/;
        var match = value.match(regex);

        if (!match) {
            input.classList.add('is-invalid');
            return false;
        }

        var day = parseInt(match[1], 10);
        var month = parseInt(match[2], 10);
        var year = parseInt(match[3], 10);

        // Validate limits
        if (day < 1 || day > 31 || month < 1 || month > 12 || year < 1900 || year > 2100) {
            input.classList.add('is-invalid');
            return false;
        }

        // Validate if date exists
        var date = new Date(year, month - 1, day);
        if (date.getDate() !== day || date.getMonth() !== month - 1 || date.getFullYear() !== year) {
            input.classList.add('is-invalid');
            return false;
        }

        input.classList.add('is-valid');
        return true;
    }

    // ========================================
    // DATE MASKING
    // ========================================

    /**
     * Applies a DD/MM/YYYY mask to an input field.
     * Handles typing, cursor position, and validation.
     * 
     * @param {HTMLInputElement} input - The input element to apply mask to
     */
    function applyDateMask(input) {
        if (!input || input.dataset.maskApplied) return;

        input.dataset.maskApplied = 'true';
        input.setAttribute('maxlength', '10');
        input.setAttribute('inputmode', 'numeric');

        // Apply mask while typing
        input.addEventListener('input', function (e) {
            var oldValue = this.dataset.oldValue || '';
            var cursorPos = this.selectionStart;
            var value = this.value.replace(/\D/g, ''); // Remove non-digits

            // If value didn't change (formatting only), do nothing
            if (value === oldValue.replace(/\D/g, '')) {
                return;
            }

            // Save old value
            this.dataset.oldValue = value;

            if (value.length > 8) {
                value = value.substring(0, 8);
            }

            // Apply formatting DD/MM/YYYY
            var formatted = '';
            if (value.length > 0) {
                formatted = value.substring(0, 2);
                if (value.length > 2) {
                    formatted += '/' + value.substring(2, 4);
                }
                if (value.length > 4) {
                    formatted += '/' + value.substring(4, 8);
                }
            }

            // Only update if value really changed
            if (this.value !== formatted) {
                this.value = formatted;

                // Adjust cursor position
                var newCursorPos = cursorPos;
                var addedChars = formatted.length - (oldValue.replace(/\D/g, '').length);

                if (formatted.length > cursorPos && formatted.charAt(cursorPos) === '/') {
                    newCursorPos = cursorPos + 1;
                } else if (addedChars > 0 && cursorPos < formatted.length) {
                    newCursorPos = cursorPos + addedChars;
                }

                if (newCursorPos > formatted.length) {
                    newCursorPos = formatted.length;
                }

                if (typeof this.setSelectionRange === 'function' && (this.type || '').toLowerCase() !== 'hidden' && document.activeElement === this) {
                    try { this.setSelectionRange(newCursorPos, newCursorPos); } catch (_) { }
                }
            }

            // Real-time validation if complete
            if (formatted.length === 10) {
                validateDateInput(this);
            } else {
                this.classList.remove('is-invalid', 'is-valid');
            }
        });

        // Validate on blur
        input.addEventListener('blur', function () {
            validateDateInput(this);
        });

        // Prevent non-numeric input
        input.addEventListener('keypress', function (e) {
            if (e.ctrlKey || e.metaKey || e.altKey) return true;
            var char = String.fromCharCode(e.which || e.keyCode);
            if (!/[0-9]/.test(char)) {
                e.preventDefault();
                return false;
            }
        });

        // Allow navigation keys
        input.addEventListener('keydown', function (e) {
            if ([8, 9, 27, 13, 46, 35, 36, 37, 38, 39, 40].indexOf(e.keyCode) !== -1) return true;
            if ((e.keyCode === 65 || e.keyCode === 67 || e.keyCode === 86 || e.keyCode === 88) && (e.ctrlKey || e.metaKey)) {
                return true;
            }
        });
    }

    // ========================================
    // DATE FIELDS INITIALIZATION
    // ========================================

    /**
     * Initializes all date fields in the document.
     * Applies Flatpickr or fallback mask based on availability.
     */
    function initDateFields() {
        document.querySelectorAll('input[type="text"]').forEach(function (input) {
            if (input.disabled || input.readOnly || input.classList.contains('no-datepicker')) {
                return;
            }

            var placeholder = (input.getAttribute('placeholder') || '').toLowerCase();
            var name = (input.getAttribute('name') || '').toLowerCase();
            var id = (input.getAttribute('id') || '').toLowerCase();
            var className = (input.className || '').toLowerCase();

            var isDateField = (
                className.includes('flatpickr-date') ||
                className.includes('date-input') ||
                placeholder.includes('dd/mm') ||
                placeholder.includes('dd/mm/aaaa') ||
                (name.includes('data_') && !name.includes('data_cadastro')) ||
                (name.includes('_data') && !name.includes('cadastro_data')) ||
                (id.includes('data_') && !id.includes('data_cadastro')) ||
                (id.includes('_data') && !id.includes('cadastro_data')) ||
                (id.includes('date') && !id.includes('update')) ||
                (name.includes('date') && !name.includes('update'))
            );

            if (isDateField) {
                if (!global.flatpickr) {
                    applyDateMask(input);
                }

                if (global.flatpickr && !input._flatpickr) {
                    try {
                        var dateConfig = {
                            dateFormat: 'Y-m-d',
                            altInput: true,
                            altFormat: 'd/m/Y',
                            allowInput: false,
                            clickOpens: true,
                            locale: flatpickr.l10ns.default || flatpickr.l10ns.pt,
                            parseDate: function (datestr, format) {
                                var regex = /^(\d{2})\/(\d{2})\/(\d{4})$/;
                                var match = datestr.match(regex);
                                if (!match) return null;
                                var day = parseInt(match[1], 10);
                                var month = parseInt(match[2], 10) - 1;
                                var year = parseInt(match[3], 10);
                                var date = new Date(year, month, day);
                                if (date.getDate() !== day || date.getMonth() !== month || date.getFullYear() !== year) return null;
                                return date;
                            }
                        };

                        var fp = global.flatpickr(input, dateConfig);

                        if (fp && fp.altInput) {
                            fp.altInput.removeAttribute('data-mask-applied');
                            applyDateMask(fp.altInput);

                            fp.config.onChange.push(function (selectedDates, dateStr, instance) {
                                if (instance.altInput) {
                                    validateDateInput(instance.altInput);
                                }
                            });

                            var originalSetDate = fp.setDate;
                            fp.setDate = function (date, triggerChange) {
                                var result = originalSetDate.call(this, date, triggerChange);
                                if (this.altInput) {
                                    setTimeout(function () {
                                        validateDateInput(fp.altInput);
                                    }, 10);
                                }
                                return result;
                            };
                        }
                    } catch (e) { }
                }
            }
        });
    }

    // ========================================
    // DATE FORMATTING
    // ========================================

    /**
     * Formats a date string to Brazilian format (DD/MM/YYYY).
     * 
     * @param {string} dateStr - Date string to format (ISO or any parseable format)
     * @param {boolean} includeTime - Whether to include time in output
     * @returns {string} - Formatted date string
     */
    function formatDate(dateStr, includeTime) {
        if (!dateStr) return '';

        // If already in Brazilian format, return as is
        var brFormatRegex = /^\d{2}\/\d{2}\/\d{4}(\s+às\s+\d{2}:\d{2})?$/;
        if (brFormatRegex.test(String(dateStr).trim())) {
            return String(dateStr);
        }

        var d = new Date(dateStr);
        if (isNaN(d.getTime())) return String(dateStr);

        var day = String(d.getDate()).padStart(2, '0');
        var month = String(d.getMonth() + 1).padStart(2, '0');
        var year = d.getFullYear();
        var out = day + '/' + month + '/' + year;

        if (includeTime) {
            var hours = String(d.getHours()).padStart(2, '0');
            var minutes = String(d.getMinutes()).padStart(2, '0');
            out += ' às ' + hours + ':' + minutes;
        }

        return out;
    }

    /**
     * Converts ISO date (YYYY-MM-DD) to Brazilian format (DD/MM/YYYY).
     * 
     * @param {string} isoDate - Date in ISO format
     * @returns {string} - Date in DD/MM/YYYY format
     */
    function isoToBr(isoDate) {
        if (!isoDate) return '';
        var parts = String(isoDate).split('-');
        if (parts.length !== 3) return isoDate;
        return parts[2] + '/' + parts[1] + '/' + parts[0];
    }

    /**
     * Converts Brazilian format (DD/MM/YYYY) to ISO date (YYYY-MM-DD).
     * 
     * @param {string} brDate - Date in DD/MM/YYYY format
     * @returns {string} - Date in ISO format
     */
    function brToIso(brDate) {
        if (!brDate) return '';
        var parts = String(brDate).split('/');
        if (parts.length !== 3) return brDate;
        return parts[2] + '-' + parts[1] + '-' + parts[0];
    }

    /**
     * Normalizes various date formats to ISO (YYYY-MM-DD).
     * 
     * @param {string} s - Date string in any format
     * @returns {string} - Date in ISO format
     */
    function normalizeToISO(s) {
        if (!s) return '';
        s = String(s).trim();

        // Already ISO
        if (/^\d{4}-\d{2}-\d{2}/.test(s)) {
            return s.substring(0, 10);
        }

        // Brazilian format
        if (/^\d{2}\/\d{2}\/\d{4}/.test(s)) {
            var p = s.split('/');
            return p[2] + '-' + p[1] + '-' + p[0];
        }

        // Try to parse as Date
        var d = new Date(s);
        if (!isNaN(d.getTime())) {
            return d.toISOString().substring(0, 10);
        }

        return '';
    }

    // ========================================
    // EXPORTS
    // ========================================

    // Create DateUtils namespace
    var DateUtils = {
        configureFlatpickrLocale: configureFlatpickrLocale,
        validateDateInput: validateDateInput,
        applyDateMask: applyDateMask,
        initDateFields: initDateFields,
        formatDate: formatDate,
        isoToBr: isoToBr,
        brToIso: brToIso,
        normalizeToISO: normalizeToISO
    };

    // Expose to global scope for backward compatibility
    global.DateUtils = DateUtils;
    global.configureFlatpickrLocale = configureFlatpickrLocale;
    global.validateDateInput = validateDateInput;
    global.applyDateMask = applyDateMask;
    global.initDateFields = initDateFields;
    global.formatDate = formatDate;
    global.isoToBr = isoToBr;
    global.brToIso = brToIso;
    global.normalizeToISO = normalizeToISO;

    console.log('✅ DateUtils module loaded');

})(typeof window !== 'undefined' ? window : this);
