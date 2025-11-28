/**
 * Editor de Planos de Sucesso
 * Gerencia a criação e edição hierárquica de planos
 */

(function() {
  'use strict';

  let faseCounter = 0;
  let grupoCounter = 0;
  let tarefaCounter = 0;

  const PlanoEditor = {
    init() {
      this.bindEvents();
      this.checkEmptyState();
    },

    bindEvents() {
      const btnAdicionarFase = document.getElementById('btnAdicionarFase');
      if (btnAdicionarFase) {
        btnAdicionarFase.addEventListener('click', () => this.adicionarFase());
      }

      const formPlano = document.getElementById('formPlano');
      if (formPlano) {
        formPlano.addEventListener('submit', (e) => this.handleSubmit(e));
      }
    },

    adicionarFase(dados = null) {
      faseCounter++;
      const faseId = dados?.id || `fase_${faseCounter}`;
      const ordem = dados?.ordem || faseCounter;

      const faseHtml = `
        <div class="accordion-item" data-fase-id="${faseId}">
          <h2 class="accordion-header">
            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${faseId}">
              <i class="bi bi-grip-vertical drag-handle me-2"></i>
              <span class="fase-nome-display">${dados?.nome || `Fase ${ordem}`}</span>
            </button>
          </h2>
          <div id="collapse${faseId}" class="accordion-collapse collapse" data-bs-parent="#fasesContainer">
            <div class="accordion-body">
              <div class="mb-3">
                <label class="form-label fw-bold">Nome da Fase</label>
                <input 
                  type="text" 
                  class="form-control fase-nome-input" 
                  placeholder="Ex: Onboarding Inicial"
                  value="${dados?.nome || ''}"
                  required
                >
              </div>

              <div class="mb-3">
                <label class="form-label fw-bold">Descrição</label>
                <textarea 
                  class="form-control fase-descricao-input" 
                  rows="2"
                  placeholder="Descrição opcional da fase..."
                >${dados?.descricao || ''}</textarea>
              </div>

              <input type="hidden" class="fase-ordem-input" value="${ordem}">

              <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="mb-0"><i class="bi bi-collection me-2"></i>Ações</h6>
                <button type="button" class="btn btn-sm btn-add btn-adicionar-grupo">
                  <i class="bi bi-plus me-1"></i>Adicionar Ação
                </button>
              </div>

              <div class="grupos-container">
                <!-- Grupos serão adicionados aqui -->
              </div>

              <button type="button" class="btn btn-remove mt-3 btn-remover-fase">
                <i class="bi bi-trash me-1"></i>Remover Fase
              </button>
            </div>
          </div>
        </div>
      `;

      const container = document.getElementById('fasesContainer');
      container.insertAdjacentHTML('beforeend', faseHtml);

      const faseElement = container.querySelector(`[data-fase-id="${faseId}"]`);
      this.bindFaseEvents(faseElement);

      // Carregar grupos se existirem
      if (dados?.grupos) {
        dados.grupos.forEach(grupo => this.adicionarGrupo(faseElement, grupo));
      }

      // Atualizar nome da fase quando digitado
      const nomeInput = faseElement.querySelector('.fase-nome-input');
      const nomeDisplay = faseElement.querySelector('.fase-nome-display');
      nomeInput.addEventListener('input', (e) => {
        nomeDisplay.textContent = e.target.value || `Fase ${ordem}`;
      });

      this.checkEmptyState();
    },

    bindFaseEvents(faseElement) {
      const btnAdicionarGrupo = faseElement.querySelector('.btn-adicionar-grupo');
      btnAdicionarGrupo.addEventListener('click', () => this.adicionarGrupo(faseElement));

      const btnRemoverFase = faseElement.querySelector('.btn-remover-fase');
      btnRemoverFase.addEventListener('click', () => this.removerFase(faseElement));
    },

    adicionarGrupo(faseElement, dados = null) {
      grupoCounter++;
      const grupoId = dados?.id || `grupo_${grupoCounter}`;

      const grupoHtml = `
        <div class="grupo-card" data-grupo-id="${grupoId}">
          <div class="grupo-header">
            <input 
              type="text" 
              class="form-control form-control-sm grupo-nome-input" 
              placeholder="Nome da ação"
              value="${dados?.nome || ''}"
              required
            >
            <button type="button" class="btn btn-sm btn-remove btn-remover-grupo">
              <i class="bi bi-trash"></i>
            </button>
          </div>

          <div class="mb-2">
            <textarea 
              class="form-control form-control-sm grupo-descricao-input" 
              rows="2"
              placeholder="Descrição da ação (opcional)"
            >${dados?.descricao || ''}</textarea>
          </div>

          <div class="d-flex justify-content-between align-items-center mb-2">
            <small class="fw-bold"><i class="bi bi-list-check me-1"></i>Tarefas</small>
            <button type="button" class="btn btn-sm btn-add btn-adicionar-tarefa">
              <i class="bi bi-plus"></i>
            </button>
          </div>

          <div class="tarefas-container">
            <!-- Tarefas serão adicionadas aqui -->
          </div>
        </div>
      `;

      const gruposContainer = faseElement.querySelector('.grupos-container');
      gruposContainer.insertAdjacentHTML('beforeend', grupoHtml);

      const grupoElement = gruposContainer.querySelector(`[data-grupo-id="${grupoId}"]`);
      this.bindGrupoEvents(grupoElement);

      // Carregar tarefas se existirem
      if (dados?.tarefas) {
        dados.tarefas.forEach(tarefa => this.adicionarTarefa(grupoElement, tarefa));
      }
    },

    bindGrupoEvents(grupoElement) {
      const btnAdicionarTarefa = grupoElement.querySelector('.btn-adicionar-tarefa');
      btnAdicionarTarefa.addEventListener('click', () => this.adicionarTarefa(grupoElement));

      const btnRemoverGrupo = grupoElement.querySelector('.btn-remover-grupo');
      btnRemoverGrupo.addEventListener('click', () => this.removerGrupo(grupoElement));
    },

    adicionarTarefa(grupoElement, dados = null) {
      tarefaCounter++;
      const tarefaId = dados?.id || `tarefa_${tarefaCounter}`;

      const tarefaHtml = `
        <div class="tarefa-item" data-tarefa-id="${tarefaId}">
          <div class="tarefa-header">
            <div class="flex-grow-1">
              <input 
                type="text" 
                class="form-control form-control-sm tarefa-nome-input mb-2" 
                placeholder="Nome da tarefa"
                value="${dados?.nome || ''}"
                required
              >
              <textarea 
                class="form-control form-control-sm tarefa-descricao-input" 
                rows="1"
                placeholder="Descrição (opcional)"
              >${dados?.descricao || ''}</textarea>
            </div>
            <button type="button" class="btn btn-sm btn-remove btn-remover-tarefa">
              <i class="bi bi-trash"></i>
            </button>
          </div>

          <div class="form-check mb-2">
            <input 
              class="form-check-input tarefa-obrigatoria-input" 
              type="checkbox" 
              id="obrig_${tarefaId}"
              ${dados?.obrigatoria ? 'checked' : ''}
            >
            <label class="form-check-label small" for="obrig_${tarefaId}">
              Tarefa Obrigatória
            </label>
          </div>
        </div>
      `;

      const tarefasContainer = grupoElement.querySelector('.tarefas-container');
      tarefasContainer.insertAdjacentHTML('beforeend', tarefaHtml);

      const tarefaElement = tarefasContainer.querySelector(`[data-tarefa-id="${tarefaId}"]`);
      this.bindTarefaEvents(tarefaElement);
    },

    bindTarefaEvents(tarefaElement) {
      const btnRemoverTarefa = tarefaElement.querySelector('.btn-remover-tarefa');
      btnRemoverTarefa.addEventListener('click', () => this.removerTarefa(tarefaElement));
    },

    removerFase(faseElement) {
      if (confirm('Tem certeza que deseja remover esta fase e todo seu conteúdo?')) {
        faseElement.remove();
        this.checkEmptyState();
      }
    },

    removerGrupo(grupoElement) {
      if (confirm('Tem certeza que deseja remover esta ação e todo seu conteúdo?')) {
        grupoElement.remove();
      }
    },

    removerTarefa(tarefaElement) {
      tarefaElement.remove();
    },

    checkEmptyState() {
      const fasesContainer = document.getElementById('fasesContainer');
      const emptyState = document.getElementById('emptyState');
      
      if (fasesContainer && emptyState) {
        const hasFases = fasesContainer.querySelectorAll('.accordion-item').length > 0;
        emptyState.style.display = hasFases ? 'none' : 'block';
      }
    },

    coletarDados() {
      const fases = [];
      const faseElements = document.querySelectorAll('[data-fase-id]');

      faseElements.forEach((faseEl, index) => {
        const fase = {
          nome: faseEl.querySelector('.fase-nome-input').value.trim(),
          descricao: faseEl.querySelector('.fase-descricao-input').value.trim(),
          ordem: index + 1,
          grupos: []
        };

        const grupoElements = faseEl.querySelectorAll('[data-grupo-id]');
        grupoElements.forEach((grupoEl, gIndex) => {
          const grupo = {
            nome: grupoEl.querySelector('.grupo-nome-input').value.trim(),
            descricao: grupoEl.querySelector('.grupo-descricao-input').value.trim(),
            ordem: gIndex + 1,
            tarefas: []
          };

          const tarefaElements = grupoEl.querySelectorAll('[data-tarefa-id]');
          tarefaElements.forEach((tarefaEl, tIndex) => {
            const tarefa = {
              nome: tarefaEl.querySelector('.tarefa-nome-input').value.trim(),
              descricao: tarefaEl.querySelector('.tarefa-descricao-input').value.trim(),
              obrigatoria: tarefaEl.querySelector('.tarefa-obrigatoria-input').checked,
              ordem: tIndex + 1
            };

            if (tarefa.nome) {
              grupo.tarefas.push(tarefa);
            }
          });

          if (grupo.nome) {
            fase.grupos.push(grupo);
          }
        });

        if (fase.nome) {
          fases.push(fase);
        }
      });

      return { fases };
    },

    validarDados(estrutura) {
      // Permite criar planos sem fases (podem ser adicionadas depois)
      if (estrutura.fases && estrutura.fases.length > 0) {
        for (const fase of estrutura.fases) {
          if (!fase.nome) {
            alert('Todas as fases devem ter um nome.');
            return false;
          }
        }
      }

      return true;
    },

    handleSubmit(e) {
      e.preventDefault();

      const form = e.target;
      
      // Validar campos obrigatórios do formulário
      const nome = form.querySelector('#nome');
      const diasDuracao = form.querySelector('#dias_duracao');
      
      if (!nome || !nome.value.trim()) {
        alert('O nome do plano é obrigatório.');
        if (nome) nome.focus();
        return;
      }
      
      if (!diasDuracao || !diasDuracao.value || parseInt(diasDuracao.value) < 1) {
        alert('Informe os dias de duração (mínimo 1 dia).');
        if (diasDuracao) diasDuracao.focus();
        return;
      }
      
      const estrutura = this.coletarDados();

      if (!this.validarDados(estrutura)) {
        return;
      }

      // Adicionar estrutura como campo hidden
      let estruturaInput = form.querySelector('input[name="estrutura"]');
      if (!estruturaInput) {
        estruturaInput = document.createElement('input');
        estruturaInput.type = 'hidden';
        estruturaInput.name = 'estrutura';
        form.appendChild(estruturaInput);
      }
      estruturaInput.value = JSON.stringify(estrutura);

      // Submeter o formulário
      form.submit();
    },

    carregarPlano(planoData) {
      if (planoData.fases) {
        planoData.fases.forEach(fase => this.adicionarFase(fase));
      }
    }
  };

  // Expor globalmente
  window.PlanoEditor = PlanoEditor;

  // Inicializar quando o DOM estiver pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => PlanoEditor.init());
  } else {
    PlanoEditor.init();
  }
})();
