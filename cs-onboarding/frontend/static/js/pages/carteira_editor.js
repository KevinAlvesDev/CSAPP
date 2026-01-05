/**
 * Definição de Carteira - Editor de Informações da Implantação
 * Permite adicionar e editar informações detalhadas sobre a implantação
 */

document.addEventListener('DOMContentLoaded', function () {
    const btnEdit = document.getElementById('btn-edit-carteira');
    const btnSave = document.getElementById('btn-save-carteira');
    const btnCancel = document.getElementById('btn-cancel-carteira');
    const viewMode = document.getElementById('carteira-view-mode');
    const editMode = document.getElementById('carteira-edit-mode');
    const textarea = document.getElementById('carteira-textarea');
    const contentDisplay = document.getElementById('carteira-content-display');
    const saveStatus = document.getElementById('carteira-save-status');
    const saveText = document.getElementById('carteira-save-text');

    const implantacaoId = document.getElementById('main-content')?.getAttribute('data-implantacao-id');

    let originalContent = '';

    // Carregar conteúdo ao abrir a aba
    const carteiraTab = document.getElementById('carteira-tab');
    if (carteiraTab) {
        carteiraTab.addEventListener('shown.bs.tab', function () {
            loadCarteiraContent();
        });
    }

    // Função para carregar conteúdo
    function loadCarteiraContent() {
        if (!implantacaoId) return;

        fetch(`/api/v1/implantacoes/${implantacaoId}/carteira`)
            .then(response => response.json())
            .then(data => {
                if (data.content) {
                    originalContent = data.content;
                    displayContent(data.content);
                } else {
                    originalContent = '';
                    showEmptyState();
                }
            })
            .catch(error => {
                console.error('Erro ao carregar definição de carteira:', error);
                showEmptyState();
            });
    }

    // Função para exibir conteúdo formatado
    function displayContent(content) {
        if (!content || content.trim() === '') {
            showEmptyState();
            return;
        }

        // Converter links em elementos clicáveis
        const formattedContent = linkify(content);

        // Remover classes de centralização se existirem
        contentDisplay.classList.remove('d-flex', 'align-items-center', 'justify-content-center');

        contentDisplay.innerHTML = formattedContent;
    }

    // Função para mostrar estado vazio
    function showEmptyState() {
        // Adicionar classes de centralização
        contentDisplay.classList.add('d-flex', 'align-items-center', 'justify-content-center');

        contentDisplay.innerHTML = `
            <div class="text-muted text-center py-5">
                <p class="mb-2">Nenhuma informação adicionada ainda.</p>
                <p class="small mb-0">Clique em "Editar" para adicionar informações sobre esta implantação.</p>
            </div>
        `;
    }

    // Função para converter links em elementos clicáveis
    function linkify(text) {
        // Escapar HTML primeiro
        const div = document.createElement('div');
        div.textContent = text;
        let escaped = div.innerHTML;

        // Converter URLs em links
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        escaped = escaped.replace(urlRegex, function (url) {
            return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="text-primary text-decoration-underline">${url}</a>`;
        });

        return escaped;
    }

    // Botão Editar
    if (btnEdit) {
        btnEdit.addEventListener('click', function () {
            textarea.value = originalContent;
            viewMode.classList.add('d-none');
            editMode.classList.remove('d-none');
            btnEdit.classList.add('d-none');
            btnSave.classList.remove('d-none');
            btnCancel.classList.remove('d-none');
            textarea.focus();
        });
    }

    // Botão Cancelar
    if (btnCancel) {
        btnCancel.addEventListener('click', function () {
            editMode.classList.add('d-none');
            viewMode.classList.remove('d-none');
            btnEdit.classList.remove('d-none');
            btnSave.classList.add('d-none');
            btnCancel.classList.add('d-none');
            saveStatus.classList.add('d-none');
        });
    }

    // Botão Salvar
    if (btnSave) {
        btnSave.addEventListener('click', function () {
            saveCarteiraContent();
        });
    }

    // Função para salvar conteúdo
    function saveCarteiraContent() {
        if (!implantacaoId) {
            showToast('Erro: ID da implantação não encontrado', 'error');
            return;
        }

        const content = textarea.value;

        // Mostrar status de salvamento
        saveStatus.classList.remove('d-none');
        saveText.textContent = 'Salvando...';
        btnSave.disabled = true;

        fetch(`/api/v1/implantacoes/${implantacaoId}/carteira`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ content: content }),
            credentials: 'include'
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erro ao salvar');
                }
                return response.json();
            })
            .then(data => {
                originalContent = content;
                displayContent(content);

                // Voltar para modo visualização
                editMode.classList.add('d-none');
                viewMode.classList.remove('d-none');
                btnEdit.classList.remove('d-none');
                btnSave.classList.add('d-none');
                btnCancel.classList.add('d-none');

                // Mostrar mensagem de sucesso
                saveText.textContent = 'Salvo com sucesso!';
                setTimeout(() => {
                    saveStatus.classList.add('d-none');
                }, 3000);

                if (window.showToast) {
                    window.showToast('Definição de carteira salva com sucesso!', 'success');
                }
            })
            .catch(error => {
                console.error('Erro ao salvar:', error);
                saveText.textContent = 'Erro ao salvar';
                saveStatus.classList.remove('text-muted');
                saveStatus.classList.add('text-danger');

                if (window.showToast) {
                    window.showToast('Erro ao salvar definição de carteira', 'error');
                }
            })
            .finally(() => {
                btnSave.disabled = false;
            });
    }

    // Helper para mostrar toast (fallback se window.showToast não existir)
    function showToast(message, type) {
        if (window.showToast) {
            window.showToast(message, type);
        } else {
            alert(message);
        }
    }
});
