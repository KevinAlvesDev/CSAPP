/**
 * Gerenciador de Avisos Personalizados
 * Permite adicionar, editar e excluir avisos customizados para implantações
 */

document.addEventListener('DOMContentLoaded', function () {
    const btnAddAviso = document.getElementById('btn-add-aviso');
    const btnSaveAviso = document.getElementById('btn-save-aviso');
    const avisosList = document.getElementById('avisos-personalizados-list');
    const avisosLoading = document.getElementById('avisos-loading');
    const avisosEmpty = document.getElementById('avisos-empty');
    const modalAviso = document.getElementById('modalAviso');
    const formAviso = document.getElementById('formAviso');

    const implantacaoId = document.getElementById('main-content')?.getAttribute('data-implantacao-id');

    let bsModalAviso;
    if (modalAviso) {
        bsModalAviso = new bootstrap.Modal(modalAviso);
    }

    // Carregar avisos ao abrir a aba
    const avisosTab = document.getElementById('avisos-tab');
    if (avisosTab) {
        avisosTab.addEventListener('shown.bs.tab', function () {
            console.log('[Avisos] Aba de avisos aberta, carregando avisos...');
            loadAvisos();
        });

        // Também carregar se a aba já estiver ativa
        avisosTab.addEventListener('click', function () {
            console.log('[Avisos] Aba de avisos clicada');
            setTimeout(() => loadAvisos(), 100);
        });
    }

    // Contador de caracteres
    const avisoMensagem = document.getElementById('aviso-mensagem');
    const charCount = document.getElementById('aviso-char-count');
    if (avisoMensagem && charCount) {
        avisoMensagem.addEventListener('input', function () {
            charCount.textContent = this.value.length;
        });
    }

    // Botão Adicionar Aviso
    if (btnAddAviso) {
        btnAddAviso.addEventListener('click', function () {
            openAvisoModal();
        });
    }

    // Botão Salvar Aviso
    if (btnSaveAviso) {
        btnSaveAviso.addEventListener('click', function () {
            saveAviso();
        });
    }


    // Função para carregar avisos
    function loadAvisos() {
        if (!implantacaoId) {
            console.error('[Avisos] ID da implantação não encontrado');
            return;
        }

        console.log(`[Avisos] Carregando avisos para implantação ${implantacaoId}`);

        if (avisosLoading) avisosLoading.classList.remove('d-none');
        if (avisosEmpty) avisosEmpty.classList.add('d-none');
        if (avisosList) avisosList.innerHTML = '';

        fetch(`/api/v1/implantacoes/${implantacaoId}/avisos`)
            .then(response => {
                console.log('[Avisos] Resposta recebida:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('[Avisos] Dados recebidos:', data);

                if (avisosLoading) avisosLoading.classList.add('d-none');

                if (data.ok && data.avisos && data.avisos.length > 0) {
                    console.log(`[Avisos] Renderizando ${data.avisos.length} avisos`);
                    renderAvisos(data.avisos);
                } else {
                    console.log('[Avisos] Nenhum aviso encontrado');
                    if (avisosEmpty) avisosEmpty.classList.remove('d-none');
                }
            })
            .catch(error => {
                console.error('[Avisos] Erro ao carregar avisos:', error);
                if (avisosLoading) avisosLoading.classList.add('d-none');
                if (avisosEmpty) avisosEmpty.classList.remove('d-none');
            });
    }

    // Função para renderizar avisos
    function renderAvisos(avisos) {
        console.log(`[Avisos] Renderizando ${avisos.length} avisos`);

        // Limpar lista primeiro
        avisosList.innerHTML = '';

        avisos.forEach(aviso => {
            const avisoEl = createAvisoElement(aviso);
            avisosList.appendChild(avisoEl);
        });

        console.log('[Avisos] Avisos renderizados com sucesso');
    }

    // Função para criar elemento de aviso
    function createAvisoElement(aviso) {
        const div = document.createElement('div');
        div.className = `alert alert-${aviso.tipo} d-flex align-items-start mb-3`;
        div.setAttribute('data-aviso-id', aviso.id);

        const icon = getIconForTipo(aviso.tipo);

        div.innerHTML = `
            <i class="${icon} fs-4 me-3 flex-shrink-0"></i>
            <div class="flex-grow-1">
                <h6 class="alert-heading mb-2">${escapeHtml(aviso.titulo)}</h6>
                <p class="mb-2">${escapeHtml(aviso.mensagem)}</p>
                <small class="text-muted">
                    <i class="bi bi-person me-1"></i>${escapeHtml(aviso.criado_por)} • 
                    <i class="bi bi-clock me-1"></i>${formatDate(aviso.data_criacao)}
                </small>
            </div>
            <div class="ms-2">
                <button class="btn btn-sm btn-outline-secondary me-1" onclick="editAviso(${aviso.id})" title="Editar">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteAviso(${aviso.id})" title="Excluir">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;

        return div;
    }

    // Função para obter ícone baseado no tipo
    function getIconForTipo(tipo) {
        const icons = {
            'info': 'bi bi-info-circle-fill',
            'warning': 'bi bi-exclamation-triangle-fill',
            'danger': 'bi bi-exclamation-octagon-fill',
            'success': 'bi bi-check-circle-fill'
        };
        return icons[tipo] || 'bi bi-info-circle-fill';
    }

    // Função para abrir modal (adicionar ou editar)
    function openAvisoModal(avisoId = null) {
        const modalTitle = document.getElementById('modalAvisoLabel');
        const avisoIdInput = document.getElementById('aviso-id');

        if (avisoId) {
            // Modo edição
            modalTitle.textContent = 'Editar Aviso';
            avisoIdInput.value = avisoId;

            // Carregar dados do aviso
            fetch(`/api/v1/implantacoes/${implantacaoId}/avisos/${avisoId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.ok && data.aviso) {
                        document.getElementById('aviso-tipo').value = data.aviso.tipo;
                        document.getElementById('aviso-titulo').value = data.aviso.titulo;
                        document.getElementById('aviso-mensagem').value = data.aviso.mensagem;
                        charCount.textContent = data.aviso.mensagem.length;
                    }
                })
                .catch(error => {
                    console.error('Erro ao carregar aviso:', error);
                    showToast('Erro ao carregar aviso', 'error');
                });
        } else {
            // Modo adicionar
            modalTitle.textContent = 'Adicionar Aviso';
            avisoIdInput.value = '';
            formAviso.reset();
            charCount.textContent = '0';
        }

        bsModalAviso.show();
    }

    // Função para salvar aviso
    function saveAviso() {
        if (!formAviso.checkValidity()) {
            formAviso.reportValidity();
            return;
        }

        const avisoId = document.getElementById('aviso-id').value;
        const tipo = document.getElementById('aviso-tipo').value;
        const titulo = document.getElementById('aviso-titulo').value;
        const mensagem = document.getElementById('aviso-mensagem').value;

        const data = { tipo, titulo, mensagem };
        const url = avisoId
            ? `/api/v1/implantacoes/${implantacaoId}/avisos/${avisoId}`
            : `/api/v1/implantacoes/${implantacaoId}/avisos`;
        const method = avisoId ? 'PUT' : 'POST';

        btnSaveAviso.disabled = true;
        btnSaveAviso.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Salvando...';

        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
            credentials: 'include'
        })
            .then(response => response.json())
            .then(data => {
                if (data.ok) {
                    bsModalAviso.hide();
                    loadAvisos();
                    showToast(avisoId ? 'Aviso atualizado com sucesso!' : 'Aviso adicionado com sucesso!', 'success');
                } else {
                    throw new Error(data.error || 'Erro ao salvar aviso');
                }
            })
            .catch(error => {
                console.error('Erro ao salvar aviso:', error);
                showToast(error.message || 'Erro ao salvar aviso', 'error');
            })
            .finally(() => {
                btnSaveAviso.disabled = false;
                btnSaveAviso.innerHTML = 'Salvar Aviso';
            });
    }

    // Função para editar aviso (exposta globalmente)
    window.editAviso = function (avisoId) {
        openAvisoModal(avisoId);
    };

    // Função para excluir aviso (exposta globalmente)
    window.deleteAviso = async function (avisoId) {
        const confirmed = await window.showConfirm({
            title: 'Excluir Aviso',
            message: 'Tem certeza que deseja excluir este aviso? Esta ação não pode ser desfeita.',
            confirmText: 'Excluir',
            cancelText: 'Cancelar',
            type: 'danger',
            icon: 'bi-trash-fill'
        });

        if (!confirmed) {
            return;
        }

        fetch(`/api/v1/implantacoes/${implantacaoId}/avisos/${avisoId}`, {
            method: 'DELETE',
            credentials: 'include'
        })
            .then(response => response.json())
            .then(data => {
                if (data.ok) {
                    loadAvisos();
                    showToast('Aviso excluído com sucesso!', 'success');
                } else {
                    throw new Error(data.error || 'Erro ao excluir aviso');
                }
            })
            .catch(error => {
                console.error('Erro ao excluir aviso:', error);
                showToast(error.message || 'Erro ao excluir aviso', 'error');
            });
    };

    // Helper functions
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatDate(dateString) {
        if (!dateString) return '';
        // Se já estiver no formato brasileiro (dd/mm/yyyy às HH:MM), retornar como está
        var brFormatRegex = /^\d{2}\/\d{2}\/\d{4}(\s+às\s+\d{2}:\d{2})?$/;
        if (brFormatRegex.test(String(dateString).trim())) {
            return String(dateString);
        }
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return String(dateString);
        return date.toLocaleDateString('pt-BR') + ' ' + date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    }

    function showToast(message, type) {
        if (window.showToast) {
            window.showToast(message, type);
        } else {
            alert(message);
        }
    }
});
