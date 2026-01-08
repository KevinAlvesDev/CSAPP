/**
 * Checklist de Finalização - JavaScript
 * Gerencia a interface do checklist de pré-finalização
 */

(function () {
    'use strict';

    let checklistData = null;
    let implantacaoId = null;

    /**
     * Inicializa o checklist quando a aba é ativada
     */
    function initChecklistFinalizacao() {
        const container = document.getElementById('main-content');
        if (!container) return;

        implantacaoId = container.dataset.implantacaoId;
        if (!implantacaoId) return;

        // Carregar checklist quando a aba for ativada
        const tab = document.getElementById('checklist-finalizacao-tab');
        if (tab) {
            tab.addEventListener('shown.bs.tab', function () {
                carregarChecklist();
            });
        }

        // Event listener para o botão de validar
        const btnValidar = document.getElementById('btn-validar-checklist-finalizacao');
        if (btnValidar) {
            btnValidar.addEventListener('click', validarChecklist);
        }
    }

    /**
     * Carrega o checklist da implantação
     */
    async function carregarChecklist() {
        const loadingEl = document.getElementById('checklist-finalizacao-loading');
        const emptyEl = document.getElementById('checklist-finalizacao-empty');
        const listEl = document.getElementById('checklist-finalizacao-list');

        try {
            // Mostrar loading
            if (loadingEl) loadingEl.classList.remove('d-none');
            if (emptyEl) emptyEl.classList.add('d-none');

            const response = await fetch(`/api/checklist-finalizacao/implantacao/${implantacaoId}`);
            const data = await response.json();

            if (!data.ok) {
                throw new Error(data.error || 'Erro ao carregar checklist');
            }

            checklistData = data.checklist;

            // Esconder loading
            if (loadingEl) loadingEl.classList.add('d-none');

            if (checklistData.total === 0) {
                if (emptyEl) emptyEl.classList.remove('d-none');
            } else {
                renderizarChecklist(checklistData);
            }

            atualizarProgresso(checklistData);

        } catch (error) {
            console.error('Erro ao carregar checklist:', error);
            if (loadingEl) loadingEl.classList.add('d-none');
            if (emptyEl) {
                emptyEl.classList.remove('d-none');
                emptyEl.innerHTML = `
                    <i class="bi bi-exclamation-triangle text-danger fs-1"></i>
                    <p class="mt-2">Erro ao carregar checklist: ${error.message}</p>
                `;
            }
        }
    }

    /**
     * Renderiza os itens do checklist
     */
    function renderizarChecklist(checklist) {
        const listEl = document.getElementById('checklist-finalizacao-list');
        if (!listEl) return;

        // Limpar conteúdo anterior (exceto loading e empty)
        const items = listEl.querySelectorAll('.checklist-item');
        items.forEach(item => item.remove());

        if (!checklist.items || checklist.items.length === 0) {
            return;
        }

        // Criar HTML para cada item
        const html = checklist.items.map(item => criarItemHTML(item)).join('');
        listEl.insertAdjacentHTML('beforeend', html);

        // Adicionar event listeners
        checklist.items.forEach(item => {
            const checkbox = document.getElementById(`check-item-${item.id}`);
            if (checkbox) {
                checkbox.addEventListener('change', () => toggleItem(item.id, checkbox.checked));
            }

            const btnEvidencia = document.getElementById(`btn-evidencia-${item.id}`);
            if (btnEvidencia) {
                btnEvidencia.addEventListener('click', () => mostrarModalEvidencia(item));
            }
        });
    }

    /**
     * Cria o HTML de um item do checklist
     */
    function criarItemHTML(item) {
        const concluido = item.concluido;
        const obrigatorio = item.obrigatorio;
        const temEvidencia = item.evidencia_url || item.evidencia_conteudo;

        return `
            <div class="card mb-3 checklist-item ${concluido ? 'border-success' : ''}" data-item-id="${item.id}">
                <div class="card-body">
                    <div class="d-flex align-items-start gap-3">
                        <!-- Checkbox -->
                        <div class="form-check mt-1">
                            <input class="form-check-input" type="checkbox" id="check-item-${item.id}" 
                                ${concluido ? 'checked' : ''}>
                        </div>

                        <!-- Conteúdo -->
                        <div class="flex-grow-1">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <h6 class="mb-0 ${concluido ? 'text-decoration-line-through text-muted' : ''}">
                                    ${item.titulo}
                                    ${obrigatorio ? '<span class="badge bg-danger ms-2">Obrigatório</span>' : ''}
                                </h6>
                                ${concluido ? '<i class="bi bi-check-circle-fill text-success fs-5"></i>' : ''}
                            </div>

                            ${item.descricao ? `<p class="text-muted small mb-2">${item.descricao}</p>` : ''}

                            <!-- Informações de conclusão -->
                            ${concluido && item.data_conclusao ? `
                                <div class="small text-muted mb-2">
                                    <i class="bi bi-clock me-1"></i>
                                    Concluído em ${formatarData(item.data_conclusao)} por ${item.usuario_conclusao || 'Usuário'}
                                </div>
                            ` : ''}

                            <!-- Evidência -->
                            ${temEvidencia ? `
                                <div class="alert alert-info alert-sm py-2 mb-2">
                                    <i class="bi bi-paperclip me-1"></i>
                                    <strong>Evidência:</strong>
                                    ${item.evidencia_url ? `<a href="${item.evidencia_url}" target="_blank" class="alert-link">${item.evidencia_url}</a>` : ''}
                                    ${item.evidencia_conteudo ? `<span>${item.evidencia_conteudo}</span>` : ''}
                                </div>
                            ` : ''}

                            ${item.observacoes ? `
                                <div class="small text-muted">
                                    <strong>Observações:</strong> ${item.observacoes}
                                </div>
                            ` : ''}

                            <!-- Botão para adicionar evidência -->
                            ${item.evidencia_tipo && !concluido ? `
                                <button class="btn btn-sm btn-outline-primary mt-2" id="btn-evidencia-${item.id}">
                                    <i class="bi bi-paperclip me-1"></i>
                                    Adicionar Evidência
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Toggle item do checklist
     */
    async function toggleItem(itemId, concluido) {
        try {
            const response = await fetch(`/api/checklist-finalizacao/item/${itemId}/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ concluido })
            });

            // Verificar se a resposta é JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                console.error('Resposta não é JSON:', text);
                throw new Error('Erro no servidor. Verifique os logs.');
            }

            const data = await response.json();

            if (!data.ok) {
                throw new Error(data.error || 'Erro ao atualizar item');
            }

            // Recarregar checklist
            await carregarChecklist();

            // Mostrar feedback
            showToast(data.message || 'Item atualizado com sucesso', 'success');

        } catch (error) {
            console.error('Erro ao toggle item:', error);
            showToast('Erro ao atualizar item: ' + error.message, 'error');
            // Reverter checkbox
            const checkbox = document.getElementById(`check-item-${itemId}`);
            if (checkbox) checkbox.checked = !concluido;
        }
    }


    /**
     * Atualiza a barra de progresso e contador
     */
    function atualizarProgresso(checklist) {
        const progressBar = document.getElementById('checklist-finalizacao-progress-bar');
        const progressText = document.getElementById('checklist-finalizacao-progress-text');
        const badgeObrigatorios = document.getElementById('checklist-obrigatorios-pendentes');
        const countObrigatorios = document.getElementById('count-obrigatorios-pendentes');
        const btnValidar = document.getElementById('btn-validar-checklist-finalizacao');

        if (progressBar) {
            progressBar.style.width = `${checklist.progresso}%`;
            progressBar.setAttribute('aria-valuenow', checklist.progresso);
        }

        if (progressText) {
            progressText.textContent = `${checklist.concluidos}/${checklist.total} itens concluídos`;
        }

        if (countObrigatorios) {
            countObrigatorios.textContent = checklist.obrigatorios_pendentes;
        }

        if (badgeObrigatorios) {
            if (checklist.obrigatorios_pendentes === 0) {
                badgeObrigatorios.classList.remove('bg-warning', 'text-dark');
                badgeObrigatorios.classList.add('bg-success');
                badgeObrigatorios.innerHTML = '<i class="bi bi-check-circle me-1"></i>Todos os itens obrigatórios concluídos';
            } else {
                badgeObrigatorios.classList.remove('bg-success');
                badgeObrigatorios.classList.add('bg-warning', 'text-dark');
            }
        }

        if (btnValidar) {
            btnValidar.disabled = !checklist.validado;
        }
    }

    /**
     * Valida o checklist
     */
    async function validarChecklist() {
        try {
            const response = await fetch(`/api/checklist-finalizacao/implantacao/${implantacaoId}/validar`);
            const data = await response.json();

            if (!data.ok) {
                throw new Error(data.error || 'Erro ao validar checklist');
            }

            if (data.validado) {
                showToast('✅ ' + data.mensagem, 'success');
            } else {
                showToast('⚠️ ' + data.mensagem, 'warning');
            }

        } catch (error) {
            console.error('Erro ao validar checklist:', error);
            showToast('Erro ao validar checklist: ' + error.message, 'error');
        }
    }

    /**
     * Mostra modal para adicionar evidência (placeholder)
     */
    function mostrarModalEvidencia(item) {
        // TODO: Implementar modal para adicionar evidência
        alert('Funcionalidade de evidência será implementada em breve');
    }

    /**
     * Formata data para exibição
     */
    function formatarData(dataStr) {
        if (!dataStr) return '';
        // Se já estiver no formato brasileiro (dd/mm/yyyy às HH:MM), retornar como está
        var brFormatRegex = /^\d{2}\/\d{2}\/\d{4}(\s+às\s+\d{2}:\d{2})?$/;
        if (brFormatRegex.test(String(dataStr).trim())) {
            return String(dataStr);
        }
        const data = new Date(dataStr);
        if (isNaN(data.getTime())) return String(dataStr);
        return data.toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * Obtém o token CSRF
     */
    function getCsrfToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    /**
     * Mostra toast de feedback
     */
    function showToast(message, type = 'info') {
        // Usar sistema de toast existente ou criar um simples
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
            alert(message);
        }
    }

    // Inicializar quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChecklistFinalizacao);
    } else {
        initChecklistFinalizacao();
    }

})();
