/**
 * ChecklistService - Lógica de negócio do Checklist
 * 
 * Responsabilidades:
 * - Validações de dados
 * - Regras de negócio
 * - Orquestração de chamadas API
 * - Tratamento de erros com notificações
 * 
 * NÃO manipula DOM (isso é responsabilidade do Renderer)
 * 
 * @example
 * const service = new ChecklistService(api, notifier);
 * const result = await service.toggleItem(123, true);
 */
class ChecklistService {
    /**
     * @param {ChecklistAPI} api - API injetada
     * @param {NotificationService} notifier - Notificador injetado
     */
    constructor(api, notifier) {
        this.api = api;
        this.notifier = notifier;
    }

    // ========================================
    // VALIDATIONS
    // ========================================

    /**
     * Valida texto de comentário
     * @param {string} texto - Texto a validar
     * @returns {boolean}
     */
    validateCommentText(texto) {
        if (!texto || !texto.trim()) {
            this.notifier.warning('O texto do comentário é obrigatório');
            return false;
        }

        if (texto.length > 5000) {
            this.notifier.warning('Comentário muito longo (máximo 5000 caracteres)');
            return false;
        }

        return true;
    }

    /**
     * Valida responsável
     * @param {string} responsavel - Nome do responsável
     * @returns {boolean}
     */
    validateResponsavel(responsavel) {
        if (!responsavel || !responsavel.trim()) {
            this.notifier.warning('O nome do responsável é obrigatório');
            return false;
        }

        if (responsavel.length > 200) {
            this.notifier.warning('Nome muito longo (máximo 200 caracteres)');
            return false;
        }

        return true;
    }

    /**
     * Valida data de previsão
     * @param {string} previsao - Data no formato YYYY-MM-DD
     * @returns {boolean}
     */
    validatePrevisao(previsao) {
        if (!previsao) {
            this.notifier.warning('A data de previsão é obrigatória');
            return false;
        }

        const date = new Date(previsao);
        if (isNaN(date.getTime())) {
            this.notifier.warning('Data inválida');
            return false;
        }

        return true;
    }

    // ========================================
    // ITEM OPERATIONS
    // ========================================

    /**
     * Toggle status de item com validação e notificação
     * @param {number} itemId - ID do item
     * @param {boolean} completed - Novo status
     * @returns {Promise<{success: boolean, progress?: number, error?: string}>}
     */
    async toggleItem(itemId, completed) {
        try {
            const data = await this.api.toggleItem(itemId, completed);

            if (data && data.ok) {
                return {
                    success: true,
                    progress: data.progress,
                    data: data
                };
            }

            throw new Error(data?.error || 'Erro ao alterar status');
        } catch (error) {
            // Erro já foi notificado pelo ApiService
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Exclui item com confirmação
     * @param {number} itemId - ID do item
     * @param {string} itemTitle - Título do item (para confirmação)
     * @returns {Promise<{success: boolean, cancelled?: boolean, progress?: number, error?: string}>}
     */
    async deleteItem(itemId, itemTitle = 'este item') {
        const confirmed = await this.notifier.confirm({
            message: `Tem certeza que deseja excluir "${itemTitle}" e todos os seus subitens? Esta ação não pode ser desfeita.`,
            title: 'Confirmar exclusão',
            type: 'danger',
            confirmText: 'Sim, excluir'
        });

        if (!confirmed) {
            return { success: false, cancelled: true };
        }

        try {
            const data = await this.api.deleteItem(itemId);

            if (data && data.ok) {
                this.notifier.success('Item excluído com sucesso');
                return {
                    success: true,
                    progress: data.progress
                };
            }

            throw new Error(data?.error || 'Erro ao excluir item');
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Atualiza responsável
     * @param {number} itemId - ID do item
     * @param {string} responsavel - Nome do responsável
     * @returns {Promise<{success: boolean, error?: string}>}
     */
    async updateResponsavel(itemId, responsavel) {
        if (!this.validateResponsavel(responsavel)) {
            return { success: false, error: 'Validação falhou' };
        }

        try {
            const data = await this.api.updateResponsavel(itemId, responsavel);

            if (data && data.ok) {
                this.notifier.success('Responsável atualizado');
                return { success: true };
            }

            throw new Error(data?.error || 'Erro ao atualizar responsável');
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Atualiza previsão
     * @param {number} itemId - ID do item
     * @param {string} previsao - Data de previsão
     * @param {boolean} isCompleted - Se o item está concluído
     * @returns {Promise<{success: boolean, error?: string}>}
     */
    async updatePrevisao(itemId, previsao, isCompleted = false) {
        if (isCompleted) {
            this.notifier.warning('Tarefa concluída: não é possível adicionar nova previsão');
            return { success: false, error: 'Item já concluído' };
        }

        if (!this.validatePrevisao(previsao)) {
            return { success: false, error: 'Validação falhou' };
        }

        try {
            const data = await this.api.updatePrevisao(itemId, previsao);

            if (data && data.ok) {
                this.notifier.success('Previsão atualizada');
                return { success: true };
            }

            throw new Error(data?.error || 'Erro ao atualizar previsão');
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Atualiza tag
     * @param {number} itemId - ID do item
     * @param {string} tag - Tag
     * @returns {Promise<{success: boolean, error?: string}>}
     */
    async updateTag(itemId, tag) {
        try {
            const data = await this.api.updateTag(itemId, tag);

            if (data && data.ok) {
                this.notifier.success('Tag atualizada');
                return { success: true, tag: data.tag || tag };
            }

            throw new Error(data?.error || 'Erro ao atualizar tag');
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // ========================================
    // COMMENTS
    // ========================================

    /**
     * Carrega comentários
     * @param {number} itemId - ID do item
     * @returns {Promise<{success: boolean, comentarios?: Array, error?: string}>}
     */
    async loadComments(itemId) {
        try {
            const data = await this.api.getComments(itemId);

            if (data && data.ok) {
                return {
                    success: true,
                    comentarios: data.comentarios || [],
                    emailResponsavel: data.email_responsavel
                };
            }

            return {
                success: false,
                error: data?.error || 'Erro ao carregar comentários'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Salva comentário com validação
     * @param {number} itemId - ID do item
     * @param {Object} commentData - Dados do comentário
     * @returns {Promise<{success: boolean, error?: string}>}
     */
    async saveComment(itemId, commentData) {
        if (!this.validateCommentText(commentData.texto)) {
            return { success: false, error: 'Validação falhou' };
        }

        try {
            const data = await this.api.saveComment(itemId, commentData);

            if (data && data.ok) {
                this.notifier.success('Comentário salvo com sucesso');
                return { success: true };
            }

            throw new Error(data?.error || 'Erro ao salvar comentário');
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Exclui comentário com confirmação
     * @param {number} comentarioId - ID do comentário
     * @returns {Promise<{success: boolean, cancelled?: boolean, error?: string}>}
     */
    async deleteComment(comentarioId) {
        const confirmed = await this.notifier.confirm({
            message: 'Deseja excluir este comentário?',
            title: 'Confirmar exclusão',
            type: 'danger'
        });

        if (!confirmed) {
            return { success: false, cancelled: true };
        }

        try {
            const data = await this.api.deleteComment(comentarioId);

            if (data && data.ok) {
                this.notifier.success('Comentário excluído');
                return { success: true };
            }

            throw new Error(data?.error || 'Erro ao excluir comentário');
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Envia comentário por email com confirmação
     * @param {number} comentarioId - ID do comentário
     * @returns {Promise<{success: boolean, cancelled?: boolean, error?: string}>}
     */
    async sendCommentEmail(comentarioId) {
        const confirmed = await this.notifier.confirm({
            message: 'Deseja enviar este comentário por e-mail ao responsável?',
            title: 'Enviar e-mail'
        });

        if (!confirmed) {
            return { success: false, cancelled: true };
        }

        try {
            const data = await this.api.sendCommentEmail(comentarioId);

            if (data && data.ok) {
                this.notifier.success('Email enviado com sucesso!');
                return { success: true };
            }

            throw new Error(data?.error || 'Erro ao enviar email');
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }
}

// Export para uso global
if (typeof window !== 'undefined') {
    window.ChecklistService = ChecklistService;
}
