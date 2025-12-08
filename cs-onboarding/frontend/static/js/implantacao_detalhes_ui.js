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
        telefoneInput.addEventListener('input', function() {
            if (window.formatarTelefone) window.formatarTelefone(this);
        });
        telefoneInput.addEventListener('blur', function() {
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
        // Load comments only if list is empty or specifically requested
        // But to keep it simple and fresh, we can reload or check if empty
        const container = document.getElementById('comments-list-container');
        // If container is effectively empty (only loading/empty placeholders), load
        // We check if we have already loaded comments by checking for .comentario-item
        if (container && container.querySelectorAll('.comentario-item').length === 0) {
          resetGlobalComments();
          carregarComentariosGerais();
        }
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
      
      // If not appending, clear existing items (be careful not to remove placeholders if they are mixed, 
      // but we structure them separately usually. Here we just append to end or clear all items first)
      // Our structure: container has loading/empty divs + comment items.
      // We should insert items before the pagination or just append to container if pagination is outside (it is inside in HTML structure?)
      // Looking at HTML: pagination is sibling to list container or inside?
      // HTML: <div id="comments-list-container"> ... </div> <div id="comments-pagination"> ... </div>
      // Wait, HTML snippet was:
      // <div id="comments-list-container" ...> 
      //    <div id="comments-loading">...</div>
      //    <div id="comments-empty">...</div>
      // </div>
      // <div id="comments-pagination">...</div>
      // So we can just append to container.
      
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
                        <span class="badge ${c.visibilidade === 'externo' ? 'bg-warning text-dark' : 'bg-info text-white'} rounded-pill" style="font-size: 0.65rem;">
                            ${c.visibilidade === 'externo' ? 'Externo' : 'Interno'}
                        </span>
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
              <div class="comentario-texto text-break">${escapeHtml(c.texto)}</div>
              ${c.imagem_url ? `<div class="mt-2"><img src="${c.imagem_url}" class="img-fluid rounded" style="max-height: 200px;" alt="Imagem anexada"></div>` : ''}
            </div>
          </div>`;
      }).join('');
      
      // Need to convert string to nodes to append properly or just innerHTML if not append
      // But since we have loading/empty divs inside, we should insert After them or handle visibility.
      // Easier: Create a wrapper for items if not exists, or just append to container.
      // The loading/empty divs are toggled with d-none.
      
      if (!append) {
        // Remove old comment items
        container.querySelectorAll('.comentario-item').forEach(e => e.remove());
      }
      
      container.insertAdjacentHTML('beforeend', html);
      
      // Add event listeners for task links
      container.querySelectorAll('.task-scroll-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const taskId = parseInt(this.dataset.taskId, 10);
            if (window.checklistRenderer && Number.isFinite(taskId)) {
                try { window.checklistRenderer.ensureItemVisible(taskId); } catch (_) {}
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
                      try { new bootstrap.Collapse(commentsSection, { toggle: true }); } catch (_) {}
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
            config.onReady = function(selectedDates, dateStr, instance) {
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
                    mask.on('accept', function() {
                        if (mask.masked.isComplete) {
                            instance.setDate(mask.value, true, 'd/m/Y');
                        }
                    });
                }
            };
        }

        const fp = window.flatpickr(input, config);
        if (input.hasAttribute('required')) {
          input.addEventListener('change', function() {
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
        modalParar.addEventListener('shown.bs.modal', function() {
          const dataParadaInput = document.getElementById('data_parada');
          const btnCal = document.getElementById('btn_cal_data_parada');
          if (dataParadaInput && !dataParadaInput._flatpickr) {
            const fp = window.flatpickr(dataParadaInput, Object.assign({}, baseConfig, {
              appendTo: modalParar.querySelector('.modal-body'),
              static: true,
              onChange: function(selectedDates, dateStr, instance) {
                if (selectedDates.length > 0) {
                  dataParadaInput.value = dateStr;
                }
              }
            }));
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
              appendTo: modalCancelar.querySelector('.modal-body'),
              static: true,
              onChange: function(selectedDates, dateStr, instance) {
                if (selectedDates.length > 0) {
                  dataCancelamentoInput.value = dateStr;
                }
              }
            }));
            if (btnCal) {
              btnCal.addEventListener('click', function(e) {
                e.preventDefault();
                fp.open();
              });
            }
          }
        });
      }

      const formParar = document.getElementById('formPararImplantacao');
      if (formParar) {
        formParar.addEventListener('submit', function(e) {
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
        formCancelar.addEventListener('submit', function(e) {
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
    }

    function computeProgress() {
      const tarefaCheckboxes = document.querySelectorAll('.tarefa-checkbox');
      const total = tarefaCheckboxes.length;
      if (!total) return;
      const done = Array.from(tarefaCheckboxes).filter(cb => cb.checked).length;
      const pct = Math.round((done / total) * 100);
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

    // Navegação entre abas (Timeline -> Comentários / Plano)
    function activateTab(targetId) {
      if (!window.bootstrap) return;
      const triggerEl = document.querySelector(`[data-bs-target="${targetId}"]`);
      if (triggerEl) {
        const tab = new bootstrap.Tab(triggerEl);
        tab.show();
      }
    }

    document.addEventListener('click', function(e) {
      const btnComments = e.target.closest('.timeline-action-comments');
      if (btnComments) {
        const itemId = parseInt(btnComments.dataset.itemId);
        activateTab('#plano-content');
        if (window.checklistRenderer && Number.isFinite(itemId)) {
          try { window.checklistRenderer.ensureItemVisible(itemId); } catch (_) {}
        }
        setTimeout(() => {
          const taskElement = document.getElementById(`checklist-item-${itemId}`) || document.querySelector(`.checklist-item[data-item-id="${itemId}"]`);
          if (taskElement) {
            taskElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            const commentsSection = document.getElementById(`comments-${itemId}`);
            if (commentsSection && window.bootstrap && bootstrap.Collapse) {
              try { new bootstrap.Collapse(commentsSection, { toggle: true }); } catch (_) {}
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
          try { window.checklistRenderer.ensureItemVisible(itemId); } catch (_) {}
        }
        e.preventDefault();
      }
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

    document.querySelectorAll('[id^="comentarios-tarefa-"]').forEach(section => {
      section.addEventListener('shown.bs.collapse', function () {
        const tarefaId = this.id.replace('comentarios-tarefa-', '');
        if (tarefaId) {
          setTimeout(() => {
            inicializarTagsComentario();
            atualizarVisibilidadeBotaoEmail(tarefaId);
          }, 100);
        }
      });
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

    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.type === 'childList') {
          mutation.addedNodes.forEach(function(node) {
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
          }
        }

        const comentarioItem = targetBtn.closest('.comentario-item');
        const historico = comentarioItem ? comentarioItem.closest('[id^="historico-tarefa-"]') : null;
        const itemId = historico ? historico.id.replace('historico-tarefa-', '') : null;

        if (comentarioItem) comentarioItem.remove();
        if (itemId) await carregarComentarios(itemId);

        showToast('Comentário excluído com sucesso', 'success');
      } catch (error) {
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
            atualizarVisibilidadeBotaoEmail(tarefaId);
            const btnComentarios = document.querySelector(`.btn-toggle-comentarios[data-tarefa-id="${tarefaId}"]`);
            if (btnComentarios) btnComentarios.classList.add('has-comments');
            showToast('Comentário salvo com sucesso!', 'success');
          } else {
            showToast('Erro ao salvar comentário: ' + (data.error || 'Erro desconhecido'), 'error');
          }
        } catch (error) {
          showToast('Erro ao comunicar com o servidor: ' + error.message, 'error');
        } finally {
          this.disabled = false;
          this.innerHTML = '<i class="bi bi-send me-1"></i>Salvar';
        }
      });
    });

    document.body.addEventListener('click', async function (e) {
      const btn = e.target.closest('.btn-enviar-email');
      if (!btn) return;

      if (btn.disabled) {
        e.preventDefault();
        e.stopPropagation();
        showToast('Email do responsável não cadastrado. Acesse "Editar Detalhes" para adicionar o email antes de enviar comentários externos.', 'warning');
        return;
      }

      const tarefaId = btn.dataset.tarefaId || btn.getAttribute('data-tarefa-id');
      const textarea = document.getElementById(`comentario-texto-${tarefaId}`);
      const texto = textarea?.value?.trim();

      if (!texto) {
        showToast('Digite uma mensagem para enviar', 'warning');
        return;
      }

      const temEmail = CONFIG.emailResponsavel && CONFIG.emailResponsavel.trim() !== '';
      if (!temEmail) {
        showToast('Email do responsável não cadastrado. Acesse "Editar Detalhes" para adicionar o email antes de enviar comentários externos.', 'warning');
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

      btn.disabled = true;
      const originalHtml = btn.innerHTML;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando...';

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

        const novoComentarioId = (data && data.comentario && data.comentario.id) ? data.comentario.id : null;
        const emailEndpoint = novoComentarioId ? `/api/enviar_email_comentario_h/${novoComentarioId}` : `/api/enviar_email_comentario_h/${tarefaId}`;
        const emailResponse = await fetch(emailEndpoint, {
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
        showToast('Erro ao comunicar com o servidor: ' + error.message, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
      }
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

    

    const modalDetalhesEmpresa = document.getElementById('modalDetalhesEmpresa');
    if (modalDetalhesEmpresa && window.flatpickr) {
      modalDetalhesEmpresa.addEventListener('shown.bs.modal', function(event) {
        const configWithMask = Object.assign({}, baseConfig, {
          onReady: function(selectedDates, dateStr, instance) {
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
            onChange: function(selectedDates, dateStr, instance) {
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
            btnCalInicioEfetivo.addEventListener('click', function(e) {
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
            onChange: function(selectedDates, dateStr, instance) {
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
            btnCalInicioProducao.addEventListener('click', function(e) {
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
            onChange: function(selectedDates, dateStr, instance) {
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
            btnCalFinalImplantacao.addEventListener('click', function(e) {
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

        if (tomSelectInstances[selectId]) {
          tomSelectInstances[selectId].destroy();
          delete tomSelectInstances[selectId];
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

        if (tomSelectInstances[selectId]) {
          tomSelectInstances[selectId].destroy();
          delete tomSelectInstances[selectId];
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
    document.addEventListener('click', async function(e) {
        const btnConsultar = e.target.closest('#btn-consultar-oamd');
        if (!btnConsultar) return;
        
        e.preventDefault();
        e.stopPropagation();

        console.log('Global Click Listener: Consultar button clicked');

        const loaderConsultar = document.getElementById('btn-consultar-oamd-loader');
        const iconConsultar = document.getElementById('btn-consultar-oamd-icon');
        const inputIdFav = document.getElementById('modal-id_favorecido');
        
        // Get ID from input or button dataset
        const currentId = inputIdFav ? inputIdFav.value.trim() : (btnConsultar.dataset.idFavorecido || '');
        console.log('ID for consultation:', currentId);
        
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
                } catch(e) {}
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
              updateText('modal-tela_apoio_link', m.tela_apoio_link);
              updateText('modal-informacao_infra', m.informacao_infra);

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

    modalDetalhesEmpresa.addEventListener('shown.bs.modal', function(event) {
        const btn = event.relatedTarget || document.querySelector('[data-bs-target="#modalDetalhesEmpresa"]');
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
          let idFavorecido = btn.dataset.idFavorecido || '';
          
          if (!idFavorecido) {
            const inputIdFav = document.getElementById('modal-id_favorecido');
            if (inputIdFav && inputIdFav.value) {
                idFavorecido = inputIdFav.value;
            }
          }
          
          const wellhubSelect = document.getElementById('modal-wellhub');
          const totalpassSelect = document.getElementById('modal-totalpass');
          if (wellhubSelect && wellhub) wellhubSelect.value = wellhub;
          if (totalpassSelect && totalpass) totalpassSelect.value = totalpass;
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

        if (catracaSelect) {
          if (catraca) catracaSelect.value = catraca;
          catracaSelect.addEventListener('change', atualizarCamposCondicionais);
          if (modeloCatracaInput && catraca === 'Sim' && modeloCatraca) {
            modeloCatracaInput.value = modeloCatraca;
          }
          // Disparar evento para atualizar UI
          catracaSelect.dispatchEvent(new Event('change'));
        }

        if (facialSelect) {
          if (facial) facialSelect.value = facial;
          facialSelect.addEventListener('change', atualizarCamposCondicionais);
          if (modeloFacialInput && facial === 'Sim' && modeloFacial) {
            modeloFacialInput.value = modeloFacial;
          }
          // Disparar evento para atualizar UI
          facialSelect.dispatchEvent(new Event('change'));
        }

        atualizarCamposCondicionais();

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

      modalDetalhesEmpresa.addEventListener('hidden.bs.modal', function() {
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

      modalDetalhesEmpresa.addEventListener('shown.bs.modal', function() {
        const telefoneInput = document.getElementById('modal-telefone_responsavel');
        if (telefoneInput && window.formatarTelefone) {
          formatarTelefone(telefoneInput);
        }

        const alunosAtivosInput = document.getElementById('modal-alunos_ativos');
        if (alunosAtivosInput) {
          alunosAtivosInput.setAttribute('min', '0');
          alunosAtivosInput.setAttribute('step', '1');
          alunosAtivosInput.addEventListener('input', function() {
            const value = this.value;
            if (value.includes('.')) {
              this.value = Math.floor(parseFloat(value) || 0);
            }
            if (parseInt(this.value, 10) < 0) {
              this.value = 0;
            }
          });
          alunosAtivosInput.addEventListener('blur', function() {
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
          idFavorecidoInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '');
          });
        }
        
        const valorAtribuidoInput = document.getElementById('modal-valor_atribuido');
        if (valorAtribuidoInput) {
          // Remove existing listeners to avoid duplication if any (though 'blur' at 1316 was simple)
          // Initialize IMask for Currency
          if (window.IMask) {
             // Remove previous instance if stored? Not storing currently.
             // Just init.
             IMask(valorAtribuidoInput, {
                mask: 'R$ num',
                blocks: {
                    num: {
                        mask: Number,
                        thousandsSeparator: '.',
                        radix: ',',
                        scale: 2,
                        signed: false,
                        normalizeZeros: true,
                        padFractionalZeros: true,
                        min: 0
                    }
                }
            });
          }
        }
        
        const cnpjInput = document.getElementById('modal-cnpj');
        if (cnpjInput && window.IMask) {
             const cnpjMask = IMask(cnpjInput, {
                mask: '00.000.000/0000-00'
            });
            
            cnpjInput.addEventListener('blur', function() {
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
             cnpjInput.addEventListener('input', function() {
                 this.classList.remove('is-invalid');
                 let feedback = this.parentNode.querySelector('.invalid-feedback');
                 if (feedback) feedback.style.display = 'none';
            });
        }

        const telaApoioInput = document.getElementById('modal-tela_apoio_link');
        if (telaApoioInput) {
            telaApoioInput.addEventListener('blur', function() {
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
            telaApoioInput.addEventListener('input', function() {
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
    let numeros = cnpj.substring(0,tamanho);
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
    numeros = cnpj.substring(0,tamanho);
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

