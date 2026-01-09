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

    const baseConfig = {
      mode: 'single',
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

    // Event listeners for Phone Input (moved from inline HTML)
    const telefoneInput = document.getElementById('modal-telefone_responsavel');
    if (telefoneInput) {
      telefoneInput.addEventListener('input', function () {
        if (window.formatarTelefone) window.formatarTelefone(this);
      });
      telefoneInput.addEventListener('blur', function () {
        if (window.validarTelefoneCompleto) window.validarTelefoneCompleto(this);
      });
    }

    if (!CONFIG.implantacaoId) {
      return;
    }

    // =========================================================================
    // Global Comments Logic (New "Comentários" Tab)
    // =========================================================================
    let globalCommentsState = {
      page: 1,
      perPage: 20,
      isLoading: false,
      hasMore: true
    };

    const commentsTabBtn = document.getElementById('comments-tab');
    if (commentsTabBtn) {
      commentsTabBtn.addEventListener('shown.bs.tab', function (e) {
        // Sempre recarrega os comentários quando a aba é exibida
        resetGlobalComments();
        carregarComentariosGerais();
      });
    }

    const btnLoadMoreComments = document.getElementById('btn-load-more-comments');
    if (btnLoadMoreComments) {
      btnLoadMoreComments.addEventListener('click', function () {
        if (!globalCommentsState.isLoading && globalCommentsState.hasMore) {
          globalCommentsState.page++;
          carregarComentariosGerais(true); // true = append
        }
      });
    }

    function resetGlobalComments() {
      globalCommentsState = {
        page: 1,
        perPage: 20,
        isLoading: false,
        hasMore: true
      };
      const container = document.getElementById('comments-list-container');
      if (container) {
        // Keep loading/empty divs, remove comments
        const items = container.querySelectorAll('.comentario-item');
        items.forEach(el => el.remove());
      }
      document.getElementById('comments-loading')?.classList.remove('d-none');
      document.getElementById('comments-empty')?.classList.add('d-none');
      document.getElementById('comments-pagination')?.classList.add('d-none');
    }

    async function carregarComentariosGerais(append = false) {
      if (globalCommentsState.isLoading) return;

      globalCommentsState.isLoading = true;
      const loadingEl = document.getElementById('comments-loading');
      const emptyEl = document.getElementById('comments-empty');
      const paginationEl = document.getElementById('comments-pagination');
      const container = document.getElementById('comments-list-container');

      if (!append && loadingEl) loadingEl.classList.remove('d-none');

      try {
        const url = `/api/checklist/implantacao/${CONFIG.implantacaoId}/comments?page=${globalCommentsState.page}&per_page=${globalCommentsState.perPage}`;
        const response = await fetch(url, {
          headers: { 'Accept': 'application/json' }
        });

        if (!response.ok) {
          throw new Error(`Erro ${response.status}`);
        }

        const data = await response.json();

        if (!append && loadingEl) loadingEl.classList.add('d-none');

        if (data.ok) {
          const comentarios = data.comments || [];
          const meta = data.pagination;

          // Update state
          globalCommentsState.hasMore = meta.page < meta.total_pages;

          if (comentarios.length === 0 && !append) {
            if (emptyEl) emptyEl.classList.remove('d-none');
            if (paginationEl) paginationEl.classList.add('d-none');
          } else {
            if (emptyEl) emptyEl.classList.add('d-none');
            renderGlobalComments(comentarios, container, append);

            if (paginationEl) {
              if (globalCommentsState.hasMore) {
                paginationEl.classList.remove('d-none');
              } else {
                paginationEl.classList.add('d-none');
              }
            }
          }
        } else {
          showToast('Erro ao carregar comentários: ' + (data.error || 'Erro desconhecido'), 'error');
        }

      } catch (error) {
        console.error('Erro ao carregar comentários gerais:', error);
        showToast('Erro ao carregar comentários. Tente novamente.', 'error');
        if (!append && loadingEl) loadingEl.classList.add('d-none');
      } finally {
        globalCommentsState.isLoading = false;
      }
    }

    function renderGlobalComments(comentarios, container, append) {
      if (!container) return;
      const html = comentarios.map(c => {
        const canEdit = (CONFIG.userEmail && c.usuario_cs === CONFIG.userEmail) || CONFIG.isManager;
        // Task reference link (scroll to task)
        const taskLink = `<a href="#" class="text-decoration-none fw-bold ms-1 small text-primary task-scroll-link" data-task-id="${c.item_id}">
           <i class="bi bi-check2-square me-1"></i>${escapeHtml(c.item_title || 'Tarefa #' + c.item_id)}
        </a>`;

        return `
          <div class="comentario-item card mb-2 border-0 shadow-sm ${c.visibilidade || 'interno'}" data-comentario-id="${c.id}">
            <div class="card-body p-3">
              <div class="d-flex justify-content-between align-items-start mb-2">
                 <div class="d-flex flex-column">
                    <div class="d-flex align-items-center gap-2">
                        <span class="fw-bold text-dark">
                            <i class="bi bi-person-circle me-1 text-secondary"></i>${escapeHtml(c.usuario_nome || c.usuario_cs || 'Usuário')}
                        </span>
                        <span class="badge ${c.visibilidade === 'externo' ? 'bg-warning text-dark' : 'bg-primary text-white'} rounded-pill" style="font-size: 0.65rem;">
                            ${c.visibilidade === 'externo' ? 'Externo' : 'Interno'}
                        </span>
                        ${c.tag === 'Ação interna' ? '<span class="badge rounded-pill bg-primary text-white" style="font-size: 0.65rem;"><i class="bi bi-briefcase"></i> Ação interna</span>' : ''}
                        ${c.tag === 'Reunião' ? '<span class="badge rounded-pill bg-danger" style="font-size: 0.65rem;"><i class="bi bi-calendar-event"></i> Reunião</span>' : ''}
                        ${(c.tag === 'No Show' || c.noshow) ? '<span class="badge rounded-pill bg-warning text-dark" style="font-size: 0.65rem;"><i class="bi bi-calendar-x"></i> No show</span>' : ''}
                        ${(c.tag === 'Simples registro' || c.tag === 'simples registro' || (c.tag && c.tag.toLowerCase() === 'simples registro')) ? '<span class="badge rounded-pill bg-secondary" style="font-size: 0.65rem;"><i class="bi bi-pencil-square"></i> Simples registro</span>' : ''}
                    </div>
                    <div class="text-muted small mt-1">
                       em ${taskLink}
                    </div>
                 </div>
                 <div class="d-flex align-items-center gap-2">
                    <span class="text-muted small" title="${c.data_criacao}">${formatarData(c.data_criacao, true)}</span>
                    ${canEdit ? `
                        <button type="button" class="btn btn-link text-danger p-0 ms-2 btn-excluir-comentario" style="font-size: 0.9rem;" data-comentario-id="${c.id}" title="Excluir">
                            <i class="bi bi-trash"></i>
                        </button>` : ''}
                 </div>
              </div>
              <div class="comentario-texto text-break" style="white-space: pre-wrap; word-wrap: break-word;">${escapeHtml(c.texto)}</div>
              ${c.imagem_url ? `<div class="mt-2"><img src="${c.imagem_url}" class="img-fluid rounded comment-image-thumbnail" style="cursor: pointer;" style="max-height: 200px;" alt="Imagem anexada"></div>` : ''}
            </div>
          </div>`;
      }).join('');


      if (!append) {
        // Remove old comment items
        container.querySelectorAll('.comentario-item').forEach(e => e.remove());
      }

      container.insertAdjacentHTML('beforeend', html);

      // Add event listeners for task links
      container.querySelectorAll('.task-scroll-link').forEach(link => {
        link.addEventListener('click', function (e) {
          e.preventDefault();
          const taskId = parseInt(this.dataset.taskId, 10);
          if (window.checklistRenderer && Number.isFinite(taskId)) {
            try { window.checklistRenderer.ensureItemVisible(taskId); } catch (_) { }
          }
          const taskElement = document.getElementById(`checklist-item-${taskId}`) || document.querySelector(`.checklist-item[data-item-id="${taskId}"]`);
          if (taskElement) {
            const planoTabBtn = document.querySelector('button[data-bs-target="#plano-content"]');
            if (planoTabBtn) {
              const tabInstance = new bootstrap.Tab(planoTabBtn);
              tabInstance.show();
            }
            setTimeout(() => {
              taskElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
              taskElement.classList.add('highlight-task');
              setTimeout(() => taskElement.classList.remove('highlight-task'), 2000);
              const commentsSection = document.getElementById(`comments-${taskId}`);
              if (commentsSection && window.bootstrap && bootstrap.Collapse) {
                try {
                  const inst = bootstrap.Collapse.getInstance(commentsSection) || new bootstrap.Collapse(commentsSection, { toggle: false });
                  inst.show();
                  if (window.checklistRenderer && typeof window.checklistRenderer.loadComments === 'function') {
                    try { window.checklistRenderer.loadComments(taskId); } catch (_) { }
                  }
                } catch (_) { }
              }
            }, 200);
          } else {
            showToast('Tarefa não encontrada na visualização atual.', 'warning');
          }
        });
      });
    }

    function formatarData(dataStr, includeTime = false) { return window.formatDate(dataStr, includeTime); }

    function escapeHtml(text) { return window.escapeHtml(text); }

    function showToast(message, type = 'info', duration = 3000) {
      // Reuse existing toast logic if available globally or create simple one
      if (window.showToast) {
        window.showToast(message, type, duration);
      } else {
        alert(message);
      }
    }

    if (window.flatpickr) {
      document.querySelectorAll('.custom-datepicker').forEach(input => {
        const config = Object.assign({}, baseConfig);

        // Integrar IMask se a classe date-mask estiver presente
        if (input.classList.contains('date-mask') && window.IMask) {
          config.onReady = function (selectedDates, dateStr, instance) {
            if (instance.altInput) {
              // Aplica a máscara ao input visível (altInput)
              const mask = IMask(instance.altInput, {
                mask: Date,
                pattern: 'd/`m/`Y',
                lazy: false,
                format: function (date) {
                  var day = date.getDate();
                  var month = date.getMonth() + 1;
                  var year = date.getFullYear();
                  if (day < 10) day = "0" + day;
                  if (month < 10) month = "0" + month;
                  return [day, month, year].join('/');
                },
                parse: function (str) {
                  var yearMonthDay = str.split('/');
                  return new Date(yearMonthDay[2], yearMonthDay[1] - 1, yearMonthDay[0]);
                },
                blocks: {
                  d: { mask: IMask.MaskedRange, from: 1, to: 31, maxLength: 2 },
                  m: { mask: IMask.MaskedRange, from: 1, to: 12, maxLength: 2 },
                  Y: { mask: IMask.MaskedRange, from: 1900, to: 2100 }
                }
              });

              // Sincronizar alterações manuais na máscara com o Flatpickr
              mask.on('accept', function () {
                if (mask.masked.isComplete) {
                  instance.setDate(mask.value, true, 'd/m/Y');
                }
              });
            }
          };
        }

        const fp = window.flatpickr(input, config);
        if (input.hasAttribute('required')) {
          input.addEventListener('change', function () {
            if (this._flatpickr && this._flatpickr.selectedDates.length > 0) {
              const date = this._flatpickr.selectedDates[0];
              this._flatpickr.setDate(date, false);
            }
          });
        }
      });

      document.querySelectorAll('button[id^="btn_cal_"], button[id^="btn-cal-"], button[id*="cal-"], button[data-toggle]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          const target = btn.previousElementSibling; // Assumindo que o input está imediatamente antes do botão (estrutura input-group)
          // No DOM final do flatpickr (com altInput), a estrutura é:
          // input[hidden], input[text].form-control, button
          // Portanto, previousElementSibling do botão é o altInput.
          // Mas o target para inicializar flatpickr deve ser o input original.

          // Se o flatpickr já estiver inicializado no input original (que pode estar oculto antes do altInput)
          // O input original geralmente é acessível.
          // Vamos verificar se o elemento anterior tem a instância _flatpickr.

          // Caso altInput esteja presente, o DOM é:
          // <input type="hidden" ...> (original)
          // <input type="text" ...> (altInput)
          // <button ...>

          // O previousElementSibling do botão é o altInput.
          // O altInput não tem a propriedade _flatpickr, mas podemos acessá-lo?
          // Não diretamente.

          // Mas se já foi inicializado, podemos buscar a instância flatpickr associada.

          // Se target for o altInput, precisamos achar o original?
          // Na verdade, se já está inicializado, podemos apenas chamar open() na instância.

          // Vamos tentar encontrar o input original.
          let inputOriginal = target;

          // Se o target for o altInput (não tem a classe original custom-datepicker se o flatpickr moveu as classes, mas geralmente copia)
          // Mas o _flatpickr fica no elemento original.

          // Melhor abordagem: procurar o input com a classe custom-datepicker dentro do mesmo parent node.
          const parent = btn.parentElement;
          const originalInput = parent.querySelector('.custom-datepicker');

          if (originalInput && originalInput._flatpickr) {
            originalInput._flatpickr.open();
          } else if (target && target.classList.contains('custom-datepicker')) {
            // Fallback se não estiver inicializado (ex: dinamicamente)
            const fp = window.flatpickr(target, Object.assign({}, baseConfig));
            fp.open();
          }
        });
      });

      const modalParar = document.getElementById('modalParar');
      if (modalParar) {
        modalParar.addEventListener('shown.bs.modal', function () {
          const dataParadaInput = document.getElementById('data_parada');
          const btnCal = document.getElementById('btn_cal_data_parada');
          if (dataParadaInput && !dataParadaInput._flatpickr) {
            const fp = window.flatpickr(dataParadaInput, Object.assign({}, baseConfig, {
              altInput: true,
              appendTo: modalParar.querySelector('.modal-body'),
              static: true,
              onChange: function (selectedDates, dateStr, instance) {
                // Garantir que o valor seja preenchido no input original
                if (selectedDates.length > 0) {
                  dataParadaInput.value = dateStr;
                  // Remover mensagem de erro se existir
                  const errorMsg = document.getElementById('data_parada_error');
                  if (errorMsg) {
                    errorMsg.classList.add('d-none');
                  }
                }
              }
            }));
            if (btnCal) {
              btnCal.addEventListener('click', function (e) {
                e.preventDefault();
                fp.open();
              });
            }
          }
        });
      }

      const modalCancelar = document.getElementById('modalCancelar');
      if (modalCancelar) {
        modalCancelar.addEventListener('shown.bs.modal', function () {
          const dataCancelamentoInput = document.getElementById('data_cancelamento');
          const btnCal = document.getElementById('btn_cal_data_cancelamento');
          if (dataCancelamentoInput && !dataCancelamentoInput._flatpickr) {
            const fp = window.flatpickr(dataCancelamentoInput, Object.assign({}, baseConfig, {
              altInput: true,
              appendTo: modalCancelar.querySelector('.modal-body'),
              static: true,
              onChange: function (selectedDates, dateStr, instance) {
                // Garantir que o valor seja preenchido no input original
                if (selectedDates.length > 0) {
                  dataCancelamentoInput.value = dateStr;
                  // Remover mensagem de erro se existir
                  const errorMsg = document.getElementById('data_cancelamento_error');
                  if (errorMsg) {
                    errorMsg.classList.add('d-none');
                  }
                }
              }
            }));
            if (btnCal) {
              btnCal.addEventListener('click', function (e) {
                e.preventDefault();
                fp.open();
              });
            }
          }
        });
      }

      const modalFinalizar = document.getElementById('modalFinalizar');
      if (modalFinalizar) {
        modalFinalizar.addEventListener('shown.bs.modal', function () {
          const dataFinalizacaoInput = document.getElementById('data_finalizacao');
          const btnCal = document.getElementById('btn_cal_data_finalizacao');
          if (dataFinalizacaoInput && !dataFinalizacaoInput._flatpickr) {
            const parent = dataFinalizacaoInput.closest('.input-group') || modalFinalizar.querySelector('.modal-body');
            if (parent && parent.style.position !== 'relative') { parent.style.position = 'relative'; }
            const fp = window.flatpickr(dataFinalizacaoInput, Object.assign({}, baseConfig, {
              appendTo: modalFinalizar.querySelector('.modal-body'),
              positionElement: dataFinalizacaoInput,
              static: true,
              onChange: function (selectedDates, dateStr, instance) {
                if (selectedDates.length > 0) {
                  dataFinalizacaoInput.value = dateStr;
                }
              }
            }));
            if (btnCal) {
              btnCal.addEventListener('click', function (e) {
                e.preventDefault();
                fp.open();
              });
            }
          }
        });
      }

      const formParar = document.getElementById('formPararImplantacao');
      if (formParar) {
        formParar.addEventListener('submit', function (e) {
          const dataParadaInput = document.getElementById('data_parada');
          const errorMsg = document.getElementById('data_parada_error');

          if (dataParadaInput) {
            let dataValida = false;

            if (dataParadaInput._flatpickr && dataParadaInput._flatpickr.selectedDates.length > 0) {
              dataValida = true;
            } else if (dataParadaInput.value && dataParadaInput.value.trim() !== '') {
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
        formCancelar.addEventListener('submit', function (e) {
          const dataCancelamentoInput = document.getElementById('data_cancelamento');
          const errorMsg = document.getElementById('data_cancelamento_error');

          if (dataCancelamentoInput) {
            let dataValida = false;

            if (dataCancelamentoInput._flatpickr && dataCancelamentoInput._flatpickr.selectedDates.length > 0) {
              dataValida = true;
            } else if (dataCancelamentoInput.value && dataCancelamentoInput.value.trim() !== '') {
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

      const btnConfirmarDesfazerInicio = document.getElementById('btn-confirmar-desfazer-inicio');
      if (btnConfirmarDesfazerInicio) {
        btnConfirmarDesfazerInicio.addEventListener('click', function (e) {
          e.preventDefault();

          // Close modal
          const modal = document.getElementById('modalDesfazerInicio');
          if (modal && window.bootstrap) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) bsModal.hide();
          }

          fetch('/desfazer_inicio_implantacao', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': CONFIG.csrfToken
            },
            body: JSON.stringify({ implantacao_id: CONFIG.implantacaoId })
          })
            .then(response => response.json())
            .then(data => {
              if (data.error) {
                showToast(data.error, 'error');
              } else {
                showToast(data.message || 'Início desfeito com sucesso!', 'success');
                setTimeout(() => location.reload(), 1000);
              }
            })
            .catch(err => {
              console.error(err);
              showToast('Erro ao desfazer início.', 'error');
            });
        });
      }
    }



    // Navegação entre abas (Timeline -> Comentários / Plano)
    function activateTab(targetId) {
      if (!window.bootstrap) return;
      const triggerEl = document.querySelector(`[data-bs-target="${targetId}"]`);
      if (triggerEl) {
        const tab = new bootstrap.Tab(triggerEl);
        tab.show();
      }
    }

    document.addEventListener('click', function (e) {
      const btnComments = e.target.closest('.timeline-action-comments');
      if (btnComments) {
        const itemId = parseInt(btnComments.dataset.itemId);
        activateTab('#plano-content');
        if (window.checklistRenderer && Number.isFinite(itemId)) {
          try { window.checklistRenderer.ensureItemVisible(itemId); } catch (_) { }
        }
        setTimeout(() => {
          const taskElement = document.getElementById(`checklist-item-${itemId}`) || document.querySelector(`.checklist-item[data-item-id="${itemId}"]`);
          if (taskElement) {
            taskElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            const commentsSection = document.getElementById(`comments-${itemId}`);
            if (commentsSection && window.bootstrap && bootstrap.Collapse) {
              try {
                const inst = bootstrap.Collapse.getInstance(commentsSection) || new bootstrap.Collapse(commentsSection, { toggle: false });
                inst.show();
                if (window.checklistRenderer && typeof window.checklistRenderer.loadComments === 'function') {
                  try { window.checklistRenderer.loadComments(itemId); } catch (_) { }
                }
              } catch (_) { }
            }
          }
        }, 200);
        e.preventDefault();
        return;
      }
      const btnTask = e.target.closest('.timeline-action-task');
      if (btnTask) {
        const itemId = parseInt(btnTask.dataset.itemId);
        activateTab('#plano-content');
        if (window.checklistRenderer && itemId) {
          try { window.checklistRenderer.ensureItemVisible(itemId); } catch (_) { }
        }
        e.preventDefault();
      }
    });






    function atualizarVisibilidadeBotaoEmail(tarefaId) {
      const tagAtiva = document.querySelector(`.comentario-tipo-tag.active[data-tarefa-id="${tarefaId}"]`);
      if (!tagAtiva) {
        return;
      }

      const tipo = tagAtiva.getAttribute('data-tipo') || tagAtiva.dataset.tipo;
      const btnEmail = document.getElementById(`btn-email-${tarefaId}`);
      const alertaEmail = document.getElementById(`alerta-email-${tarefaId}`);

      const temEmail = CONFIG.emailResponsavel && CONFIG.emailResponsavel.trim() !== '';

      if (btnEmail) {
        const deveMostrar = tipo === 'externo';
        if (deveMostrar) {
          btnEmail.classList.remove('d-none');

          if (!temEmail) {
            btnEmail.disabled = true;
            btnEmail.classList.add('btn-secondary');
            btnEmail.classList.remove('btn-primary');
            btnEmail.title = 'Email do responsável não cadastrado. Acesse "Editar Detalhes" para adicionar.';
            btnEmail.setAttribute('data-bs-toggle', 'tooltip');
            btnEmail.setAttribute('data-bs-placement', 'top');

            if (alertaEmail) {
              alertaEmail.classList.remove('d-none');
            }
          } else {
            btnEmail.disabled = false;
            btnEmail.classList.remove('btn-secondary');
            btnEmail.classList.add('btn-primary');
            btnEmail.removeAttribute('title');
            btnEmail.removeAttribute('data-bs-toggle');
            btnEmail.removeAttribute('data-bs-placement');

            if (alertaEmail) {
              alertaEmail.classList.add('d-none');
            }
          }

          if (window.bootstrap && window.bootstrap.Tooltip) {
            const tooltipInstance = bootstrap.Tooltip.getInstance(btnEmail);
            if (tooltipInstance) {
              tooltipInstance.dispose();
            }
            if (!temEmail) {
              new bootstrap.Tooltip(btnEmail);
            }
          }
        } else {
          btnEmail.classList.add('d-none');
          if (alertaEmail) {
            alertaEmail.classList.add('d-none');
          }
        }
      }
    }

    function inicializarTagsComentario() {
      document.querySelectorAll('.comentario-tipo-tag').forEach(tag => {
        const tarefaId = tag.getAttribute('data-tarefa-id') || tag.dataset.tarefaId;
        if (tarefaId && tag.classList.contains('active')) {
          atualizarVisibilidadeBotaoEmail(tarefaId);
        }
      });
    }

    document.body.addEventListener('click', function (e) {
      const tag = e.target.closest('.comentario-tipo-tag');
      if (!tag) return;

      const tarefaId = tag.getAttribute('data-tarefa-id') || tag.dataset.tarefaId;
      if (!tarefaId) return;

      const tipo = tag.getAttribute('data-tipo') || tag.dataset.tipo;
      if (!tipo) return;

      const container = tag.closest('.d-flex');
      if (container) {
        container.querySelectorAll('.comentario-tipo-tag').forEach(t => t.classList.remove('active'));
      }
      tag.classList.add('active');

      setTimeout(() => {
        atualizarVisibilidadeBotaoEmail(tarefaId);
      }, 10);
    });

    inicializarTagsComentario();

    const observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        if (mutation.type === 'childList') {
          mutation.addedNodes.forEach(function (node) {
            if (node.nodeType === 1) {
              const tags = node.querySelectorAll ? node.querySelectorAll('.comentario-tipo-tag') : [];
              tags.forEach(tag => {
                const tarefaId = tag.getAttribute('data-tarefa-id') || tag.dataset.tarefaId;
                if (tarefaId && tag.classList.contains('active')) {
                  atualizarVisibilidadeBotaoEmail(tarefaId);
                }
              });
            }
          });
        }
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    document.querySelectorAll('.comentario-tipo-tag.active').forEach(tag => {
      const tarefaId = tag.dataset.tarefaId;
      if (tarefaId) {
        atualizarVisibilidadeBotaoEmail(tarefaId);
      }
    });

    async function reloadTimeline() {
      try {
        const tab = document.getElementById('timeline-content');
        if (!tab) return;
        const implId = tab.getAttribute('data-impl-id');
        if (!implId) return;
        const resp = await fetch(`/api/implantacao/${implId}/timeline?per_page=100`, {
          headers: { 'Accept': 'application/json', 'X-CSRFToken': (window.CONFIG && window.CONFIG.csrfToken) ? window.CONFIG.csrfToken : '' },
          credentials: 'same-origin'
        });
        const data = await resp.json();
        if (data && data.ok) {
          const serverLogs = data.logs || [];
          const merged = mergeWithBufferedEvents(serverLogs);
          renderTimelineList(merged);
        } else {
          const merged = mergeWithBufferedEvents([]);
          renderTimelineList(merged);
        }
      } catch (_) { }
    }

    function renderTimelineList(items) {
      const ul = document.getElementById('timeline-list') || document.querySelector('.timeline-list');
      if (!ul) return;
      ul.innerHTML = '';
      if (!items.length) {
        ul.innerHTML = '<li class="alert alert-light text-center small py-2">Nenhum evento registrado.</li>';
        return;
      }
      const html = items.map(log => {
        const t = log.tipo_evento || '';
        let icon = 'bi-info-circle-fill';
        if (t === 'novo_comentario') icon = 'bi-chat-left-text-fill';
        else if (t.includes('tarefa')) icon = 'bi-check-circle-fill';
        else if (t.includes('status')) icon = 'bi-flag-fill';
        const dt = (window.formatDate ? window.formatDate(log.data_criacao, true) : (log.data_criacao || ''));
        const detalhes = (log.detalhes || '').replace(/\n/g, '<br>');
        let actions = '';
        const m = /Item\s+(\d+)/.exec(log.detalhes || '');
        const itemId = m ? parseInt(m[1], 10) : null;
        if (t === 'novo_comentario' && itemId) actions += `<button class="btn btn-sm btn-outline-primary timeline-action-comments" data-item-id="${itemId}">Ver comentários</button>`;
        return `
          <li class="timeline-item">
            <div class="timeline-icon"><i class="bi ${icon}"></i></div>
            <div class="timeline-content shadow-sm">
              <div class="d-flex justify-content-between mb-2">
                <span class="fw-bold text-primary">${log.usuario_nome || ''}</span>
                <span class="small text-muted">${dt}</span>
              </div>
              <p class="mb-0 text-secondary">${detalhes}</p>
              <div class="mt-2 d-flex gap-2">${actions}</div>
            </div>
          </li>`;
      }).join('');
      ul.innerHTML = html;
    }

    function getImplId() {
      const tab = document.getElementById('timeline-content');
      return tab ? tab.getAttribute('data-impl-id') : null;
    }

    function readTimelineBuffer() {
      try {
        const implId = getImplId();
        if (!implId) return [];
        const raw = localStorage.getItem(`timelineBuffer:${implId}`);
        const arr = raw ? JSON.parse(raw) : [];
        return Array.isArray(arr) ? arr : [];
      } catch (_) { return []; }
    }

    function writeTimelineBuffer(items) {
      try {
        const implId = getImplId();
        if (!implId) return;
        const capped = (items || []).slice(-100);
        localStorage.setItem(`timelineBuffer:${implId}`, JSON.stringify(capped));
      } catch (_) { }
    }

    function mergeWithBufferedEvents(serverLogs) {
      const buf = readTimelineBuffer();
      const byKey = new Map();
      const push = (log) => {
        if (!log) return;
        const k = `${log.tipo_evento || ''}|${log.detalhes || ''}|${log.data_criacao || ''}`;
        if (!byKey.has(k)) byKey.set(k, log);
      };
      (serverLogs || []).forEach(push);
      buf.forEach(push);
      // Return newest first by data_criacao if possible
      const arr = Array.from(byKey.values());
      arr.sort((a, b) => {
        const da = new Date(a.data_criacao || 0).getTime();
        const db = new Date(b.data_criacao || 0).getTime();
        return db - da;
      });
      return arr;
    }

    window.reloadTimeline = reloadTimeline;
    window.appendTimelineEvent = function (type, detalhes) {
      const ul = document.getElementById('timeline-list') || document.querySelector('.timeline-list');
      if (!ul) return;
      const t = type || '';
      let icon = 'bi-info-circle-fill';
      if (t === 'novo_comentario') icon = 'bi-chat-left-text-fill';
      else if (t.indexOf('tarefa') >= 0) icon = 'bi-check-circle-fill';
      else if (t.indexOf('status') >= 0) icon = 'bi-flag-fill';
      const now = new Date().toISOString();
      const dt = window.formatDate ? window.formatDate(now, true) : now;
      const text = (detalhes || '').replace(/\n/g, '<br>');
      let actions = '';
      const m = /Item\s+(\d+)/.exec(detalhes || '');
      const itemId = m ? parseInt(m[1], 10) : null;
      if (t === 'novo_comentario' && itemId) actions += `<button class="btn btn-sm btn-outline-primary timeline-action-comments" data-item-id="${itemId}">Ver comentários</button>`;
      const usuario = (window.CONFIG && window.CONFIG.emailUsuarioLogado) ? window.CONFIG.emailUsuarioLogado : '';
      const li = document.createElement('li');
      li.className = 'timeline-item';
      li.innerHTML = `
        <div class="timeline-icon"><i class="bi ${icon}"></i></div>
        <div class="timeline-content shadow-sm">
          <div class="d-flex justify-content-between mb-2">
            <span class="fw-bold text-primary">${usuario}</span>
            <span class="small text-muted">${dt}</span>
          </div>
          <p class="mb-0 text-secondary">${text}</p>
          <div class="mt-2 d-flex gap-2">${actions}</div>
        </div>
      `;
      ul.prepend(li);

      // Persist optimistic event to buffer
      const buf = readTimelineBuffer();
      buf.push({ tipo_evento: t, detalhes: detalhes || '', usuario_nome: usuario, data_criacao: now });
      writeTimelineBuffer(buf);
    };

    try {
      const timelineTabBtn = document.getElementById('timeline-tab');
      if (timelineTabBtn) {
        timelineTabBtn.addEventListener('shown.bs.tab', function () { try { window.reloadTimeline(); } catch (_) { } });
      }
    } catch (_) { }

    try {
      document.addEventListener('DOMContentLoaded', function () {
        try {
          const planoTabBtn = document.getElementById('plano-tab');
          const timelineTabBtn = document.getElementById('timeline-tab');
          const commentsTabBtn = document.getElementById('comments-tab');
          const planoPane = document.getElementById('plano-content');
          const timelinePane = document.getElementById('timeline-content');
          const commentsPane = document.getElementById('comments-content');

          try {
            if (window.location && window.location.hash && (window.location.hash === '#timeline-content' || window.location.hash === '#comments-content')) {
              if (history && history.replaceState) {
                history.replaceState(null, document.title, window.location.pathname + window.location.search);
              } else {
                window.location.hash = '';
              }
            }
          } catch (_) { }

          // Reset panes
          [timelinePane, commentsPane].forEach(p => {
            if (!p) return;
            p.classList.remove('show');
            p.classList.remove('active');
          });
          if (planoPane) {
            planoPane.classList.add('show');
            planoPane.classList.add('active');
          }

          // Reset tabs
          [timelineTabBtn, commentsTabBtn].forEach(b => { if (b) b.classList.remove('active'); });
          if (planoTabBtn) planoTabBtn.classList.add('active');

          // Ensure bootstrap tab API reflects the state
          if (window.bootstrap && bootstrap.Tab && planoTabBtn) {
            const inst = bootstrap.Tab.getOrCreateInstance(planoTabBtn);
            inst.show();
          }

          // Defensive: keep only one pane active at any time
          const tabContent = document.querySelector('.tab-content');
          const enforceSingleActive = () => {
            const panes = document.querySelectorAll('.tab-content .tab-pane');
            let foundActive = false;
            panes.forEach(p => {
              const isActive = p.classList.contains('active');
              if (isActive && !foundActive) {
                foundActive = true;
                p.classList.add('show');
                p.style.display = 'block';
                p.classList.remove('d-none');
              } else {
                p.classList.remove('show');
                p.classList.remove('active');
                p.style.display = 'none';
                p.classList.add('d-none');
              }
            });
            if (!foundActive && planoPane) {
              planoPane.classList.add('active');
              planoPane.classList.add('show');
              planoPane.style.display = 'block';
              planoPane.classList.remove('d-none');
            }
          };
          enforceSingleActive();
          try {
            if (tabContent) {
              const mo = new MutationObserver(() => enforceSingleActive());
              mo.observe(tabContent, { attributes: true, subtree: true, attributeFilter: ['class'] });
            }
          } catch (_) { }

          // Tab click handlers to toggle d-none properly
          try {
            const allTabBtns = document.querySelectorAll('[data-bs-toggle="tab"]');
            allTabBtns.forEach(btn => {
              btn.addEventListener('shown.bs.tab', function (ev) {
                const target = ev.target.getAttribute('data-bs-target');
                const panes = document.querySelectorAll('.tab-content .tab-pane');
                panes.forEach(p => {
                  if ('#' + p.id === target) {
                    p.classList.remove('d-none');
                    p.classList.add('active');
                    p.classList.add('show');
                    p.style.display = 'block';
                  } else {
                    p.classList.remove('show');
                    p.classList.remove('active');
                    p.classList.add('d-none');
                    p.style.display = 'none';
                  }
                });
              });
            });
          } catch (_) { }
        } catch (_) { }
      });
    } catch (_) { }

    // DISABLED: Duplicate submit handler - already handled by modal_detalhes_empresa.js
    /*
    try {
      document.body.addEventListener('submit', async function (e) {
        const form = e.target;
        const modal = form.closest('#modalDetalhesEmpresa');
        if (!modal) return;
        e.preventDefault();
        e.stopPropagation();
        try {
          const fd = new FormData(form);
          fd.set('redirect_to', 'modal');
          const resp = await fetch('/atualizar_detalhes_empresa', {
            method: 'POST',
            headers: { 'Accept': 'application/json', 'X-CSRFToken': (window.CONFIG && window.CONFIG.csrfToken) ? window.CONFIG.csrfToken : '' },
            body: fd,
            credentials: 'same-origin'
          });
          const data = await resp.json();
          if (data && data.ok) {
            showToast('Detalhes atualizados', 'success');
            // permanece no modal; opcionalmente, reativar botão salvar
          } else {
            showToast('Erro ao salvar detalhes', 'error');
          }
        } catch (err) {
          showToast('Falha ao comunicar com o servidor', 'error');
        }
      });
    } catch (_) { }
    */

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
        const response = await fetch(`/api/checklist/comment/${comentarioId}`, {
          method: 'DELETE',
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
          }
        }

        const comentarioItem = targetBtn.closest('.comentario-item');
        const historico = comentarioItem ? comentarioItem.closest('[id^="historico-tarefa-"]') : null;
        const itemId = historico ? historico.id.replace('historico-tarefa-', '') : null;

        if (comentarioItem) comentarioItem.remove();
        if (itemId) await carregarComentarios(itemId);

        showToast('Comentário excluído com sucesso', 'success');
        try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) { }
      } catch (error) {
        showToast('Erro ao comunicar com o servidor: ' + error.message, 'error');
      }
    });







    const modalDetalhesEmpresa = document.getElementById('modalDetalhesEmpresa');
    if (modalDetalhesEmpresa && window.flatpickr) {
      modalDetalhesEmpresa.addEventListener('shown.bs.modal', function (event) {
        const configWithMask = Object.assign({}, baseConfig, {
          onReady: function (selectedDates, dateStr, instance) {
            if (instance.altInput && window.IMask) {
              IMask(instance.altInput, {
                mask: Date,
                pattern: 'd/`m/`Y',
                blocks: {
                  d: { mask: IMask.MaskedRange, from: 1, to: 31, maxLength: 2 },
                  m: { mask: IMask.MaskedRange, from: 1, to: 12, maxLength: 2 },
                  Y: { mask: IMask.MaskedRange, from: 1900, to: 2100, maxLength: 4 }
                },
                format: function (date) {
                  var day = date.getDate();
                  var month = date.getMonth() + 1;
                  var year = date.getFullYear();
                  if (day < 10) day = "0" + day;
                  if (month < 10) month = "0" + month;
                  return [day, month, year].join('/');
                },
                parse: function (str) {
                  var yearMonthDay = str.split('/');
                  return new Date(yearMonthDay[2], yearMonthDay[1] - 1, yearMonthDay[0]);
                },
                lazy: false,
                overwrite: true
              });
            }
          }
        });

        const inicioEfetivoInput = document.getElementById('modal-inicio_efetivo');
        const btnCalInicioEfetivo = document.getElementById('btn-cal-inicio_efetivo');
        if (inicioEfetivoInput) {
          if (inicioEfetivoInput._flatpickr) {
            inicioEfetivoInput._flatpickr.destroy();
          }
          const valorInicial = inicioEfetivoInput.value || '';
          const fp1 = window.flatpickr(inicioEfetivoInput, Object.assign({}, configWithMask, {
            defaultDate: valorInicial || null,
            onChange: function (selectedDates, dateStr, instance) {
              if (selectedDates.length > 0) {
                inicioEfetivoInput.value = dateStr;
              } else {
                inicioEfetivoInput.value = '';
              }
            }
          }));
          if (valorInicial) {
            fp1.setDate(valorInicial, false);
          }
          if (btnCalInicioEfetivo) {
            btnCalInicioEfetivo.addEventListener('click', function (e) {
              e.preventDefault();
              fp1.open();
            });
          }
        }

        const inicioProducaoInput = document.getElementById('modal-data_inicio_producao');
        const btnCalInicioProducao = document.getElementById('btn-cal-data_inicio_producao');
        if (inicioProducaoInput) {
          if (inicioProducaoInput._flatpickr) {
            inicioProducaoInput._flatpickr.destroy();
          }
          const valorInicial = inicioProducaoInput.value || '';
          const fp2 = window.flatpickr(inicioProducaoInput, Object.assign({}, configWithMask, {
            defaultDate: valorInicial || null,
            onChange: function (selectedDates, dateStr, instance) {
              if (selectedDates.length > 0) {
                inicioProducaoInput.value = dateStr;
              } else {
                inicioProducaoInput.value = '';
              }
            }
          }));
          if (valorInicial) {
            fp2.setDate(valorInicial, false);
          }
          if (btnCalInicioProducao) {
            btnCalInicioProducao.addEventListener('click', function (e) {
              e.preventDefault();
              fp2.open();
            });
          }
        }

        const finalImplantacaoInput = document.getElementById('modal-data_final_implantacao');
        const btnCalFinalImplantacao = document.getElementById('btn-cal-data_final_implantacao');
        if (finalImplantacaoInput) {
          if (finalImplantacaoInput._flatpickr) {
            finalImplantacaoInput._flatpickr.destroy();
          }
          const valorInicial = finalImplantacaoInput.value || '';
          const fp3 = window.flatpickr(finalImplantacaoInput, Object.assign({}, configWithMask, {
            defaultDate: valorInicial || null,
            onChange: function (selectedDates, dateStr, instance) {
              if (selectedDates.length > 0) {
                finalImplantacaoInput.value = dateStr;
              } else {
                finalImplantacaoInput.value = '';
              }
            }
          }));
          if (valorInicial) {
            fp3.setDate(valorInicial, false);
          }
          if (btnCalFinalImplantacao) {
            btnCalFinalImplantacao.addEventListener('click', function (e) {
              e.preventDefault();
              fp3.open();
            });
          }
        }

        // Duplicate dataCadastro initialization removed
      });

      const tomSelectInstances = {};
      function initTomSelectMulti(selectId, valueStr) {
        const select = document.getElementById(selectId);
        if (!select || !select.classList.contains('tom-select-multi')) return;

        // Check for existing instance in our tracking object
        if (tomSelectInstances[selectId]) {
          try {
            tomSelectInstances[selectId].destroy();
          } catch (e) {
            console.warn('Error destroying Tom Select instance:', e);
          }
          delete tomSelectInstances[selectId];
        }

        // Check for existing instance on the element itself
        if (select.tomselect) {
          try {
            select.tomselect.destroy();
          } catch (e) {
            console.warn('Error destroying Tom Select from element:', e);
          }
        }

        const tomSelect = new TomSelect(select, {
          plugins: ['remove_button'],
          maxItems: null,
          placeholder: 'Selecione...',
          allowEmptyOption: true,
          create: false
        });

        if (valueStr && valueStr.trim() !== '') {
          const values = valueStr.split(',').map(v => v.trim()).filter(v => v && v !== '');
          if (values.length > 0) {
            tomSelect.setValue(values);
          }
        }

        tomSelectInstances[selectId] = tomSelect;
      }

      function initTomSelectSingle(selectId, valueStr) {
        const select = document.getElementById(selectId);
        if (!select || !select.classList.contains('tom-select-single')) return;

        // Check for existing instance in our tracking object
        if (tomSelectInstances[selectId]) {
          try {
            tomSelectInstances[selectId].destroy();
          } catch (e) {
            console.warn('Error destroying Tom Select instance:', e);
          }
          delete tomSelectInstances[selectId];
        }

        // Check for existing instance on the element itself
        if (select.tomselect) {
          try {
            select.tomselect.destroy();
          } catch (e) {
            console.warn('Error destroying Tom Select from element:', e);
          }
        }

        const tomSelect = new TomSelect(select, {
          placeholder: 'Selecione...',
          allowEmptyOption: true,
          create: false
        });

        if (valueStr && valueStr.trim() !== '') {
          tomSelect.setValue(valueStr.trim());
        }

        tomSelectInstances[selectId] = tomSelect;
      }

      // Global Click Listener for Consultar OAMD Button (Delegation)
      document.addEventListener('click', async function (e) {
        const btnConsultar = e.target.closest('#btn-consultar-oamd');
        if (!btnConsultar) return;

        e.preventDefault();
        e.stopPropagation();


        const loaderConsultar = document.getElementById('btn-consultar-oamd-loader');
        const iconConsultar = document.getElementById('btn-consultar-oamd-icon');
        const inputIdFav = document.getElementById('modal-id_favorecido');

        // Get ID from input or button dataset
        const currentId = inputIdFav ? inputIdFav.value.trim() : (btnConsultar.dataset.idFavorecido || '');

        if (!currentId) {
          showToast('ID Favorecido não informado', 'warning');
          return;
        }

        btnConsultar.disabled = true;
        if (loaderConsultar) loaderConsultar.classList.remove('d-none');
        if (iconConsultar) iconConsultar.classList.add('d-none');

        try {
          const response = await fetch(`/api/consultar_empresa?id_favorecido=${currentId}`, {
            method: 'GET',
            headers: {
              'Accept': 'application/json',
              'X-CSRFToken': CONFIG.csrfToken
            }
          });

          if (!response.ok) {
            let errorMsg = `Erro na requisição: ${response.status}`;
            try {
              const errData = await response.json();
              if (errData.error) errorMsg = errData.error;
            } catch (e) { }
            throw new Error(errorMsg);
          }

          const data = await response.json();

          if (data.ok && data.mapped) {
            const m = data.mapped;

            const updateDate = (inputId, val) => {
              const input = document.getElementById(inputId);
              if (!input || !val) return;

              let dateVal = String(val).split('T')[0];

              if (input._flatpickr) {
                input._flatpickr.setDate(dateVal, true);

                const altInput = input._flatpickr.altInput;
                if (altInput) {
                  altInput.classList.add('bg-success', 'bg-opacity-10');
                  setTimeout(() => altInput.classList.remove('bg-success', 'bg-opacity-10'), 2000);
                  altInput.readOnly = true;
                  altInput.classList.add('bg-light');
                  altInput.style.cursor = 'not-allowed';
                }
              } else {
                input.value = dateVal;
              }

              input.readOnly = true;
              input.classList.add('bg-light');
              input.style.cursor = 'not-allowed';
              const parent = input.closest('.input-group');
              if (parent) {
                const btn = parent.querySelector('button');
                if (btn) btn.disabled = true;
              }
            };

            updateDate('modal-data_inicio_producao', m.data_inicio_producao);
            updateDate('modal-inicio_efetivo', m.data_inicio_efetivo);
            updateDate('modal-data_final_implantacao', m.data_final_implantacao);
            updateDate('modal-data_cadastro', m.data_cadastro);

            const updateText = (inputId, val) => {
              const input = document.getElementById(inputId);
              if (input && val) {
                input.value = val;
                input.classList.add('bg-success', 'bg-opacity-10');
                setTimeout(() => input.classList.remove('bg-success', 'bg-opacity-10'), 2000);

                // Make read-only
                input.readOnly = true;
                input.classList.add('bg-light');
                input.style.cursor = 'not-allowed';
              }
            };

            updateText('modal-status_implantacao', m.status_implantacao);
            updateText('modal-nivel_atendimento', m.nivel_atendimento);
            updateText('modal-chave_oamd', m.chave_oamd);
            (function () {
              const empresa = data.empresa || {};
              let infraVal = m.informacao_infra || '';
              if (!infraVal) {
                const nomezw = String(empresa.nomeempresazw || '').trim();
                const mName = nomezw.match(/zw[_-]?(\d+)/i);
                if (mName && mName[1]) infraVal = `ZW_${mName[1]}`;
              }
              if (!infraVal) {
                const empzw = empresa.empresazw;
                const empzwNum = typeof empzw === 'number' ? empzw : parseInt(String(empzw || '').trim(), 10);
                if (!Number.isNaN(empzwNum) && empzwNum > 1) infraVal = `ZW_${empzwNum}`;
              }
              updateText('modal-informacao_infra', infraVal);

              let linkVal = m.tela_apoio_link || '';
              if ((!linkVal || !String(linkVal).trim()) && infraVal) {
                const mDigits = String(infraVal).match(/(\d+)/);
                if (mDigits && mDigits[1]) linkVal = `http://zw${mDigits[1]}.pactosolucoes.com.br/app`;
              }
              if (!linkVal || !String(linkVal).trim()) {
                const entries = Object.entries(empresa);
                for (let i = 0; i < entries.length; i++) {
                  const v = String(entries[i][1] || '');
                  const mUrl = v.match(/https?:\/\/[^\s]*zw(\d+)[^\s]*/i);
                  if (mUrl && mUrl[1]) { linkVal = `http://zw${mUrl[1]}.pactosolucoes.com.br/app`; break; }
                }
              }
              updateText('modal-tela_apoio_link', linkVal);
            })();

            if (m.cnpj) {
              const cnpjInput = document.getElementById('modal-cnpj');
              if (cnpjInput) {
                cnpjInput.value = m.cnpj;
                cnpjInput.dispatchEvent(new Event('input'));
                cnpjInput.classList.add('bg-success', 'bg-opacity-10');
                setTimeout(() => cnpjInput.classList.remove('bg-success', 'bg-opacity-10'), 2000);

                cnpjInput.readOnly = true;
                cnpjInput.classList.add('bg-light');
                cnpjInput.style.cursor = 'not-allowed';
              }
            }

            if (m.nivel_receita) {
              const mrrInput = document.getElementById('modal-valor_atribuido');
              if (mrrInput) {
                mrrInput.value = m.nivel_receita;
                mrrInput.dispatchEvent(new Event('input'));
                mrrInput.classList.add('bg-success', 'bg-opacity-10');
                setTimeout(() => mrrInput.classList.remove('bg-success', 'bg-opacity-10'), 2000);

                mrrInput.readOnly = true;
                mrrInput.classList.add('bg-light');
                mrrInput.style.cursor = 'not-allowed';
              }
            }

            // Preencher campos de contato do responsável a partir dos dados brutos
            const empresa = data.empresa || {};

            // Responsável Cliente (Nome)
            const nomeResp = empresa.nomedono || empresa.responsavelnome || '';
            if (nomeResp) {
              updateText('modal-responsavel_cliente', nomeResp);
            }

            // E-mail Responsável
            const emailResp = empresa.email || empresa.responsavelemail || '';
            if (emailResp) {
              updateText('modal-email_responsavel', emailResp);
            }

            // Telefone Responsável - pode vir com nome concatenado (ex: "NOME: TELEFONE;")
            let telResp = empresa.telefone || empresa.responsaveltelefone || '';

            if (telResp && telResp.includes(':')) {
              const parts = telResp.split(':');
              if (parts.length >= 2) {
                // Parte 1 é o Nome
                const nomeDoTelefone = parts[0].trim();
                // Parte 2 é o Telefone
                const numeroDoTelefone = parts.slice(1).join(':').trim().replace(/;+$/, '').trim();

                // Preencher o campo de Nome com o valor extraído
                if (nomeDoTelefone) {
                  updateText('modal-responsavel_cliente', nomeDoTelefone);
                }

                // Usar apenas o número para o campo de telefone
                telResp = numeroDoTelefone;
              }
            }

            if (telResp) {
              updateText('modal-telefone_responsavel', telResp.replace(/;+$/, '').trim());
            }

            const now = new Date().getTime();
            const lastUpdateSpan = document.getElementById('oamd-last-update');
            const lastUpdateTimeSpan = document.getElementById('oamd-last-update-time');
            if (lastUpdateSpan && lastUpdateTimeSpan) {
              lastUpdateSpan.style.display = 'inline-block';
              lastUpdateTimeSpan.textContent = new Date(now).toLocaleTimeString();
            }

            const cacheKey = `oamd_cache_${currentId}`;
            localStorage.setItem(cacheKey, JSON.stringify({
              timestamp: now,
              data: m
            }));

            showToast('Dados atualizados com sucesso do OAMD', 'success');

          } else {
            showToast('Não foi possível obter dados do OAMD', 'warning');
          }

        } catch (error) {
          console.error('Erro ao consultar OAMD:', error);
          showToast('Erro ao consultar OAMD: ' + error.message, 'error');
        } finally {
          btnConsultar.disabled = false;
          if (loaderConsultar) loaderConsultar.classList.add('d-none');
          if (iconConsultar) iconConsultar.classList.remove('d-none');
        }
      });

      modalDetalhesEmpresa.addEventListener('shown.bs.modal', function (event) {
        const btn = event.relatedTarget || document.querySelector('[data-bs-target="#modalDetalhesEmpresa"]');
        let cargo = '', nivelReceita = '', seguimento = '', tiposPlanos = '', sistemaAnterior = '', recorrenciaUsa = '';
        let catraca = '', facial = '', modeloCatraca = '', modeloFacial = '';
        let idFavorecido = ''; // Declare at the top to avoid ReferenceError

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
          idFavorecido = btn.dataset.idFavorecido || '';

          if (!idFavorecido) {
            const inputIdFav = document.getElementById('modal-id_favorecido');
            if (inputIdFav && inputIdFav.value) {
              idFavorecido = inputIdFav.value;
            }
          }
          // Nota: valores de wellhub/totalpass são definidos por modal_detalhes_empresa.js
        }

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

        initTomSelectMulti('modal-seguimento', seguimento);
        initTomSelectMulti('modal-tipos_planos', tiposPlanos);

        // Initialize Modalidades, Horários, and Formas de Pagamento (same behavior as Segmento and Tipos de Planos)
        const modalidadesSelect = document.getElementById('modal-modalidades');
        const horariosSelect = document.getElementById('modal-horarios_func');
        const formasPagamentoSelect = document.getElementById('modal-formas_pagamento');

        const modalidades = btn ? (btn.dataset.modalidades || '') : (modalidadesSelect ? (modalidadesSelect.dataset.value || '') : '');
        const horarios = btn ? (btn.dataset.horariosFuncamento || '') : (horariosSelect ? (horariosSelect.dataset.value || '') : '');
        const formasPagamento = btn ? (btn.dataset.formasPagamento || '') : (formasPagamentoSelect ? (formasPagamentoSelect.dataset.value || '') : '');

        initTomSelectMulti('modal-modalidades', modalidades);
        initTomSelectMulti('modal-horarios_func', horarios);
        initTomSelectMulti('modal-formas_pagamento', formasPagamento);

        initTomSelectSingle('modal-cargo_responsavel', cargo);
        initTomSelectSingle('modal-nivel_receita', nivelReceita);
        initTomSelectSingle('modal-sistema_anterior', sistemaAnterior);
        initTomSelectSingle('modal-recorrencia_usa', recorrenciaUsa);

        const catracaSelect = document.getElementById('modal-catraca');
        const facialSelect = document.getElementById('modal-facial');
        const rowCatracaModelo = document.getElementById('row-catraca-modelo');
        const rowFacialModelo = document.getElementById('row-facial-modelo');
        const modeloCatracaInput = document.getElementById('modal-modelo_catraca');
        const modeloFacialInput = document.getElementById('modal-modelo_facial');

        function atualizarCamposCondicionais() {
          if (catracaSelect && rowCatracaModelo) {
            const isCatracaSim = catracaSelect.value === 'Sim';
            rowCatracaModelo.style.display = isCatracaSim ? 'block' : 'none';
            if (modeloCatracaInput) {
              modeloCatracaInput.required = isCatracaSim;
              if (!isCatracaSim) modeloCatracaInput.value = '';
            }
          }

          if (facialSelect && rowFacialModelo) {
            const isFacialSim = facialSelect.value === 'Sim';
            rowFacialModelo.style.display = isFacialSim ? 'block' : 'none';
            if (modeloFacialInput) {
              modeloFacialInput.required = isFacialSim;
              if (!isFacialSim) modeloFacialInput.value = '';
            }
          }
        }

        // Nota: valores de catraca/facial são definidos por modal_detalhes_empresa.js
        // Aqui mantemos apenas a lógica de UI condicional (mostrar/esconder modelo)
        if (catracaSelect) {
          catracaSelect.addEventListener('change', atualizarCamposCondicionais);
          if (modeloCatracaInput && catracaSelect.value === 'Sim' && modeloCatraca) {
            modeloCatracaInput.value = modeloCatraca;
          }
        }

        if (facialSelect) {
          facialSelect.addEventListener('change', atualizarCamposCondicionais);
          if (modeloFacialInput && facialSelect.value === 'Sim' && modeloFacial) {
            modeloFacialInput.value = modeloFacial;
          }
        }

        // Dispara a atualização após modal_detalhes_empresa.js ter definido os valores
        setTimeout(function () {
          atualizarCamposCondicionais();
        }, 150);

        // Antiga Lógica do botão Consultar OAMD (Removida em favor do listener global)
        // Mantendo apenas inicialização de cache visual
        const lastUpdateSpan = document.getElementById('oamd-last-update');
        const lastUpdateTimeSpan = document.getElementById('oamd-last-update-time');
        const inputIdFav = document.getElementById('modal-id_favorecido');

        // Verificar cache local se houver ID inicial
        if (idFavorecido) {
          const cacheKey = `oamd_cache_${idFavorecido}`;
          const cachedData = localStorage.getItem(cacheKey);

          if (cachedData) {
            try {
              const parsed = JSON.parse(cachedData);
              const now = new Date().getTime();
              if (now - parsed.timestamp < 300000) { // 5 min
                if (lastUpdateSpan && lastUpdateTimeSpan) {
                  lastUpdateSpan.style.display = 'inline-block';
                  lastUpdateTimeSpan.textContent = new Date(parsed.timestamp).toLocaleTimeString();
                }
              }
            } catch (e) {
              console.error('Erro ao ler cache OAMD', e);
            }
          }
        }


      });

      modalDetalhesEmpresa.addEventListener('hidden.bs.modal', function () {
        Object.keys(tomSelectInstances).forEach(key => {
          if (tomSelectInstances[key]) {
            try {
              tomSelectInstances[key].destroy();
            } catch (e) {
            }
            delete tomSelectInstances[key];
          }
        });
      });

      modalDetalhesEmpresa.addEventListener('shown.bs.modal', function () {
        const telefoneInput = document.getElementById('modal-telefone_responsavel');
        if (telefoneInput && window.formatarTelefone) {
          formatarTelefone(telefoneInput);
        }

        const alunosAtivosInput = document.getElementById('modal-alunos_ativos');
        if (alunosAtivosInput) {
          alunosAtivosInput.setAttribute('min', '0');
          alunosAtivosInput.setAttribute('step', '1');
          alunosAtivosInput.addEventListener('input', function () {
            const value = this.value;
            if (value.includes('.')) {
              this.value = Math.floor(parseFloat(value) || 0);
            }
            if (parseInt(this.value, 10) < 0) {
              this.value = 0;
            }
          });
          alunosAtivosInput.addEventListener('blur', function () {
            const numValue = parseInt(this.value, 10);
            if (isNaN(numValue) || numValue < 0 || this.value === '') {
              this.value = 0;
            } else {
              this.value = numValue;
            }
          });
        }

        const idFavorecidoInput = document.getElementById('modal-id_favorecido');
        if (idFavorecidoInput) {
          idFavorecidoInput.addEventListener('input', function () {
            this.value = this.value.replace(/[^0-9]/g, '');
          });
        }

        // Campo valor_atribuido (Nível de Receita) não usa máscara de moeda
        // pois o valor vindo do OAMD é texto descritivo (ex: "Platina (MRR do grupo entre R$1.000,00 a R$ 1.999,99)")


        const cnpjInput = document.getElementById('modal-cnpj');
        if (cnpjInput && window.IMask) {
          const cnpjMask = IMask(cnpjInput, {
            mask: '00.000.000/0000-00'
          });

          cnpjInput.addEventListener('blur', function () {
            const val = cnpjMask.unmaskedValue;
            if (val && !validateCNPJ(val)) {
              this.classList.add('is-invalid');
              let feedback = this.parentNode.querySelector('.invalid-feedback');
              if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.innerText = 'CNPJ inválido';
                this.parentNode.appendChild(feedback);
              }
              feedback.style.display = 'block';
            } else {
              this.classList.remove('is-invalid');
              let feedback = this.parentNode.querySelector('.invalid-feedback');
              if (feedback) feedback.style.display = 'none';
            }
          });
          cnpjInput.addEventListener('input', function () {
            this.classList.remove('is-invalid');
            let feedback = this.parentNode.querySelector('.invalid-feedback');
            if (feedback) feedback.style.display = 'none';
          });
        }

        // Máscara de dinheiro para valor_monetario
        const valorInput = document.getElementById('modal-valor_monetario');
        if (valorInput && window.IMask) {
          IMask(valorInput, {
            mask: 'R$ num',
            blocks: {
              num: {
                mask: Number,
                scale: 2,
                thousandsSeparator: '.',
                radix: ',',
                mapToRadix: ['.'],
                min: 0,
                max: 999999999.99,  // Increased limit to ~1 billion
                normalizeZeros: false,  // Allow typing 0
                padFractionalZeros: false  // Don't force decimal places
              }
            }
          });
        }

        const telaApoioInput = document.getElementById('modal-tela_apoio_link');
        if (telaApoioInput) {
          telaApoioInput.addEventListener('blur', function () {
            const val = this.value;
            if (val && !isValidURL(val)) {
              this.classList.add('is-invalid');
              let feedback = this.parentNode.querySelector('.invalid-feedback');
              if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.innerText = 'URL inválida (ex: https://exemplo.com)';
                this.parentNode.appendChild(feedback);
              }
              feedback.style.display = 'block';
            } else {
              this.classList.remove('is-invalid');
              let feedback = this.parentNode.querySelector('.invalid-feedback');
              if (feedback) feedback.style.display = 'none';
            }
          });
          telaApoioInput.addEventListener('input', function () {
            this.classList.remove('is-invalid');
            let feedback = this.parentNode.querySelector('.invalid-feedback');
            if (feedback) feedback.style.display = 'none';
          });
        }

        // Duplicate dataCadastro initialization removed
      });
    }
  });

  function isValidURL(string) {
    try {
      new URL(string);
      return true;
    } catch (_) {
      return false;
    }
  }

  function validateCNPJ(cnpj) {
    cnpj = cnpj.replace(/[^\d]+/g, '');
    if (cnpj == '') return false;
    if (cnpj.length != 14) return false;
    if (/^(\d)\1+$/.test(cnpj)) return false;

    let tamanho = cnpj.length - 2
    let numeros = cnpj.substring(0, tamanho);
    let digitos = cnpj.substring(tamanho);
    let soma = 0;
    let pos = tamanho - 7;
    for (let i = tamanho; i >= 1; i--) {
      soma += numeros.charAt(tamanho - i) * pos--;
      if (pos < 2) pos = 9;
    }
    let resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
    if (resultado != digitos.charAt(0)) return false;

    tamanho = tamanho + 1;
    numeros = cnpj.substring(0, tamanho);
    soma = 0;
    pos = tamanho - 7;
    for (let i = tamanho; i >= 1; i--) {
      soma += numeros.charAt(tamanho - i) * pos--;
      if (pos < 2) pos = 9;
    }
    resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
    if (resultado != digitos.charAt(1)) return false;

    return true;
  }
})();

