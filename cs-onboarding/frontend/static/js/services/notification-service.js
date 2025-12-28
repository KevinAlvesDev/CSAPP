/**
 * Notification Service - Camada de notificações ao usuário
 * 
 * Implementa Single Responsibility (SOLID - S): Apenas notificações
 * Implementa Open/Closed (SOLID - O): Extensível via strategies
 * Implementa Interface Segregation (SOLID - I): Métodos específicos
 * 
 * @example
 * const notifier = new NotificationService({ toast: showToast, confirm: showConfirm });
 * notifier.success('Salvo com sucesso!');
 * const confirmed = await notifier.confirm({ message: 'Tem certeza?' });
 */
class NotificationService {
    /**
     * @param {Object} strategies - Estratégias de notificação
     */
    constructor(strategies = {}) {
        this.strategies = {
            toast: strategies.toast || (window.showToast ? window.showToast.bind(window) : null),
            confirm: strategies.confirm || (window.showConfirm ? window.showConfirm.bind(window) : null),
            ...strategies
        };
    }

    /**
     * Mostra notificação de sucesso
     * @param {string} message - Mensagem
     * @param {number} duration - Duração em ms
     */
    success(message, duration = 5000) {
        if (this.strategies.toast) {
            return this.strategies.toast(message, 'success', duration);
        }
        console.log('[SUCCESS]', message);
    }

    /**
     * Mostra notificação de erro
     * @param {string} message - Mensagem
     * @param {number} duration - Duração em ms
     */
    error(message, duration = 5000) {
        if (this.strategies.toast) {
            return this.strategies.toast(message, 'error', duration);
        }
        console.error('[ERROR]', message);
    }

    /**
     * Mostra notificação de aviso
     * @param {string} message - Mensagem
     * @param {number} duration - Duração em ms
     */
    warning(message, duration = 5000) {
        if (this.strategies.toast) {
            return this.strategies.toast(message, 'warning', duration);
        }
        console.warn('[WARNING]', message);
    }

    /**
     * Mostra notificação informativa
     * @param {string} message - Mensagem
     * @param {number} duration - Duração em ms
     */
    info(message, duration = 5000) {
        if (this.strategies.toast) {
            return this.strategies.toast(message, 'info', duration);
        }
        console.info('[INFO]', message);
    }

    /**
     * Mostra diálogo de confirmação
     * @param {Object|string} options - Opções ou mensagem
     * @returns {Promise<boolean>}
     */
    async confirm(options) {
        if (this.strategies.confirm) {
            // Se options é string, converte para objeto
            const opts = typeof options === 'string' ? { message: options } : options;
            return this.strategies.confirm(opts);
        }

        // Fallback para confirm nativo
        const message = typeof options === 'string' ? options : options.message;
        return window.confirm(message);
    }

    /**
     * Adiciona nova estratégia de notificação (Open/Closed Principle)
     * @param {string} name - Nome da estratégia
     * @param {Function} implementation - Implementação
     */
    addStrategy(name, implementation) {
        this.strategies[name] = implementation;
        return this;
    }

    /**
     * Executa estratégia customizada
     * @param {string} name - Nome da estratégia
     * @param  {...any} args - Argumentos
     */
    execute(name, ...args) {
        if (this.strategies[name]) {
            return this.strategies[name](...args);
        }
        throw new Error(`Notification strategy "${name}" not found`);
    }
}

// Export para uso global
if (typeof window !== 'undefined') {
    window.NotificationService = NotificationService;
}
