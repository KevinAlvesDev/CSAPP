/**
 * API Service - Camada de comunicação HTTP
 * 
 * Implementa Single Responsibility (SOLID - S): Apenas comunicação HTTP
 * Implementa Dependency Inversion (SOLID - D): Depende de abstrações, não implementações
 * Implementa Interface Segregation (SOLID - I): Métodos focados e específicos
 * 
 * @example
 * const api = new ApiService(httpClient, progressBar, notifier);
 * const data = await api.get('/api/users');
 * await api.post('/api/users', { name: 'John' });
 */
class ApiService {
    /**
     * @param {Function} httpClient - Cliente HTTP (ex: window.apiFetch)
     * @param {Object} progressBar - Serviço de barra de progresso
     * @param {Object} notifier - Serviço de notificações
     */
    constructor(httpClient, progressBar, notifier) {
        this.http = httpClient;
        this.progress = progressBar;
        this.notifier = notifier;
    }

    /**
     * Requisição HTTP genérica
     * @param {string} url - URL da requisição
     * @param {Object} options - Opções da requisição
     * @returns {Promise<*>} Resposta da requisição
     */
    async request(url, options = {}) {
        const showProgress = options.showProgress !== false;
        const showErrorToast = options.showErrorToast !== false;

        if (showProgress && this.progress) {
            this.progress.start();
        }

        try {
            const response = await this.http(url, options);
            return response;
        } catch (error) {
            if (showErrorToast && this.notifier) {
                this.notifier.error(error.message);
            }
            throw error;
        } finally {
            if (showProgress && this.progress) {
                this.progress.done();
            }
        }
    }

    /**
     * GET request
     * @param {string} url - URL da requisição
     * @param {Object} options - Opções adicionais
     * @returns {Promise<*>}
     */
    async get(url, options = {}) {
        return this.request(url, { ...options, method: 'GET' });
    }

    /**
     * POST request
     * @param {string} url - URL da requisição
     * @param {*} data - Dados a enviar
     * @param {Object} options - Opções adicionais
     * @returns {Promise<*>}
     */
    async post(url, data, options = {}) {
        const body = data instanceof FormData ? data : JSON.stringify(data);
        return this.request(url, { ...options, method: 'POST', body });
    }

    /**
     * PUT request
     * @param {string} url - URL da requisição
     * @param {*} data - Dados a enviar
     * @param {Object} options - Opções adicionais
     * @returns {Promise<*>}
     */
    async put(url, data, options = {}) {
        const body = data instanceof FormData ? data : JSON.stringify(data);
        return this.request(url, { ...options, method: 'PUT', body });
    }

    /**
     * DELETE request
     * @param {string} url - URL da requisição
     * @param {Object} options - Opções adicionais
     * @returns {Promise<*>}
     */
    async delete(url, options = {}) {
        return this.request(url, { ...options, method: 'DELETE' });
    }

    /**
     * PATCH request
     * @param {string} url - URL da requisição
     * @param {*} data - Dados a enviar
     * @param {Object} options - Opções adicionais
     * @returns {Promise<*>}
     */
    async patch(url, data, options = {}) {
        const body = data instanceof FormData ? data : JSON.stringify(data);
        return this.request(url, { ...options, method: 'PATCH', body });
    }
}

// Export para uso global
if (typeof window !== 'undefined') {
    window.ApiService = ApiService;
}
