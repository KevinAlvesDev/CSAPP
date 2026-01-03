/**
 * Bug Prevention Service
 * Sistema de detecção automática de problemas comuns
 * 
 * Monitora:
 * - Erros de JavaScript
 * - Chamadas de API falhando
 * - Elementos DOM faltando
 * - Performance lenta
 * - Dados inconsistentes
 */

(function () {
    'use strict';

    const BugPreventionService = {
        enabled: true, // Desabilitar em produção
        errors: [],
        warnings: [],
        apiCalls: [],
        performanceMetrics: {},

        init() {
            if (!this.enabled) return;

            console.log('🛡️ [Bug Prevention] Service initialized');

            // Monitor erros globais
            this.setupErrorMonitoring();

            // Monitor chamadas de API
            this.setupAPIMonitoring();

            // Monitor performance
            this.setupPerformanceMonitoring();

            // Monitor DOM
            this.setupDOMMonitoring();

            // Report periódico
            setInterval(() => this.generateReport(), 60000); // A cada 1 minuto
        },

        // =====================================================================
        // MONITORAMENTO DE ERROS
        // =====================================================================
        setupErrorMonitoring() {
            // Capturar erros não tratados
            window.addEventListener('error', (event) => {
                this.logError({
                    type: 'JavaScript Error',
                    message: event.message,
                    filename: event.filename,
                    line: event.lineno,
                    column: event.colno,
                    stack: event.error?.stack,
                    timestamp: new Date().toISOString()
                });
            });

            // Capturar promises rejeitadas
            window.addEventListener('unhandledrejection', (event) => {
                this.logError({
                    type: 'Unhandled Promise Rejection',
                    message: event.reason?.message || event.reason,
                    stack: event.reason?.stack,
                    timestamp: new Date().toISOString()
                });
            });

            console.log('✅ [Bug Prevention] Error monitoring active');
        },

        logError(error) {
            this.errors.push(error);

            console.group('❌ [Bug Prevention] ERROR DETECTED');
            console.error('Type:', error.type);
            console.error('Message:', error.message);
            if (error.filename) console.error('File:', error.filename, `Line ${error.line}:${error.column}`);
            if (error.stack) console.error('Stack:', error.stack);
            console.groupEnd();

            // Alerta visual
            if (window.showToast) {
                showToast(`🐛 Erro detectado: ${error.message}`, 'error', 5000);
            }

            // Limitar array de erros
            if (this.errors.length > 50) {
                this.errors = this.errors.slice(-50);
            }
        },

        // =====================================================================
        // MONITORAMENTO DE API
        // =====================================================================
        setupAPIMonitoring() {
            // Interceptar fetch
            const originalFetch = window.fetch;
            const self = this;

            window.fetch = function (...args) {
                const url = args[0];
                const startTime = performance.now();

                return originalFetch.apply(this, args)
                    .then(response => {
                        const duration = performance.now() - startTime;

                        self.logAPICall({
                            url,
                            method: args[1]?.method || 'GET',
                            status: response.status,
                            ok: response.ok,
                            duration,
                            timestamp: new Date().toISOString()
                        });

                        // Alerta se API está lenta
                        if (duration > 3000) {
                            self.logWarning({
                                type: 'Slow API',
                                message: `API call to ${url} took ${duration.toFixed(0)}ms`,
                                url,
                                duration
                            });
                        }

                        // Alerta se API falhou
                        if (!response.ok) {
                            self.logWarning({
                                type: 'API Error',
                                message: `API call to ${url} failed with status ${response.status}`,
                                url,
                                status: response.status
                            });
                        }

                        return response;
                    })
                    .catch(error => {
                        const duration = performance.now() - startTime;

                        self.logAPICall({
                            url,
                            method: args[1]?.method || 'GET',
                            status: 'ERROR',
                            ok: false,
                            duration,
                            error: error.message,
                            timestamp: new Date().toISOString()
                        });

                        self.logError({
                            type: 'API Network Error',
                            message: `Failed to fetch ${url}: ${error.message}`,
                            url,
                            error: error.message
                        });

                        throw error;
                    });
            };

            console.log('✅ [Bug Prevention] API monitoring active');
        },

        logAPICall(call) {
            this.apiCalls.push(call);

            if (!call.ok) {
                console.warn('⚠️ [Bug Prevention] API Call Failed:', call);
            }

            // Limitar array
            if (this.apiCalls.length > 100) {
                this.apiCalls = this.apiCalls.slice(-100);
            }
        },

        logWarning(warning) {
            this.warnings.push({
                ...warning,
                timestamp: new Date().toISOString()
            });

            console.warn('⚠️ [Bug Prevention] WARNING:', warning.message);

            // Limitar array
            if (this.warnings.length > 50) {
                this.warnings = this.warnings.slice(-50);
            }
        },

        // =====================================================================
        // MONITORAMENTO DE PERFORMANCE
        // =====================================================================
        setupPerformanceMonitoring() {
            // Monitor tempo de carregamento da página
            window.addEventListener('load', () => {
                const perfData = performance.timing;
                const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;

                this.performanceMetrics.pageLoad = pageLoadTime;

                console.log(`⏱️ [Bug Prevention] Page loaded in ${pageLoadTime}ms`);

                if (pageLoadTime > 5000) {
                    this.logWarning({
                        type: 'Slow Page Load',
                        message: `Page took ${pageLoadTime}ms to load`,
                        duration: pageLoadTime
                    });
                }
            });

            console.log('✅ [Bug Prevention] Performance monitoring active');
        },

        // =====================================================================
        // MONITORAMENTO DE DOM
        // =====================================================================
        setupDOMMonitoring() {
            // Verificar elementos críticos
            const checkCriticalElements = () => {
                const criticalSelectors = [
                    '#main-content',
                    '.modal',
                    'form'
                ];

                const missing = [];

                criticalSelectors.forEach(selector => {
                    if (!document.querySelector(selector)) {
                        missing.push(selector);
                    }
                });

                if (missing.length > 0) {
                    this.logWarning({
                        type: 'Missing DOM Elements',
                        message: `Critical elements not found: ${missing.join(', ')}`,
                        elements: missing
                    });
                }
            };

            // Verificar após DOM carregar
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', checkCriticalElements);
            } else {
                checkCriticalElements();
            }

            console.log('✅ [Bug Prevention] DOM monitoring active');
        },

        // =====================================================================
        // RELATÓRIOS
        // =====================================================================
        generateReport() {
            if (!this.enabled) return;

            const report = {
                timestamp: new Date().toISOString(),
                errors: this.errors.length,
                warnings: this.warnings.length,
                apiCalls: this.apiCalls.length,
                failedAPICalls: this.apiCalls.filter(c => !c.ok).length,
                slowAPICalls: this.apiCalls.filter(c => c.duration > 3000).length,
                performanceMetrics: this.performanceMetrics
            };

            console.group('📊 [Bug Prevention] Status Report');
            console.log('Errors:', report.errors);
            console.log('Warnings:', report.warnings);
            console.log('API Calls:', report.apiCalls);
            console.log('Failed API Calls:', report.failedAPICalls);
            console.log('Slow API Calls:', report.slowAPICalls);
            console.log('Performance:', report.performanceMetrics);
            console.groupEnd();

            // Alerta se houver muitos erros
            if (report.errors > 5) {
                console.error(`🚨 [Bug Prevention] HIGH ERROR COUNT: ${report.errors} errors detected!`);
            }

            return report;
        },

        // =====================================================================
        // UTILITÁRIOS
        // =====================================================================
        getErrors() {
            return this.errors;
        },

        getWarnings() {
            return this.warnings;
        },

        getAPICallStats() {
            const total = this.apiCalls.length;
            const failed = this.apiCalls.filter(c => !c.ok).length;
            const slow = this.apiCalls.filter(c => c.duration > 3000).length;
            const avgDuration = this.apiCalls.reduce((sum, c) => sum + c.duration, 0) / total;

            return {
                total,
                failed,
                slow,
                avgDuration: avgDuration.toFixed(0),
                successRate: ((total - failed) / total * 100).toFixed(1) + '%'
            };
        },

        clearLogs() {
            this.errors = [];
            this.warnings = [];
            this.apiCalls = [];
            console.log('🧹 [Bug Prevention] Logs cleared');
        }
    };

    // Inicializar automaticamente
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => BugPreventionService.init());
    } else {
        BugPreventionService.init();
    }

    // Expor globalmente
    window.BugPreventionService = BugPreventionService;

    console.log('🛡️ [Bug Prevention] Service loaded');

})();
