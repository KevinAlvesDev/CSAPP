/**
 * Modal Selecionar Plano Logic
 * Handles fetching, filtering, and applying success plans.
 */

(function () {
    'use strict';

    let planosDisponiveis = [];

    document.addEventListener('DOMContentLoaded', function () {
        const modalElement = document.getElementById('modalSelecionarPlano');
        if (!modalElement) return;

        const container = document.getElementById('planosListModal');
        const buscaInput = document.getElementById('buscaPlanoModal');

        // --- Event Listeners ---

        // Load plans when modal opens
        modalElement.addEventListener('show.bs.modal', function () {
            // Injetar CSS do Preview dinamicamente
            if (!document.getElementById('preview-plano-css')) {
                const link = document.createElement('link');
                link.id = 'preview-plano-css';
                link.rel = 'stylesheet';
                link.href = '/static/css/preview_plano.css';
                document.head.appendChild(link);
            }

            carregarPlanos();
            // Reset search
            if (buscaInput) buscaInput.value = '';
        });

        // Busca apenas sob demanda (botao/Enter), sem auto-busca ao digitar
        if (buscaInput) {
            buscaInput.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    carregarPlanos((buscaInput.value || '').trim());
                }
            });
        }

        // Busca explicita por clique no botao (delegacao para evitar perda de binding)
        modalElement.addEventListener('click', function (e) {
            const btnBuscar = e.target.closest('#btnBuscarPlanoModal');
            if (!btnBuscar) return;
            e.preventDefault();
            carregarPlanos((buscaInput?.value || '').trim());
        });

        // Event Delegation for dynamically created buttons
        if (container) {
            container.addEventListener('click', function (e) {
                const target = e.target;

                // Agora o botão "Aplicar" abre o preview primeiro (tornando-o obrigatório)
                const aplicarBtn = target.closest('.btn-aplicar-plano');
                if (aplicarBtn) {
                    const id = aplicarBtn.dataset.id;
                    const nome = aplicarBtn.dataset.nome;
                    if (id && nome) visualizarPreviewPlano(id, nome);
                    return;
                }

            });
        }

        // Listener para toggle de itens no preview (Expandir/Retrair)
        document.addEventListener('click', function (e) {
            const header = e.target.closest('.preview-item-header.clickable-header');
            if (header && document.getElementById('modalPreviewPlanoGlobal')?.contains(header)) {
                const targetId = header.dataset.target;
                const container = document.getElementById(targetId);
                const icon = header.querySelector('.toggle-icon');

                if (container) {
                    if (container.style.display === 'none') {
                        container.style.display = 'block';
                        if (icon) icon.style.transform = 'rotate(0deg)';
                    } else {
                        container.style.display = 'none';
                        if (icon) icon.style.transform = 'rotate(-90deg)';
                    }
                }
            }
        });

        // --- Functions ---

        function carregarPlanos(termoBusca = '') {
            if (!container) return;

            // Show loading state
            container.innerHTML = `
                <div class="col-12 text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Carregando planos...</span>
                    </div>
                </div>
            `;

            // Detectar contexto da implantação atual
            let context = 'onboarding'; // default
            const path = window.location.pathname;

            if (path.includes('/grandes_contas/')) {
                context = 'grandes_contas';
            } else if (path.includes('/onboarding/')) {
                context = 'onboarding';
            }

            // Priorizar contexto explícito do DOM quando disponível
            const mainContent = document.getElementById('main-content');
            if (mainContent && mainContent.dataset.context) {
                context = mainContent.dataset.context;
            }

            const params = new URLSearchParams({
                somente_templates: 'true',
                context
            });
            if (termoBusca) params.set('busca', termoBusca);

            window.apiFetch(`/api/planos-sucesso?${params.toString()}`)
                .then(data => {
                    if (data.success && data.planos) {
                        planosDisponiveis = data.planos;
                        renderizarPlanos(planosDisponiveis);
                    } else {
                        // Se success for false mas não der exception, mostra aviso
                        container.innerHTML = `
                        <div class="col-12">
                            <div class="alert alert-warning">
                                <i class="bi bi-exclamation-triangle me-2"></i>
                                Nenhum plano ativo encontrado para este módulo.
                            </div>
                        </div>
                    `;
                    }
                })
                .catch(() => {
                    // O apiFetch já mostra Toast de erro, aqui só atualizamos a UI
                    container.innerHTML = `
                    <div class="col-12">
                        <div class="alert alert-danger">
                            <i class="bi bi-x-circle me-2"></i>
                            Erro ao carregar planos. Tente recarregar a página.
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
                                class="btn-aplicar-plano"
                                data-id="${plano.id}"
                                data-nome="${escapeHtml(plano.nome)}"
                                style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 0.5rem;"
                            >
                                <i class="bi bi-check-circle me-1"></i>Aplicar Este Plano
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function formatarData(dataStr) { return window.formatDate(dataStr, false) || 'N/A'; }

        // --- Preview Logic (Refatorado para Enterprise Level) ---

        function renderItem(item, level) {
            const title = item.title || item.nome || '';
            const comment = item.comment || item.descricao || '';
            const children = item.children || [];
            const hasChildren = children.length > 0;
            const uniqueId = 'item-' + Math.random().toString(36).substr(2, 9);

            // Ícones e cores baseados no nível (lógica de apresentação dinâmica)
            const icons = ['bi-layers-fill', 'bi-collection', 'bi-list-check', 'bi-circle'];
            const colors = ['#667eea', '#4299e1', '#48bb78', '#a0aec0'];
            const iconClass = icons[Math.min(level, 3)];
            const colorStyle = colors[Math.min(level, 3)];

            const rootClass = level === 0 ? 'root-level' : '';

            let html = `
                <div class="preview-item" style="margin-left: ${level * 1.0}rem;">
                    <div 
                        class="preview-item-header ${hasChildren ? 'clickable-header' : ''} ${rootClass}" 
                        data-target="${uniqueId}"
                    >
                        <!-- Seta de Toggle -->
                        <div style="width: 1rem; text-align: center;">
                            ${hasChildren ?
                    `<i class="bi bi-chevron-down toggle-icon" style="transform: rotate(-90deg);"></i>` :
                    ``
                }
                        </div>

                        <i class="bi ${iconClass} type-icon" style="color: ${colorStyle};"></i>
                        
                        <div class="item-title">
                            ${escapeHtml(title)}
                            ${hasChildren ? `<span class="item-count">${children.length}</span>` : ''}
                        </div>
                    </div>
            `;

            if (comment) {
                html += `<div class="item-comment">${escapeHtml(comment)}</div>`;
            }

            if (hasChildren) {
                html += `<div id="${uniqueId}" class="children-container" style="display: none;">`;
                children.forEach(child => {
                    html += renderItem(child, level + 1);
                });
                html += '</div>';
            }

            html += '</div>';
            return html;
        }

        function visualizarPreviewPlano(planoId, planoNome) {
            let modalPreview = document.getElementById('modalPreviewPlanoGlobal');

            if (!modalPreview) {
                const modalHTML = `
                    <div class="modal fade" id="modalPreviewPlanoGlobal" tabindex="-1">
                        <div class="modal-dialog modal-lg modal-dialog-scrollable">
                            <div class="modal-content">
                                <div class="modal-header preview-modal-header">
                                    <h5 class="modal-title">
                                        <i class="bi bi-eye-fill me-2"></i>
                                        <span id="previewPlanoTitulo">Preview do Plano</span>
                                    </h5>
                                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                                </div>
                                <div class="modal-body" id="previewPlanoConteudo">
                                    <div class="preview-loading">
                                        <div class="spinner-border text-primary" role="status">
                                            <span class="visually-hidden">Carregando...</span>
                                        </div>
                                        <p class="mt-2 text-muted">Carregando preview...</p>
                                    </div>
                                </div>
                                <div class="modal-footer d-flex justify-content-between">
                                    <button type="button" class="btn btn-outline-secondary px-4" data-bs-dismiss="modal">
                                        <i class="bi bi-arrow-left me-1"></i>Voltar
                                    </button>
                                    <button type="button" class="btn btn-success px-4" id="btnConfirmarAplicacaoPlano">
                                        <i class="bi bi-check-circle me-1"></i>Confirmar e Aplicar Plano
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                document.body.insertAdjacentHTML('beforeend', modalHTML);
                modalPreview = document.getElementById('modalPreviewPlanoGlobal');
            }

            const previewConteudo = document.getElementById('previewPlanoConteudo');
            const previewTitulo = document.getElementById('previewPlanoTitulo');

            // Reset loading state
            previewConteudo.innerHTML = `
                <div class="preview-loading">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Carregando...</span>
                    </div>
                    <p class="mt-2 text-muted">Carregando preview...</p>
                </div>
            `;

            // apiFetch simplificado (tratamento de erro automático)
            window.apiFetch(`/planos/${planoId}/preview`)
                .then(data => {
                    if (!data.success || !data.plano) {
                        throw new Error(data.error || 'Plano não encontrado');
                    }

                    const plano = data.plano;
                    previewTitulo.textContent = plano.nome;

                    let html = `
                        <div class="preview-container">
                            <div class="preview-plan-header">
                                <h4 class="preview-plan-title">${escapeHtml(plano.nome)}</h4>
                                ${plano.descricao ? `<p class="preview-plan-desc">${escapeHtml(plano.descricao)}</p>` : ''}
                            </div>
                    `;

                    if (plano.items && plano.items.length > 0) {
                        html += '<div class="items-list">';
                        plano.items.forEach(item => {
                            html += renderItem(item, 0);
                        });
                        html += '</div>';
                    } else {
                        html += `
                            <div class="preview-empty-state">
                                <i class="bi bi-inbox preview-empty-icon"></i>
                                <span class="preview-empty-text">Este plano ainda não possui estrutura definida</span>
                            </div>
                        `;
                    }

                    html += '</div>';
                    previewConteudo.innerHTML = html;
                })
                .catch(error => {
                    // apiFetch já mostra Toast, aqui apenas atualizamos o modal para não ficar em loading eterno
                    previewConteudo.innerHTML = `
                        <div class="alert alert-danger m-3">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            Não foi possível carregar o preview.
                        </div>
                    `;
                });

            // Configurar botão de confirmação
            const btnConfirmar = document.getElementById('btnConfirmarAplicacaoPlano');
            if (btnConfirmar) {
                // Remover listeners antigos clonando o botão
                const btnNovo = btnConfirmar.cloneNode(true);
                btnConfirmar.parentNode.replaceChild(btnNovo, btnConfirmar);

                btnNovo.addEventListener('click', async function () {
                    // Chamamos a função de aplicar plano (passando o parâmetro para pular confirmação redundante)
                    await aplicarPlano(planoId, planoNome, btnNovo, true);
                });
            }

            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const bsModal = bootstrap.Modal.getInstance(modalPreview) || new bootstrap.Modal(modalPreview);
                bsModal.show();
            } else if (typeof $ !== 'undefined' && $.fn.modal) {
                $(modalPreview).modal('show');
            }
        }

        async function aplicarPlano(planoId, planoNome, btnElement, pularConfirmacao = false) {
            const implantacaoId = document.querySelector('#main-content')?.dataset?.implantacaoId;
            if (!implantacaoId) {
                if (window.showToast) window.showToast('Erro: ID da implantação não encontrado.', 'error');
                return;
            }

            // Comentários são preservados automaticamente neste fluxo.
            const preservarComentarios = true;

            // Confirmação padrão (pula se já veio do preview)
            let confirmed = false;
            if (pularConfirmacao) {
                confirmed = true;
            } else if (window.showConfirm) {
                confirmed = await window.showConfirm({
                    title: 'Aplicar Plano',
                    message: `Tem certeza que deseja aplicar o plano "${planoNome}"?\n\nA estrutura atual será substituída.`,
                    confirmText: 'Sim, aplicar plano',
                    type: 'warning'
                });
            } else {
                // Fallback se showConfirm não estiver disponível
                confirmed = confirm(`Tem certeza que deseja aplicar o plano "${planoNome}"?\n\nA estrutura atual será substituída.`);
            }
            if (!confirmed) return;

            // Aplicar plano com preservação automática de comentários
            const originalText = btnElement.innerHTML;
            btnElement.disabled = true;
            btnElement.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Aplicando...';

            window.apiFetch(`/planos/implantacao/${implantacaoId}/aplicar`, {
                method: 'POST',
                body: JSON.stringify({
                    plano_id: planoId,
                    preservar_comentarios: preservarComentarios
                })
            })
                .then(data => {
                    if (data.success) {
                        const msg = preservarComentarios
                            ? 'Plano aplicado! Comentários anteriores preservados na aba "Comentários".'
                            : 'Plano aplicado com sucesso!';
                        if (window.showToast) window.showToast(msg, 'success');
                        else alert(msg);

                        // Sempre voltar para a visao principal da implantacao (sem plano_historico_id)
                        window.location.assign(window.location.pathname);
                    } else {
                        throw new Error(data.error || 'Erro desconhecido ao aplicar plano');
                    }
                })
                .catch(error => {
                    btnElement.disabled = false;
                    btnElement.innerHTML = originalText;
                });
        }

        function escapeHtml(text) { return window.escapeHtml(text); }

    });

})();
