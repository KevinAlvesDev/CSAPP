/*
* =================================================================================
* Funções AJAX para a página de detalhes da implantação (implantacao_detalhes.html)
* =================================================================================
*/

/**
 * Pega o CSRF token (se você estiver usando WTForms ou Flask-SeaSurf)
 * Você pode remover isso se não estiver usando CSRF por AJAX.
 */
function getCsrfToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

/**
 * Função helper para mostrar/esconder spinners de botões
 * @param {HTMLElement} button - O elemento do botão
 * @param {boolean} show - True para mostrar spinner, false para esconder
 */
function toggleButtonSpinner(button, show) {
    if (!button) return;
    const buttonText = button.querySelector('.button-text');
    const spinner = button.querySelector('.spinner-border');
    
    if (show) {
        button.disabled = true;
        if (buttonText) buttonText.style.display = 'none';
        if (spinner) spinner.style.display = 'inline-block';
    } else {
        button.disabled = false;
        if (buttonText) buttonText.style.display = 'inline-block';
        if (spinner) spinner.style.display = 'none';
    }
}

/**
 * Função helper para atualizar o log da timeline (usado por várias funções)
 * @param {object} logData - O objeto de log vindo da API
 */
function atualizarTimeline(logData) {
    if (!logData) return;
    
    const timelineContainer = document.getElementById('timeline-container');
    if (!timelineContainer) return;

    // Formata a data (a API deve retornar 'data_criacao' em formato ISO)
    let dataFormatada = 'agora';
    if (logData.data_criacao) {
        try {
            const dataObj = new Date(logData.data_criacao);
            dataFormatada = dataObj.toLocaleString('pt-BR', { 
                day: '2-digit', 
                month: '2-digit', 
                year: 'numeric', 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        } catch (e) { console.warn("Formato de data inválido no log da timeline."); }
    }

    // Cria o novo HTML do log
    const logHtml = `
        <li class="timeline-item">
            <div class="timeline-info">
                <strong>${logData.usuario_nome || logData.usuario_cs || 'Sistema'}</strong>
                <span class="text-muted small">${dataFormatada}</span>
            </div>
            <div class="timeline-body">
                <span class="badge ${logData.tipo_evento || 'log-default'}">${logData.tipo_evento || 'LOG'}</span>
                <p class="mt-1 mb-0">${logData.detalhes.replace(/\n/g, '<br>') || ''}</p>
            </div>
        </li>
    `;
    
    timelineContainer.insertAdjacentHTML('afterbegin', logHtml);
}

/**
 * Atualiza o progresso da barra principal
 * @param {number} novoProgresso - Valor de 0 a 100
 */
function atualizarBarraProgresso(novoProgresso) {
    const progressBar = document.getElementById('main-progress-bar');
    const progressText = document.getElementById('main-progress-text');
    if (progressBar) {
        progressBar.style.width = novoProgresso + '%';
        progressBar.setAttribute('aria-valuenow', novoProgresso);
    }
    if (progressText) {
        progressText.textContent = Math.round(novoProgresso) + '%';
    }
}

/**
 * Lida com o resultado de uma implantação finalizada (ex: toggle de tarefa)
 * @param {object} logFinalizacao - O log da timeline vindo da API
 */
function handleImplantacaoFinalizada(logFinalizacao) {
    if (logFinalizacao) {
        // --- ATUALIZAÇÃO: Usa showToast ---
        showToast('Implantação finalizada automaticamente!', 'success');
        
        // Atualiza o status na UI
        const statusBadge = document.getElementById('status-badge');
        if (statusBadge) {
            statusBadge.className = 'badge bg-success';
            statusBadge.textContent = 'Finalizada';
        }
        
        // Atualiza a timeline
        atualizarTimeline(logFinalizacao);
        
        // Desativa todos os botões de ação (ex: pausar, etc.)
        document.querySelectorAll('.action-button').forEach(btn => btn.disabled = true);
        
        // Oculta área de adicionar tarefas/comentários
        document.getElementById('add-task-form-container')?.remove();
        document.querySelectorAll('.comment-form-container').forEach(form => form.remove());
    }
}


// =================================================================================
// FUNÇÕES DE AÇÃO (AJAX)
// =================================================================================

/**
 * (Ação) Atualiza o status (Pausar, Iniciar, etc.)
 * Usado pelo modal 'pararImplantacaoModal' e botões 'iniciar-agora', etc.
 */
function ajaxAtualizarStatus(implantacaoId, novoStatus, motivoParada = '') {
    const url = `/implantacao/${implantacaoId}/atualizar-status`;
    const button = document.getElementById(`btn-parar-implantacao`); // Assume que o ID é estático
    
    toggleButtonSpinner(button, true);

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            // 'X-CSRFToken': getCsrfToken() // Descomente se usar CSRF
        },
        body: JSON.stringify({
            novo_status: novoStatus,
            motivo_parada: motivoParada
        })
    })
    .then(response => response.json())
    .then(data => {
        toggleButtonSpinner(button, false);
        if (data.ok) {
            // Recarrega a página para refletir todas as mudanças de status
            window.location.reload();
        } else {
            // --- ATUALIZAÇÃO: Substitui alert por showToast ---
            showToast('Erro ao atualizar status: ' + data.error, 'error');
        }
    })
    .catch(error => {
        toggleButtonSpinner(button, false);
        // --- ATUALIZAÇÃO: Substitui alert por showToast ---
        showToast('Erro de rede: ' + error.message, 'error');
        console.error('Erro de rede:', error);
    });
}

/**
 * (Ação) Marca ou desmarca uma tarefa como concluída
 * @param {HTMLElement} checkbox - O input checkbox que foi clicado
 * @param {number} tarefaId - O ID da tarefa
 */
function ajaxToggleTarefa(checkbox, tarefaId) {
    const url = `/api/toggle_tarefa/${tarefaId}`;
    const label = checkbox.closest('label');
    const spinner = label ? label.querySelector('.task-spinner') : null;
    const checkIcon = label ? label.querySelector('.check-icon') : null;

    // Mostra spinner e esconde ícone
    if (spinner) spinner.style.display = 'inline-block';
    if (checkIcon) checkIcon.style.display = 'none';
    checkbox.disabled = true;

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            // 'X-CSRFToken': getCsrfToken() 
        }
    })
    .then(response => response.json())
    .then(data => {
        // Esconde spinner e mostra ícone
        if (spinner) spinner.style.display = 'none';
        if (checkIcon) checkIcon.style.display = 'block';
        checkbox.disabled = false;

        if (data.ok) {
            // Atualiza o progresso
            atualizarBarraProgresso(data.novo_progresso);
            // Atualiza a timeline
            atualizarTimeline(data.log_tarefa);
            // Verifica se a implantação foi finalizada
            handleImplantacaoFinalizada(data.log_finalizacao);
        } else {
            // Reverte o checkbox se deu erro
            checkbox.checked = !checkbox.checked;
            // --- ATUALIZAÇÃO: Substitui alert por showToast ---
            showToast(data.error, 'error');
        }
    })
    .catch(error => {
        // Esconde spinner e mostra ícone
        if (spinner) spinner.style.display = 'none';
        if (checkIcon) checkIcon.style.display = 'block';
        checkbox.disabled = false;
        
        // Reverte o checkbox
        checkbox.checked = !checkbox.checked;
        
        // --- ATUALIZAÇÃO: Substitui alert por showToast ---
        showToast('Erro de rede: ' + error.message, 'error');
        console.error('Erro de rede:', error);
    });
}

/**
 * (Ação) Adiciona um novo comentário a uma tarefa
 * @param {HTMLFormElement} form - O formulário de comentário
 */
function ajaxAdicionarComentario(form) {
    const tarefaId = form.dataset.tarefaId;
    if (!tarefaId) return;
    
    const url = `/api/adicionar_comentario/${tarefaId}`;
    const button = form.querySelector('button[type="submit"]');
    const formData = new FormData(form);

    toggleButtonSpinner(button, true);

    fetch(url, {
        method: 'POST',
        body: formData,
        // headers: { 'X-CSRFToken': getCsrfToken() } // FormData não usa Content-Type
    })
    .then(response => response.json())
    .then(data => {
        toggleButtonSpinner(button, false);
        if (data.ok) {
            // Limpa o formulário
            form.reset();
            const preview = form.querySelector('.comment-image-preview');
            if (preview) preview.innerHTML = '';
            
            // Adiciona o comentário à lista na UI
            const commentList = document.getElementById(`comment-list-${tarefaId}`);
            if (commentList) {
                // Formata a data (a API deve retornar 'data_criacao' em formato ISO)
                let dataFormatada = 'agora';
                if (data.comentario.data_criacao) {
                    try {
                        const dataObj = new Date(data.comentario.data_criacao);
                        dataFormatada = dataObj.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
                    } catch(e) {}
                }

                const imgHtml = data.comentario.imagem_url ? 
                    `<a href="${data.comentario.imagem_url}" target="_blank" class="comment-image-link">
                        <img src="${data.comentario.imagem_url}" alt="Imagem do Comentário" class="comment-image">
                     </a>` : '';
                
                const commentHtml = `
                    <div class="comment-item" id="comment-${data.comentario.id}">
                        <div class="comment-header">
                            <strong>${data.comentario.usuario_nome || data.comentario.usuario_cs}</strong>
                            <span class="text-muted small">${dataFormatada}</span>
                            <button class="btn btn-sm btn-outline-danger p-0 px-1 float-end" onclick="ajaxExcluirComentario(${data.comentario.id})">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                        <div class="comment-body">
                            <p>${data.comentario.texto.replace(/\n/g, '<br>')}</p>
                            ${imgHtml}
                        </div>
                    </div>
                `;
                commentList.insertAdjacentHTML('beforeend', commentHtml);
            }
            
            // Atualiza a timeline
            atualizarTimeline(data.log_comentario);
            
        } else {
            // --- ATUALIZAÇÃO: Substitui alert por showToast ---
            showToast(data.error, 'error');
        }
    })
    .catch(error => {
        toggleButtonSpinner(button, false);
        // --- ATUALIZAÇÃO: Substitui alert por showToast ---
        showToast('Erro de rede: ' + error.message, 'error');
        console.error('Erro de rede:', error);
    });
}

/**
 * (Ação) Exclui um comentário
 * @param {number} comentarioId - O ID do comentário
 */
function ajaxExcluirComentario(comentarioId) {
    // --- ATENÇÃO: confirm() mantido intencionalmente ---
    // A substituição ideal para 'confirm' é um Modal Bootstrap,
    // que é uma alteração mais complexa.
    if (!confirm('Tem certeza que deseja excluir este comentário?')) {
        return;
    }

    const url = `/api/excluir_comentario/${comentarioId}`;
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            // 'X-CSRFToken': getCsrfToken() 
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            // Remove o comentário da UI
            const commentElement = document.getElementById(`comment-${comentarioId}`);
            if (commentElement) {
                commentElement.remove();
            }
            // Atualiza a timeline
            atualizarTimeline(data.log_exclusao);
            
        } else {
            // --- ATUALIZAÇÃO: Substitui alert por showToast ---
            showToast(data.error, 'error');
        }
    })
    .catch(error => {
        // --- ATUALIZAÇÃO: Substitui alert por showToast ---
        showToast('Erro de rede: ' + error.message, 'error');
        console.error('Erro de rede:', error);
    });
}

/**
 * (Ação) Exclui uma tarefa
 * @param {number} tarefaId - O ID da tarefa
 * @param {HTMLElement} linkElement - O elemento <a> que foi clicado
 */
function ajaxExcluirTarefa(tarefaId, linkElement) {
    // --- ATENÇÃO: confirm() mantido intencionalmente ---
    if (!confirm('Tem certeza que deseja excluir esta tarefa? (Comentários e imagens associadas serão perdidos)')) {
        return;
    }
    
    const url = `/api/excluir_tarefa/${tarefaId}`;
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            // 'X-CSRFToken': getCsrfToken() 
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            // Remove a tarefa da UI
            const taskElement = linkElement.closest('.task-item');
            if (taskElement) {
                taskElement.remove();
            }
            // Atualiza o progresso
            atualizarBarraProgresso(data.novo_progresso);
            // Atualiza a timeline
            atualizarTimeline(data.log_exclusao);
            // Verifica se a implantação foi finalizada
            handleImplantacaoFinalizada(data.log_finalizacao);
            
        } else {
            // --- ATUALIZAÇÃO: Substitui alert por showToast ---
            showToast(data.error, 'error');
        }
    })
    .catch(error => {
        // --- ATUALIZAÇÃO: Substitui alert por showToast ---
        showToast('Erro de rede: ' + error.message, 'error');
        console.error('Erro de rede:', error);
    });
}

/**
 * (Ação) Adiciona uma nova tarefa
 * @param {HTMLFormElement} form - O formulário de adicionar tarefa
 */
function ajaxAdicionarTarefa(form) {
    const implantacaoId = form.dataset.implantacaoId;
    if (!implantacaoId) return;

    const url = `/implantacao/${implantacaoId}/adicionar-tarefa`;
    const button = form.querySelector('button[type="submit"]');
    const formData = new FormData(form);

    toggleButtonSpinner(button, true);

    fetch(url, {
        method: 'POST',
        body: formData,
        // headers: { 'X-CSRFToken': getCsrfToken() } 
    })
    .then(response => response.json())
    .then(data => {
        toggleButtonSpinner(button, false);
        if (data.ok) {
            // Recarrega a página para refletir a nova tarefa e módulo
            window.location.reload();
        } else {
            // --- ATUALIZAÇÃO: Substitui alert por showToast ---
            showToast(data.error, 'error');
        }
    })
    .catch(error => {
        toggleButtonSpinner(button, false);
        // --- ATUALIZAÇÃO: Substitui alert por showToast ---
        showToast('Erro de rede: ' + error.message, 'error');
        console.error('Erro de rede:', error);
    });
}

/**
 * (Ação) Reordena tarefas (via drag-and-drop do SortableJS)
 * @param {string} moduloNome - O nome do módulo (tarefa_pai)
 * @param {Array} novaOrdemIds - Array de IDs na nova ordem
 * @param {number} implantacaoId - O ID da implantação
 */
function ajaxReordenarTarefas(moduloNome, novaOrdemIds, implantacaoId) {
    const url = `/api/reordenar_tarefas`;
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            // 'X-CSRFToken': getCsrfToken() 
        },
        body: JSON.stringify({
            implantacao_id: implantacaoId,
            tarefa_pai: moduloNome,
            ordem: novaOrdemIds
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            // Loga na timeline (o re-drag é permitido)
            atualizarTimeline(data.log_reordenar);
        } else {
            // --- ATUALIZAÇÃO: Substitui alert por showToast ---
            showToast('Erro ao reordenar tarefas: ' + data.error, 'error');
            // Recarrega a página para reverter a ordem visual
            window.location.reload();
        }
    })
    .catch(error => {
        // --- ATUALIZAÇÃO: Substitui alert por showToast ---
        showToast('Erro de rede ao reordenar: ' + error.message, 'error');
        console.error('Erro de rede:', error);
        window.location.reload();
    });
}

/**
 * (Ação) Exclui todas as tarefas de um módulo
 * @param {string} moduloNome - O nome do módulo (tarefa_pai)
 * @param {number} implantacaoId - O ID da implantação
 */
function ajaxExcluirModulo(moduloNome, implantacaoId) {
    // --- ATENÇÃO: confirm() mantido intencionalmente ---
    if (!confirm(`Tem certeza que deseja excluir TODO o módulo '${moduloNome}'?\n\n(Todas as tarefas, comentários e imagens deste módulo serão perdidos!)`)) {
        return;
    }

    const url = `/api/excluir_tarefas_modulo`;
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            // 'X-CSRFToken': getCsrfToken() 
        },
        body: JSON.stringify({
            implantacao_id: implantacaoId,
            tarefa_pai: moduloNome
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            // Remove o módulo da UI
            const moduloElement = document.getElementById(`modulo-${moduloNome.replace(/[^a-zA-Z0-9]/g, '-')}`);
            if (moduloElement) {
                moduloElement.remove();
            }
            // Atualiza o progresso
            atualizarBarraProgresso(data.novo_progresso);
            // Atualiza a timeline
            atualizarTimeline(data.log_exclusao_modulo);
            // Verifica se a implantação foi finalizada
            handleImplantacaoFinalizada(data.log_finalizacao);
            
        } else {
            // --- ATUALIZAÇÃO: Substitui alert por showToast ---
            showToast('Erro ao excluir módulo: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        // --- ATUALIZAÇÃO: Substitui alert por showToast ---
        showToast('Erro de rede ao excluir módulo: ' + error.message, 'error');
        console.error('Erro de rede:', error);
    });
}

/**
 * (Ação) Salva os detalhes da empresa (Modal 'detalhesEmpresaModal')
 * @param {HTMLFormElement} form - O formulário do modal
 */
function ajaxSalvarDetalhesEmpresa(form) {
    const implantacaoId = form.dataset.implantacaoId;
    if (!implantacaoId) return;

    const url = `/implantacao/${implantacaoId}/salvar-detalhes-empresa`;
    const button = form.querySelector('button[type="submit"]');
    const formData = new FormData(form);

    toggleButtonSpinner(button, true);

    fetch(url, {
        method: 'POST',
        body: formData,
        // headers: { 'X-CSRFToken': getCsrfToken() } 
    })
    .then(response => response.json())
    .then(data => {
        toggleButtonSpinner(button, false);
        if (data.ok) {
            // --- ATUALIZAÇÃO: Substitui alert por showToast ---
            showToast('Detalhes salvos com sucesso!', 'success');
            
            // Fecha o modal
            const modalElement = document.getElementById('detalhesEmpresaModal');
            const modalInstance = bootstrap.Modal.getInstance(modalElement);
            if (modalInstance) {
                modalInstance.hide();
            }
            
            // Atualiza os campos na página principal (se necessário)
            // (Esta parte pode ser complexa e 'window.location.reload()' pode ser mais fácil)
            if (data.log_detalhes) {
                atualizarTimeline(data.log_detalhes);
            }
            
            // Simplesmente recarrega para ver as mudanças
            window.location.reload();
            
        } else {
            // --- ATUALIZAÇÃO: Substitui alert por showToast ---
            showToast(data.error, 'error');
        }
    })
    .catch(error => {
        toggleButtonSpinner(button, false);
        // --- ATUALIZAÇÃO: Substitui alert por showToast ---
        showToast('Erro de rede: ' + error.message, 'error');
        console.error('Erro de rede:', error);
    });
}


// =================================================================================
// EVENT LISTENERS (Inicialização)
// =================================================================================

document.addEventListener('DOMContentLoaded', function() {
    
    // --- Listener para formulário de Adicionar Tarefa ---
    const addTaskForm = document.getElementById('add-task-form');
    if (addTaskForm) {
        addTaskForm.addEventListener('submit', function(e) {
            e.preventDefault();
            ajaxAdicionarTarefa(this);
        });
    }

    // --- Listeners para formulários de Adicionar Comentário ---
    const commentForms = document.querySelectorAll('.comment-form');
    commentForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            ajaxAdicionarComentario(this);
        });

        // Listener para preview de imagem no comentário
        const imageInput = form.querySelector('input[type="file"]');
        const previewContainer = form.querySelector('.comment-image-preview');
        if (imageInput && previewContainer) {
            imageInput.addEventListener('change', function() {
                previewContainer.innerHTML = ''; // Limpa previews antigos
                if (this.files && this.files[0]) {
                    const file = this.files[0];
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        img.classList.add('comment-image-preview-thumb');
                        
                        const removeBtn = document.createElement('span');
                        removeBtn.classList.add('remove-preview-btn');
                        removeBtn.innerHTML = '&times;';
                        removeBtn.onclick = () => {
                            imageInput.value = ''; // Limpa o input
                            previewContainer.innerHTML = ''; // Limpa o preview
                        };

                        previewContainer.appendChild(img);
                        previewContainer.appendChild(removeBtn);
                    }
                    reader.readAsDataURL(file);
                }
            });
        }
    });

    // --- Listener para o botão de salvar no modal 'pararImplantacaoModal' ---
    const saveStopButton = document.getElementById('btn-salvar-parada');
    if (saveStopButton) {
        saveStopButton.addEventListener('click', function() {
            const implantacaoId = this.dataset.implantacaoId;
            const motivo = document.getElementById('motivo_parada_input').value;
            if (!motivo) {
                 // --- ATUALIZAÇÃO: Substitui alert por showToast ---
                showToast('Por favor, selecione um motivo para a parada.', 'warning');
                return;
            }
            ajaxAtualizarStatus(implantacaoId, 'parada', motivo);
        });
    }
    
    // --- Listener para o botão de salvar no modal 'detalhesEmpresaModal' ---
    const saveDetalhesForm = document.getElementById('detalhes-empresa-form');
    if (saveDetalhesForm) {
        saveDetalhesForm.addEventListener('submit', function(e) {
            e.preventDefault();
            ajaxSalvarDetalhesEmpresa(this);
        });
    }

    // --- Inicialização do Drag-and-Drop (SortableJS) ---
    // (A biblioteca SortableJS precisa estar importada no seu <head> ou <body>)
    if (typeof Sortable !== 'undefined') {
        const taskLists = document.querySelectorAll('.task-list');
        taskLists.forEach(list => {
            new Sortable(list, {
                group: 'tarefas', // Permite arrastar entre listas
                animation: 150,
                handle: '.drag-handle', // Define o ícone de arrastar
                ghostClass: 'sortable-ghost', // Classe CSS para o "fantasma"
                chosenClass: 'sortable-chosen', // Classe CSS para o item escolhido
                dragClass: 'sortable-drag', // Classe CSS para o item sendo arrastado
                
                // Chamado ao soltar um item
                onEnd: function (evt) {
                    const itemEl = evt.item; // O item arrastado
                    const toList = evt.to; // A lista de destino
                    const moduloNome = toList.dataset.moduloNome;
                    const implantacaoId = toList.dataset.implantacaoId;

                    if (!moduloNome || !implantacaoId) {
                        console.error("Dados do módulo ou implantação não encontrados na lista.");
                        return;
                    }

                    // Pega a nova ordem dos IDs
                    const novaOrdemIds = Array.from(toList.children).map(el => el.dataset.tarefaId);
                    
                    // Envia a nova ordem para o backend
                    ajaxReordenarTarefas(moduloNome, novaOrdemIds, implantacaoId);
                }
            });
        });
    } else {
        console.warn("Biblioteca SortableJS não encontrada. Drag-and-drop não será ativado.");
    }
    
});