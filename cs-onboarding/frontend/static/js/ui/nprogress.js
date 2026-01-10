/**
 * CS Onboarding - NProgress Bar
 * Extracted from common.js for better maintainability.
 * 
 * @module ui/nprogress
 * @description Minimal progress bar for API requests.
 */

(function (global) {
    'use strict';

    // ========================================
    // INJECT CSS STYLES
    // ========================================

    function injectNProgressStyles() {
        if (document.getElementById('nprogress-styles')) return;

        const style = document.createElement('style');
        style.id = 'nprogress-styles';
        style.textContent = `
            #nprogress-container {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
                z-index: 99999;
                pointer-events: none;
            }
            #nprogress-bar {
                height: 100%;
                background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
                background-size: 200% 100%;
                animation: nprogress-gradient 2s ease infinite;
                box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
                width: 0%;
                opacity: 0;
                transition: width 0.2s ease-out, opacity 0.3s ease;
            }
            @keyframes nprogress-gradient {
                0% { background-position: 100% 0; }
                100% { background-position: -100% 0; }
            }
        `;
        document.head.appendChild(style);
    }

    // Inject styles when module loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectNProgressStyles);
    } else {
        injectNProgressStyles();
    }

    // ========================================
    // NPROGRESS IMPLEMENTATION
    // ========================================

    const NProgress = {
        activeRequests: 0,
        timer: null,

        /**
         * Gets or creates the progress bar element.
         */
        get element() {
            let el = document.getElementById('nprogress-bar');
            if (!el) {
                const container = document.createElement('div');
                container.id = 'nprogress-container';
                container.innerHTML = '<div id="nprogress-bar"></div>';
                document.body.appendChild(container);
                el = container.firstChild;
            }
            return el;
        },

        /**
         * Starts the progress bar.
         */
        start() {
            if (this.activeRequests === 0) {
                const el = this.element;
                el.style.transition = 'none';
                el.style.opacity = '1';
                el.style.width = '0%';

                // Force reflow
                void el.offsetWidth;

                el.style.transition = 'width 0.2s ease-out, opacity 0.3s ease';
                el.style.width = '15%';
                this.simulateProgress();
            }
            this.activeRequests++;
        },

        /**
         * Simulates progress animation.
         */
        simulateProgress() {
            if (this.timer) clearInterval(this.timer);
            this.timer = setInterval(() => {
                const currentWidth = parseFloat(this.element.style.width) || 0;
                if (currentWidth < 90) {
                    const inc = Math.random() * 5;
                    this.element.style.width = (currentWidth + inc) + '%';
                }
            }, 300);
        },

        /**
         * Completes the progress bar.
         */
        done() {
            this.activeRequests--;
            if (this.activeRequests <= 0) {
                this.activeRequests = 0;
                if (this.timer) clearInterval(this.timer);

                this.element.style.width = '100%';

                setTimeout(() => {
                    this.element.style.opacity = '0';
                    setTimeout(() => {
                        this.element.style.width = '0%';
                    }, 300);
                }, 200);
            }
        },

        /**
         * Sets progress to a specific percentage.
         * @param {number} percent - Progress percentage (0-100)
         */
        set(percent) {
            const p = Math.max(0, Math.min(100, percent));
            this.element.style.opacity = '1';
            this.element.style.width = p + '%';
        }
    };

    // ========================================
    // EXPORTS
    // ========================================

    global.NProgress = NProgress;

    console.log('✅ NProgress module loaded');

})(typeof window !== 'undefined' ? window : this);
