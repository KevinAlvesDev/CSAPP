document.addEventListener('DOMContentLoaded', function () {
    let planoIdParaExcluir = null;
    let planoIdParaClonar = null;

    // ========================================
    // EXCLUSÃO DE PLANO
    // ========================================
    document.querySelectorAll('.btn-excluir-plano').forEach(btn => {
        btn.addEventListener('click', function () {
            planoIdParaExcluir = this.dataset.planoId;
            const planoNome = this.dataset.planoNome;
            const nomeElement = document.getElementById('planoNomeExcluir');
            if (nomeElement) {
                nomeElement.textContent = planoNome;
            }
        });
    });

    const btnConfirmar = document.getElementById('btnConfirmarExclusao');
    if (btnConfirmar) {
        btnConfirmar.addEventListener('click', function () {
            if (!planoIdParaExcluir) return;

            const btnOriginalText = this.innerHTML;
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Excluindo...';

            window.apiFetch(`/planos/${planoIdParaExcluir}`, {
                method: 'DELETE'
            })
                .then(data => {
                    if (data.success) {
                        if (window.showToast) window.showToast('Plano excluído com sucesso!', 'success');
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        throw new Error(data.error || 'Erro ao excluir plano');
                    }
                })
                .catch(error => {
                    // apiFetch já mostra toast de erro
                    this.disabled = false;
                    this.innerHTML = btnOriginalText;
                });
        });
    }

    // ========================================
    // CLONAGEM DE PLANO
    // ========================================
    document.querySelectorAll('.btn-clonar-plano').forEach(btn => {
        btn.addEventListener('click', function () {
            planoIdParaClonar = this.dataset.planoId;
            const planoNome = this.dataset.planoNome;

            // Preencher modal
            const nomeElement = document.getElementById('planoNomeClonar');
            if (nomeElement) {
                nomeElement.textContent = planoNome;
            }

            // Sugerir nome para o novo plano
            const inputNome = document.getElementById('novoNomePlano');
            if (inputNome) {
                inputNome.value = `${planoNome} - Cópia`;
                inputNome.select();
            }

            // Limpar descrição
            const inputDescricao = document.getElementById('novaDescricaoPlano');
            if (inputDescricao) {
                inputDescricao.value = '';
            }

            // Abrir modal
            const modal = new bootstrap.Modal(document.getElementById('modalClonarPlano'));
            modal.show();
        });
    });

    const btnConfirmarClonagem = document.getElementById('btnConfirmarClonagem');
    if (btnConfirmarClonagem) {
        btnConfirmarClonagem.addEventListener('click', async function () {
            if (!planoIdParaClonar) return;

            const form = document.getElementById('formClonarPlano');
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }

            const novoNome = document.getElementById('novoNomePlano').value.trim();
            const novaDescricao = document.getElementById('novaDescricaoPlano').value.trim();

            if (!novoNome) {
                if (window.showToast) window.showToast('Nome do plano é obrigatório', 'warning');
                return;
            }

            const btnOriginalText = this.innerHTML;
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Clonando...';

            try {
                const data = await window.apiFetch(`/planos/${planoIdParaClonar}/clonar`, {
                    method: 'POST',
                    body: JSON.stringify({
                        nome: novoNome,
                        descricao: novaDescricao || null
                    })
                });

                if (data.ok || data.success) {
                    if (window.showToast) window.showToast(data.message || 'Plano clonado com sucesso!', 'success');

                    // Fechar modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('modalClonarPlano'));
                    if (modal) modal.hide();

                    // Redirecionar para o novo plano ou recarregar
                    if (data.redirect_url) {
                        setTimeout(() => window.location.href = data.redirect_url, 1000);
                    } else {
                        setTimeout(() => window.location.reload(), 1000);
                    }
                } else {
                    throw new Error(data.error || 'Erro ao clonar plano');
                }
            } catch (error) {
                // apiFetch já mostra toast de erro
                this.disabled = false;
                this.innerHTML = btnOriginalText;
            }
        });
    }

    // Limpar modal ao fechar
    const modalClonar = document.getElementById('modalClonarPlano');
    if (modalClonar) {
        modalClonar.addEventListener('hidden.bs.modal', function () {
            planoIdParaClonar = null;
            document.getElementById('formClonarPlano').reset();
        });
    }
});

