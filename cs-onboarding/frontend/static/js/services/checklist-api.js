/**
 * ChecklistAPI - Camada de comunicação HTTP para Checklist
 * 
 * Responsabilidade Única (SOLID-S): Apenas requisições HTTP
 * Não contém lógica de negócio, validação ou manipulação de DOM
 * 
 * @example
 * const api = new ChecklistAPI(apiService);
 * const data = await api.getTree(123);
 */
class ChecklistAPI {
    /**
     * @param {ApiService} apiService - Serviço de API injetado
     */
    constructor(apiService) {
        this.api = apiService;
    }

    // ========================================
    // CHECKLIST TREE
    // ========================================

    /**
     * Carrega árvore do checklist
     * @param {number} implantacaoId - ID da implantação
     * @param {string} format - Formato ('nested' ou 'flat')
     * @returns {Promise<Object>}
     */
    async getTree(implantacaoId, format = 'nested') {
        const params = new URLSearchParams({
            implantacao_id: implantacaoId,
            format: format
        });
        return this.api.get(`/api/checklist/tree?${params}`);
    }

    // ========================================
    // ITEM OPERATIONS
    // ========================================

    /**
     * Toggle status de um item
     * @param {number} itemId - ID do item
     * @param {boolean} completed - Novo status
     * @returns {Promise<Object>}
     */
    async toggleItem(itemId, completed) {
        return this.api.post(`/api/checklist/toggle/${itemId}`, { completed });
    }

    /**
     * Exclui um item
     * @param {number} itemId - ID do item
     * @returns {Promise<Object>}
     */
    async deleteItem(itemId) {
        return this.api.post(`/api/checklist/delete/${itemId}`);
    }

    /**
     * Atualiza responsável de um item
     * @param {number} itemId - ID do item
     * @param {string} responsavel - Nome do responsável
     * @returns {Promise<Object>}
     */
    async updateResponsavel(itemId, responsavel) {
        return this.api.post(`/api/checklist/responsavel/${itemId}`, { responsavel });
    }

    /**
     * Atualiza previsão de um item
     * @param {number} itemId - ID do item
     * @param {string} previsao - Data de previsão
     * @returns {Promise<Object>}
     */
    async updatePrevisao(itemId, previsao) {
        return this.api.post(`/api/checklist/previsao/${itemId}`, { previsao });
    }

    /**
     * Atualiza tag de um item
     * @param {number} itemId - ID do item
     * @param {string} tag - Tag
     * @returns {Promise<Object>}
     */
    async updateTag(itemId, tag) {
        return this.api.post(`/api/checklist/tag/${itemId}`, { tag });
    }

    // ========================================
    // COMMENTS
    // ========================================

    /**
     * Carrega comentários de um item
     * @param {number} itemId - ID do item
     * @returns {Promise<Object>}
     */
    async getComments(itemId) {
        return this.api.get(`/api/checklist/comments/${itemId}`, {
            showErrorToast: false // Não mostrar erro (fallback no UI)
        });
    }

    /**
     * Salva comentário
     * @param {number} itemId - ID do item
     * @param {Object} commentData - Dados do comentário
     * @param {string} commentData.texto - Texto do comentário
     * @param {string} commentData.visibilidade - 'interno' ou 'externo'
     * @param {boolean} commentData.noshow - Se é no-show
     * @param {string} commentData.tag - Tag do comentário
     * @returns {Promise<Object>}
     */
    async saveComment(itemId, commentData) {
        return this.api.post(`/api/checklist/comment/${itemId}`, commentData);
    }

    /**
     * Exclui comentário
     * @param {number} comentarioId - ID do comentário
     * @returns {Promise<Object>}
     */
    async deleteComment(comentarioId) {
        return this.api.delete(`/api/checklist/comment/${comentarioId}`);
    }

    /**
     * Envia comentário por email
     * @param {number} comentarioId - ID do comentário
     * @returns {Promise<Object>}
     */
    async sendCommentEmail(comentarioId) {
        return this.api.post(`/api/checklist/comment/${comentarioId}/email`);
    }
}

// Export para uso global
if (typeof window !== 'undefined') {
    window.ChecklistAPI = ChecklistAPI;
}
