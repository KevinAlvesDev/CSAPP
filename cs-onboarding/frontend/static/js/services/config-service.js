/**
 * Serviço de Configurações
 * Carrega configurações dinâmicas do backend (tags, status, etc)
 * Corrige Bug #3 - Tags Hardcoded
 */

class ConfigService {
    constructor() {
        this.cache = {
            tags: {},
            status: null,
            niveis: null,
            eventos: null,
            lastFetch: {}
        };
        this.CACHE_DURATION = 0; // CACHE DESABILITADO - sempre buscar dados frescos
    }

    /**
     * Carrega tags do sistema
     * @param {string} tipo - 'comentario', 'tarefa', 'ambos', ou null para todos
     * @param {boolean} forceRefresh - Forçar atualização do cache
     * @returns {Promise<Array>} Lista de tags
     */
    async getTags(tipo = 'ambos', forceRefresh = false) {
        const now = Date.now();
        const cacheKey = tipo || 'all';

        // Verificar cache
        if (!forceRefresh &&
            this.cache.tags[cacheKey] &&
            this.cache.lastFetch.tags &&
            (now - this.cache.lastFetch.tags) < this.CACHE_DURATION) {
            return this.cache.tags[cacheKey];
        }

        try {
            const url = tipo
                ? `/api/config/tags?tipo=${encodeURIComponent(tipo)}`
                : '/api/config/tags';

            const response = await fetch(url);
            const data = await response.json();

            if (data.ok) {
                // Atualizar cache
                this.cache.tags[cacheKey] = data.tags;
                this.cache.lastFetch.tags = now;

                return data.tags;
            } else {
                console.error('Erro ao carregar tags:', data.error);
                return this._getFallbackTags(tipo);
            }
        } catch (error) {
            console.error('Erro ao carregar tags:', error);
            // Fallback para tags hardcoded (compatibilidade)
            return this._getFallbackTags(tipo);
        }
    }

    /**
     * Obtém classe de badge para uma tag específica
     * @param {string} tagNome - Nome da tag
     * @returns {Promise<string>} Classe CSS do badge
     */
    async getTagBadgeClass(tagNome) {
        const tags = await this.getTags();
        const tag = tags.find(t => t.nome === tagNome);
        return tag ? tag.cor_badge : 'bg-secondary';
    }

    /**
     * Obtém ícone para uma tag específica
     * @param {string} tagNome - Nome da tag
     * @returns {Promise<string>} Classe do ícone Bootstrap
     */
    async getTagIcon(tagNome) {
        const tags = await this.getTags();
        const tag = tags.find(t => t.nome === tagNome);
        return tag ? tag.icone : 'bi-tag';
    }

    /**
     * Renderiza seletor de tags HTML
     * @param {string} itemId - ID do item
     * @param {string} tipo - Tipo de tags a exibir
     * @returns {Promise<string>} HTML do seletor
     */
    async renderTagSelector(itemId, tipo = 'ambos') {
        const tags = await this.getTags(tipo);

        let html = '<div class="tag-selector d-flex flex-wrap gap-2">';
        tags.forEach(tag => {
            html += `
                <span class="comentario-tipo-tag tag-option ${tag.cor_badge}" 
                      data-item-id="${itemId}" 
                      data-tag="${tag.nome}"
                      style="cursor: pointer; padding: 0.25rem 0.5rem; border-radius: 0.25rem;">
                    <i class="bi ${tag.icone}"></i> ${tag.nome}
                </span>
            `;
        });
        html += '</div>';

        return html;
    }

    /**
     * Carrega status de implantação
     * @param {boolean} forceRefresh - Forçar atualização do cache
     * @returns {Promise<Array>} Lista de status
     */
    async getStatus(forceRefresh = false) {
        const now = Date.now();

        if (!forceRefresh &&
            this.cache.status &&
            this.cache.lastFetch.status &&
            (now - this.cache.lastFetch.status) < this.CACHE_DURATION) {
            return this.cache.status;
        }

        try {
            const response = await fetch('/api/config/status');
            const data = await response.json();

            if (data.ok) {
                this.cache.status = data.status;
                this.cache.lastFetch.status = now;
                return data.status;
            }
        } catch (error) {
            console.error('Erro ao carregar status:', error);
        }

        return [];
    }

    /**
     * Carrega níveis de atendimento
     * @param {boolean} forceRefresh - Forçar atualização do cache
     * @returns {Promise<Array>} Lista de níveis
     */
    async getNiveis(forceRefresh = false) {
        const now = Date.now();

        if (!forceRefresh &&
            this.cache.niveis &&
            this.cache.lastFetch.niveis &&
            (now - this.cache.lastFetch.niveis) < this.CACHE_DURATION) {
            return this.cache.niveis;
        }

        try {
            const response = await fetch('/api/config/niveis');
            const data = await response.json();

            if (data.ok) {
                this.cache.niveis = data.niveis;
                this.cache.lastFetch.niveis = now;
                return data.niveis;
            }
        } catch (error) {
            console.error('Erro ao carregar níveis:', error);
        }

        return [];
    }

    /**
     * Limpa todo o cache
     */
    clearCache() {
        this.cache = {
            tags: {},
            status: null,
            niveis: null,
            eventos: null,
            lastFetch: {}
        };
    }

    /**
     * Limpa cache de um tipo específico
     * @param {string} type - 'tags', 'status', 'niveis', etc
     */
    clearCacheType(type) {
        if (type === 'tags') {
            this.cache.tags = {};
            delete this.cache.lastFetch.tags;
        } else {
            this.cache[type] = null;
            delete this.cache.lastFetch[type];
        }
    }

    /**
     * Fallback para tags hardcoded (compatibilidade)
     * @private
     */
    _getFallbackTags(tipo) {
        const allTags = [
            { id: 1, nome: 'Ação interna', icone: 'bi-briefcase', cor_badge: 'bg-primary', tipo: 'ambos', ordem: 1 },
            { id: 2, nome: 'Reunião', icone: 'bi-calendar-event', cor_badge: 'bg-danger', tipo: 'ambos', ordem: 2 },
            { id: 3, nome: 'No Show', icone: 'bi-calendar-x', cor_badge: 'bg-warning text-dark', tipo: 'comentario', ordem: 3 },
            { id: 4, nome: 'Simples registro', icone: 'bi-pencil-square', cor_badge: 'bg-secondary', tipo: 'comentario', ordem: 4 },
            { id: 5, nome: 'Cliente', icone: 'bi-person-badge', cor_badge: 'bg-info', tipo: 'tarefa', ordem: 5 },
            { id: 6, nome: 'Rede', icone: 'bi-diagram-3', cor_badge: 'bg-success', tipo: 'tarefa', ordem: 6 }
        ];

        if (!tipo || tipo === 'ambos') return allTags;
        return allTags.filter(t => t.tipo === tipo || t.tipo === 'ambos');
    }
}

// Exportar instância singleton
if (typeof window !== 'undefined') {
    window.configService = new ConfigService();
}

// Exportar para módulos ES6 (se necessário)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ConfigService;
}
