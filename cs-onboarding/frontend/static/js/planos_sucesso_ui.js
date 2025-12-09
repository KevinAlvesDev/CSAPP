document.addEventListener('DOMContentLoaded', function () {
    let planoIdParaExcluir = null;

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

            // Tenta obter o token CSRF de várias fontes possíveis
            let csrfToken = '';
            const csrfInput = document.querySelector('input[name="csrf_token"]');
            if (csrfInput) {
                csrfToken = csrfInput.value;
            } else {
                const csrfMeta = document.querySelector('meta[name="csrf-token"]');
                if (csrfMeta) {
                    csrfToken = csrfMeta.content;
                }
            }

            fetch(`/planos/${planoIdParaExcluir}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.reload();
                } else {
                    alert(data.error || 'Erro ao excluir plano');
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Erro ao excluir plano');
            });
        });
    }
});
