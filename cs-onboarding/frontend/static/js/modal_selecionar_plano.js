/**
 * Modal Selecionar Plano Logic
 * Handles fetching, filtering, and applying success plans.
 */

(function() {
    'use strict';

    let planosDisponiveis = [];
    let planoSelecionado = null;

    document.addEventListener('DOMContentLoaded', function() {
        const modalElement = document.getElementById('modalSelecionarPlano');
        if (!modalElement) return;

        const container = document.getElementById('planosListModal');
        const buscaInput = document.getElementById('buscaPlanoModal');

        // --- Event Listeners ---

        // Load plans when modal opens
        modalElement.addEventListener('show.bs.modal', function() {
            carregarPlanos();
            // Reset search
            if (buscaInput) buscaInput.value = '';
        });

        // Filter plans on input
        if (buscaInput) {
            buscaInput.addEventListener('input', function(e) {
                filtrarPlanos(e.target.value);
            });
        }

        // Event Delegation for dynamically created buttons
        if (container) {
            container.addEventListener('click', function(e) {
                const target = e.target;
                
                // Handle "Preview" button
                const previewBtn = target.closest('.btn-preview-plano');
                if (previewBtn) {
                    const id = previewBtn.dataset.id;
                    if (id) visualizarPreviewPlano(id);
                    return;
                }

                // Handle "Aplicar" button
                const aplicarBtn = target.closest('.btn-aplicar-plano');
                if (aplicarBtn) {
                    const id = aplicarBtn.dataset.id;
                    const nome = aplicarBtn.dataset.nome;
                    if (id && nome) aplicarPlano(id, nome, aplicarBtn);
                    return;
                }

                // Handle Card Selection
                const card = target.closest('.plano-select-card');
                if (card && !target.closest('button')) {
                    container.querySelectorAll('.plano-select-card').forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    planoSelecionado = parseInt(card.dataset.planoId);
                }
            });
        }

        // --- Functions ---

        function carregarPlanos() {
            if (!container) return;
            
            // Show loading state
            container.innerHTML = `
                <div class="col-12 text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Carregando planos...</span>
                    </div>
                </div>
            `;

            fetch('/planos/?ativo=true', {
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    return response.text().then(text => {
                        throw new Error('Resposta não é JSON. Servidor retornou: ' + text.substring(0, 100));
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success && data.planos) {
                    planosDisponiveis = data.planos;
                    renderizarPlanos(planosDisponiveis);
                } else {
                    container.innerHTML = `
                        <div class="col-12">
                            <div class="alert alert-warning">
                                <i class="bi bi-exclamation-triangle me-2"></i>
                                Nenhum plano ativo encontrado.
                            </div>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Erro ao carregar planos:', error);
                container.innerHTML = `
                    <div class="col-12">
                        <div class="alert alert-danger">
                            <i class="bi bi-x-circle me-2"></i>
                            Erro ao carregar planos: ${error.message}
                        </div>
                    </div>
                `;
            });
        }

        function renderizarPlanos(planos) {
            if (!container) return;

            if (!planos || planos.length === 0) {
                container.innerHTML = `
                    <div class="col-12">
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle me-2"></i>
                            Nenhum plano encontrado com os critérios de busca.
                        </div>
                    </div>
                `;
                return;
            }

            container.innerHTML = planos.map(plano => `
                <div class="col-md-6">
                    <div class="plano-select-card" data-plano-id="${plano.id}">
                        <div class="plano-select-title">
                            <i class="bi bi-diagram-3 me-2"></i>${escapeHtml(plano.nome)}
                        </div>
                        <div class="plano-select-description">
                            ${escapeHtml(plano.descricao || 'Sem descrição')}
                        </div>
                        <div class="plano-select-stats">
                            <div class="plano-select-stat">
                                <i class="bi bi-person-fill"></i>
                                <span>${escapeHtml(plano.criado_por || 'Sistema')}</span>
                            </div>
                            <div class="plano-select-stat">
                                <i class="bi bi-calendar-fill"></i>
                                <span>${formatarData(plano.data_criacao)}</span>
                            </div>
                        </div>
                        <div class="plano-select-actions">
                            <button 
                                type="button" 
                                class="btn-preview-plano"
                                data-id="${plano.id}"
                            >
                                <i class="bi bi-eye me-1"></i>Preview
                            </button>
                            <button 
                                type="button" 
                                class="btn-aplicar-plano"
                                data-id="${plano.id}"
                                data-nome="${escapeHtml(plano.nome)}"
                            >
                                <i class="bi bi-check-circle me-1"></i>Aplicar Este Plano
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function filtrarPlanos(termo) {
            const termoLower = termo.toLowerCase();
            const planosFiltrados = planosDisponiveis.filter(plano =>
                plano.nome.toLowerCase().includes(termoLower) ||
                (plano.descricao && plano.descricao.toLowerCase().includes(termoLower))
            );
            renderizarPlanos(planosFiltrados);
        }

        function formatarData(dataStr) { return window.formatDate(dataStr, false) || 'N/A'; }

        function visualizarPreviewPlano(planoId) {
            window.open(`/planos/${planoId}`, '_blank');
        }

        async function aplicarPlano(planoId, planoNome, btnElement) {
            let confirmed = false;
            
            if (window.showConfirm) {
                confirmed = await window.showConfirm({
                    title: 'Aplicar Plano',
                    message: `Tem certeza que deseja aplicar o plano "${planoNome}"?\n\nA estrutura atual será substituída.`,
                    confirmText: 'Sim, aplicar plano',
                    type: 'warning'
                });
            } else {
                confirmed = confirm(`Tem certeza que deseja aplicar o plano "${planoNome}"?\n\nA estrutura atual será substituída.`);
            }

            if (!confirmed) return;

            const implantacaoId = document.querySelector('#main-content')?.dataset?.implantacaoId;
            if (!implantacaoId) {
                if (window.showToast) window.showToast('Erro: ID da implantação não encontrado.', 'error');
                else alert('Erro: ID da implantação não encontrado.');
                return;
            }

            const originalText = btnElement.innerHTML;
            btnElement.disabled = true;
            btnElement.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Aplicando...';

            fetch(`/planos/implantacao/${implantacaoId}/aplicar`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
                },
                body: JSON.stringify({ plano_id: planoId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (window.showToast) window.showToast('Plano aplicado com sucesso!', 'success');
                    else alert('Plano aplicado com sucesso!');
                    
                    window.location.reload();
                } else {
                    const msg = 'Erro ao aplicar plano: ' + (data.error || 'Erro desconhecido');
                    if (window.showToast) window.showToast(msg, 'error');
                    else alert(msg);
                    
                    btnElement.disabled = false;
                    btnElement.innerHTML = originalText;
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                const msg = 'Erro ao aplicar plano: ' + error.message;
                if (window.showToast) window.showToast(msg, 'error');
                else alert(msg);
                
                btnElement.disabled = false;
                btnElement.innerHTML = originalText;
            });
        }

        function escapeHtml(text) { return window.escapeHtml(text); }

    });

})();
