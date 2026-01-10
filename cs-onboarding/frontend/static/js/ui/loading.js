/**
 * CS Onboarding - Skeleton Loading Helper
 * Extracted from common.js for better maintainability.
 * 
 * @module ui/loading
 * @description Skeleton screen loading states.
 */

(function (global) {
    'use strict';

    // ========================================
    // INJECT CSS STYLES
    // ========================================

    function injectSkeletonStyles() {
        if (document.getElementById('skeleton-styles')) return;

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
            .dark-mode .skeleton-item {
                background: #1e293b;
                border-color: #334155;
            }
            .skeleton-line {
                background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                background-size: 200% 100%;
                animation: skeleton-loading 1.5s ease-in-out infinite;
                border-radius: 4px;
            }
            .dark-mode .skeleton-line {
                background: linear-gradient(90deg, #334155 25%, #475569 50%, #334155 75%);
                background-size: 200% 100%;
            }
        `;
        document.head.appendChild(style);
    }

    // Inject styles when module loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectSkeletonStyles);
    } else {
        injectSkeletonStyles();
    }

    // ========================================
    // SKELETON SCREEN FUNCTION
    // ========================================

    /**
     * Shows a skeleton loading screen in a container.
     * 
     * @param {HTMLElement} container - Container element to fill with skeleton
     * @param {number} [count=3] - Number of skeleton items to show
     */
    function showSkeleton(container, count = 3) {
        if (!container) return;

        const skeletonHTML = `
        <div class="skeleton-item mb-3">
            <div class="skeleton-line" style="height: 20px; width: 60%; margin-bottom: 10px;"></div>
            <div class="skeleton-line" style="height: 16px; width: 100%; margin-bottom: 8px;"></div>
            <div class="skeleton-line" style="height: 16px; width: 80%;"></div>
        </div>
        `;

        container.innerHTML = skeletonHTML.repeat(count);
    }

    /**
     * Shows a table skeleton loading screen.
     * 
     * @param {HTMLElement} container - Container element
     * @param {number} [rows=5] - Number of rows
     * @param {number} [cols=4] - Number of columns
     */
    function showTableSkeleton(container, rows = 5, cols = 4) {
        if (!container) return;

        let html = '<table class="table"><tbody>';
        for (let r = 0; r < rows; r++) {
            html += '<tr>';
            for (let c = 0; c < cols; c++) {
                const width = 50 + Math.random() * 40;
                html += `<td><div class="skeleton-line" style="height: 16px; width: ${width}%;"></div></td>`;
            }
            html += '</tr>';
        }
        html += '</tbody></table>';

        container.innerHTML = html;
    }

    /**
     * Shows a card skeleton loading screen.
     * 
     * @param {HTMLElement} container - Container element
     * @param {number} [count=3] - Number of cards
     */
    function showCardSkeleton(container, count = 3) {
        if (!container) return;

        const cardHTML = `
        <div class="col-md-4 mb-3">
            <div class="card skeleton-item">
                <div class="card-body">
                    <div class="skeleton-line" style="height: 24px; width: 70%; margin-bottom: 16px;"></div>
                    <div class="skeleton-line" style="height: 14px; width: 100%; margin-bottom: 8px;"></div>
                    <div class="skeleton-line" style="height: 14px; width: 90%; margin-bottom: 8px;"></div>
                    <div class="skeleton-line" style="height: 14px; width: 60%;"></div>
                </div>
            </div>
        </div>
        `;

        container.innerHTML = '<div class="row">' + cardHTML.repeat(count) + '</div>';
    }

    // ========================================
    // EXPORTS
    // ========================================

    // Create Loading namespace
    var Loading = {
        showSkeleton: showSkeleton,
        showTableSkeleton: showTableSkeleton,
        showCardSkeleton: showCardSkeleton
    };

    // Expose to global scope for backward compatibility
    global.Loading = Loading;
    global.showSkeleton = showSkeleton;

    console.log('✅ Loading module loaded');

})(typeof window !== 'undefined' ? window : this);
