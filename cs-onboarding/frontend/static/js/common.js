/**
 * CS Onboarding - Common Scripts (Refactored)
 * 
 * This file has been refactored to use modular architecture.
 * Most functionality has been extracted to separate modules:
 * 
 * - utils/date-utils.js     - Date formatting, validation, masking, Flatpickr
 * - utils/phone-utils.js    - Phone formatting and validation
 * - utils/html-utils.js     - HTML escaping, progress bar, multi-select
 * - ui/toast.js             - Toast notifications
 * - ui/confirm-dialog.js    - Confirmation dialogs
 * - ui/loading.js           - Skeleton loading states
 * - ui/nprogress.js         - Request progress bar
 * - ui/sidebar.js           - Sidebar navigation, theme toggle, tooltips
 * 
 * This file now only contains:
 * - Service Container initialization
 * - HTMX Polyfill (legacy)
 * - Global Modals initialization
 * - API Client (apiFetch)
 * - UX Enhancements (animations, ripple effects)
 */

(function () {
    'use strict';

    // ========================================
    // SERVICE CONTAINER INITIALIZATION
    // ========================================

    // Create container global (Dependency Injection)
    window.appContainer = window.ServiceContainer ? new window.ServiceContainer() : null;

    // Function to initialize services (called after dependencies are loaded)
    window.initializeServices = function () {
        if (!window.appContainer) return;

        // Register NProgress
        window.appContainer.registerValue('progress', window.NProgress);

        // Register base functions
        window.appContainer.registerValue('showToast', window.showToast);
        window.appContainer.registerValue('showConfirm', window.showConfirm);
        window.appContainer.registerValue('apiFetch', window.apiFetch);

        // Register NotificationService
        if (window.NotificationService) {
            window.appContainer.register('notifier', (container) => {
                return new window.NotificationService({
                    toast: container.resolve('showToast'),
                    confirm: container.resolve('showConfirm')
                });
            });
        }

        // Register ApiService
        if (window.ApiService) {
            window.appContainer.register('api', (container) => {
                return new window.ApiService(
                    container.resolve('apiFetch'),
                    container.resolve('progress'),
                    container.resolve('notifier')
                );
            });
        }

        // Expose services globally for backward compatibility
        if (window.appContainer.has('api')) {
            window.$api = window.appContainer.resolve('api');
        }
        if (window.appContainer.has('notifier')) {
            window.$notifier = window.appContainer.resolve('notifier');
        }

        // Register ChecklistAPI
        if (window.ChecklistAPI) {
            window.appContainer.register('checklistAPI', (container) => {
                return new window.ChecklistAPI(container.resolve('api'));
            });
        }

        // Register ChecklistService
        if (window.ChecklistService) {
            window.appContainer.register('checklistService', (container) => {
                return new window.ChecklistService(
                    container.resolve('checklistAPI'),
                    container.resolve('notifier')
                );
            });
        }

        // Register ConfigService
        if (window.ConfigService) {
            window.appContainer.register('configService', (container) => {
                return new window.ConfigService(container.resolve('api'));
            });
        }

        // Expose ConfigService globally
        if (window.appContainer.has('configService')) {
            window.$configService = window.appContainer.resolve('configService');
        }

        // Expose ChecklistService globally
        if (window.appContainer.has('checklistService')) {
            window.$checklistService = window.appContainer.resolve('checklistService');
        }

        console.log('✅ Service Container initialized');
    };

    // ========================================
    // HTMX POLYFILL (Legacy)
    // ========================================

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

        // HTMX Error handling
        document.addEventListener('htmx:responseError', function () {
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

    // ========================================
    // GLOBAL MODALS INITIALIZATION
    // ========================================

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

                        // Add photo preview handler
                        const fotoInput = document.getElementById('foto');
                        if (fotoInput) {
                            fotoInput.addEventListener('change', function (e) {
                                const file = e.target.files[0];
                                if (file && file.type.startsWith('image/')) {
                                    const reader = new FileReader();
                                    reader.onload = function (event) {
                                        const previewContainer = document.getElementById('profile-photo-preview');
                                        if (previewContainer) {
                                            if (previewContainer.tagName === 'DIV') {
                                                const img = document.createElement('img');
                                                img.id = 'profile-photo-preview';
                                                img.alt = 'Foto de Perfil';
                                                img.className = 'rounded-circle border';
                                                img.style.cssText = 'width: 96px; height: 96px; object-fit: cover;';
                                                img.src = event.target.result;
                                                previewContainer.parentNode.replaceChild(img, previewContainer);
                                            } else {
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
                        .then(function (r) {
                            const updatedPhoto = r.headers.get('X-Updated-Photo-Url');
                            const updatedName = r.headers.get('X-Updated-Name');

                            if (updatedPhoto) {
                                const els = document.querySelectorAll('.user-photo-global, #sidebar-user-photo');
                                els.forEach(function (img) {
                                    img.src = updatedPhoto + '?v=' + new Date().getTime();
                                });
                            }

                            if (updatedName) {
                                const els = document.querySelectorAll('.user-name-global, #sidebar-user-name');
                                els.forEach(function (el) {
                                    el.textContent = updatedName;
                                });
                            }

                            return r.text();
                        })
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

    // ========================================
    // API CLIENT WRAPPER
    // ========================================

    window.apiFetch = async function (url, options = {}) {
        // Start Progress Bar (unless suppressed)
        if (options.showProgress !== false && window.NProgress) {
            NProgress.start();
        }

        const defaultHeaders = {
            'X-Requested-With': 'XMLHttpRequest'
        };

        // Only set Content-Type to JSON if body is NOT FormData
        if (!(options.body instanceof FormData)) {
            defaultHeaders['Content-Type'] = 'application/json';
        }

        // Auto-inject CSRF Token
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value ||
            document.querySelector('meta[name="csrf-token"]')?.content;

        if (csrfToken) {
            defaultHeaders['X-CSRFToken'] = csrfToken;
        }

        const config = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, config);

            // Handle 401 Unauthorized
            if (response.status === 401) {
                window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                return;
            }

            // Handle non-2xx responses
            if (!response.ok) {
                let errorMessage = `Erro na requisição (${response.status})`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorData.message || errorMessage;
                } catch (e) {
                    try {
                        const text = await response.text();
                        if (text && text.length < 200) errorMessage = text;
                    } catch (e2) { }
                }
                throw new Error(errorMessage);
            }

            // Return JSON by default
            if (options.parseJson === false) return response;
            return await response.json();

        } catch (error) {
            console.error('API Error:', error);
            if (options.showErrorToast !== false && window.showToast) {
                window.showToast(error.message, 'error');
            }
            throw error;
        } finally {
            if (options.showProgress !== false && window.NProgress) {
                NProgress.done();
            }
        }
    };

    // ========================================
    // UX ENHANCEMENTS
    // ========================================

    function initUXEnhancements() {
        // 1. Entrance Animations for Cards
        const cards = document.querySelectorAll('.card, .metric-card, .list-group-item');
        cards.forEach((card, index) => {
            if (index < 20) {
                card.classList.add('animate-fade-in-up');
                card.style.animationDelay = `${index * 50}ms`;
            } else {
                card.classList.add('animate-fade-in');
            }
        });

        // 2. Ripple Effect for Buttons
        document.body.addEventListener('click', function (e) {
            const btn = e.target.closest('.btn');
            if (btn && !btn.disabled) {
                const rect = btn.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                const ripple = document.createElement('span');
                ripple.classList.add('ripple');
                ripple.style.left = `${x}px`;
                ripple.style.top = `${y}px`;

                const existing = btn.querySelector('.ripple');
                if (existing) existing.remove();

                btn.appendChild(ripple);
                setTimeout(() => ripple.remove(), 600);
            }
        });

        // 3. Real-time Form Validation
        const emailInputs = document.querySelectorAll('input[type="email"]');
        emailInputs.forEach(input => {
            input.addEventListener('blur', function () { validateEmail(this); });
            input.addEventListener('input', function () {
                if (this.classList.contains('is-invalid')) validateEmail(this);
            });
        });

        const requiredInputs = document.querySelectorAll('input[required], textarea[required], select[required]');
        requiredInputs.forEach(input => {
            input.addEventListener('blur', function () { validateRequired(this); });
        });

        function validateEmail(input) {
            const value = input.value.trim();
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

            if (value && !emailRegex.test(value)) {
                input.classList.add('is-invalid');
                input.classList.remove('is-valid');
                showFieldError(input, 'Email inválido');
            } else if (value) {
                input.classList.remove('is-invalid');
                input.classList.add('is-valid');
                removeFieldError(input);
            } else {
                input.classList.remove('is-invalid', 'is-valid');
                removeFieldError(input);
            }
        }

        function validateRequired(input) {
            const value = input.value.trim();
            if (!value) {
                input.classList.add('is-invalid');
                input.classList.remove('is-valid');
                showFieldError(input, 'Campo obrigatório');
            } else {
                input.classList.remove('is-invalid');
                input.classList.add('is-valid');
                removeFieldError(input);
            }
        }

        function showFieldError(input, message) {
            removeFieldError(input);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback d-block';
            errorDiv.textContent = message;
            errorDiv.dataset.validationError = 'true';
            input.parentNode.appendChild(errorDiv);
        }

        function removeFieldError(input) {
            const existing = input.parentNode.querySelector('[data-validation-error]');
            if (existing) existing.remove();
        }
    }

    // ========================================
    // RE-INITIALIZE DATE FIELDS ON MODAL OPEN
    // ========================================

    document.addEventListener('shown.bs.modal', function () {
        setTimeout(function () {
            if (window.initDateFields) window.initDateFields();
        }, 100);
    });

    // ========================================
    // INITIALIZATION
    // ========================================

    document.addEventListener('DOMContentLoaded', function () {
        // Initialize Flatpickr locale (from date-utils.js)
        if (window.configureFlatpickrLocale) {
            window.configureFlatpickrLocale();
        }

        // Initialize date fields (from date-utils.js)
        if (window.initDateFields) {
            window.initDateFields();
        }

        // Setup HTMX fallback
        setupHTMXFallback();

        // Initialize global modals
        initGlobalModals();

        // Initialize UX enhancements
        initUXEnhancements();

        console.log('✅ Common.js initialized (refactored)');
    });

    // Initialize Service Container
    if (typeof window.initializeServices === 'function') {
        window.initializeServices();
    }

})();
