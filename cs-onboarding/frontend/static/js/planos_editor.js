/**
 * Editor de Planos de Sucesso - Hierarquia Infinita
 * Gerencia a criação e edição de planos com estrutura hierárquica ilimitada
 */

(function () {
  'use strict';

  let itemCounter = 0;

  const PlanoEditor = {
    init() {
      this.bindEvents();
      this.checkEmptyState();
    },

    bindEvents() {
      const btnAdicionarItem = document.getElementById('btnAdicionarItem');
      if (btnAdicionarItem) {
        btnAdicionarItem.addEventListener('click', () => this.adicionarItemRaiz());
      }

      const formPlano = document.getElementById('formPlano');
      if (formPlano) {
        formPlano.addEventListener('submit', (e) => this.handleSubmit(e));
      }
    },

    adicionarItemRaiz(dados = null) {
      itemCounter++;
      const itemId = dados?.id || `item_${itemCounter}`;
      const container = document.getElementById('itemsContainer');

      if (dados && dados.children && dados.children.length > 0) {
        dados.expanded = true;
      }

      const itemElement = this.criarItemElement(itemId, dados, 0, null);
      container.insertAdjacentHTML('beforeend', itemElement);

      const element = container.querySelector(`[data-item-id="${itemId}"]`);
      this.bindItemEvents(element);

      if (dados && dados.children && dados.children.length > 0) {
        this.carregarFilhosRecursivo(dados, element);
      }

      this.checkEmptyState();
      return element;
    },

    criarItemElement(itemId, dados = null, level = 0, parentId = null) {
      const indent = level * 20;
      const title = dados?.title || dados?.nome || '';
      const comment = dados?.comment || dados?.descricao || '';
      const obrigatoria = dados?.obrigatoria || false;
      const tag = dados?.tag || '';
      const isExpanded = dados?.expanded !== false;
      const hasChildren = dados?.children && dados.children.length > 0;
      const showToggle = hasChildren || level >= 0;

      return `
        <div class="checklist-item-editor" data-item-id="${itemId}" data-level="${level}" data-parent-id="${parentId || ''}" data-expanded="${isExpanded}" style="margin-left: ${indent}px;">
          <div class="checklist-item-header-editor">
            <div class="d-flex align-items-center gap-2 flex-grow-1">
              ${showToggle ? `
                <button type="button" class="btn btn-sm btn-link p-0 toggle-children" style="min-width: 24px;">
                  <i class="bi ${isExpanded ? 'bi-chevron-down expanded' : 'bi-chevron-right'}"></i>
                </button>
              ` : '<div style="width: 24px;"></div>'}
              <input 
                type="text" 
                class="form-control form-control-sm item-title-input" 
                placeholder="Nome do item"
                value="${this.escapeHtml(title)}"
                required
              >
              <select class="form-select form-select-sm item-tag-select" style="max-width: 180px;">
                <option value="">Sem tag</option>
                <option value="Ação interna" ${tag === 'Ação interna' ? 'selected' : ''}>Ação interna</option>
                <option value="Reunião" ${tag === 'Reunião' ? 'selected' : ''}>Reunião</option>
                <option value="Cliente" ${tag === 'Cliente' ? 'selected' : ''}>Cliente</option>
                <option value="Rede" ${tag === 'Rede' ? 'selected' : ''}>Rede</option>
              </select>
            </div>
            <div class="d-flex align-items-center gap-1">
              <button type="button" class="btn btn-sm btn-primary btn-add-child" title="Adicionar filho">
                <i class="bi bi-plus-lg"></i>
              </button>
              <button type="button" 
                      class="btn btn-sm btn-danger btn-remove-item ${obrigatoria ? 'disabled' : ''}" 
                      title="${obrigatoria ? 'Não é possível excluir tarefas obrigatórias' : 'Remover'}"
                      ${obrigatoria ? 'disabled' : ''}>
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </div>
          
          <div class="item-body ${isExpanded ? '' : 'd-none'}">
            <!-- Campo de descrição/comentário removido na criação de tarefas -->
            <div class="mb-2">
              <div class="form-check">
                <input 
                  class="form-check-input item-obrigatoria-input" 
                  type="checkbox" 
                  id="obrigatoria_${itemId}"
                  ${obrigatoria ? 'checked' : ''}
                >
                <label class="form-check-label" for="obrigatoria_${itemId}">
                  Tarefa obrigatória
                </label>
              </div>
            </div>
            
            <div class="item-children" data-parent-id="${itemId}">
            </div>
          </div>
        </div>
      `;
    },

    adicionarFilho(parentElement, dados = null) {
      itemCounter++;
      const parentId = parentElement.getAttribute('data-item-id');
      const level = parseInt(parentElement.getAttribute('data-level')) + 1;
      const itemId = dados?.id || `item_${itemCounter}`;

      const childrenContainer = parentElement.querySelector('.item-children');
      const itemElement = this.criarItemElement(itemId, dados, level, parentId);
      childrenContainer.insertAdjacentHTML('beforeend', itemElement);

      const element = childrenContainer.querySelector(`[data-item-id="${itemId}"]`);
      this.bindItemEvents(element);

      this.expandItem(parentElement);
    },

    expandItem(element) {
      const body = element.querySelector('.item-body');
      const icon = element.querySelector('.toggle-children i');

      body.classList.remove('d-none');
      icon.classList.remove('bi-chevron-right');
      icon.classList.add('bi-chevron-down', 'expanded');
      element.setAttribute('data-expanded', 'true');
    },

    collapseItem(element) {
      const body = element.querySelector('.item-body');
      const icon = element.querySelector('.toggle-children i');

      body.classList.add('d-none');
      icon.classList.remove('bi-chevron-down', 'expanded');
      icon.classList.add('bi-chevron-right');
      element.setAttribute('data-expanded', 'false');
    },

    toggleItem(element) {
      const isExpanded = element.getAttribute('data-expanded') === 'true';
      if (isExpanded) {
        this.collapseItem(element);
      } else {
        this.expandItem(element);
      }
    },

    bindItemEvents(element) {
      const btnAddChild = element.querySelector('.btn-add-child');
      const btnRemove = element.querySelector('.btn-remove-item');
      const btnToggle = element.querySelector('.toggle-children');
      const obrigatoriaInput = element.querySelector('.item-obrigatoria-input');

      if (btnAddChild) {
        btnAddChild.addEventListener('click', () => this.adicionarFilho(element));
      }

      if (btnRemove) {
        btnRemove.addEventListener('click', () => this.removerItem(element));
      }

      if (btnToggle) {
        btnToggle.addEventListener('click', () => this.toggleItem(element));
      }

      if (obrigatoriaInput && btnRemove) {
        obrigatoriaInput.addEventListener('change', () => {
          const isObrigatoria = obrigatoriaInput.checked;
          if (isObrigatoria) {
            btnRemove.classList.add('disabled');
            btnRemove.disabled = true;
            btnRemove.title = 'Não é possível excluir tarefas obrigatórias';
          } else {
            btnRemove.classList.remove('disabled');
            btnRemove.disabled = false;
            btnRemove.title = 'Remover';
          }
        });
      }
    },

    removerItem(element) {
      const obrigatoriaInput = element.querySelector('.item-obrigatoria-input');
      const isObrigatoria = obrigatoriaInput && obrigatoriaInput.checked;

      if (isObrigatoria) {
        alert('Não é possível excluir uma tarefa obrigatória. Desmarque a opção "Tarefa obrigatória" antes de excluir.');
        return;
      }

      if (confirm('Tem certeza que deseja remover este item e todos os seus filhos?')) {
        element.remove();
        this.checkEmptyState();
      }
    },

    checkEmptyState() {
      const itemsContainer = document.getElementById('itemsContainer');
      const emptyState = document.getElementById('emptyState');

      if (itemsContainer && emptyState) {
        const hasItems = itemsContainer.querySelectorAll('[data-item-id]').length > 0;
        emptyState.style.display = hasItems ? 'none' : 'block';
      }
    },

    coletarDados() {
      const itemsContainer = document.getElementById('itemsContainer');
      const rootItems = itemsContainer.querySelectorAll('[data-item-id][data-level="0"]');

      const items = [];
      rootItems.forEach(itemEl => {
        const item = this.coletarItemRecursivo(itemEl);
        if (item.title) {
          items.push(item);
        }
      });

      return { items };
    },

    coletarItemRecursivo(element) {
      const title = element.querySelector('.item-title-input').value.trim();
      const commentEl = element.querySelector('.item-comment-input');
      const comment = commentEl ? commentEl.value.trim() : '';
      const obrigatoriaInput = element.querySelector('.item-obrigatoria-input');
      const obrigatoria = obrigatoriaInput ? obrigatoriaInput.checked : false;
      const tagInput = element.querySelector('.item-tag-select');
      const tag = tagInput ? tagInput.value : '';
      const level = parseInt(element.getAttribute('data-level'));

      const item = {
        title: title,
        comment: comment,
        obrigatoria: obrigatoria,
        tag: tag,
        level: level,
        ordem: 0, // Será calculado no backend se necessário
        children: []
      };

      const childrenContainer = element.querySelector('.item-children');
      if (childrenContainer) {
        // Modificado para pegar apenas filhos diretos e evitar duplicação
        const children = Array.from(childrenContainer.children).filter(el => el.hasAttribute('data-item-id'));
        children.forEach(childEl => {
          const child = this.coletarItemRecursivo(childEl);
          if (child.title) {
            item.children.push(child);
          }
        });
      }

      return item;
    },

    validarDados(estrutura) {
      if (!estrutura.items || estrutura.items.length === 0) {
        alert('Adicione pelo menos um item ao plano.');
        return false;
      }

      const validarItem = (item) => {
        if (!item.title || !item.title.trim()) {
          alert('Todos os itens devem ter um título.');
          return false;
        }

        if (item.children) {
          for (const child of item.children) {
            if (!validarItem(child)) {
              return false;
            }
          }
        }

        return true;
      };

      for (const item of estrutura.items) {
        if (!validarItem(item)) {
          return false;
        }
      }

      return true;
    },

    carregarPlano(planoData) {
      if (planoData.items && Array.isArray(planoData.items)) {
        planoData.items.forEach(item => {
          this.adicionarItemRaiz(item);
        });
      } else if (planoData.fases && Array.isArray(planoData.fases)) {
        this.carregarPlanoLegado(planoData);
      } else if (planoData.estrutura && planoData.estrutura.items) {
        planoData.estrutura.items.forEach(item => {
          this.adicionarItemRaiz(item);
        });
      }
    },

    carregarPlanoLegado(planoData) {
      planoData.fases.forEach((fase, faseIndex) => {
        const faseItem = {
          title: fase.nome,
          comment: fase.descricao || '',
          level: 0,
          expanded: true,
          children: []
        };

        if (fase.grupos && fase.grupos.length > 0) {
          fase.grupos.forEach(grupo => {
            const grupoItem = {
              title: grupo.nome,
              comment: grupo.descricao || '',
              level: 1,
              children: []
            };

            if (grupo.tarefas && grupo.tarefas.length > 0) {
              grupo.tarefas.forEach(tarefa => {
                grupoItem.children.push({
                  title: tarefa.nome,
                  comment: tarefa.descricao || '',
                  level: 2
                });
              });
            }

            faseItem.children.push(grupoItem);
          });
        }

        this.adicionarItemRaiz(faseItem);
      });
    },

    carregarFilhosRecursivo(itemData, parentElement) {
      if (!itemData.children || itemData.children.length === 0) {
        return;
      }

      itemData.children.forEach(childData => {
        this.adicionarFilho(parentElement, childData);

        const childrenContainer = parentElement.querySelector('.item-children');
        if (childrenContainer) {
          const lastChild = childrenContainer.querySelector('[data-item-id]:last-child');
          if (lastChild && childData.children && childData.children.length > 0) {
            this.carregarFilhosRecursivo(childData, lastChild);
          }
        }
      });
    },

    escapeHtml(text) {
      if (!text) return '';
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    },

    handleSubmit(e) {
      e.preventDefault();

      const form = e.target;
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

      let estruturaInput = form.querySelector('input[name="estrutura"]');
      if (!estruturaInput) {
        estruturaInput = document.createElement('input');
        estruturaInput.type = 'hidden';
        estruturaInput.name = 'estrutura';
        form.appendChild(estruturaInput);
      }
      estruturaInput.value = JSON.stringify(estrutura);

      form.submit();
    }
  };

  window.PlanoEditor = PlanoEditor;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => PlanoEditor.init());
  } else {
    PlanoEditor.init();
  }
})();
