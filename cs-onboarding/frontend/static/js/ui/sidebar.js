/**
 * CS Onboarding - Sidebar Module
 * Extracted from common.js for better maintainability.
 * 
 * @module ui/sidebar
 * @description Sidebar navigation and theme toggle functionality.
 */

(function (global) {
    'use strict';

    // ========================================
    // SIDEBAR TOGGLE
    // ========================================

    /**
     * Initializes sidebar toggle functionality.
     */
    function initSidebar() {
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.getElementById('menu');
        const mainContent = document.querySelector('.main-content');

        if (!sidebarToggle || !sidebar) return;

        function updateMainContent() {
            const isCompactViewport = global.matchMedia && global.matchMedia('(max-width: 1200px)').matches;
            if (isCompactViewport) {
                sidebar.classList.add('collapsed');
                if (mainContent) {
                    mainContent.style.marginLeft = '60px';
                    mainContent.style.width = 'calc(100% - 60px)';
                }
                return;
            }

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

        // Load saved state
        const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        if (isCollapsed) {
            sidebar.classList.add('collapsed');
        }
        updateMainContent();

        // Update toggle icon
        const icon = sidebarToggle.querySelector('i');
        if (icon) {
            icon.style.transform = isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
        }

        // Toggle handler
        sidebarToggle.addEventListener('click', function () {
            if (global.matchMedia && global.matchMedia('(max-width: 1200px)').matches) {
                // Em viewport compacto, manter sidebar no modo compacto para evitar quebra em zoom alto.
                updateMainContent();
                return;
            }
            sidebar.classList.toggle('collapsed');
            const icon = sidebarToggle.querySelector('i');
            if (icon) {
                icon.style.transform = sidebar.classList.contains('collapsed') ? 'rotate(180deg)' : 'rotate(0deg)';
            }
            updateMainContent();
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
        });

        // Recalcula layout em resize/zoom (zoom altera viewport efetivo).
        global.addEventListener('resize', updateMainContent);
    }

    // ========================================
    // THEME TOGGLE (Dark Mode)
    // ========================================

    /**
     * Applies a theme to the page.
     * @param {boolean} isDark - Whether to apply dark mode
     */
    function applyTheme(isDark) {
        const themeIcon = document.getElementById('themeIcon');
        const themeText = document.getElementById('themeText');

        if (isDark) {
            document.documentElement.setAttribute('data-bs-theme', 'dark');
            document.documentElement.classList.add('dark-mode');
            document.body.classList.add('dark-mode');
            if (themeIcon) {
                themeIcon.classList.remove('bi-moon-stars');
                themeIcon.classList.add('bi-sun-fill');
            }
            if (themeText) themeText.textContent = 'Tema Claro';
        } else {
            document.documentElement.removeAttribute('data-bs-theme');
            document.documentElement.classList.remove('dark-mode');
            document.body.classList.remove('dark-mode');
            if (themeIcon) {
                themeIcon.classList.remove('bi-sun-fill');
                themeIcon.classList.add('bi-moon-stars');
            }
            if (themeText) themeText.textContent = 'Tema Escuro';
        }
    }

    /**
     * Initializes theme toggle functionality.
     */
    function initTheme() {
        const themeToggle = document.getElementById('themeToggle');

        // Load saved theme
        const savedTheme = localStorage.getItem('theme');
        const prefersDark = global.matchMedia && global.matchMedia('(prefers-color-scheme: dark)').matches;
        const isDarkMode = savedTheme === 'dark' || (savedTheme === null && prefersDark);
        applyTheme(isDarkMode);

        if (themeToggle) {
            themeToggle.addEventListener('click', function (e) {
                e.preventDefault();
                const isDark = document.body.classList.contains('dark-mode');
                applyTheme(!isDark);
                const newTheme = !isDark ? 'dark' : 'light';
                localStorage.setItem('theme', newTheme);
                // Set cookie for server-side rendering
                document.cookie = 'theme=' + newTheme + ';path=/;max-age=31536000';
            });
        }
    }

    // ========================================
    // TOOLTIPS
    // ========================================

    /**
     * Initializes Bootstrap tooltips.
     */
    function initTooltips() {
        try {
            if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                const tooltipEls = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
                tooltipEls.forEach(function (el) {
                    bootstrap.Tooltip.getOrCreateInstance(el);
                });
            }
        } catch (e) {
            console.warn('Failed to initialize tooltips:', e);
        }
    }

    // ========================================
    // MOBILE MENU HELPER
    // ========================================

    /**
     * Closes mobile menu when a modal opens.
     */
    function initMobileMenuHelper() {
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
                // If bigSlide is active, trigger close
                if (global.jQuery && jQuery.fn && jQuery.fn.bigSlide) {
                    jQuery('.menu-link').trigger('click');
                }
            } catch (e) { /* ignore */ }
        });
    }

    // ========================================
    // INITIALIZATION
    // ========================================

    /**
     * Initializes all sidebar and theme functionality.
     */
    function initSidebarAndTooltips() {
        initSidebar();
        initTheme();
        initTooltips();
        initMobileMenuHelper();
    }

    // Auto-initialize on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSidebarAndTooltips);
    } else {
        initSidebarAndTooltips();
    }

    // ========================================
    // EXPORTS
    // ========================================

    // Create Sidebar namespace
    var Sidebar = {
        init: initSidebar,
        initTheme: initTheme,
        initTooltips: initTooltips,
        applyTheme: applyTheme
    };

    global.Sidebar = Sidebar;

    console.log('✅ Sidebar module loaded');

})(typeof window !== 'undefined' ? window : this);
