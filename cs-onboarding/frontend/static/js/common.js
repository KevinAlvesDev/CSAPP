/**
 * CS Onboarding - Common Scripts
 * Centralizes global functionality, date handling, masking, and HTMX polyfills.
 * Moved from base.html for better maintainability and caching.
 */

(function () {
    'use strict';

    // --- Flatpickr Localization ---
    function configureFlatpickrLocale() {
        if (window.flatpickr) {
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

    // --- Date Validation & Masking ---

    window.validateDateInput = function (input) {
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
    };

    window.applyDateMask = function (input) {
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
                window.validateDateInput(this);
            } else {
                this.classList.remove('is-invalid', 'is-valid');
            }
        });

        // Validate on blur
        input.addEventListener('blur', function () {
            window.validateDateInput(this);
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
    };

    window.initDateFields = function () {
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
                if (!window.flatpickr) {
                    window.applyDateMask(input);
                }

                if (window.flatpickr && !input._flatpickr) {
                    try {
                        var dateConfig = {
                            dateFormat: 'Y-m-d',
                            altInput: true,
                            altFormat: 'd/m/Y',
                            allowInput: false,
                            clickOpens: true,
                            locale: flatpickr.l10ns.default || flatpickr.l10ns.pt, // Use configured locale
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

                        var fp = window.flatpickr(input, dateConfig);

                        if (fp && fp.altInput) {
                            fp.altInput.removeAttribute('data-mask-applied');
                            window.applyDateMask(fp.altInput);

                            fp.config.onChange.push(function (selectedDates, dateStr, instance) {
                                if (instance.altInput) {
                                    window.validateDateInput(instance.altInput);
                                }
                            });

                            var originalSetDate = fp.setDate;
                            fp.setDate = function (date, triggerChange) {
                                var result = originalSetDate.call(this, date, triggerChange);
                                if (this.altInput) {
                                    setTimeout(function () {
                                        window.validateDateInput(fp.altInput);
                                    }, 10);
                                }
                                return result;
                            };
                        }
                    } catch (e) { }
                }
            }
        });
    };

    // --- Utils Centralizados ---
    window.escapeHtml = function (text) {
        if (!text) return '';
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;")
            .replace(/\n/g, '<br>');
    };

    window.formatDate = function (dateStr, includeTime) {
        if (!dateStr) return '';
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
    };

    window.updateProgressBar = function (percent) {
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
    };

    // --- HTMX Polyfill ---

    function ensureHTMX() {
        if (window.htmx) return true;
        var urls = [
            'https://cdn.jsdelivr.net/npm/htmx.org@1.9.10/dist/htmx.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/htmx/1.9.10/htmx.min.js'
        ];
        var i = 0;
        function loadNext() {
            if (window.htmx) return;
            if (i >= urls.length) { polyfillHTMX(); return; }
            var s = document.createElement('script'); s.src = urls[i++]; s.async = true;
            s.onload = function () { };
            s.onerror = function () { loadNext(); };
            document.head.appendChild(s);
        }
        loadNext();
        return !!window.htmx;
    }

    function polyfillHTMX() {
        // Minimal fallback: intercept comment forms and send via fetch
        document.addEventListener('submit', function (ev) {
            var form = ev.target;
            if (!form || !form.matches('form[hx-post]')) return;
            ev.preventDefault();
            try {
                var targetSel = form.getAttribute('hx-target');
                var postUrl = form.getAttribute('hx-post');
                var swapMode = (form.getAttribute('hx-swap') || 'beforeend').toLowerCase();
                var target = targetSel ? document.querySelector(targetSel) : null;
                if (!postUrl || !target) { form.submit(); return; }
                var fd = new FormData(form);
                fetch(postUrl, { method: 'POST', body: fd, headers: { 'HX-Request': 'true' } })
                    .then(function (r) { return r.text(); })
                    .then(function (html) {
                        var temp = document.createElement('div'); temp.innerHTML = html;
                        var nodes = Array.from(temp.childNodes);
                        if (swapMode === 'beforeend') nodes.forEach(function (n) { target.appendChild(n); });
                        else if (swapMode === 'outerhtml') { target.outerHTML = html; }
                        else { target.innerHTML = html; }
                        var evt = new Event('comment_saved_fallback'); document.body.dispatchEvent(evt);
                    })
                    .catch(function (e) { console.error('Failed to send comment:', e); alert('Erro ao salvar comentário.'); });
            } catch (e2) { console.error('HTMX fallback failed:', e2); form.submit(); }
        }, true);

        document.addEventListener('click', function (ev) {
            var el = ev.target && ev.target.closest('[hx-post]');
            if (!el) return;
            if (el.closest('form')) return;
            if (!(el.tagName === 'BUTTON' || el.tagName === 'A')) return;
            ev.preventDefault();
            var confirmMsg = el.getAttribute('hx-confirm');
            if (confirmMsg && !window.confirm(confirmMsg)) return;
            var postUrl = el.getAttribute('hx-post');
            var targetSel = el.getAttribute('hx-target');
            var swapMode = (el.getAttribute('hx-swap') || 'innerHTML').toLowerCase();
            var target = targetSel ? document.querySelector(targetSel) : null;
            if (!postUrl || !target) return;
            try { el.disabled = true; } catch (e) { }
            fetch(postUrl, { method: 'POST', headers: { 'HX-Request': 'true' } })
                .then(function (r) { return r.text(); })
                .then(function (html) {
                    if (swapMode === 'outerhtml') { target.outerHTML = html; }
                    else if (swapMode === 'beforeend') {
                        var temp = document.createElement('div'); temp.innerHTML = html;
                        Array.from(temp.childNodes).forEach(function (n) { target.appendChild(n); });
                    } else { target.innerHTML = html; }
                })
                .catch(function () {
                    try {
                        var alert = document.createElement('div');
                        alert.className = 'alert alert-danger alert-dismissible fade show my-2';
                        alert.innerHTML = 'Falha ao excluir comentário.' + '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
                        var container = document.querySelector('.container') || document.body;
                        container.prepend(alert);
                        setTimeout(function () { try { var ai = bootstrap.Alert.getOrCreateInstance(alert); ai.close(); } catch (e) { } }, 3000);
                    } catch (e) { }
                })
                .finally(function () { try { el.disabled = false; } catch (e) { } });
        }, true);
    }

    function setupHTMXFallback() {
        if (!window.htmx) {
            if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', ensureHTMX); }
            else { ensureHTMX(); }
        }

        // Modal specific HTMX handling
        document.addEventListener('submit', function (ev) {
            var form = ev.target;
            if (!form || !form.matches('#modalGerenciarUsuarios form[hx-post]')) return;
            ev.preventDefault();
            try {
                var targetSel = form.getAttribute('hx-target');
                var postUrl = form.getAttribute('hx-post');
                var swapMode = (form.getAttribute('hx-swap') || 'innerHTML').toLowerCase();
                var target = targetSel ? document.querySelector(targetSel) : null;
                if (!postUrl || !target) return;
                var fd = new FormData(form);
                fetch(postUrl, { method: 'POST', body: fd, headers: { 'HX-Request': 'true' } })
                    .then(function (r) { return r.text(); })
                    .then(function (html) {
                        if (swapMode === 'outerhtml') { target.outerHTML = html; }
                        else if (swapMode === 'beforeend') {
                            var temp = document.createElement('div'); temp.innerHTML = html;
                            Array.from(temp.childNodes).forEach(function (n) { target.appendChild(n); });
                        } else { target.innerHTML = html; }
                    })
                    .catch(function (e) { console.error('Modal form submission failed:', e); });
            } catch (e) { console.error('Error processing modal submit:', e); }
        }, true);

        // Delete comment specific handling
        document.addEventListener('click', function (ev) {
            var el = ev.target && ev.target.closest('button[hx-post], a[hx-post]');
            if (!el) return;
            var postUrl = el.getAttribute('hx-post');
            if (!postUrl || postUrl.indexOf('/api/excluir_comentario/') === -1) return;
            ev.preventDefault();
            ev.stopPropagation();
            try { ev.stopImmediatePropagation(); } catch (e) { }
            var confirmMsg = el.getAttribute('hx-confirm');
            if (confirmMsg && !window.confirm(confirmMsg)) return;
            var targetSel = el.getAttribute('hx-target');
            var swapMode = (el.getAttribute('hx-swap') || 'outerHTML').toLowerCase();
            var target = targetSel ? document.querySelector(targetSel) : null;
            if (!target) return;
            try { el.disabled = true; } catch (e) { }
            fetch(postUrl, { method: 'POST', headers: { 'HX-Request': 'true' } })
                .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.text(); })
                .then(function (html) {
                    if (swapMode === 'outerhtml') { target.outerHTML = html; }
                    else { target.innerHTML = html; }
                })
                .catch(function (e) { console.error('Delete comment failed:', e); })
                .finally(function () { try { el.disabled = false; } catch (e) { } });
        }, true);

        // Send Email specific handling
        document.addEventListener('click', function (ev) {
            var el = ev.target && ev.target.closest('button[hx-post], a[hx-post]');
            if (!el) return;
            var postUrl = el.getAttribute('hx-post');
            if (!postUrl || postUrl.indexOf('/api/enviar_email_comentario/') === -1) return;
            ev.preventDefault();
            ev.stopPropagation();
            try { ev.stopImmediatePropagation(); } catch (e) { }
            var confirmMsg = el.getAttribute('hx-confirm');
            if (confirmMsg && !window.confirm(confirmMsg)) return;
            var targetSel = el.getAttribute('hx-target');
            var swapMode = (el.getAttribute('hx-swap') || 'beforeend').toLowerCase();
            var target = targetSel ? document.querySelector(targetSel) : null;
            if (!target) return;
            try { el.disabled = true; } catch (e) { }
            fetch(postUrl, { method: 'POST', headers: { 'HX-Request': 'true' } })
                .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.text(); })
                .then(function (html) {
                    if (swapMode === 'outerhtml') { target.outerHTML = html; }
                    else if (swapMode === 'beforeend') {
                        var temp = document.createElement('div'); temp.innerHTML = html;
                        Array.from(temp.childNodes).forEach(function (n) { target.appendChild(n); });
                    } else { target.innerHTML = html; }
                    try {
                        var ok = /text-success/.test(html);
                        var msg = ok ? 'E-mail enviado ao responsável.' : 'Falha ao enviar e-mail ao responsável.';
                        var cls = ok ? 'alert-success' : 'alert-danger';
                        var alert = document.createElement('div');
                        alert.className = 'alert ' + cls + ' alert-dismissible fade show my-2';
                        alert.innerHTML = msg + '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
                        var container = document.querySelector('#detalhesTabContent') || document.querySelector('.container') || document.body;
                        container.prepend(alert);
                        setTimeout(function () { try { var ai = bootstrap.Alert.getOrCreateInstance(alert); ai.close(); } catch (e) { } }, 3000);
                    } catch (e) { }
                })
                .catch(function () {
                    try {
                        var alert = document.createElement('div');
                        alert.className = 'alert alert-danger alert-dismissible fade show my-2';
                        alert.innerHTML = 'Falha ao enviar e-mail ao responsável.' + '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
                        var container = document.querySelector('#detalhesTabContent') || document.querySelector('.container') || document.body;
                        container.prepend(alert);
                        setTimeout(function () { try { var ai = bootstrap.Alert.getOrCreateInstance(alert); ai.close(); } catch (e) { } }, 3000);
                    } catch (e) { }
                })
                .finally(function () { try { el.disabled = false; } catch (e) { } });
        }, true);

        // HTMX Error handling
        document.addEventListener('htmx:responseError', function (ev) {
            try {
                var alert = document.createElement('div');
                alert.className = 'alert alert-danger alert-dismissible fade show my-2';
                alert.innerHTML = 'Falha ao salvar. Tente novamente.' + '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
                var container = document.querySelector('.container') || document.body;
                container.prepend(alert);
                setTimeout(function () { try { var alertInst = bootstrap.Alert.getOrCreateInstance(alert); alertInst.close(); } catch (e) { } }, 3000);
            } catch (e) { }
        });
    }

    // --- Sidebar & Tooltips ---

    function initSidebarAndTooltips() {
        // Tooltips
        try {
            var tooltipEls = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipEls.forEach(function (el) { bootstrap.Tooltip.getOrCreateInstance(el); });
        } catch (e) { }

        // Sidebar Toggle
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.getElementById('menu');
        const mainContent = document.querySelector('.main-content');

        if (sidebarToggle && sidebar) {
            function updateMainContent() {
                if (sidebar.classList.contains('collapsed')) {
                    if (mainContent) {
                        mainContent.style.marginLeft = '60px';
                        mainContent.style.width = 'calc(100% - 60px)';
                    }
                } else {
                    if (mainContent) {
                        mainContent.style.marginLeft = '280px';
                        mainContent.style.width = 'calc(100% - 280px)';
                    }
                }
            }

            const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
            if (isCollapsed) {
                sidebar.classList.add('collapsed');
            }
            updateMainContent();

            const icon = sidebarToggle.querySelector('i');
            if (icon) {
                icon.style.transform = isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
            }

            sidebarToggle.addEventListener('click', function () {
                sidebar.classList.toggle('collapsed');
                const icon = sidebarToggle.querySelector('i');
                if (icon) {
                    icon.style.transform = sidebar.classList.contains('collapsed') ? 'rotate(180deg)' : 'rotate(0deg)';
                }
                updateMainContent();
                localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
            });
        }

        // Theme Toggle (Dark Mode)
        const themeToggle = document.getElementById('themeToggle');
        const themeIcon = document.getElementById('themeIcon');
        const themeText = document.getElementById('themeText');

        function applyTheme(isDark) {
            if (isDark) {
                document.documentElement.setAttribute('data-bs-theme', 'dark');
                document.body.classList.add('dark-mode');
                if (themeIcon) {
                    themeIcon.classList.remove('bi-moon-stars');
                    themeIcon.classList.add('bi-sun-fill');
                }
                if (themeText) themeText.textContent = 'Tema Claro';
            } else {
                document.documentElement.removeAttribute('data-bs-theme');
                document.body.classList.remove('dark-mode');
                if (themeIcon) {
                    themeIcon.classList.remove('bi-sun-fill');
                    themeIcon.classList.add('bi-moon-stars');
                }
                if (themeText) themeText.textContent = 'Tema Escuro';
            }
        }

        // Carregar tema salvo
        const savedTheme = localStorage.getItem('darkMode');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const isDarkMode = savedTheme === 'true' || (savedTheme === null && prefersDark);
        applyTheme(isDarkMode);

        if (themeToggle) {
            themeToggle.addEventListener('click', function (e) {
                e.preventDefault();
                const isDark = document.body.classList.contains('dark-mode');
                applyTheme(!isDark);
                localStorage.setItem('darkMode', !isDark);
            });
        }
    }

    // --- Utility Functions ---

    window.formatarTelefone = function (input) {
        // Remove tudo que não é número
        let v = input.value.replace(/\D/g, '').substring(0, 11);

        // Aplica máscara conforme o tamanho
        if (v.length > 10) {
            // Celular: (XX) XXXXX-XXXX
            v = v.replace(/^(\d{2})(\d{5})(\d{4}).*/, '($1) $2-$3');
        } else if (v.length > 6) {
            // Telefone fixo: (XX) XXXX-XXXX
            v = v.replace(/^(\d{2})(\d{4})(\d{0,4}).*/, '($1) $2-$3');
        } else if (v.length > 2) {
            // DDD + início: (XX) XXXX
            v = v.replace(/^(\d{2})(\d{0,5}).*/, '($1) $2');
        } else if (v.length > 0) {
            // Apenas DDD: (XX
            v = v.replace(/^(\d{0,2}).*/, '($1');
        }

        input.value = v;

        // Validação visual
        const telefoneInput = input;
        const telefoneNumeros = v.replace(/\D/g, '');
        const isValid = telefoneNumeros.length >= 10 && telefoneNumeros.length <= 11;

        // Remove classes anteriores
        telefoneInput.classList.remove('is-valid', 'is-invalid');

        // Adiciona classe de validação
        if (telefoneNumeros.length > 0) {
            if (isValid) {
                telefoneInput.classList.add('is-valid');
                telefoneInput.setCustomValidity('');
            } else {
                telefoneInput.classList.add('is-invalid');
                telefoneInput.setCustomValidity('Telefone deve ter 10 ou 11 dígitos');
            }
        } else {
            telefoneInput.setCustomValidity('');
        }
    };

    window.validarTelefone = function (telefone) {
        if (!telefone) return true; // Campo opcional
        const numeros = telefone.replace(/\D/g, '');
        return numeros.length >= 10 && numeros.length <= 11;
    };

    window.validarTelefoneCompleto = function (input) {
        const telefone = input.value.trim();
        const telefoneInput = input;

        // Remove classes anteriores
        telefoneInput.classList.remove('is-valid', 'is-invalid');

        if (telefone.length === 0) {
            // Campo vazio é válido (opcional)
            telefoneInput.setCustomValidity('');
            return true;
        }

        const numeros = telefone.replace(/\D/g, '');
        const isValid = numeros.length >= 10 && numeros.length <= 11;

        if (isValid) {
            telefoneInput.classList.add('is-valid');
            telefoneInput.setCustomValidity('');
            return true;
        } else {
            telefoneInput.classList.add('is-invalid');
            telefoneInput.setCustomValidity('Telefone deve ter 10 ou 11 dígitos');
            return false;
        }
    };

    window.setMultipleSelect = function (selectElement, dataValue) {
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
    };

    // --- Mobile & Modal Helpers ---

    document.addEventListener('show.bs.modal', function () {
        try {
            var menu = document.getElementById('menu');
            var push = document.querySelector('.push');
            var backdrop = document.querySelector('.bigslide-backdrop');
            if (document.body.classList.contains('menu-open')) {
                document.body.classList.remove('menu-open');
                if (menu) menu.classList.remove('open');
                if (push) push.classList.remove('push-shifted');
                if (backdrop) backdrop.classList.add('d-none');
            }
            // Se bigSlide estiver ativo, aciona o fechamento para sincronizar estado interno
            if (window.jQuery && jQuery.fn && jQuery.fn.bigSlide) {
                jQuery('.menu-link').trigger('click');
            }
        } catch (e) { /* ignora erros de ambiente */ }
    });

    // --- Initialization ---

    document.addEventListener('DOMContentLoaded', function () {
        configureFlatpickrLocale();
        initDateFields();
        setupHTMXFallback();
        initSidebarAndTooltips();
    });

    // Re-initialize when modals are opened
    document.addEventListener('shown.bs.modal', function () {
        setTimeout(function () {
            if (window.initDateFields) window.initDateFields();
        }, 100);
    });

    // ========================================
    // SISTEMA DE TOASTS
    // ========================================
    window.showToast = function (message, type = 'info', duration = 5000) {
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            return;
        }

        const toastId = 'toast-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        const bgClass = {
            'success': 'bg-success',
            'error': 'bg-danger',
            'warning': 'bg-warning',
            'info': 'bg-info',
            'primary': 'bg-primary'
        }[type] || 'bg-info';

        const icon = {
            'success': 'bi-check-circle-fill',
            'error': 'bi-x-circle-fill',
            'warning': 'bi-exclamation-triangle-fill',
            'info': 'bi-info-circle-fill',
            'primary': 'bi-bell-fill'
        }[type] || 'bi-info-circle-fill';

        const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
          <div class="d-flex">
            <div class="toast-body d-flex align-items-center">
              <i class="bi ${icon} me-2"></i>
              <span>${message}</span>
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>
        </div>
      `;

        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: duration
        });
        toast.show();

        toastElement.addEventListener('hidden.bs.toast', function () {
            toastElement.remove();
        });
    };

    // ========================================
    // SISTEMA DE CONFIRMAÇÕES INTELIGENTES
    // ========================================
    window.showConfirm = function (options) {
        return new Promise((resolve) => {
            const {
                title = 'Confirmar ação',
                message = 'Tem certeza que deseja continuar?',
                confirmText = 'Confirmar',
                cancelText = 'Cancelar',
                type = 'warning',
                icon = 'bi-exclamation-triangle-fill'
            } = options;

            const modalId = 'confirmModal-' + Date.now();
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
                  <button type="button" class="btn btn-${type === 'danger' ? 'danger' : 'primary'}" id="${modalId}Confirm">${confirmText}</button>
                </div>
              </div>
            </div>
          </div>
        `;

            document.body.insertAdjacentHTML('beforeend', modalHTML);
            const modalElement = document.getElementById(modalId);
            const modal = new bootstrap.Modal(modalElement);

            document.getElementById(modalId + 'Confirm').addEventListener('click', () => {
                modal.hide();
                resolve(true);
                modalElement.addEventListener('hidden.bs.modal', () => modalElement.remove(), { once: true });
            });

            modalElement.addEventListener('hidden.bs.modal', () => {
                resolve(false);
                modalElement.remove();
            }, { once: true });

            modal.show();
        });
    };

    // ========================================
    // LOADING STATES - Skeleton Screen Helper
    // ========================================
    window.showSkeleton = function (container, count = 3) {
        if (!container) return;

        const skeletonHTML = `
        <div class="skeleton-item mb-3">
          <div class="skeleton-line" style="height: 20px; width: 60%; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: skeleton-loading 1.5s ease-in-out infinite; border-radius: 4px; margin-bottom: 10px;"></div>
          <div class="skeleton-line" style="height: 16px; width: 100%; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: skeleton-loading 1.5s ease-in-out infinite; border-radius: 4px; margin-bottom: 8px;"></div>
          <div class="skeleton-line" style="height: 16px; width: 80%; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: skeleton-loading 1.5s ease-in-out infinite; border-radius: 4px;"></div>
        </div>
      `;

        container.innerHTML = skeletonHTML.repeat(count);
    };

    // Adicionar animação CSS para skeleton
    if (!document.getElementById('skeleton-styles')) {
        const style = document.createElement('style');
        style.id = 'skeleton-styles';
        style.textContent = `
        @keyframes skeleton-loading {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
        .skeleton-item {
          padding: 1rem;
          background: #fff;
          border-radius: 8px;
          border: 1px solid #e9ecef;
        }
      `;
        document.head.appendChild(style);
    }

    // --- Global Modals Initialization ---
    function initGlobalModals() {
        // Modal Gerenciar Usuários
        const modalGerenciarUsuarios = document.getElementById('modalGerenciarUsuarios');
        if (modalGerenciarUsuarios) {
            const urlParams = new URLSearchParams(window.location.search);
            const shouldOpenModal = urlParams.get('open_users_modal') === 'true';
            const loadManagementContent = () => {
                const contentDiv = document.getElementById('users-management-content');
                const spinnerHTML = `<div class="text-center py-5" id="users-loading-spinner"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Carregando...</span></div><p class="mt-2">Carregando lista de usuários...</p></div>`;
                contentDiv.innerHTML = spinnerHTML;
                const url = modalGerenciarUsuarios.dataset.url || '/management/users/modal';
                fetch(url)
                    .then(response => { if (!response.ok) { return response.text().then(text => { throw new Error(text || `Erro ${response.status} ao carregar usuários.`); }); } return response.text(); })
                    .then(html => { contentDiv.innerHTML = html; })
                    .catch(error => { console.error('Erro ao carregar gerenciamento de usuários:', error); contentDiv.innerHTML = `<div class="alert alert-danger">Falha ao carregar a lista de usuários. Detalhes: ${error.message}</div>`; });
            };
            modalGerenciarUsuarios.addEventListener('shown.bs.modal', loadManagementContent);
            if (shouldOpenModal) { setTimeout(() => { const bsModal = bootstrap.Modal.getOrCreateInstance(modalGerenciarUsuarios); if (bsModal) { bsModal.show(); const currentUrl = new URL(window.location); currentUrl.searchParams.delete('open_users_modal'); history.replaceState(null, '', currentUrl.toString()); } }, 100); }
        }

        // Modal Perfil
        const modalPerfil = document.getElementById('modalPerfil');
        if (modalPerfil) {
            const urlParams = new URLSearchParams(window.location.search);
            const shouldOpenProfileModal = urlParams.get('open_profile_modal') === 'true';
            const loadProfileContent = () => {
                const contentDiv = document.getElementById('profile-content');
                const spinnerHTML = `<div class="text-center py-5" id="profile-loading-spinner"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Carregando...</span></div><p class="mt-2">Carregando perfil...</p></div>`;
                contentDiv.innerHTML = spinnerHTML;
                const url = modalPerfil.dataset.url || '/profile/modal';
                fetch(url)
                    .then(response => { if (!response.ok) { return response.text().then(text => { throw new Error(text || `Erro ${response.status} ao carregar perfil.`); }); } return response.text(); })
                    .then(html => {
                        contentDiv.innerHTML = html;

                        // Adicionar preview de foto
                        const fotoInput = document.getElementById('foto');
                        if (fotoInput) {
                            fotoInput.addEventListener('change', function (e) {
                                const file = e.target.files[0];
                                if (file && file.type.startsWith('image/')) {
                                    const reader = new FileReader();
                                    reader.onload = function (event) {
                                        const previewContainer = document.getElementById('profile-photo-preview');
                                        if (previewContainer) {
                                            // Se for uma div (placeholder), substituir por img
                                            if (previewContainer.tagName === 'DIV') {
                                                const img = document.createElement('img');
                                                img.id = 'profile-photo-preview';
                                                img.alt = 'Foto de Perfil';
                                                img.className = 'rounded-circle border';
                                                img.style.cssText = 'width: 96px; height: 96px; object-fit: cover;';
                                                img.src = event.target.result;
                                                previewContainer.parentNode.replaceChild(img, previewContainer);
                                            } else {
                                                // Se já for img, apenas atualizar o src
                                                previewContainer.src = event.target.result;
                                            }
                                        }
                                    };
                                    reader.readAsDataURL(file);
                                }
                            });
                        }
                    })
                    .catch(error => { console.error('Erro ao carregar perfil:', error); contentDiv.innerHTML = `<div class="alert alert-danger">Falha ao carregar o perfil. Detalhes: ${error.message}</div>`; });
            };
            modalPerfil.addEventListener('shown.bs.modal', loadProfileContent);
            modalPerfil.addEventListener('submit', function (ev) {
                const form = ev.target;
                if (!form || !modalPerfil.contains(form)) return;
                ev.preventDefault();
                try {
                    const contentDiv = document.getElementById('profile-content');
                    const postUrl = form.getAttribute('hx-post') || form.getAttribute('action');
                    if (!postUrl) { form.submit(); return; }
                    const fd = new FormData(form);
                    fetch(postUrl, { method: 'POST', body: fd, headers: { 'HX-Request': 'true' } })
                        .then(function (r) { return r.text(); })
                        .then(function (html) { contentDiv.innerHTML = html; })
                        .catch(function (err) { console.error('Falha ao salvar perfil no modal:', err); });
                } catch (e) { console.error('Erro ao interceptar submit no modal Perfil:', e); }
            }, true);
            if (shouldOpenProfileModal) {
                setTimeout(() => {
                    const bsModal = bootstrap.Modal.getOrCreateInstance(modalPerfil);
                    if (bsModal) {
                        bsModal.show();
                        const currentUrl = new URL(window.location);
                        currentUrl.searchParams.delete('open_profile_modal');
                        history.replaceState(null, '', currentUrl.toString());
                    }
                }, 100);
            }
        }
    }

    // Call initGlobalModals on load
    document.addEventListener('DOMContentLoaded', function () {
        initGlobalModals();
    });

})();
