/**
 * Service Container - Dependency Injection Container
 * 
 * Implementa o princípio de Inversão de Dependência (SOLID - D)
 * Gerencia todas as dependências do sistema de forma centralizada
 * 
 * @example
 * const container = new ServiceContainer();
 * container.register('api', (c) => new ApiService(c.resolve('http')));
 * const api = container.resolve('api');
 */
class ServiceContainer {
    constructor() {
        this.services = new Map();
        this.singletons = new Map();
    }

    /**
     * Registra um serviço no container
     * @param {string} name - Nome do serviço
     * @param {Function} factory - Função que cria o serviço
     * @param {boolean} singleton - Se true, mantém apenas uma instância
     */
    register(name, factory, singleton = true) {
        this.services.set(name, { factory, singleton });
        return this; // Fluent interface
    }

    /**
     * Resolve (obtém) um serviço do container
     * @param {string} name - Nome do serviço
     * @returns {*} Instância do serviço
     */
    resolve(name) {
        const service = this.services.get(name);
        if (!service) {
            throw new Error(`Service "${name}" not registered in container`);
        }

        // Se é singleton e já foi criado, retorna a instância existente
        if (service.singleton && this.singletons.has(name)) {
            return this.singletons.get(name);
        }

        // Cria nova instância (passa o container para permitir resolução de dependências)
        const instance = service.factory(this);

        // Armazena singleton
        if (service.singleton) {
            this.singletons.set(name, instance);
        }

        return instance;
    }

    /**
     * Registra um valor direto (não factory)
     * @param {string} name - Nome do serviço
     * @param {*} value - Valor a ser registrado
     */
    registerValue(name, value) {
        this.singletons.set(name, value);
        this.services.set(name, {
            factory: () => value,
            singleton: true
        });
        return this;
    }

    /**
     * Verifica se um serviço está registrado
     * @param {string} name - Nome do serviço
     * @returns {boolean}
     */
    has(name) {
        return this.services.has(name);
    }

    /**
     * Remove um serviço do container
     * @param {string} name - Nome do serviço
     */
    unregister(name) {
        this.services.delete(name);
        this.singletons.delete(name);
        return this;
    }
}

// Export para uso global
if (typeof window !== 'undefined') {
    window.ServiceContainer = ServiceContainer;
}
