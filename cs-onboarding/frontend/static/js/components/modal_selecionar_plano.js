/**
 * Modal Selecionar Plano Logic
 * Handles fetching, filtering, and applying success plans.
 */

(function () {
    'use strict';

    let planosDisponiveis = [];
    let planoSelecionado = null;

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

        // Filter plans on input
        if (buscaInput) {
            buscaInput.addEventListener('input', function (e) {
                filtrarPlanos(e.target.value);
            });
        }

        // Event Delegation for dynamically created buttons
        if (container) {
            container.addEventListener('click', function (e) {
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

            // Detectar o contexto da implantação atual
            // Primeiro tenta pegar do URL (ex: /grandes_contas/...)
            let context = 'onboarding'; // default
            const path = window.location.pathname;

            console.log('🔍 [DEBUG] Detecção de Contexto - URL atual:', path);

            if (path.includes('/grandes_contas/')) {
                context = 'grandes_contas';
                console.log('✅ [DEBUG] Contexto detectado pelo URL: grandes_contas');
            } else if (path.includes('/onboarding/')) {
                context = 'onboarding';
                console.log('✅ [DEBUG] Contexto detectado pelo URL: onboarding');
            } else {
                console.log('⚠️ [DEBUG] URL não contém /grandes_contas/ nem /onboarding/, usando default: onboarding');
            }

            // Também pode tentar pegar de um atributo data no DOM se existir
            const mainContent = document.getElementById('main-content');
            if (mainContent && mainContent.dataset.context) {
                const dataContext = mainContent.dataset.context;
                console.log('📋 [DEBUG] Atributo data-context encontrado:', dataContext);
                if (dataContext !== context) {
                    console.log('🔄 [DEBUG] Sobrescrevendo contexto de', context, 'para', dataContext);
                }
                context = dataContext;
            } else {
                console.log('⚠️ [DEBUG] Elemento #main-content ou data-context não encontrado');
            }

            console.log('🎯 [DEBUG] Contexto FINAL que será enviado para API:', context);

            window.apiFetch(`/planos/?ativo=true&context=${context}`)
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
                .catch(error => {
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
                    `<i class="bi bi-chevron-down toggle-icon"></i>` :
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
                html += `<div id="${uniqueId}" class="children-container">`;
                children.forEach(child => {
                    html += renderItem(child, level + 1);
                });
                html += '</div>';
            }

            html += '</div>';
            return html;
        }

        function visualizarPreviewPlano(planoId) {
            let modalPreview = document.getElementById('modalPreviewPlanoGlobal');

            if (!modalPreview) {
                const modalHTML = `
                    <div class="modal fade" id="modalPreviewPlanoGlobal" tabindex="-1">
                        <div class="modal-dialog modal-lg modal-dialog-scrollable">
                            <div class="modal-content">
                                <div class="modal-header preview-modal-header">
                                    <h5 class="modal-title">
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
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
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

            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const bsModal = new bootstrap.Modal(modalPreview);
                bsModal.show();
            } else if (typeof $ !== 'undefined' && $.fn.modal) {
                $(modalPreview).modal('show');
            }
        }

        async function aplicarPlano(planoId, planoNome, btnElement) {
            // Primeira confirmação: deseja aplicar o plano?
            let confirmed = false;

            if (window.showConfirm) {
                confirmed = await window.showConfirm({
                    title: 'Aplicar Plano',
                    message: `Tem certeza que deseja aplicar o plano "${planoNome}"?\n\nA estrutura atual será substituída.`,
                    confirmText: 'Sim, aplicar plano',
                    type: 'warning'
                });
            }

            if (!confirmed) return;

            const implantacaoId = document.querySelector('#main-content')?.dataset?.implantacaoId;
            if (!implantacaoId) {
                if (window.showToast) window.showToast('Erro: ID da implantação não encontrado.', 'error');
                return;
            }

            const originalText = btnElement.innerHTML;
            btnElement.disabled = true;
            btnElement.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Verificando...';

            try {
                // Verificar se há comentários existentes
                const checkResponse = await window.apiFetch(`/api/checklist/implantacao/${implantacaoId}/comments/count`);

                let manterComentarios = false;

                if (checkResponse.ok && checkResponse.has_comments) {
                    // Há comentários - perguntar ao usuário o que fazer
                    btnElement.innerHTML = originalText;
                    btnElement.disabled = false;

                    const manterConfirmado = await window.showConfirm({
                        title: 'Comentários Existentes',
                        message: `Esta implantação possui ${checkResponse.count} comentário(s) vinculado(s) às tarefas atuais.\n\nDeseja preservar esses comentários? Eles continuarão visíveis na aba "Comentários", mas não estarão mais associados a tarefas específicas.`,
                        confirmText: 'Manter Comentários',
                        cancelText: 'Excluir Comentários',
                        type: 'info'
                    });

                    manterComentarios = manterConfirmado;

                    // Desabilitar botão novamente para a operação de aplicação
                    btnElement.disabled = true;
                    btnElement.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Aplicando...';
                } else {
                    btnElement.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Aplicando...';
                }

                // Aplicar o plano com a escolha do usuário
                const response = await window.apiFetch(`/planos/implantacao/${implantacaoId}/aplicar`, {
                    method: 'POST',
                    body: JSON.stringify({
                        plano_id: planoId,
                        manter_comentarios: manterComentarios
                    })
                });

                if (response.success) {
                    if (window.showToast) {
                        const msg = manterComentarios
                            ? 'Plano aplicado com sucesso! Comentários preservados.'
                            : 'Plano aplicado com sucesso!';
                        window.showToast(msg, 'success');
                    }
                    window.location.reload();
                } else {
                    throw new Error(response.error || 'Erro desconhecido ao aplicar plano');
                }
            } catch (error) {
                btnElement.disabled = false;
                btnElement.innerHTML = originalText;
                // apiFetch já exibe toast de erro
            }
        }

        function escapeHtml(text) { return window.escapeHtml(text); }

    });

})();
