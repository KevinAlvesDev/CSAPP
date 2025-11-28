function formatDataComentario(dataStr) { if (!dataStr) return ''; try { const dateObj = new Date(dataStr.replace(' ', 'T') + 'Z'); if (isNaN(dateObj.getTime())) throw new Error("Inválida"); const day = String(dateObj.getDate()).padStart(2, '0'); const month = String(dateObj.getMonth() + 1).padStart(2, '0'); const year = dateObj.getFullYear(); return `${day}/${month}/${year}`; } catch (e) { console.error("Erro data:", dataStr, e); return 'Inválida'; } }
function formatDataLog(dataStr) { if (!dataStr) return ''; try { const dateObj = new Date(dataStr.replace(' ', 'T') + 'Z'); if (isNaN(dateObj.getTime())) throw new Error("Inválida"); return dateObj.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }).replace(',', ' às'); } catch (e) { console.error("Erro data log:", dataStr, e); return 'Inválida'; } }
function toggleComment(button, elementId) { const textElement = document.getElementById(elementId); if (!textElement) return; const isExpanded = textElement.classList.toggle('expanded'); button.textContent = isExpanded ? 'Ver menos...' : 'Ver mais...'; }
function criarTimelineItemHTML(log) { if (!log || !log.data_criacao) return ''; let iconClass = 'bi-info-circle-fill'; if (log.tipo_evento === 'novo_comentario') iconClass = 'bi-chat-left-text-fill'; else if (log.tipo_evento?.includes('tarefa')) iconClass = 'bi-check-circle-fill'; else if (log.tipo_evento?.includes('status') || log.tipo_evento?.includes('implantacao') || log.tipo_evento?.includes('detalhes')) iconClass = 'bi-flag-fill'; else if (log.tipo_evento === 'modulo_excluido') iconClass = 'bi-trash-fill'; const dataFormatada = formatDataLog(log.data_criacao); const detalhesHTML = (log.detalhes || '').replace(/\n/g, '<br>'); return `<li class="timeline-item"><div class="timeline-icon"><i class="bi ${iconClass}"></i></div><div class="timeline-content"><div class="timeline-header"><span class="timeline-usuario">${log.usuario_nome || 'Sistema'}</span><span class="timeline-data">${dataFormatada}</span></div><p class="timeline-detalhes">${detalhesHTML}</p></div></li>`; }
function adicionarLogNaTimeline(log) { if (!log) return; const timelineList = document.querySelector('#timeline-content .timeline-list'); if (!timelineList) return; const noTimelineMsg = document.getElementById('no-timeline-msg'); if (noTimelineMsg) noTimelineMsg.remove(); const logHTML = criarTimelineItemHTML(log); if (logHTML) timelineList.insertAdjacentHTML('afterbegin', logHTML); }

function updateProgressBar(progress) { const progressBar = document.querySelector('#progress-total-bar'); if (progressBar) { const progressNum = parseInt(progress) || 0; progressBar.style.width = progressNum + '%'; progressBar.setAttribute('aria-valuenow', progressNum); progressBar.textContent = progressNum + '%'; } }

function confirmWithModal(message) {
    return new Promise((resolve) => {
        if (!window.bootstrap) { resolve(window.confirm(message)); return; }
        const html = `
        <div class="modal fade" tabindex="-1" id="confirmActionModal">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">Confirmar ação</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
              </div>
              <div class="modal-body"><p>${message}</p></div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-primary" id="confirmActionBtn">Confirmar</button>
              </div>
            </div>
          </div>
        </div>`;
        const wrap = document.createElement('div'); wrap.innerHTML = html; const modalEl = wrap.firstElementChild; document.body.appendChild(modalEl);
        const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl, { backdrop: 'static', keyboard: true });
        const cleanup = () => { bsModal.hide(); modalEl.addEventListener('hidden.bs.modal', () => modalEl.remove(), { once: true }); };
        modalEl.querySelector('#confirmActionBtn').addEventListener('click', () => { resolve(true); cleanup(); });
        modalEl.addEventListener('hide.bs.modal', () => { resolve(false); }, { once: true });
        bsModal.show();
    });
}

async function excluirTarefa(tarefaId, button, CONFIG) {
    const ok = await confirmWithModal('Excluir tarefa e comentários?');
    if (!ok) return;
    const endpointUrl = button?.dataset?.deleteUrl || (CONFIG.endpoints.delTarefa + tarefaId);
    const originalHTML = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    const listItem = button.closest('.list-group-item');
    if (listItem) listItem.style.opacity = '0.5';
    fetch(endpointUrl, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.ok) {
                if (listItem) listItem.remove();
                adicionarLogNaTimeline(data.log_exclusao);
                if (data.novo_progresso !== undefined) updateProgressBar(data.novo_progresso);
                if (data.implantacao_finalizada) {
                    adicionarLogNaTimeline(data.log_finalizacao);
                    window.location.reload();
                }
            } else {
                throw new Error(data.error || 'Erro.');
            }
        })
        .catch(error => {
            alert(`Erro: ${error.message}`);
            if (listItem) listItem.style.opacity = '1';
        })
        .finally(() => {
            button.innerHTML = originalHTML;
            button.disabled = false;
        });
}
async function excluirTodasDoModulo(button, moduloNome, CONFIG) {
    const ok = await confirmWithModal(`EXCLUIR TODAS as tarefas do módulo "${moduloNome}"? Esta ação é irreversível.`);
    if (!ok) return;
    // Detecta modelo hierárquico pelo hx-post dos checkboxes dentro do módulo
    let isHier = false;
    const collapseWrap = button.closest('.module-header') ? button.closest('.module-header').nextElementSibling : null;
    if (collapseWrap) {
        const anyHier = collapseWrap.querySelector('.task-checkbox[hx-post*="/api/toggle_subtarefa_h/"], .task-checkbox[hx-post*="/api/toggle_tarefa_h/"]');
        isHier = !!anyHier;
    }
    const endpointUrl = isHier ? CONFIG.endpoints.delModuloHier : CONFIG.endpoints.delModulo;
    const cardElement = button.closest('.module-header'); // Procura o .module-header
    const collapseElement = cardElement ? cardElement.nextElementSibling : null; // Pega o .collapse
    const originalBtnHTML = button.innerHTML; button.disabled = true; button.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Excluindo...`;

    if (cardElement) cardElement.style.opacity = '0.5';
    if (collapseElement) collapseElement.style.opacity = '0.5';

    const payload = isHier ? { implantacao_id: CONFIG.implantacaoId, grupo_nome: moduloNome } : { implantacao_id: CONFIG.implantacaoId, tarefa_pai: moduloNome };
    fetch(endpointUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }).then(response => response.json()).then(data => { if (data.ok) { if (collapseElement) { const taskList = collapseElement.querySelector('.list-group-sortable'); if (taskList) { taskList.innerHTML = ''; const noTaskMsg = document.createElement('div'); noTaskMsg.className = 'list-group-item text-center small text-muted fst-italic'; noTaskMsg.textContent = 'Nenhuma tarefa. Use "Adicionar Tarefa".'; taskList.appendChild(noTaskMsg); } } adicionarLogNaTimeline(data.log_exclusao_modulo); if (data.novo_progresso !== undefined) updateProgressBar(data.novo_progresso); if (data.implantacao_finalizada) { adicionarLogNaTimeline(data.log_finalizacao); window.location.reload(); } } else { throw new Error(data.error || 'Erro.'); } }).catch(error => { console.error('Erro:', error); alert(`Erro: ${error.message}`); }).finally(() => { button.innerHTML = originalBtnHTML; button.disabled = false; if (cardElement) cardElement.style.opacity = '1'; if (collapseElement) collapseElement.style.opacity = '1'; });
}
function marcarTodasDoModulo(button, collapseId, CONFIG) {
    const collapseElement = document.getElementById(collapseId); if (!collapseElement) return; const bsCollapse = bootstrap.Collapse.getOrCreateInstance(collapseElement); bsCollapse.show(); setTimeout(async () => {
        const checkboxesNaoMarcadas = Array.from(collapseElement.querySelectorAll('.task-checkbox:not(:checked)')); if (checkboxesNaoMarcadas.length === 0) { alert('Todas já concluídas.'); return; } const ok = await confirmWithModal(`Marcar ${checkboxesNaoMarcadas.length} tarefa(s) como concluída(s)?`); if (!ok) return; const originalBtnHTML = button.innerHTML; button.disabled = true; button.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Marcando...`; let promises = []; let errors = []; let ultimaFinalizada = false; let ultimoLogTarefa = null; let ultimoLogFinalizacao = null; let ultimoProgresso = null; checkboxesNaoMarcadas.forEach(checkbox => {
            const tarefaId = parseInt(checkbox.closest('li').dataset.id); if (isNaN(tarefaId)) return;
            const endpointUrl = checkbox.getAttribute('hx-post') || (CONFIG.endpoints.toggleTarefa + tarefaId);
            checkbox.disabled = true; const promise = fetch(endpointUrl, { method: 'POST' }).then(response => response.text()).then(text => {
                let data;
                try { data = JSON.parse(text); } catch (_) { data = null; }
                if (data && typeof data === 'object' && data.ok !== undefined) {
                    if (data.ok) {
                        const label = checkbox.closest('li').querySelector('label.form-check-label');
                        checkbox.checked = true;
                        if (label) label.classList.add('text-decoration-line-through', 'text-success');
                        ultimoProgresso = data.novo_progresso;
                        ultimoLogTarefa = data.log_tarefa;
                        if (data.implantacao_finalizada) { ultimaFinalizada = true; ultimoLogFinalizacao = data.log_finalizacao; }
                        return { success: true };
                    } else { throw new Error(data.error || 'Erro'); }
                } else {
                    const wrapper = checkbox.closest('li');
                    if (wrapper && text && text.trim().startsWith('<')) {
                        wrapper.outerHTML = text;
                        const newCb = document.querySelector(`#${checkbox.id}`);
                        if (newCb) { newCb.checked = true; }
                        return { success: true };
                    }
                    throw new Error('Resposta inválida');
                }
            }).catch(error => {
                console.error(`Erro ${tarefaId}:`, error);

                errors.push(error?.message || 'Erro ao marcar tarefa');
                checkbox.checked = false; const label = checkbox.closest('li').querySelector('label.form-check-label'); if (label) label.classList.remove('text-decoration-line-through', 'text-success'); return { success: false };
            }).finally(() => { checkbox.disabled = false; }); promises.push(promise);
        }); Promise.all(promises).then(() => {
            button.innerHTML = originalBtnHTML; button.disabled = false; if (ultimoProgresso !== null) updateProgressBar(ultimoProgresso); if (ultimoLogTarefa) adicionarLogNaTimeline(ultimoLogTarefa); if (ultimaFinalizada) { if (ultimoLogFinalizacao) adicionarLogNaTimeline(ultimoLogFinalizacao); window.location.reload(); return; } if (errors.length > 0) {
                const uniqueReasons = Array.from(new Set(errors.filter(Boolean)));
                if (uniqueReasons.length === 1) {
                    alert(`Falha ao marcar ${errors.length} tarefa(s).\nMotivo: ${uniqueReasons[0]}`);
                } else {
                    alert(`Falha ao marcar ${errors.length} tarefa(s).\nMotivo(s):\n- ${uniqueReasons.join('\n- ')}`);
                }
            }
        });
    }, 300);
}

document.addEventListener('DOMContentLoaded', function () {

    const mainContent = document.getElementById('main-content');
    if (!mainContent) {
        console.error("Elemento #main-content não encontrado. A página de detalhes não funcionará.");
        return;
    }
    const CONFIG = {
        implantacaoId: parseInt(mainContent.dataset.implantacaoId, 10),
        emailUsuarioLogado: mainContent.dataset.emailUsuarioLogado,
        endpoints: {
            reordenar: mainContent.dataset.urlReordenar,
            toggleTarefa: mainContent.dataset.urlToggleTarefa,
            addComentario: mainContent.dataset.urlAdicionarComentario,
            delComentario: mainContent.dataset.urlExcluirComentario,
            delTarefa: mainContent.dataset.urlExcluirTarefa,
            delModulo: mainContent.dataset.urlExcluirModulo,
            delModuloHier: mainContent.dataset.urlExcluirModuloHier,
            reordenarHier: mainContent.dataset.urlReordenarHier
        }
    };
    if (!CONFIG.implantacaoId) {
        console.error("data-implantacao-id não encontrado no #main-content.");
        return;
    }


    document.body.addEventListener('click', function (event) {
        const target = event.target;

        const deleteTaskButton = target.closest('button[title="Excluir Tarefa"]');
        if (deleteTaskButton) {
            const tarefaId = parseInt(target.closest('li[data-id]').dataset.id);
            if (tarefaId) window.excluirTarefa(tarefaId, deleteTaskButton, CONFIG);
            return;
        }

        // REMOVIDO: botões "Marcar todas" agora são tratados diretamente no template HTML
        // com event listeners específicos (.btn-marcar-todas-fase, .btn-marcar-todas-grupo, etc.)

        // REMOVIDO: botões "Desmarcar todas" agora são tratados diretamente no template HTML
        // com event listeners específicos (.btn-desmarcar-todas-fase, .btn-desmarcar-todas-grupo, etc.)


        const toggleCommentButton = target.closest('button[data-action="toggle-comment"]');
        if (toggleCommentButton) {
            const targetId = toggleCommentButton.dataset.targetId;
            if (targetId) window.toggleComment(toggleCommentButton, targetId); // A função helper toggleComment ainda é útil
            return;
        }

        const deleteCommentButton = target.closest('button[data-action="delete-comment"]');
        if (deleteCommentButton) {
            const commentId = parseInt(deleteCommentButton.dataset.commentId);
            if (commentId) {
                const endpointUrl = CONFIG.endpoints.delComentario + commentId;
                window.excluirComentario(commentId, endpointUrl, deleteCommentButton); // A função helper excluirComentario ainda é útil
            }
            return;
        }

    });


    window.toggleComment = toggleComment;
    window.excluirTarefa = excluirTarefa;
    window.marcarTodasDoModulo = marcarTodasDoModulo;
    window.excluirTodasDoModulo = excluirTodasDoModulo;

    function initializeSortableLists(CONFIG) {
        if (!window.Sortable) {
            console.warn('Sortable não carregado ainda. Aguardando evento de pronto.');
            return;
        }
        document.querySelectorAll('.list-group-sortable').forEach(listEl => {
            const hasHierarchical = Array.from(listEl.querySelectorAll('.task-checkbox')).some(cb => {
                const hp = cb.getAttribute('hx-post') || '';
                return hp.includes('/api/toggle_subtarefa_h/') || hp.includes('/api/toggle_tarefa_h/');
            });
            if (hasHierarchical) {
                new Sortable(listEl, {
                    animation: 150,
                    handle: '.handle',
                    ghostClass: 'bg-secondary',
                    onEnd: function (evt) {
                        const novaOrdemIds = Array.from(evt.to.children).map(item => parseInt(item.dataset.id));
                        fetch(CONFIG.endpoints.reordenarHier, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ implantacao_id: CONFIG.implantacaoId, grupo_nome: modulo, ordem: novaOrdemIds })
                        }).then(r => r.json()).then(d => {
                            if (d.ok && d.log_reordenar) adicionarLogNaTimeline(d.log_reordenar);
                            else if (!d.ok) throw new Error(d.error);
                        }).catch(e => alert('Erro salvar ordem.'));
                    },
                });
                return;
            }
            const moduloContainer = listEl.closest('.collapse, .card');
            let modulo = moduloContainer?.dataset.modulo;
            if (!modulo && moduloContainer?.classList.contains('card')) {
                const header = moduloContainer.querySelector('.card-header');
                const collapseTarget = header?.getAttribute('data-bs-target');
                if (collapseTarget) {
                    const collapseElement = document.querySelector(collapseTarget);
                    if (collapseElement) modulo = collapseElement.dataset.modulo;
                }
                if (!modulo) {
                    const headerText = header?.querySelector('h5')?.textContent.trim();
                    if (headerText) modulo = headerText;
                }
            }
            if (!modulo) { console.warn("Módulo não encontrado:", listEl); return; }
            new Sortable(listEl, {
                animation: 150,
                handle: '.handle',
                ghostClass: 'bg-secondary',
                onEnd: function (evt) {
                    const novaOrdemIds = Array.from(evt.to.children).map(item => parseInt(item.dataset.id));
                    fetch(CONFIG.endpoints.reordenar, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ implantacao_id: CONFIG.implantacaoId, tarefa_pai: modulo, ordem: novaOrdemIds })
                    }).then(r => r.json()).then(d => {
                        if (d.ok) adicionarLogNaTimeline(d.log_reordenar);
                        else throw new Error(d.error);
                    }).catch(e => alert('Erro salvar ordem.'));
                },
            });
        });
    }

    if (window.Sortable) {
        initializeSortableLists(CONFIG);
    } else {
        document.addEventListener('sortable-ready', function () {
            initializeSortableLists(CONFIG);
        }, { once: true });
    }
    // Sistema de tabs: buscar tanto #detalhesTab quanto #contentTabs
    const tabSelector = '#detalhesTab .nav-link, #contentTabs .nav-link'; 
    const tabPaneSelector = '#detalhesTabContent .tab-pane, #contentTabsContent .tab-pane'; 
    const tabs = document.querySelectorAll(tabSelector); 
    const panes = document.querySelectorAll(tabPaneSelector); 
    const tabStorageKey = `tabAtiva-implantacao-${CONFIG.implantacaoId}`;
    function activateTabById(buttonId) { const targetButton = document.getElementById(buttonId); const targetPaneId = targetButton?.getAttribute('data-bs-target'); if (!targetButton || !targetPaneId) { console.warn(`[ActivateTab] Botão/painel não encontrado: ${buttonId}`); return false; } const targetPane = document.querySelector(targetPaneId); if (!targetPane) { console.warn(`[ActivateTab] Painel não encontrado: ${targetPaneId}`); return false; } console.log(`[ActivateTab] Ativando: ${buttonId}`); tabs.forEach(t => t.classList.remove('active')); panes.forEach(p => p.classList.remove('active', 'show')); targetButton.classList.add('active'); targetPane.classList.add('active', 'show'); localStorage.setItem(tabStorageKey, buttonId); return true; }
    tabs.forEach(tab => { tab.addEventListener('shown.bs.tab', event => { console.log('[Tab Event] shown:', event.target.id); localStorage.setItem(tabStorageKey, event.target.id); if (window.location.hash) { console.log('[Tab Event] Limpando hash'); history.pushState("", document.title, window.location.pathname + window.location.search); } }); });
    let activated = false; const urlHash = window.location.hash; console.log('[Init] Hash:', urlHash); if (urlHash) { let hashId = urlHash.substring(1); let buttonIdToActivate = null; if (hashId.endsWith('-content')) { buttonIdToActivate = hashId.replace('-content', '-tab'); } else { const directButton = document.getElementById(hashId); if (directButton && directButton.matches(tabSelector)) { buttonIdToActivate = hashId; } } if (buttonIdToActivate) { console.log('[Init] Ativando via hash:', buttonIdToActivate); if (activateTabById(buttonIdToActivate)) { activated = true; console.log('[Init] Limpando hash pós ativação.'); history.pushState("", document.title, window.location.pathname + window.location.search); } else { history.pushState("", document.title, window.location.pathname + window.location.search); } } else { console.warn('[Init] Hash inválido.'); history.pushState("", document.title, window.location.pathname + window.location.search); } }
    if (!activated) { const savedTabId = localStorage.getItem(tabStorageKey); console.log('[Init] Restaurando via localStorage:', savedTabId); if (savedTabId) { if (!activateTabById(savedTabId)) { localStorage.removeItem(tabStorageKey); } else { activated = true; } } }
    if (!activated) { const firstTabButton = document.querySelector(tabSelector); if (firstTabButton) { console.log('[Init Fallback] Ativando padrão:', firstTabButton.id); activateTabById(firstTabButton.id); } else { console.error("[Init Fallback] Nenhuma aba!"); } }
    document.querySelectorAll('.comment-text').forEach(textEl => { const wrapper = textEl.closest('.comment-content-wrapper'); let button = wrapper ? wrapper.querySelector('button[onclick^="toggleComment"]') : null; const maxHeight = parseFloat(window.getComputedStyle(textEl).maxHeight); const isOverflowing = textEl.scrollHeight > maxHeight + 5; if (isOverflowing && !button) { const newButton = document.createElement('button'); newButton.className = 'btn btn-sm btn-link p-0 small'; newButton.textContent = 'Ver mais...'; newButton.onclick = function () { toggleComment(this, textEl.id); }; textElement.parentNode.insertBefore(newButton, textEl.nextSibling); } else if (!isOverflowing && button) { button.remove(); } else if (isOverflowing && button) { button.textContent = textEl.classList.contains('expanded') ? 'Ver menos...' : 'Ver mais...'; } });
    document.querySelectorAll('.module-header[data-bs-toggle="collapse"]').forEach(header => { const collapseId = header.getAttribute('data-bs-target'); const collapseElement = document.querySelector(collapseId); const icon = header.querySelector('i.bi-chevron-down, i.bi-chevron-up'); if (collapseElement && icon) { collapseElement.addEventListener('show.bs.collapse', () => { icon.classList.replace('bi-chevron-down', 'bi-chevron-up'); }); collapseElement.addEventListener('hide.bs.collapse', () => { icon.classList.replace('bi-chevron-up', 'bi-chevron-down'); }); if (collapseElement.classList.contains('show')) { icon.classList.replace('bi-chevron-down', 'bi-chevron-up'); } } });



    document.addEventListener('progress_update', function (event) {
        const data = event.detail || {};
        if (data.novo_progresso !== undefined) {
            updateProgressBar(data.novo_progresso);
        }
        if (data.log_tarefa) {
            adicionarLogNaTimeline(data.log_tarefa);
        }
        if (data.implantacao_finalizada) {
            if (data.log_finalizacao) adicionarLogNaTimeline(data.log_finalizacao);
            window.location.reload();
        }
    });


    document.body.addEventListener('htmx:afterSwap', function (event) {
        const target = event.detail.target;

        // Atualiza progresso quando uma tarefa ou subtarefa é alterada
        if (target && target.id && (target.id.startsWith('task-item-') || target.id.startsWith('subtarefa-'))) {
            // A barra de progresso é atualizada via OOB swap pelo servidor ou evento
            // Não precisamos fazer nada aqui, o HTMX já processou o OOB
            // O evento 'progress_update' será disparado via HX-Trigger-After-Swap
            console.log('Item atualizado:', target.id);
        }

        // Scroll e reset de formulário de comentários
        if (target && target.id && target.id.startsWith('comment-list-')) {
            try {
                // Scroll para o final da lista de comentários
                target.scrollTop = target.scrollHeight;

                // Reseta o formulário de comentário
                const form = target.previousElementSibling;
                if (form && form.classList && form.classList.contains('comment-form')) {
                    form.reset();
                }
            } catch (e) {
                console.warn('Falha ao limpar/rolar após comentário HTMX:', e);
            }
        }
    });

    // Função para atualizar badges de status nos módulos
    function updateModuleBadges() {
        try {
            document.querySelectorAll('.module-header').forEach(header => {
                const collapseElement = header.nextElementSibling;
                if (!collapseElement || !collapseElement.classList.contains('module-content-collapse')) return;

                const checkboxes = collapseElement.querySelectorAll('.task-checkbox');
                const total = checkboxes.length;

                if (total === 0) return;

                let completed = 0;
                checkboxes.forEach(checkbox => {
                    if (checkbox.checked) completed++;
                });

                const percentage = Math.round((completed / total) * 100);

                // Remove badge existente se houver
                const existingBadge = header.querySelector('.module-status-badge');
                if (existingBadge) existingBadge.remove();

                // Cria novo badge
                const badge = document.createElement('span');
                badge.className = 'badge module-status-badge ms-2';
                badge.style.fontSize = '0.75rem';
                badge.style.fontWeight = '600';
                badge.style.padding = '0.35rem 0.65rem';
                badge.style.borderRadius = '6px';
                badge.textContent = `${completed}/${total}`;

                // Define cor baseada no percentual
                if (percentage === 100) {
                    badge.style.backgroundColor = '#28a745';
                    badge.style.color = '#fff';
                } else if (percentage >= 50) {
                    badge.style.backgroundColor = '#ffc107';
                    badge.style.color = '#000';
                } else if (percentage > 0) {
                    badge.style.backgroundColor = '#fd7e14';
                    badge.style.color = '#fff';
                } else {
                    badge.style.backgroundColor = '#6c757d';
                    badge.style.color = '#fff';
                }

                // Adiciona o badge ao título
                const titleElement = header.querySelector('h5');
                if (titleElement) {
                    titleElement.appendChild(badge);
                }
            });
        } catch (error) {
            console.error('Erro ao atualizar badges dos módulos:', error);
        }
    }

    // Inicializa os badges
    updateModuleBadges();

    // Atualiza badges quando tarefas mudam
    document.body.addEventListener('change', function (ev) {
        if (ev.target && ev.target.classList && ev.target.classList.contains('task-checkbox')) {
            updateModuleBadges();
        }
    });

    // Atualiza badges após eventos HTMX
    document.body.addEventListener('htmx:afterSwap', function () {
        setTimeout(updateModuleBadges, 100);
    });
});
