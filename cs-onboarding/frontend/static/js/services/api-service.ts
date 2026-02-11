/**
 * API Service - Camada de comunicação HTTP (TypeScript)
 *
 * Implementa Single Responsibility (SOLID - S): Apenas comunicação HTTP
 * Implementa Dependency Inversion (SOLID - D): Depende de interfaces, não implementações
 * Implementa Interface Segregation (SOLID - I): Métodos focados e específicos
 *
 * @example
 * const api = new ApiServiceClass(httpClient, progressBar, notifier);
 * const data = await api.get<User[]>('/api/users');
 * await api.post('/api/users', { name: 'John' });
 */

import type { ApiRequestOptions, Notifier, ProgressBar } from '../types';

type HttpClient = (url: string, options?: RequestInit) => Promise<Response>;

export class ApiServiceClass {
    private http: HttpClient;
    private progress: ProgressBar | null;
    private notifier: Notifier | null;

    constructor(
        httpClient: HttpClient,
        progressBar?: ProgressBar | null,
        notifier?: Notifier | null
    ) {
        this.http = httpClient;
        this.progress = progressBar ?? null;
        this.notifier = notifier ?? null;
    }

    /**
     * Requisição HTTP genérica com progress + error handling.
     */
    async request<T = unknown>(url: string, options: ApiRequestOptions = {}): Promise<T> {
        const showProgress = options.showProgress !== false;
        const showErrorToast = options.showErrorToast !== false;

        if (showProgress && this.progress) {
            this.progress.start();
        }

        try {
            const response = await this.http(url, options);
            return response as unknown as T;
        } catch (error) {
            if (showErrorToast && this.notifier) {
                const message = error instanceof Error ? error.message : 'Erro desconhecido';
                this.notifier.error(message);
            }
            throw error;
        } finally {
            if (showProgress && this.progress) {
                this.progress.done();
            }
        }
    }

    /** GET request */
    async get<T = unknown>(url: string, options: ApiRequestOptions = {}): Promise<T> {
        return this.request<T>(url, { ...options, method: 'GET' });
    }

    /** POST request */
    async post<T = unknown>(url: string, data?: unknown, options: ApiRequestOptions = {}): Promise<T> {
        const body = data instanceof FormData ? data : JSON.stringify(data);
        return this.request<T>(url, { ...options, method: 'POST', body });
    }

    /** PUT request */
    async put<T = unknown>(url: string, data?: unknown, options: ApiRequestOptions = {}): Promise<T> {
        const body = data instanceof FormData ? data : JSON.stringify(data);
        return this.request<T>(url, { ...options, method: 'PUT', body });
    }

    /** DELETE request */
    async delete<T = unknown>(url: string, options: ApiRequestOptions = {}): Promise<T> {
        return this.request<T>(url, { ...options, method: 'DELETE' });
    }

    /** PATCH request */
    async patch<T = unknown>(url: string, data?: unknown, options: ApiRequestOptions = {}): Promise<T> {
        const body = data instanceof FormData ? data : JSON.stringify(data);
        return this.request<T>(url, { ...options, method: 'PATCH', body });
    }
}

// Export para uso global (compat com código legado)
if (typeof window !== 'undefined') {
    (window as any).ApiService = ApiServiceClass;
}
