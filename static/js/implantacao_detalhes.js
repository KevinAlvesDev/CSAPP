// static/js/implantacao_detalhes.js

// --- Funções Helper para UI ---
// (Estas funções não precisam de dados do Flask)
function formatDataComentario(dataStr) { if (!dataStr) return ''; try { const dateObj = new Date(dataStr.replace(' ', 'T') + 'Z'); if (isNaN(dateObj.getTime())) throw new Error("Inválida"); const day = String(dateObj.getDate()).padStart(2, '0'); const month = String(dateObj.getMonth() + 1).padStart(2, '0'); const year = dateObj.getFullYear(); return `${day}/${month}/${year}`; } catch (e) { console.error("Erro data:", dataStr, e); return 'Inválida'; } }
function formatDataLog(dataStr) { if (!dataStr) return ''; try { const dateObj = new Date(dataStr.replace(' ', 'T') + 'Z'); if (isNaN(dateObj.getTime())) throw new Error("Inválida"); return dateObj.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }).replace(',', ' às'); } catch (e) { console.error("Erro data log:", dataStr, e); return 'Inválida'; } }
function toggleComment(button, elementId) { const textElement = document.getElementById(elementId); if (!textElement) return; const isExpanded = textElement.classList.toggle('expanded'); button.textContent = isExpanded ? 'Ver menos...' : 'Ver mais...'; }
function criarTimelineItemHTML(log) { if (!log || !log.data_criacao) return ''; let iconClass = 'bi-info-circle-fill'; if (log.tipo_evento === 'novo_comentario') iconClass = 'bi-chat-left-text-fill'; else if (log.tipo_evento?.includes('tarefa')) iconClass = 'bi-check-circle-fill'; else if (log.tipo_evento?.includes('status') || log.tipo_evento?.includes('implantacao') || log.tipo_evento?.includes('detalhes')) iconClass = 'bi-flag-fill'; else if (log.tipo_evento === 'modulo_excluido') iconClass = 'bi-trash-fill'; const dataFormatada = formatDataLog(log.data_criacao); const detalhesHTML = (log.detalhes || '').replace(/\n/g, '<br>'); return `<li class="timeline-item"><div class="timeline-icon"><i class="bi ${iconClass}"></i></div><div class="timeline-content"><div class="timeline-header"><span class="timeline-usuario">${log.usuario_nome || 'Sistema'}</span><span class="timeline-data">${dataFormatada}</span></div><p class="timeline-detalhes">${detalhesHTML}</p></div></li>`; }
function adicionarLogNaTimeline(log) { if (!log) return; const timelineList = document.querySelector('#timeline-content .timeline-list'); if (!timelineList) return; const noTimelineMsg = document.getElementById('no-timeline-msg'); if (noTimelineMsg) noTimelineMsg.remove(); const logHTML = criarTimelineItemHTML(log); if (logHTML) timelineList.insertAdjacentHTML('afterbegin', logHTML); }

// --- INÍCIO DA CORREÇÃO (BUG 3) ---
function criarComentarioHTML(comentario, emailUsuarioLogado, urls) {
    if (!comentario || !comentario.id) return '';
    const dataFormatada = formatDataComentario(comentario.data_criacao);
    
    let botaoExcluir = '';
    if (comentario.usuario_cs == emailUsuarioLogado) {
        // REMOVIDO: onclick="..."
        // ADICIONADO: data-action="delete-comment" e data-comment-id
        botaoExcluir = `<button class="btn btn-sm btn-link text-danger p-0 small mt-1" data-action="delete-comment" data-comment-id="${comentario.id}">Excluir</button>`;
    }

    let textoHTML = `<p class="mb-1 small comment-text" id="comment-text-${comentario.id}">${comentario.texto || ''}</p>`;
    if (comentario.texto && comentario.texto.length > 200) {
        // REMOVIDO: onclick="..."
        // ADICIONADO: data-action="toggle-comment" e data-target-id
        textoHTML += `<button class="btn btn-sm btn-link p-0 small" data-action="toggle-comment" data-target-id="comment-text-${comentario.id}">Ver mais...</button>`;
    }
    
    let imagemHTML = '';
    if (comentario.imagem_url) {
        imagemHTML = `<a href="${comentario.imagem_url}" target="_blank" title="Ampliar"><img src="${comentario.imagem_url}" class="img-fluid rounded mt-1 comment-image"></a>`;
    }
    
    return `<div class="list-group-item list-group-item-action py-1 px-2" id="comentario-${comentario.id}">
                <div class="d-flex w-100 justify-content-between align-items-center mb-1">
                    <strong class="mb-0 small"><i class="bi bi-person-fill me-1"></i> ${comentario.usuario_nome || comentario.usuario_cs}</strong>
                    <small class="text-secondary">${dataFormatada}</small>
                </div>
                <div class="comment-content-wrapper">${textoHTML}${imagemHTML}</div>
                ${botaoExcluir}
            </div>`;
}
// --- FIM DA CORREÇÃO (BUG 3) ---

function updateProgressBar(progress) { const progressBar = document.querySelector('#main-content .progress-bar'); if (progressBar) { const progressNum = parseInt(progress) || 0; progressBar.style.width = progressNum + '%'; progressBar.setAttribute('aria-valuenow', progressNum); progressBar.textContent = progressNum + '%'; } }

// --- Funções de Ação (Adaptadas para ler URLs do objeto CONFIG) ---
function adicionarComentario(tarefaId, button, CONFIG) { 
    const endpointUrl = CONFIG.endpoints.addComentario + tarefaId;
    const form = button.closest('.comment-form'); const textarea = form.querySelector('textarea'); const fileInput = form.querySelector('input[type="file"]'); const comentarioTexto = textarea.value.trim(); const file = fileInput.files.length > 0 ? fileInput.files[0] : null; if (comentarioTexto === '' && !file) { alert('Comentário vazio sem imagem.'); return; } if (file) { const allowedTypes = ['image/png', 'image/jpeg', 'image/gif']; if (!allowedTypes.includes(file.type)) { alert('Tipo de arquivo não permitido.'); fileInput.value = null; return; } } const originalBtnHTML = button.innerHTML; button.disabled = true; button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Salvando...'; const formData = new FormData(form); fetch(endpointUrl, { method: 'POST', body: formData }).then(response => response.json()).then(data => { if (data.ok && data.comentario) { const commentList = document.getElementById('comment-list-' + tarefaId); const noCommentMsg = document.getElementById('no-comment-' + tarefaId); if (noCommentMsg) noCommentMsg.remove(); const comentarioHTML = criarComentarioHTML(data.comentario, CONFIG.emailUsuarioLogado, CONFIG.endpoints); if (comentarioHTML) { commentList.insertAdjacentHTML('beforeend', commentList.innerHTML); commentList.scrollTop = commentList.scrollHeight; } textarea.value = ''; fileInput.value = null; adicionarLogNaTimeline(data.log_comentario); } else { throw new Error(data.error || 'Erro desconhecido.'); } }).catch(error => { console.error('Erro:', error); alert(`Erro: ${error.message}`); }).finally(() => { button.innerHTML = originalBtnHTML; button.disabled = false; }); }
function excluirComentario(comentarioId, endpointUrl, button) { if (!confirm('Excluir este comentário?')) return; const comentarioElement = button.closest('.list-group-item'); if (comentarioElement) comentarioElement.style.opacity = '0.5'; fetch(endpointUrl, { method: 'POST' }).then(response => response.json()).then(data => { if (data.ok) { if (comentarioElement) comentarioElement.remove(); const listElement = button.closest('.list-group'); if(listElement && listElement.children.length === 0){ const tarefaIdGuess = listElement.id.split('-')[2]; listElement.innerHTML = `<div class="list-group-item ... fst-italic" id="no-comment-${tarefaIdGuess}"> Nenhum comentário. </div>`; } adicionarLogNaTimeline(data.log_exclusao); } else { throw new Error(data.error || 'Erro.'); } }).catch(error => { console.error('Erro:', error); alert(`Erro: ${error.message}`); if (comentarioElement) comentarioElement.style.opacity = '1'; }); }
function toggleTarefa(tarefaId, checkbox, CONFIG) { 
    const label = checkbox.closest('li').querySelector('label.form-check-label'); const isChecked = checkbox.checked; checkbox.disabled = true; 
    const endpointUrl = CONFIG.endpoints.toggleTarefa + tarefaId;
    fetch(endpointUrl, { method: 'POST' }).then(response => response.json()).then(data => { if (data.ok) { if (data.novo_status === 1) { label.classList.add('text-decoration-line-through', 'text-success'); } else { label.classList.remove('text-decoration-line-through', 'text-success'); } if (data.novo_progresso !== undefined) { updateProgressBar(data.novo_progresso); } adicionarLogNaTimeline(data.log_tarefa); if (data.implantacao_finalizada) { adicionarLogNaTimeline(data.log_finalizacao); window.location.reload(); } } else { checkbox.checked = !isChecked; throw new Error(data.error || 'Erro.'); } }).catch(error => { console.error('Erro:', error); alert(`Erro: ${error.message}`); checkbox.checked = !isChecked; }).finally(() => { checkbox.disabled = false; }); }
function excluirTarefa(tarefaId, button, CONFIG) { 
    if (!confirm('Excluir tarefa e comentários?')) return; 
    const endpointUrl = CONFIG.endpoints.delTarefa + tarefaId;
    button.disabled = true; button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>'; const listItem = button.closest('.list-group-item'); if (listItem) listItem.style.opacity = '0.5'; fetch(endpointUrl, { method: 'POST' }).then(response => response.json()).then(data => { if (data.ok) { if(listItem) listItem.remove(); adicionarLogNaTimeline(data.log_exclusao); if (data.novo_progresso !== undefined) updateProgressBar(data.novo_progresso); if (data.implantacao_finalizada) { adicionarLogNaTimeline(data.log_finalizacao); window.location.reload(); } } else { throw new Error(data.error || 'Erro.'); } }).catch(error => { console.error('Erro:', error); alert(`Erro: ${error.message}`); button.innerHTML = '<i class="bi bi-x-lg"></i>'; button.disabled = false; if (listItem) listItem.style.opacity = '1'; }); }
function excluirTodasDoModulo(button, moduloNome, CONFIG) { 
    if (!confirm(`EXCLUIR TODAS as tarefas do módulo "${moduloNome}"? Irreversível!`)) return; 
    const endpointUrl = CONFIG.endpoints.delModulo;
    const cardElement = button.closest('.module-header'); // Procura o .module-header
    const collapseElement = cardElement ? cardElement.nextElementSibling : null; // Pega o .collapse
    const originalBtnHTML = button.innerHTML; button.disabled = true; button.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Excluindo...`; 
    
    // Aplica opacidade ao cabeçalho E ao conteúdo
    if (cardElement) cardElement.style.opacity = '0.5';
    if (collapseElement) collapseElement.style.opacity = '0.5';

    fetch(endpointUrl, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ implantacao_id: CONFIG.implantacaoId, tarefa_pai: moduloNome }) }).then(response => response.json()).then(data => { if (data.ok) { if (collapseElement) { const taskList = collapseElement.querySelector('.list-group-sortable'); if (taskList) { taskList.innerHTML = ''; const noTaskMsg = document.createElement('div'); noTaskMsg.className = 'list-group-item text-center small text-muted fst-italic'; noTaskMsg.textContent = 'Nenhuma tarefa. Use "Adicionar Tarefa".'; taskList.appendChild(noTaskMsg); } } adicionarLogNaTimeline(data.log_exclusao_modulo); if (data.novo_progresso !== undefined) updateProgressBar(data.novo_progresso); if (data.implantacao_finalizada) { adicionarLogNaTimeline(data.log_finalizacao); window.location.reload(); } } else { throw new Error(data.error || 'Erro.'); } }).catch(error => { console.error('Erro:', error); alert(`Erro: ${error.message}`); }).finally(() => { button.innerHTML = originalBtnHTML; button.disabled = false; if (cardElement) cardElement.style.opacity = '1'; if (collapseElement) collapseElement.style.opacity = '1'; }); }
function marcarTodasDoModulo(button, collapseId, CONFIG) { 
    const collapseElement = document.getElementById(collapseId); if (!collapseElement) return; const bsCollapse = bootstrap.Collapse.getOrCreateInstance(collapseElement); bsCollapse.show(); setTimeout(() => { const checkboxesNaoMarcadas = Array.from(collapseElement.querySelectorAll('.task-checkbox:not(:checked)')); if (checkboxesNaoMarcadas.length === 0) { alert('Todas já concluídas.'); return; } if (!confirm(`Marcar ${checkboxesNaoMarcadas.length} tarefa(s) como concluída(s)?`)) return; const originalBtnHTML = button.innerHTML; button.disabled = true; button.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Marcando...`; let promises = []; let errors = []; let ultimaFinalizada = false; let ultimoLogTarefa = null; let ultimoLogFinalizacao = null; let ultimoProgresso = null; checkboxesNaoMarcadas.forEach(checkbox => { const tarefaId = parseInt(checkbox.closest('li').dataset.id); if (isNaN(tarefaId)) return; 
    const endpointUrl = CONFIG.endpoints.toggleTarefa + tarefaId;
    checkbox.disabled = true; const promise = fetch(endpointUrl, { method: 'POST' }).then(response => response.json()).then(data => { if (data.ok) { const label = checkbox.closest('li').querySelector('label.form-check-label'); checkbox.checked = true; if(label) label.classList.add('text-decoration-line-through', 'text-success'); ultimoProgresso = data.novo_progresso; ultimoLogTarefa = data.log_tarefa; if(data.implantacao_finalizada) { ultimaFinalizada = true; ultimoLogFinalizacao = data.log_finalizacao; } return { success: true }; } else { throw new Error(data.error || 'Erro'); } }).catch(error => { console.error(`Erro ${tarefaId}:`, error); errors.push(tarefaId); checkbox.checked = false; const label = checkbox.closest('li').querySelector('label.form-check-label'); if(label) label.classList.remove('text-decoration-line-through', 'text-success'); return { success: false }; }).finally(() => { checkbox.disabled = false; }); promises.push(promise); }); Promise.all(promises).then(() => { button.innerHTML = originalBtnHTML; button.disabled = false; if (ultimoProgresso !== null) updateProgressBar(ultimoProgresso); if (ultimoLogTarefa) adicionarLogNaTimeline(ultimoLogTarefa); if (ultimaFinalizada) { if (ultimoLogFinalizacao) adicionarLogNaTimeline(ultimoLogFinalizacao); window.location.reload(); return; } if (errors.length > 0) alert(`Falha ao marcar ${errors.length} tarefa(s).`); }); }, 300); }

// --- Inicialização da Página ---
document.addEventListener('DOMContentLoaded', function() {
    
    // 1. LÊ AS CONFIGURAÇÕES DO JINJA2 A PARTIR DA TAG <main>
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
            delModulo: mainContent.dataset.urlExcluirModulo
        }
    };
    if (!CONFIG.implantacaoId) {
         console.error("data-implantacao-id não encontrado no #main-content.");
         return;
    }

    // 2. ATRIBUI OS EVENTOS (LISTENERS) AOS BOTÕES
    // (Esta é a parte que substitui os onclicks inline)
    document.body.addEventListener('click', function(event) {
        const target = event.target;
        
        // Botão Salvar Comentário
        const saveCommentButton = target.closest('.comment-form button[type="button"]');
        if (saveCommentButton) {
            const tarefaId = parseInt(target.closest('li[data-id]').dataset.id);
            if(tarefaId) window.adicionarComentario(tarefaId, saveCommentButton, CONFIG);
            return; 
        }

        // Botão Excluir Tarefa
        const deleteTaskButton = target.closest('button[title="Excluir Tarefa"]');
        if (deleteTaskButton) {
            const tarefaId = parseInt(target.closest('li[data-id]').dataset.id);
            if(tarefaId) window.excluirTarefa(tarefaId, deleteTaskButton, CONFIG);
            return;
        }

        // Botão Marcar Todas
        const markAllButton = target.closest('button[title="Marcar todas"]');
        if (markAllButton) {
             // --- INÍCIO DA CORREÇÃO ---
             event.stopPropagation(); // Impede o clique de "borbulhar" para o .module-header
             // --- FIM DA CORREÇÃO ---
             const collapseId = markAllButton.closest('.module-header').getAttribute('data-bs-target').substring(1);
             if(collapseId) window.marcarTodasDoModulo(markAllButton, collapseId, CONFIG);
             return;
        }

        // Botão Excluir Todas
        const deleteAllButton = target.closest('button[title="Excluir todas"]');
        if (deleteAllButton) {
             // --- INÍCIO DA CORREÇÃO ---
             event.stopPropagation(); // Impede o clique de "borbulhar" para o .module-header
             // --- FIM DA CORREÇÃO ---
             const moduloNome = deleteAllButton.closest('.module-header').nextElementSibling.dataset.modulo;
             if(moduloNome) window.excluirTodasDoModulo(deleteAllButton, moduloNome, CONFIG);
             return;
        }

        // --- INÍCIO DA CORREÇÃO (BUG 3) ---
        // Botão "Ver mais..." (comentário) - REFACTORIZADO
        const toggleCommentButton = target.closest('button[data-action="toggle-comment"]');
        if (toggleCommentButton) {
            const targetId = toggleCommentButton.dataset.targetId;
            if(targetId) window.toggleComment(toggleCommentButton, targetId); // A função helper toggleComment ainda é útil
            return;
        }
        
        // Botão Excluir Comentário - REFACTORIZADO
        const deleteCommentButton = target.closest('button[data-action="delete-comment"]');
        if (deleteCommentButton) {
            const commentId = parseInt(deleteCommentButton.dataset.commentId);
            if(commentId) {
                const endpointUrl = CONFIG.endpoints.delComentario + commentId;
                window.excluirComentario(commentId, endpointUrl, deleteCommentButton); // A função helper excluirComentario ainda é útil
            }
            return;
        }
        // --- FIM DA CORREÇÃO (BUG 3) ---
    });
    
    // Listener separado para Checkbox (evento 'change')
    document.body.addEventListener('change', function(event) {
        const target = event.target;
        // Toggle Tarefa (Checkbox)
        if (target.classList.contains('task-checkbox')) {
            const tarefaId = parseInt(target.closest('li[data-id]').dataset.id);
            if(tarefaId) window.toggleTarefa(tarefaId, target, CONFIG);
        }
    });


    // 3. INICIALIZA FUNCIONALIDADES DA PÁGINA (Sortable, Tabs)
    // (Atribui as funções à 'window' para que os 'onclick' gerados dinamicamente funcionem)
    window.toggleTarefa = toggleTarefa; 
    window.adicionarComentario = adicionarComentario; 
    window.excluirComentario = excluirComentario; 
    window.toggleComment = toggleComment; 
    window.excluirTarefa = excluirTarefa; 
    window.marcarTodasDoModulo = marcarTodasDoModulo; 
    window.excluirTodasDoModulo = excluirTodasDoModulo;
    
    document.querySelectorAll('.list-group-sortable').forEach(listEl => { const moduloContainer = listEl.closest('.collapse, .card'); let modulo = moduloContainer?.dataset.modulo; if (!modulo && moduloContainer?.classList.contains('card')) { const header = moduloContainer.querySelector('.card-header'); const collapseTarget = header?.getAttribute('data-bs-target'); if (collapseTarget) { const collapseElement = document.querySelector(collapseTarget); if(collapseElement) modulo = collapseElement.dataset.modulo; } if (!modulo) { const headerText = header?.querySelector('h5')?.textContent.trim(); if (headerText) modulo = headerText; } } if (!modulo) { console.warn("Módulo não encontrado:", listEl); return; } new Sortable(listEl, { animation: 150, handle: '.handle', ghostClass: 'bg-secondary', onEnd: function (evt) { const novaOrdemIds = Array.from(evt.to.children).map(item => parseInt(item.dataset.id)); fetch(CONFIG.endpoints.reordenar, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ implantacao_id: CONFIG.implantacaoId, tarefa_pai: modulo, ordem: novaOrdemIds }) }).then(r => r.json()).then(d => { if (d.ok) adicionarLogNaTimeline(d.log_reordenar); else throw new Error(d.error); }).catch(e => alert('Erro salvar ordem.')); }, }); });
    const tabSelector = '#detalhesTab .nav-link'; const tabPaneSelector = '#detalhesTabContent .tab-pane'; const tabs = document.querySelectorAll(tabSelector); const panes = document.querySelectorAll(tabPaneSelector); const tabStorageKey = `tabAtiva-implantacao-${CONFIG.implantacaoId}`;
    function activateTabById(buttonId) { const targetButton = document.getElementById(buttonId); const targetPaneId = targetButton?.getAttribute('data-bs-target'); if (!targetButton || !targetPaneId) { console.warn(`[ActivateTab] Botão/painel não encontrado: ${buttonId}`); return false; } const targetPane = document.querySelector(targetPaneId); if (!targetPane) { console.warn(`[ActivateTab] Painel não encontrado: ${targetPaneId}`); return false; } console.log(`[ActivateTab] Ativando: ${buttonId}`); tabs.forEach(t => t.classList.remove('active')); panes.forEach(p => p.classList.remove('active', 'show')); targetButton.classList.add('active'); targetPane.classList.add('active', 'show'); localStorage.setItem(tabStorageKey, buttonId); return true; }
    tabs.forEach(tab => { tab.addEventListener('shown.bs.tab', event => { console.log('[Tab Event] shown:', event.target.id); localStorage.setItem(tabStorageKey, event.target.id); if (window.location.hash) { console.log('[Tab Event] Limpando hash'); history.pushState("", document.title, window.location.pathname + window.location.search); } }); });
    let activated = false; const urlHash = window.location.hash; console.log('[Init] Hash:', urlHash); if (urlHash) { let hashId = urlHash.substring(1); let buttonIdToActivate = null; if (hashId.endsWith('-content')) { buttonIdToActivate = hashId.replace('-content', '-tab'); } else { const directButton = document.getElementById(hashId); if (directButton && directButton.matches(tabSelector)) { buttonIdToActivate = hashId; } } if (buttonIdToActivate) { console.log('[Init] Ativando via hash:', buttonIdToActivate); if (activateTabById(buttonIdToActivate)) { activated = true; console.log('[Init] Limpando hash pós ativação.'); history.pushState("", document.title, window.location.pathname + window.location.search); } else { history.pushState("", document.title, window.location.pathname + window.location.search); } } else { console.warn('[Init] Hash inválido.'); history.pushState("", document.title, window.location.pathname + window.location.search); } }
    if (!activated) { const savedTabId = localStorage.getItem(tabStorageKey); console.log('[Init] Restaurando via localStorage:', savedTabId); if (savedTabId) { if (!activateTabById(savedTabId)) { localStorage.removeItem(tabStorageKey); } else { activated = true; } } }
    if (!activated) { const firstTabButton = document.querySelector(tabSelector); if (firstTabButton) { console.log('[Init Fallback] Ativando padrão:', firstTabButton.id); activateTabById(firstTabButton.id); } else { console.error("[Init Fallback] Nenhuma aba!"); } }
    document.querySelectorAll('.comment-text').forEach(textEl => { const wrapper = textEl.closest('.comment-content-wrapper'); let button = wrapper ? wrapper.querySelector('button[onclick^="toggleComment"]') : null; const maxHeight = parseFloat(window.getComputedStyle(textEl).maxHeight); const isOverflowing = textEl.scrollHeight > maxHeight + 5; if (isOverflowing && !button) { const newButton = document.createElement('button'); newButton.className = 'btn btn-sm btn-link p-0 small'; newButton.textContent = 'Ver mais...'; newButton.onclick = function() { toggleComment(this, textEl.id); }; textElement.parentNode.insertBefore(newButton, textEl.nextSibling); } else if (!isOverflowing && button) { button.remove(); } else if (isOverflowing && button) { button.textContent = textEl.classList.contains('expanded') ? 'Ver menos...' : 'Ver mais...'; } });
    document.querySelectorAll('.module-header[data-bs-toggle="collapse"]').forEach(header => { const collapseId = header.getAttribute('data-bs-target'); const collapseElement = document.querySelector(collapseId); const icon = header.querySelector('i.bi-chevron-down, i.bi-chevron-up'); if (collapseElement && icon) { collapseElement.addEventListener('show.bs.collapse', () => { icon.classList.replace('bi-chevron-down','bi-chevron-up'); }); collapseElement.addEventListener('hide.bs.collapse', () => { icon.classList.replace('bi-chevron-up','bi-chevron-down'); }); if (collapseElement.classList.contains('show')) { icon.classList.replace('bi-chevron-down','bi-chevron-up'); } } });
});