'use strict';

(function () {
  document.addEventListener('DOMContentLoaded', function () {
    const mainContent = document.getElementById('main-content');
    if (!mainContent) {
      return;
    }

    const CONFIG = {
      implantacaoId: mainContent.dataset.implantacaoId,
      emailUsuarioLogado: mainContent.dataset.emailUsuarioLogado,
      userEmail: mainContent.dataset.emailUsuarioLogado || '',
      emailResponsavel: mainContent.dataset.emailResponsavel || '',
      csrfToken: document.querySelector('input[name="csrf_token"]')?.value || '',
      isManager: (mainContent.dataset.isManager || 'false') === 'true'
    };

    if (!CONFIG.implantacaoId) {
      return;
    }

    if (window.flatpickr) {
      const baseConfig = {
        dateFormat: 'Y-m-d',
        altInput: true,
        altFormat: 'd/m/Y',
        allowInput: true,
        locale: {
          firstDayOfWeek: 1,
          weekdays: {
            shorthand: ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'],
            longhand: ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']
          },
          months: {
            shorthand: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
            longhand: ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
          }
        }
      };

      document.querySelectorAll('.flatpickr-date:not(.no-datepicker)').forEach(input => {
        const fp = window.flatpickr(input, Object.assign({}, baseConfig));
        // Garantir que o valor seja salvo corretamente
        if (input.hasAttribute('required')) {
          input.addEventListener('change', function() {
            if (this._flatpickr && this._flatpickr.selectedDates.length > 0) {
              const date = this._flatpickr.selectedDates[0];
              this._flatpickr.setDate(date, false);
            }
          });
        }
      });

      // Inicializar botões de calendário
      document.querySelectorAll('button[id^="btn_cal_"], button[id^="btn-cal-"], button[id*="cal-"], button[data-toggle]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          const target = btn.previousElementSibling;
          if (target && target._flatpickr) {
            target._flatpickr.open();
          } else if (target && target.classList.contains('flatpickr-date')) {
            // Se o flatpickr ainda não foi inicializado, inicializar agora
            const fp = window.flatpickr(target, Object.assign({}, baseConfig));
            fp.open();
          }
        });
      });

      // Inicializar especificamente os campos de data dos modais
      const modalParar = document.getElementById('modalParar');
      if (modalParar) {
        modalParar.addEventListener('shown.bs.modal', function() {
          const dataParadaInput = document.getElementById('data_parada');
          const btnCal = document.getElementById('btn_cal_data_parada');
          if (dataParadaInput && !dataParadaInput._flatpickr) {
            const fp = window.flatpickr(dataParadaInput, Object.assign({}, baseConfig, {
              onChange: function(selectedDates, dateStr, instance) {
                if (selectedDates.length > 0) {
                  // O valor real (dateStr) já está em Y-m-d, que é o que o backend espera
                  // O altInput mostra DD/MM/AAAA para o usuário
                  dataParadaInput.value = dateStr; // Formato Y-m-d para o backend
                }
              }
            }));
            // Configurar botão do calendário
            if (btnCal) {
              btnCal.addEventListener('click', function(e) {
                e.preventDefault();
                fp.open();
              });
            }
          }
        });
      }

      const modalCancelar = document.getElementById('modalCancelar');
      if (modalCancelar) {
        modalCancelar.addEventListener('shown.bs.modal', function() {
          const dataCancelamentoInput = document.getElementById('data_cancelamento');
          const btnCal = document.getElementById('btn_cal_data_cancelamento');
          if (dataCancelamentoInput && !dataCancelamentoInput._flatpickr) {
            const fp = window.flatpickr(dataCancelamentoInput, Object.assign({}, baseConfig, {
              onChange: function(selectedDates, dateStr, instance) {
                if (selectedDates.length > 0) {
                  // O valor real (dateStr) já está em Y-m-d, que é o que o backend espera
                  // O altInput mostra DD/MM/AAAA para o usuário
                  dataCancelamentoInput.value = dateStr; // Formato Y-m-d para o backend
                }
              }
            }));
            // Configurar botão do calendário
            if (btnCal) {
              btnCal.addEventListener('click', function(e) {
                e.preventDefault();
                fp.open();
              });
            }
          }
        });
      }

      // Validação dos formulários de parar e cancelar
      const formParar = document.getElementById('formPararImplantacao');
      if (formParar) {
        formParar.addEventListener('submit', function(e) {
          const dataParadaInput = document.getElementById('data_parada');
          const errorMsg = document.getElementById('data_parada_error');
          
          if (dataParadaInput) {
            let dataValida = false;
            
            // Verificar se o flatpickr tem uma data selecionada
            if (dataParadaInput._flatpickr && dataParadaInput._flatpickr.selectedDates.length > 0) {
              // O valor já está no formato Y-m-d (que é o que o backend espera)
              dataValida = true;
            } else if (dataParadaInput.value && dataParadaInput.value.trim() !== '') {
              // Validar formato Y-m-d ou DD/MM/AAAA
              const datePatternYmd = /^\d{4}-\d{2}-\d{2}$/;
              const datePatternDmy = /^\d{2}\/\d{2}\/\d{4}$/;
              if (datePatternYmd.test(dataParadaInput.value.trim()) || datePatternDmy.test(dataParadaInput.value.trim())) {
                dataValida = true;
              }
            }
            
            if (!dataValida) {
              e.preventDefault();
              if (errorMsg) {
                errorMsg.classList.remove('d-none');
              }
              dataParadaInput.focus();
              return false;
            } else {
              if (errorMsg) {
                errorMsg.classList.add('d-none');
              }
            }
          }
        });
      }

      const formCancelar = document.getElementById('formCancelarImplantacao');
      if (formCancelar) {
        formCancelar.addEventListener('submit', function(e) {
          const dataCancelamentoInput = document.getElementById('data_cancelamento');
          const errorMsg = document.getElementById('data_cancelamento_error');
          
          if (dataCancelamentoInput) {
            let dataValida = false;
            
            // Verificar se o flatpickr tem uma data selecionada
            if (dataCancelamentoInput._flatpickr && dataCancelamentoInput._flatpickr.selectedDates.length > 0) {
              // O valor já está no formato Y-m-d (que é o que o backend espera)
              dataValida = true;
            } else if (dataCancelamentoInput.value && dataCancelamentoInput.value.trim() !== '') {
              // Validar formato Y-m-d ou DD/MM/AAAA
              const datePatternYmd = /^\d{4}-\d{2}-\d{2}$/;
              const datePatternDmy = /^\d{2}\/\d{2}\/\d{4}$/;
              if (datePatternYmd.test(dataCancelamentoInput.value.trim()) || datePatternDmy.test(dataCancelamentoInput.value.trim())) {
                dataValida = true;
              }
            }
            
            if (!dataValida) {
              e.preventDefault();
              if (errorMsg) {
                errorMsg.classList.remove('d-none');
              }
              dataCancelamentoInput.focus();
              return false;
            } else {
              if (errorMsg) {
                errorMsg.classList.add('d-none');
              }
            }
          }
        });
      }
    }

    function computeProgress() {
      const tarefaCheckboxes = document.querySelectorAll('.tarefa-checkbox');
      const total = tarefaCheckboxes.length;
      const done = Array.from(tarefaCheckboxes).filter(cb => cb.checked).length;
      const pct = total ? Math.round((done / total) * 100) : 0;

      const bar = document.getElementById('progress-total-bar');
      const valorEl = document.getElementById('progresso-valor');
      if (bar) {
        bar.style.width = pct + '%';
        bar.setAttribute('aria-valuenow', pct);
      }
      if (valorEl) valorEl.textContent = pct + '%';
    }

    document.querySelectorAll('.tarefa-nome.no-checkbox-toggle').forEach(label => {
      label.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
      });
    });

    document.querySelectorAll('.tarefa-checkbox').forEach(checkbox => {
      checkbox.addEventListener('change', async function () {
        const tarefaId = this.dataset.tarefaId;
        const concluido = this.checked;

        try {
          const response = await fetch(`/api/toggle_tarefa_h/${tarefaId}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
              'X-CSRFToken': CONFIG.csrfToken
            },
            body: JSON.stringify({ concluido })
          });

          if (!response.ok) {
            this.checked = !concluido;
            showToast('Erro ao atualizar tarefa', 'error');
            return;
          }

          const data = await response.json();
          if (data.ok || data.success) {
            computeProgress();
            showToast('Tarefa atualizada', 'success', 2000);
          } else {
            this.checked = !concluido;
            showToast('Erro ao atualizar tarefa', 'error');
          }
        } catch (error) {
          this.checked = !concluido;
          showToast('Erro ao comunicar com o servidor', 'error');
        }
      });
    });

    document.querySelectorAll('.btn-toggle-comentarios').forEach(btn => {
      btn.addEventListener('click', async function () {
        const tarefaId = this.dataset.tarefaId;
        const comentariosSection = document.getElementById(`comentarios-tarefa-${tarefaId}`);

        if (!comentariosSection) return;

        const isShown = comentariosSection.classList.contains('show');
        if (!isShown) {
          await carregarComentarios(tarefaId);
        }

        new bootstrap.Collapse(comentariosSection, { toggle: true });
      });
    });

    document.querySelectorAll('.comentario-tipo-tag').forEach(tag => {
      tag.addEventListener('click', function () {
        const tarefaId = this.dataset.tarefaId;
        if (!tarefaId) return;

        const tipo = this.dataset.tipo;
        const container = this.closest('.d-flex');
        container.querySelectorAll('.comentario-tipo-tag').forEach(t => t.classList.remove('active'));
        this.classList.add('active');

        const btnEmail = document.getElementById(`btn-email-${tarefaId}`);
        if (btnEmail) {
          btnEmail.classList.toggle('d-none', tipo !== 'externo');
        }
      });
    });

    document.body.addEventListener('click', async function (e) {
      const targetBtn = e.target.closest('.btn-excluir-comentario');
      if (!targetBtn) return;

      const comentarioId = targetBtn.dataset.comentarioId;
      const confirmed = await showConfirm({
        title: 'Excluir Comentário',
        message: 'Tem certeza que deseja excluir este comentário? Esta ação não pode ser desfeita.',
        confirmText: 'Excluir',
        cancelText: 'Cancelar',
        type: 'danger',
        icon: 'bi-trash-fill'
      });

      if (!confirmed) return;

      try {
        const response = await fetch(`/api/excluir_comentario_h/${comentarioId}`, {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
            'X-CSRFToken': CONFIG.csrfToken
          }
        });

        if (!response.ok) {
          const errorText = await response.text();
          showToast('Erro ao excluir comentário: ' + (errorText || `Status ${response.status}`), 'error');
          return;
        }

        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          const data = await response.json();
          if (!data.ok && !data.success) {
            showToast('Erro ao excluir comentário: ' + (data.error || 'Erro desconhecido'), 'error');
            return;
          }
        } else if (!contentType.includes('text/html')) {
          try {
            const text = await response.text();
            const data = JSON.parse(text);
            if (!data.ok && !data.success) {
              showToast('Erro ao excluir comentário: ' + (data.error || 'Erro desconhecido'), 'error');
              return;
            }
          } catch (err) {
            console.warn('Resposta não é JSON nem HTML, assumindo sucesso');
          }
        }

        const comentarioItem = targetBtn.closest('.comentario-item');
        const historico = comentarioItem ? comentarioItem.closest('[id^="historico-tarefa-"]') : null;
        const itemId = historico ? historico.id.replace('historico-tarefa-', '') : null;

        if (comentarioItem) comentarioItem.remove();
        if (itemId) await carregarComentarios(itemId);

        showToast('Comentário excluído com sucesso', 'success');
      } catch (error) {
        console.error('Erro:', error);
        showToast('Erro ao comunicar com o servidor: ' + error.message, 'error');
      }
    });

    document.querySelectorAll('.btn-salvar-comentario').forEach(btn => {
      btn.addEventListener('click', async function () {
        const tarefaId = this.dataset.tarefaId;
        const textarea = document.getElementById(`comentario-texto-${tarefaId}`);
        const texto = textarea?.value?.trim();

        if (!texto) {
          showToast('Digite um comentário', 'warning');
          return;
        }

        const tipoTag = document.querySelector(`.comentario-tipo-tag.active[data-tarefa-id="${tarefaId}"]`);
        const visibilidade = tipoTag?.dataset?.tipo || 'interno';
        const imagemInput = document.querySelector(`.comentario-imagem-input[data-tarefa-id="${tarefaId}"]`);

        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Salvando...';

        try {
          const formData = new FormData();
          formData.append('comentario', texto);
          formData.append('visibilidade', visibilidade);
          if (imagemInput && imagemInput.files[0]) {
            formData.append('imagem', imagemInput.files[0]);
          }

          const response = await fetch(`/api/adicionar_comentario_h/tarefa/${tarefaId}`, {
            method: 'POST',
            headers: {
              'Accept': 'application/json',
              'X-CSRFToken': CONFIG.csrfToken
            },
            body: formData
          });

          if (!response.ok) {
            const errorText = await response.text();
            showToast('Erro ao salvar comentário: ' + (errorText || `Status ${response.status}`), 'error');
            return;
          }

          let data;
          const contentType = response.headers.get('content-type') || '';
          if (contentType.includes('application/json')) {
            data = await response.json();
          } else {
            try {
              const text = await response.text();
              data = JSON.parse(text);
            } catch (err) {
              data = { ok: true, success: true };
            }
          }

          if (data.ok || data.success) {
            textarea.value = '';
            if (imagemInput) imagemInput.value = '';
            await carregarComentarios(tarefaId);
            const btnComentarios = document.querySelector(`.btn-toggle-comentarios[data-tarefa-id="${tarefaId}"]`);
            if (btnComentarios) btnComentarios.classList.add('has-comments');
            showToast('Comentário salvo com sucesso!', 'success');
          } else {
            showToast('Erro ao salvar comentário: ' + (data.error || 'Erro desconhecido'), 'error');
          }
        } catch (error) {
          console.error('Erro:', error);
          showToast('Erro ao comunicar com o servidor: ' + error.message, 'error');
        } finally {
          this.disabled = false;
          this.innerHTML = '<i class="bi bi-send me-1"></i>Salvar';
        }
      });
    });

    document.querySelectorAll('.btn-enviar-email').forEach(btn => {
      btn.addEventListener('click', async function () {
        const tarefaId = this.dataset.tarefaId;
        const textarea = document.getElementById(`comentario-texto-${tarefaId}`);
        const texto = textarea?.value?.trim();

        if (!texto) {
          showToast('Digite uma mensagem para enviar', 'warning');
          return;
        }

        if (!CONFIG.emailResponsavel) {
          showToast('Email do responsável não cadastrado. Acesse "Editar Detalhes" para adicionar.', 'warning');
          return;
        }

        const confirmed = await showConfirm({
          title: 'Enviar Email',
          message: `Deseja enviar este comentário por email para ${CONFIG.emailResponsavel}?`,
          confirmText: 'Enviar',
          cancelText: 'Cancelar',
          type: 'primary',
          icon: 'bi-envelope-fill'
        });

        if (!confirmed) return;

        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando...';

        try {
          const formData = new FormData();
          formData.append('comentario', texto);
          formData.append('visibilidade', 'externo');

          const saveResponse = await fetch(`/api/adicionar_comentario_h/tarefa/${tarefaId}`, {
            method: 'POST',
            headers: {
              'Accept': 'application/json',
              'X-CSRFToken': CONFIG.csrfToken
            },
            body: formData
          });

          if (!saveResponse.ok) {
            const errorText = await saveResponse.text();
            showToast('Erro ao salvar comentário: ' + (errorText || `Status ${saveResponse.status}`), 'error');
            return;
          }

          let data;
          const contentType = saveResponse.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            data = await saveResponse.json();
          } else {
            data = { ok: true, success: true };
          }

          if (!data.ok && !data.success) {
            showToast('Erro ao salvar comentário: ' + (data.error || 'Erro desconhecido'), 'error');
            return;
          }

          textarea.value = '';
          await carregarComentarios(tarefaId);

          const emailResponse = await fetch(`/api/enviar_comentario_email/${tarefaId}`, {
            method: 'POST',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json',
              'X-CSRFToken': CONFIG.csrfToken
            },
            body: JSON.stringify({ comentario: texto })
          });

          if (!emailResponse.ok) {
            const errorText = await emailResponse.text();
            showToast('Comentário salvo, mas falha ao enviar email: ' + (errorText || `Status ${emailResponse.status}`), 'warning');
            return;
          }

          const emailData = await emailResponse.json();
          if (!emailData.ok && !emailData.success) {
            showToast('Comentário salvo, mas falha ao enviar email: ' + (emailData.error || 'Erro desconhecido'), 'warning');
            return;
          }

          showToast('Comentário salvo e email enviado com sucesso!', 'success');
        } catch (error) {
          console.error('Erro:', error);
          showToast('Erro ao comunicar com o servidor: ' + error.message, 'error');
        } finally {
          this.disabled = false;
          this.innerHTML = '<i class="bi bi-envelope me-1"></i>Enviar Email';
        }
      });
    });

    async function carregarComentarios(itemId) {
      const historicoContainer = document.getElementById(`historico-tarefa-${itemId}`);
      if (!historicoContainer) return;

      window.showSkeleton?.(historicoContainer, 2);

      try {
        const response = await fetch(`/api/listar_comentarios_h/tarefa/${itemId}`, {
          headers: { 'Accept': 'application/json' }
        });

        if (!response.ok) {
          historicoContainer.innerHTML = `
            <div class="alert alert-danger small py-2 mb-0">
              <i class="bi bi-exclamation-triangle me-1"></i>Erro ao carregar comentários: ${response.status}
            </div>`;
          return;
        }

        let data;
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          data = await response.json();
        } else {
          const text = await response.text();
          try {
            data = JSON.parse(text);
          } catch (err) {
            historicoContainer.innerHTML = `
              <div class="alert alert-danger small py-2 mb-0">
                <i class="bi bi-exclamation-triangle me-1"></i>Erro ao carregar comentários: resposta inválida
              </div>`;
            return;
          }
        }

        if (data.ok || data.success) {
          const comentarios = data.comentarios || [];
          if (comentarios.length === 0) {
            historicoContainer.innerHTML = `
              <div class="text-center text-muted small py-2">
                <i class="bi bi-chat-left-text"></i> Nenhum comentário ainda
              </div>`;
            return;
          }

          historicoContainer.innerHTML = comentarios.map(c => {
            const canEdit = (CONFIG.userEmail && c.usuario_cs === CONFIG.userEmail) || CONFIG.isManager;
            return `
              <div class="comentario-item ${c.visibilidade || 'interno'}" data-comentario-id="${c.id}">
                <div class="comentario-meta">
                  <span class="comentario-autor">
                    <i class="bi bi-person-circle me-1"></i>${c.usuario_nome || c.usuario_cs || 'Usuário'}
                    <span class="badge ${c.visibilidade === 'externo' ? 'bg-warning' : 'bg-info'} ms-2" style="font-size: 0.65rem;">
                      ${c.visibilidade === 'externo' ? 'Externo' : 'Interno'}
                    </span>
                  </span>
                  <div class="d-flex align-items-center gap-2">
                    <span class="comentario-data">${formatarData(c.data_criacao, false)}</span>
                    ${canEdit ? `
                      <button type="button" class="btn btn-sm btn-outline-danger btn-excluir-comentario" data-comentario-id="${c.id}" title="Excluir">
                        <i class="bi bi-trash"></i>
                      </button>` : ''}
                  </div>
                </div>
                <div class="comentario-texto">${escapeHtml(c.texto)}</div>
                ${c.imagem_url ? `<img src="${c.imagem_url}" class="comentario-imagem" alt="Imagem anexada">` : ''}
              </div>`;
          }).join('');
        } else {
          historicoContainer.innerHTML = `
            <div class="alert alert-danger small py-2 mb-0">
              <i class="bi bi-exclamation-triangle me-1"></i>${data.error || 'Erro ao carregar comentários'}
            </div>`;
        }
      } catch (error) {
        console.error('Erro ao processar resposta:', error);
        historicoContainer.innerHTML = `
          <div class="alert alert-danger small py-2 mb-0">
            <i class="bi bi-exclamation-triangle me-1"></i>Erro ao processar resposta do servidor
          </div>`;
      }
    }

    document.querySelectorAll('.tarefa-item').forEach(item => {
      const checkbox = item.querySelector('.tarefa-checkbox');
      if (!checkbox) return;

      let status = item.getAttribute('data-tarefa-status') || '';
      status = status.toLowerCase();
      const isConcluida = (status === 'concluida' || status === 'concluido');

      checkbox.checked = isConcluida;
      item.setAttribute('data-tarefa-status', isConcluida ? 'concluida' : 'pendente');
      item.classList.toggle('concluida', isConcluida);

      const statusBadge = item.querySelector('.tarefa-status');
      if (statusBadge) {
        statusBadge.textContent = isConcluida ? 'Concluído' : 'Pendente';
        statusBadge.classList.remove('concluido', 'pendente');
        statusBadge.classList.add(isConcluida ? 'concluido' : 'pendente');
      }
    });

    computeProgress();
    document.body.addEventListener('progress_update', computeProgress);

    function formatarData(dataStr, includeTime = false) {
      try {
        const data = new Date(dataStr);
        if (includeTime) {
          return data.toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          });
        }
        return data.toLocaleDateString('pt-BR');
      } catch {
        return dataStr;
      }
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    // Inicializar campos de data do modal Detalhes da Empresa
    const modalDetalhesEmpresa = document.getElementById('modalDetalhesEmpresa');
    if (modalDetalhesEmpresa && window.flatpickr) {
      modalDetalhesEmpresa.addEventListener('shown.bs.modal', function() {
        const baseConfig = {
          dateFormat: 'Y-m-d',
          altInput: true,
          altFormat: 'd/m/Y',
          allowInput: false,
          locale: {
            firstDayOfWeek: 1,
            weekdays: {
              shorthand: ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'],
              longhand: ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']
            },
            months: {
              shorthand: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
              longhand: ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
            }
          }
        };

        // Início Efetivo
        const inicioEfetivoInput = document.getElementById('modal-inicio_efetivo');
        const btnCalInicioEfetivo = document.getElementById('btn-cal-inicio_efetivo');
        if (inicioEfetivoInput) {
          // Se já existe flatpickr, destruir para reinicializar
          if (inicioEfetivoInput._flatpickr) {
            inicioEfetivoInput._flatpickr.destroy();
          }
          const valorInicial = inicioEfetivoInput.value || '';
          const fp1 = window.flatpickr(inicioEfetivoInput, Object.assign({}, baseConfig, {
            defaultDate: valorInicial || null,
            onChange: function(selectedDates, dateStr, instance) {
              if (selectedDates.length > 0) {
                inicioEfetivoInput.value = dateStr; // Formato Y-m-d para o backend
              } else {
                inicioEfetivoInput.value = '';
              }
            }
          }));
          if (valorInicial) {
            fp1.setDate(valorInicial, false);
          }
          if (btnCalInicioEfetivo) {
            btnCalInicioEfetivo.addEventListener('click', function(e) {
              e.preventDefault();
              fp1.open();
            });
          }
        }

        // Início Produção
        const inicioProducaoInput = document.getElementById('modal-data_inicio_producao');
        const btnCalInicioProducao = document.getElementById('btn-cal-data_inicio_producao');
        if (inicioProducaoInput) {
          // Se já existe flatpickr, destruir para reinicializar
          if (inicioProducaoInput._flatpickr) {
            inicioProducaoInput._flatpickr.destroy();
          }
          const valorInicial = inicioProducaoInput.value || '';
          const fp2 = window.flatpickr(inicioProducaoInput, Object.assign({}, baseConfig, {
            defaultDate: valorInicial || null,
            onChange: function(selectedDates, dateStr, instance) {
              if (selectedDates.length > 0) {
                inicioProducaoInput.value = dateStr; // Formato Y-m-d para o backend
              } else {
                inicioProducaoInput.value = '';
              }
            }
          }));
          if (valorInicial) {
            fp2.setDate(valorInicial, false);
          }
          if (btnCalInicioProducao) {
            btnCalInicioProducao.addEventListener('click', function(e) {
              e.preventDefault();
              fp2.open();
            });
          }
        }

        // Fim da Implantação
        const finalImplantacaoInput = document.getElementById('modal-data_final_implantacao');
        const btnCalFinalImplantacao = document.getElementById('btn-cal-data_final_implantacao');
        if (finalImplantacaoInput) {
          // Se já existe flatpickr, destruir para reinicializar
          if (finalImplantacaoInput._flatpickr) {
            finalImplantacaoInput._flatpickr.destroy();
          }
          const valorInicial = finalImplantacaoInput.value || '';
          const fp3 = window.flatpickr(finalImplantacaoInput, Object.assign({}, baseConfig, {
            defaultDate: valorInicial || null,
            onChange: function(selectedDates, dateStr, instance) {
              if (selectedDates.length > 0) {
                finalImplantacaoInput.value = dateStr; // Formato Y-m-d para o backend
              } else {
                finalImplantacaoInput.value = '';
              }
            }
          }));
          if (valorInicial) {
            fp3.setDate(valorInicial, false);
          }
          if (btnCalFinalImplantacao) {
            btnCalFinalImplantacao.addEventListener('click', function(e) {
              e.preventDefault();
              fp3.open();
            });
          }
        }
      });

      // Instâncias do Tom Select
      const tomSelectInstances = {};

      // Função para inicializar Tom Select em campos multi-select
      function initTomSelectMulti(selectId, valueStr) {
        const select = document.getElementById(selectId);
        if (!select || !select.classList.contains('tom-select-multi')) return;

        // Destruir instância existente se houver
        if (tomSelectInstances[selectId]) {
          tomSelectInstances[selectId].destroy();
          delete tomSelectInstances[selectId];
        }

        // Inicializar Tom Select para multi-select
        const tomSelect = new TomSelect(select, {
          plugins: ['remove_button'],
          maxItems: null,
          placeholder: 'Selecione...',
          allowEmptyOption: true,
          create: false
        });

        // Definir valores se houver
        if (valueStr && valueStr.trim() !== '') {
          const values = valueStr.split(',').map(v => v.trim()).filter(v => v && v !== '');
          if (values.length > 0) {
            tomSelect.setValue(values);
          }
        }

        tomSelectInstances[selectId] = tomSelect;
      }

      // Função para inicializar Tom Select em campos single-select
      function initTomSelectSingle(selectId, valueStr) {
        const select = document.getElementById(selectId);
        if (!select || !select.classList.contains('tom-select-single')) return;

        // Destruir instância existente se houver
        if (tomSelectInstances[selectId]) {
          tomSelectInstances[selectId].destroy();
          delete tomSelectInstances[selectId];
        }

        // Inicializar Tom Select para single-select
        const tomSelect = new TomSelect(select, {
          placeholder: 'Selecione...',
          allowEmptyOption: true,
          create: false
        });

        // Definir valor se houver
        if (valueStr && valueStr.trim() !== '') {
          tomSelect.setValue(valueStr.trim());
        }

        tomSelectInstances[selectId] = tomSelect;
      }

      // Popular campos quando o modal abrir
      modalDetalhesEmpresa.addEventListener('shown.bs.modal', function() {
        // Obter valores dos data-attributes do botão ou do template
        const btn = document.querySelector('[data-bs-target="#modalDetalhesEmpresa"]');
        let cargo = '', nivelReceita = '', seguimento = '', tiposPlanos = '', sistemaAnterior = '', recorrenciaUsa = '';
        let catraca = '', facial = '', modeloCatraca = '', modeloFacial = '';

        if (btn) {
          cargo = btn.dataset.cargo || '';
          nivelReceita = btn.dataset.nivelReceita || '';
          seguimento = btn.dataset.seguimento || '';
          tiposPlanos = btn.dataset.tiposPlanos || '';
          sistemaAnterior = btn.dataset.sistemaAnterior || '';
          recorrenciaUsa = btn.dataset.recorrenciaUsa || '';
          catraca = btn.dataset.catraca || '';
          facial = btn.dataset.facial || '';
          modeloCatraca = btn.dataset.modeloCatraca || '';
          modeloFacial = btn.dataset.modeloFacial || '';
          const wellhub = btn.dataset.wellhub || '';
          const totalpass = btn.dataset.totalpass || '';
          
          // Popular campos WellHub e TotalPass
          const wellhubSelect = document.getElementById('modal-wellhub');
          const totalpassSelect = document.getElementById('modal-totalpass');
          if (wellhubSelect && wellhub) wellhubSelect.value = wellhub;
          if (totalpassSelect && totalpass) totalpassSelect.value = totalpass;
        }

        // Tentar pegar dos data-attributes dos selects também
        const cargoSelect = document.getElementById('modal-cargo_responsavel');
        const nivelReceitaSelect = document.getElementById('modal-nivel_receita');
        const seguimentoSelect = document.getElementById('modal-seguimento');
        const tiposPlanosSelect = document.getElementById('modal-tipos_planos');
        const sistemaAnteriorSelect = document.getElementById('modal-sistema_anterior');
        const recorrenciaUsaSelect = document.getElementById('modal-recorrencia_usa');

        if (cargoSelect && !cargo) cargo = cargoSelect.dataset.value || '';
        if (nivelReceitaSelect && !nivelReceita) nivelReceita = nivelReceitaSelect.dataset.value || '';
        if (seguimentoSelect && !seguimento) seguimento = seguimentoSelect.dataset.value || '';
        if (tiposPlanosSelect && !tiposPlanos) tiposPlanos = tiposPlanosSelect.dataset.value || '';
        if (sistemaAnteriorSelect && !sistemaAnterior) sistemaAnterior = sistemaAnteriorSelect.dataset.value || '';
        if (recorrenciaUsaSelect && !recorrenciaUsa) recorrenciaUsa = recorrenciaUsaSelect.dataset.value || '';

        // Inicializar Tom Select para campos multi-select
        initTomSelectMulti('modal-seguimento', seguimento);
        initTomSelectMulti('modal-tipos_planos', tiposPlanos);
        
        // Inicializar Tom Select para campos single-select
        initTomSelectSingle('modal-cargo_responsavel', cargo);
        initTomSelectSingle('modal-nivel_receita', nivelReceita);
        initTomSelectSingle('modal-sistema_anterior', sistemaAnterior);
        initTomSelectSingle('modal-recorrencia_usa', recorrenciaUsa);

        // Campos condicionais - Catraca e Facial
        const catracaSelect = document.getElementById('modal-catraca');
        const facialSelect = document.getElementById('modal-facial');
        const rowCatracaModelo = document.getElementById('row-catraca-modelo');
        const rowFacialModelo = document.getElementById('row-facial-modelo');
        const modeloCatracaInput = document.getElementById('modal-modelo_catraca');
        const modeloFacialInput = document.getElementById('modal-modelo_facial');

        // Função para atualizar visibilidade dos campos condicionais
        function atualizarCamposCondicionais() {
          if (catracaSelect && rowCatracaModelo) {
            const isCatracaSim = catracaSelect.value === 'Sim';
            rowCatracaModelo.style.display = isCatracaSim ? 'block' : 'none';
            if (!isCatracaSim && modeloCatracaInput) {
              modeloCatracaInput.value = '';
            }
          }
          
          if (facialSelect && rowFacialModelo) {
            const isFacialSim = facialSelect.value === 'Sim';
            rowFacialModelo.style.display = isFacialSim ? 'block' : 'none';
            if (!isFacialSim && modeloFacialInput) {
              modeloFacialInput.value = '';
            }
          }
        }

        if (catracaSelect) {
          if (catraca) catracaSelect.value = catraca;
          catracaSelect.addEventListener('change', atualizarCamposCondicionais);
          if (modeloCatracaInput && catraca === 'Sim' && modeloCatraca) {
            modeloCatracaInput.value = modeloCatraca;
          }
        }

        if (facialSelect) {
          if (facial) facialSelect.value = facial;
          facialSelect.addEventListener('change', atualizarCamposCondicionais);
          if (modeloFacialInput && facial === 'Sim' && modeloFacial) {
            modeloFacialInput.value = modeloFacial;
          }
        }

        // Atualizar visibilidade inicial
        atualizarCamposCondicionais();
      });

      // Limpar instâncias quando o modal fechar
      modalDetalhesEmpresa.addEventListener('hidden.bs.modal', function() {
        Object.keys(tomSelectInstances).forEach(key => {
          if (tomSelectInstances[key]) {
            try {
              tomSelectInstances[key].destroy();
            } catch (e) {
              console.warn('Erro ao destruir Tom Select:', e);
            }
            delete tomSelectInstances[key];
          }
        });
      });

      // Aplicar formatação de telefone quando o modal abrir
      modalDetalhesEmpresa.addEventListener('shown.bs.modal', function() {
        const telefoneInput = document.getElementById('modal-telefone_responsavel');
        if (telefoneInput && window.formatarTelefone) {
          // Aplicar formatação no valor existente
          formatarTelefone(telefoneInput);
        }
      });

      // Campos condicionais: Catraca e Facial (event listeners)
      const catracaSelect = document.getElementById('modal-catraca');
      const facialSelect = document.getElementById('modal-facial');
      const rowCatracaModelo = document.getElementById('row-catraca-modelo');
      const rowFacialModelo = document.getElementById('row-facial-modelo');

      if (catracaSelect) {
        catracaSelect.addEventListener('change', function() {
          if (rowCatracaModelo) {
            rowCatracaModelo.style.display = (this.value === 'Sim') ? 'block' : 'none';
            if (this.value !== 'Sim') {
              const modeloInput = document.getElementById('modal-modelo_catraca');
              if (modeloInput) modeloInput.value = '';
            }
          }
        });
      }

      if (facialSelect) {
        facialSelect.addEventListener('change', function() {
          if (rowFacialModelo) {
            rowFacialModelo.style.display = (this.value === 'Sim') ? 'block' : 'none';
            if (this.value !== 'Sim') {
              const modeloInput = document.getElementById('modal-modelo_facial');
              if (modeloInput) modeloInput.value = '';
            }
          }
        });
      }
    }
  });
})();

