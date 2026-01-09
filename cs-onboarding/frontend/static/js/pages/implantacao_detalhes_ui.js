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
          shorthand: ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'SÃ¡b'],
          longhand: ['Domingo', 'Segunda-feira', 'TerÃ§a-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'SÃ¡bado']
        },
        months: {
          shorthand: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
          longhand: ['Janeiro', 'Fevereiro', 'MarÃ§o', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
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
    // Global Comments Logic (New "ComentÃ¡rios" Tab)
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
        // Sempre recarrega os comentÃ¡rios quando a aba Ã© exibida
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
          showToast('Erro ao carregar comentÃ¡rios: ' + (data.error || 'Erro desconhecido'), 'error');
        }

      } catch (error) {
        console.error('Erro ao carregar comentÃ¡rios gerais:', error);
        showToast('Erro ao carregar comentÃ¡rios. Tente novamente.', 'error');
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
                            <i class="bi bi-person-circle me-1 text-secondary"></i>${escapeHtml(c.usuario_nome || c.usuario_cs || 'UsuÃ¡rio')}
                        </span>
                        <span class="badge ${c.visibilidade === 'externo' ? 'bg-warning text-dark' : 'bg-primary text-white'} rounded-pill" style="font-size: 0.65rem;">
                            ${c.visibilidade === 'externo' ? 'Externo' : 'Interno'}
                        </span>
                        ${c.tag === 'AÃ§Ã£o interna' ? '<span class="badge rounded-pill bg-primary text-white" style="font-size: 0.65rem;"><i class="bi bi-briefcase"></i> AÃ§Ã£o interna</span>' : ''}
                        ${c.tag === 'ReuniÃ£o' ? '<span class="badge rounded-pill bg-danger" style="font-size: 0.65rem;"><i class="bi bi-calendar-event"></i> ReuniÃ£o</span>' : ''}
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
            showToast('Tarefa nÃ£o encontrada na visualizaÃ§Ã£o atual.', 'warning');
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
              // Aplica a mÃ¡scara ao input visÃ­vel (altInput)
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

              // Sincronizar alteraÃ§Ãµes manuais na mÃ¡scara com o Flatpickr
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
          const target = btn.previousElementSibling; // Assumindo que o input estÃ¡ imediatamente antes do botÃ£o (estrutura input-group)
          // No DOM final do flatpickr (com altInput), a estrutura Ã©:
          // input[hidden], input[text].form-control, button
          // Portanto, previousElementSibling do botÃ£o Ã© o altInput.
          // Mas o target para inicializar flatpickr deve ser o input original.

          // Se o flatpickr jÃ¡ estiver inicializado no input original (que pode estar oculto antes do altInput)
          // O input original geralmente Ã© acessÃ­vel.
          // Vamos verificar se o elemento anterior tem a instÃ¢ncia _flatpickr.

          // Caso altInput esteja presente, o DOM Ã©:
          // <input type="hidden" ...> (original)
          // <input type="text" ...> (altInput)
          // <button ...>

          // O previousElementSibling do botÃ£o Ã© o altInput.
          // O altInput nÃ£o tem a propriedade _flatpickr, mas podemos acessÃ¡-lo?
          // NÃ£o diretamente.

          // Mas se jÃ¡ foi inicializado, podemos buscar a instÃ¢ncia flatpickr associada.

          // Se target for o altInput, precisamos achar o original?
          // Na verdade, se jÃ¡ estÃ¡ inicializado, podemos apenas chamar open() na instÃ¢ncia.

          // Vamos tentar encontrar o input original.
          let inputOriginal = target;

          // Se o target for o altInput (nÃ£o tem a classe original custom-datepicker se o flatpickr moveu as classes, mas geralmente copia)
          // Mas o _flatpickr fica no elemento original.

          // Melhor abordagem: procurar o input com a classe custom-datepicker dentro do mesmo parent node.
          const parent = btn.parentElement;
          const originalInput = parent.querySelector('.custom-datepicker');

          if (originalInput && originalInput._flatpickr) {
            originalInput._flatpickr.open();
          } else if (target && target.classList.contains('custom-datepicker')) {
            // Fallback se nÃ£o estiver inicializado (ex: dinamicamente)
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
                showToast(data.message || 'InÃ­cio desfeito com sucesso!', 'success');
                setTimeout(() => location.reload(), 1000);
              }
            })
            .catch(err => {
              console.error(err);
              showToast('Erro ao desfazer inÃ­cio.', 'error');
            });
        });
      }
    }



    // NavegaÃ§Ã£o entre abas (Timeline -> ComentÃ¡rios / Plano)
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
            btnEmail.title = 'Email do responsÃ¡vel nÃ£o cadastrado. Acesse "Editar Detalhes" para adicionar.';
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
        if (t === 'novo_comentario' && itemId) actions += `<button class="btn btn-sm btn-outline-primary timeline-action-comments" data-item-id="${itemId}">Ver comentÃ¡rios</button>`;
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
      if (t === 'novo_comentario' && itemId) actions += `<button class="btn btn-sm btn-outline-primary timeline-action-comments" data-item-id="${itemId}">Ver comentÃ¡rios</button>`;
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
            // permanece no modal; opcionalmente, reativar botÃ£o salvar
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
        title: 'Excluir ComentÃ¡rio',
        message: 'Tem certeza que deseja excluir este comentÃ¡rio? Esta aÃ§Ã£o nÃ£o pode ser desfeita.',
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
          showToast('Erro ao excluir comentÃ¡rio: ' + (errorText || `Status ${response.status}`), 'error');
          return;
        }

        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          const data = await response.json();
          if (!data.ok && !data.success) {
            showToast('Erro ao excluir comentÃ¡rio: ' + (data.error || 'Erro desconhecido'), 'error');
            return;
          }
        } else if (!contentType.includes('text/html')) {
          try {
            const text = await response.text();
            const data = JSON.parse(text);
            if (!data.ok && !data.success) {
              showToast('Erro ao excluir comentÃ¡rio: ' + (data.error || 'Erro desconhecido'), 'error');
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

        showToast('ComentÃ¡rio excluÃ­do com sucesso', 'success');
        try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) { }
      } catch (error) {
        showToast('Erro ao comunicar com o servidor: ' + error.message, 'error');
      }
    });





    // =========================================================================
    // MODAL DETALHES EMPRESA - LÃ³gica movida para modal_detalhes_empresa.js
    // Este arquivo NÃƒO deve ter lÃ³gica do modal para evitar conflitos
    // =========================================================================
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


