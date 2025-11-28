/**
 * Editor de Planos de Sucesso - Hierarquia Infinita
 * Gerencia a criação e edição de planos com estrutura hierárquica ilimitada
 */

(function() {
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

    /**
     * Adiciona um item raiz (nível 0)
     */
    adicionarItemRaiz(dados = null) {
      itemCounter++;
      const itemId = dados?.id || `item_${itemCounter}`;
      const container = document.getElementById('itemsContainer');
      
      // Se dados existem e têm children, marcar como expandido
      if (dados && dados.children && dados.children.length > 0) {
        dados.expanded = true;
      }
      
      const itemElement = this.criarItemElement(itemId, dados, 0, null);
      container.insertAdjacentHTML('beforeend', itemElement);
      
      const element = container.querySelector(`[data-item-id="${itemId}"]`);
      this.bindItemEvents(element);
      
      // Carregar filhos se existirem
      if (dados && dados.children && dados.children.length > 0) {
        this.carregarFilhosRecursivo(dados, element);
      }
      
      this.checkEmptyState();
      return element;
    },

    /**
     * Cria HTML para um item (genérico, qualquer nível)
     */
    criarItemElement(itemId, dados = null, level = 0, parentId = null) {
      const indent = level * 20;
      const title = dados?.title || dados?.nome || '';
      const comment = dados?.comment || dados?.descricao || '';
      const isExpanded = dados?.expanded !== false;
      const hasChildren = dados?.children && dados.children.length > 0;
      const showToggle = hasChildren || level >= 0; // Sempre mostrar toggle (pode adicionar filhos)
      
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
            </div>
            <div class="d-flex align-items-center gap-1">
              <button type="button" class="btn btn-sm btn-primary btn-add-child" title="Adicionar filho">
                <i class="bi bi-plus-lg"></i>
              </button>
              ${level > 0 ? `
                <button type="button" class="btn btn-sm btn-danger btn-remove-item" title="Remover">
                  <i class="bi bi-trash"></i>
                </button>
              ` : `
                <button type="button" class="btn btn-sm btn-danger btn-remove-item" title="Remover">
                  <i class="bi bi-trash"></i>
                </button>
              `}
            </div>
          </div>
          
          <div class="item-body ${isExpanded ? '' : 'd-none'}">
            <div class="mb-2 mt-2">
              <textarea 
                class="form-control form-control-sm item-comment-input" 
                rows="2"
                placeholder="Descrição/Comentário (opcional)"
              >${this.escapeHtml(comment)}</textarea>
            </div>
            
            <div class="item-children" data-parent-id="${itemId}">
              <!-- Filhos serão adicionados aqui -->
            </div>
          </div>
        </div>
      `;
    },

    /**
     * Adiciona um filho a um item
     */
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
      
      // Expandir pai se estiver colapsado
      this.expandItem(parentElement);
    },

    /**
     * Expande/colapsa um item
     */
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

    /**
     * Vincula eventos a um item
     */
    bindItemEvents(element) {
      const btnAddChild = element.querySelector('.btn-add-child');
      const btnRemove = element.querySelector('.btn-remove-item');
      const btnToggle = element.querySelector('.toggle-children');
      
      if (btnAddChild) {
        btnAddChild.addEventListener('click', () => this.adicionarFilho(element));
      }
      
      if (btnRemove) {
        btnRemove.addEventListener('click', () => this.removerItem(element));
      }
      
      if (btnToggle) {
        btnToggle.addEventListener('click', () => this.toggleItem(element));
      }
    },

    /**
     * Remove um item e seus filhos
     */
    removerItem(element) {
      if (confirm('Tem certeza que deseja remover este item e todos os seus filhos?')) {
        element.remove();
        this.checkEmptyState();
      }
    },

    /**
     * Verifica estado vazio
     */
    checkEmptyState() {
      const itemsContainer = document.getElementById('itemsContainer');
      const emptyState = document.getElementById('emptyState');
      
      if (itemsContainer && emptyState) {
        const hasItems = itemsContainer.querySelectorAll('[data-item-id]').length > 0;
        emptyState.style.display = hasItems ? 'none' : 'block';
      }
    },

    /**
     * Coleta dados da estrutura hierárquica
     */
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

    /**
     * Coleta dados de um item e seus filhos recursivamente
     */
    coletarItemRecursivo(element) {
      const title = element.querySelector('.item-title-input').value.trim();
      const comment = element.querySelector('.item-comment-input').value.trim();
      const level = parseInt(element.getAttribute('data-level'));
      
      const item = {
        title: title,
        comment: comment,
        level: level,
        ordem: 0, // Será calculado no backend se necessário
        children: []
      };
      
      // Coletar filhos
      const childrenContainer = element.querySelector('.item-children');
      if (childrenContainer) {
        const children = childrenContainer.querySelectorAll('[data-item-id]');
        children.forEach(childEl => {
          const child = this.coletarItemRecursivo(childEl);
          if (child.title) {
            item.children.push(child);
          }
        });
      }
      
      return item;
    },

    /**
     * Valida dados da estrutura
     */
    validarDados(estrutura) {
      if (!estrutura.items || estrutura.items.length === 0) {
        alert('Adicione pelo menos um item ao plano.');
        return false;
      }
      
      // Validar recursivamente
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

    /**
     * Carrega plano (suporta formato antigo e novo)
     */
    carregarPlano(planoData) {
      if (planoData.items && Array.isArray(planoData.items)) {
        // Formato novo (checklist_items)
        planoData.items.forEach(item => {
          this.adicionarItemRaiz(item);
        });
      } else if (planoData.fases && Array.isArray(planoData.fases)) {
        // Formato antigo (fases/grupos/tarefas) - converter
        this.carregarPlanoLegado(planoData);
      } else if (planoData.estrutura && planoData.estrutura.items) {
        // Formato com estrutura.items
        planoData.estrutura.items.forEach(item => {
          this.adicionarItemRaiz(item);
        });
      }
    },

    /**
     * Carrega plano em formato legado (fases/grupos/tarefas)
     */
    carregarPlanoLegado(planoData) {
      planoData.fases.forEach((fase, faseIndex) => {
        const faseItem = {
          title: fase.nome,
          comment: fase.descricao || '',
          level: 0,
          expanded: true,
          children: []
        };
        
        // Criar estrutura de filhos para grupos
        if (fase.grupos && fase.grupos.length > 0) {
          fase.grupos.forEach(grupo => {
            const grupoItem = {
              title: grupo.nome,
              comment: grupo.descricao || '',
              level: 1,
              children: []
            };
            
            // Adicionar tarefas como filhos do grupo
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
        
        // Adicionar fase com toda a estrutura
        this.adicionarItemRaiz(faseItem);
      });
    },

    /**
     * Carrega filhos recursivamente
     */
    carregarFilhosRecursivo(itemData, parentElement) {
      if (!itemData.children || itemData.children.length === 0) {
        return;
      }
      
      itemData.children.forEach(childData => {
        this.adicionarFilho(parentElement, childData);
        
        // Encontrar elemento recém-criado e carregar seus filhos
        const childrenContainer = parentElement.querySelector('.item-children');
        if (childrenContainer) {
          const lastChild = childrenContainer.querySelector('[data-item-id]:last-child');
          if (lastChild && childData.children && childData.children.length > 0) {
            this.carregarFilhosRecursivo(childData, lastChild);
          }
        }
      });
    },

    /**
     * Escapa HTML para evitar XSS
     */
    escapeHtml(text) {
      if (!text) return '';
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    },

    /**
     * Manipula submit do formulário
     */
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
