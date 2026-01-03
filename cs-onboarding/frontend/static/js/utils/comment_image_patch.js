/**
 * Patch para integrar upload de imagens com o sistema de comentários existente
 * Este arquivo intercepta as chamadas de API de comentários e adiciona imagem_url automaticamente
 */

(function () {
    'use strict';

    // Interceptar fetch global para adicionar imagem_url
    const originalFetch = window.fetch;

    window.fetch = function (...args) {
        const [url, options] = args;

        // Verificar se é uma requisição de comentário
        if (url && url.includes('/api/checklist/comment/') && options && options.method === 'POST') {
            try {
                const body = JSON.parse(options.body);

                // Extrair ID da tarefa da URL (formato: /api/checklist/comment/123)
                const match = url.match(/\/api\/checklist\/comment\/(\d+)/);
                if (match) {
                    const tarefaId = match[1];

                    // Verificar se há imagem pendente
                    if (typeof window.getPendingImageUrl === 'function') {
                        const imageUrl = window.getPendingImageUrl(tarefaId);

                        if (imageUrl) {
                            console.log(`[CommentPatch] Anexando imagem ao comentário da tarefa ${tarefaId}`);
                            body.imagem_url = imageUrl;
                            options.body = JSON.stringify(body);

                            // Chamar fetch original e limpar imagem após sucesso
                            return originalFetch.apply(this, args).then(response => {
                                const clonedResponse = response.clone();
                                clonedResponse.json().then(data => {
                                    if (data.ok && typeof window.clearPendingImage === 'function') {
                                        window.clearPendingImage(tarefaId);
                                    }
                                });
                                return response;
                            });
                        }
                    }
                }
            } catch (e) {
                // Se não conseguir parsear, continuar normalmente
                console.warn('[CommentPatch] Erro ao processar body:', e);
            }
        }

        return originalFetch.apply(this, args);
    };

    console.log('[CommentPatch] Interceptor de fetch instalado');
})();
