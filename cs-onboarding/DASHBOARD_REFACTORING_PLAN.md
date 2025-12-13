# 📋 Plano de Refatoração do Dashboard.html

## 🎯 Objetivo
Reduzir o arquivo de 1024 linhas (78 KB) para aproximadamente 300 linhas (20 KB)

## 📊 Análise Atual

### Estrutura do Arquivo
- **Linhas 1-47**: Header e filtros
- **Linhas 48-85**: Cards de métricas (DUPLICADO 7x)
- **Linhas 87-96**: Flash messages
- **Linhas 98-595**: Tabs com tabelas (MUITO DUPLICADO)
- **Linhas 599-731**: Modals (3 modals grandes)
- **Linhas 738-1024**: JavaScript inline (286 linhas!)

### Problemas Identificados
1. ❌ **Cards de métricas duplicados** - Mesmo HTML repetido 7 vezes
2. ❌ **Tabelas duplicadas** - Estrutura similar em cada tab
3. ❌ **Data attributes enormes** - 30+ attributes por link
4. ❌ **JavaScript inline** - 286 linhas de JS no template
5. ❌ **Modals inline** - Poderiam estar em arquivos separados

## ✅ Ações de Refatoração

### Fase 1: Usar Macros para Cards (PRONTO ✅)
**Arquivo**: `macros/cards.html`

**Antes** (linhas 50-84):
```html
<div class="card p-3 text-center">
    <h6 class="text-secondary">Novas</h6>
    <h4 class="mb-0 text-dark">{{ m.impl_novas | default(0) }}</h4>
    <div class="text-muted small">R$ {{ "%.2f"|format(...) }}</div>
</div>
<!-- Repetido 7 vezes -->
```

**Depois** (5 linhas):
```jinja
{% from 'macros/cards.html' import card_stats %}

<div class="metrics-grid mb-4">
    {{ card_stats('Novas', m.impl_novas|default(0), 'dark', 'bi-inbox', metrics.total_valor_novas) }}
    {{ card_stats('Em Andamento', m.impl_andamento_total|default(0), 'primary', 'bi-hourglass-split', metrics.total_valor_andamento) }}
    {{ card_stats('Paradas', m.impl_paradas|default(0), 'danger', 'bi-pause-circle', metrics.total_valor_paradas) }}
    {{ card_stats('Futuras', m.implantacoes_futuras|default(0), 'info', 'bi-calendar-event', metrics.total_valor_futuras) }}
    {{ card_stats('Sem previsão', m.implantacoes_sem_previsao|default(0), 'warning', 'bi-question-circle', metrics.total_valor_sem_previsao) }}
    {{ card_stats('Concluídas', m.impl_finalizadas|default(0), 'success', 'bi-check-circle', metrics.total_valor_finalizadas) }}
    {{ card_stats('Módulos', m.modulos_total|default(0), 'dark', 'bi-puzzle', metrics.total_valor_modulos) }}
</div>
```

**Economia**: 35 linhas → 9 linhas (74% redução)

### Fase 2: Criar Partial para Tabela de Implantações
**Arquivo**: `partials/_implantacoes_table.html`

**Criar componente reutilizável**:
```jinja
{# partials/_implantacoes_table.html #}
{% macro implantacoes_table(implantacoes, status, show_progress=false, show_actions=true) %}
<div class="table-responsive">
    <table class="table table-hover align-middle">
        <thead>
            <tr>
                <th>Empresa</th>
                <th>Implantador</th>
                <th>Tipo</th>
                {% if show_progress %}<th>Progresso</th>{% endif %}
                <th>Valor</th>
                {% if show_actions %}<th>Ações</th>{% endif %}
            </tr>
        </thead>
        <tbody>
            {% for impl in implantacoes %}
            {% include 'partials/_implantacao_row.html' %}
            {% endfor %}
        </tbody>
    </table>
</div>
{% endmacro %}
```

**Economia**: 150 linhas de tabelas → 30 linhas (80% redução)

### Fase 3: Extrair JavaScript para Arquivo Externo
**Arquivo**: `static/js/pages/dashboard.js`

**Mover todo JavaScript** (linhas 738-1024):
```javascript
// static/js/pages/dashboard.js

// Tab persistence
function initTabPersistence() {
    const tabs = document.querySelectorAll('#myTab .nav-link');
    const storageKey = 'tabAtiva-dashboard';
    
    tabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', event => {
            localStorage.setItem(storageKey, event.target.id);
        });
    });
    
    // Restore active tab
    const savedTab = localStorage.getItem(storageKey);
    if (savedTab) {
        const tabEl = document.getElementById(savedTab);
        if (tabEl) {
            new bootstrap.Tab(tabEl).show();
        }
    }
}

// Modal handlers
function initModals() {
    // Agendar modal
    const agendarModal = document.getElementById('agendarInicioModal');
    if (agendarModal) {
        agendarModal.addEventListener('show.bs.modal', handleAgendarModal);
    }
    
    // Detalhes empresa modal
    const detalhesModal = document.getElementById('modalDetalhesEmpresa');
    if (detalhesModal) {
        detalhesModal.addEventListener('show.bs.modal', handleDetalhesModal);
    }
}

// Consulta empresa
async function consultarEmpresa() {
    const idFavorecido = document.getElementById('idFavorecido').value;
    const feedback = document.getElementById('consultaFeedback');
    
    if (!idFavorecido) {
        feedback.innerHTML = '<span class="text-danger">Digite um ID Favorecido</span>';
        return;
    }
    
    try {
        const response = await fetch(`/api/consultar_empresa?id_favorecido=${idFavorecido}`);
        const data = await response.json();
        
        if (data.ok) {
            document.getElementById('nomeEmpresa').value = data.empresa.nomefantasia || '';
            feedback.innerHTML = '<span class="text-success">Empresa encontrada!</span>';
        } else {
            feedback.innerHTML = `<span class="text-warning">${data.error}</span>`;
        }
    } catch (error) {
        feedback.innerHTML = '<span class="text-danger">Erro ao consultar</span>';
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    initTabPersistence();
    initModals();
    
    // Bind consultar button
    const btnConsultar = document.getElementById('btnConsultarEmpresa');
    if (btnConsultar) {
        btnConsultar.addEventListener('click', consultarEmpresa);
    }
});
```

**Economia**: 286 linhas de JS inline → 1 linha de import

### Fase 4: Mover Modals para Arquivos Separados
**Arquivos**: 
- `modals/_nova_implantacao.html`
- `modals/_implantar_modulo.html`
- `modals/_agendar_inicio.html`

**No dashboard.html**:
```jinja
{% include 'modals/_nova_implantacao.html' %}
{% include 'modals/_implantar_modulo.html' %}
{% include 'modals/_agendar_inicio.html' %}
```

**Economia**: 130 linhas → 3 linhas (96% redução)

### Fase 5: Simplificar Data Attributes
**Criar função JS para carregar dados sob demanda**:

**Antes**:
```html
<a href="#" 
   data-id="{{ impl.id }}"
   data-nome="{{ impl.nome_empresa }}"
   data-responsavel="{{ impl.responsavel_cliente | default('') }}"
   data-cargo="{{ impl.cargo_responsavel | default('') }}"
   ... (30+ attributes)
>
```

**Depois**:
```html
<a href="#" 
   class="btn-edit-empresa"
   data-impl-id="{{ impl.id }}"
   onclick="loadImplDetails({{ impl.id }})">
```

**JavaScript**:
```javascript
async function loadImplDetails(implId) {
    const response = await fetch(`/api/v1/implantacoes/${implId}`);
    const data = await response.json();
    populateModal(data);
}
```

**Economia**: 30 linhas por item → 2 linhas (93% redução)

## 📈 Resultado Esperado

### Antes
```
dashboard.html: 1024 linhas (78 KB)
├── HTML: 738 linhas
├── JavaScript inline: 286 linhas
└── Modals inline: 130 linhas
```

### Depois
```
dashboard.html: ~250 linhas (18 KB)
├── HTML: 200 linhas (usando macros e includes)
├── JavaScript: 1 linha (import externo)
└── Modals: 3 linhas (includes)

static/js/pages/dashboard.js: 300 linhas (novo)
modals/_nova_implantacao.html: 40 linhas (novo)
modals/_implantar_modulo.html: 45 linhas (novo)
modals/_agendar_inicio.html: 45 linhas (novo)
partials/_implantacoes_table.html: 50 linhas (novo)
```

### Benefícios
- ✅ **75% redução** no tamanho do dashboard.html
- ✅ **Código reutilizável** (macros e partials)
- ✅ **JavaScript separado** (fácil debugar e minificar)
- ✅ **Modals organizados** (fácil manter)
- ✅ **Performance melhorada** (cache de JS/CSS)
- ✅ **Manutenção facilitada** (mudanças em um lugar)

## 🚀 Próximos Passos

1. ✅ Macros criadas (cards, forms, buttons)
2. ⏳ Criar `static/js/pages/dashboard.js`
3. ⏳ Criar partials de tabelas
4. ⏳ Mover modals para arquivos separados
5. ⏳ Refatorar dashboard.html usando componentes
6. ⏳ Testar funcionalidade
7. ⏳ Aplicar mesmo padrão em `implantacao_detalhes.html`

---

**Status**: Preparação completa ✅  
**Próxima ação**: Criar arquivos JavaScript e partials
