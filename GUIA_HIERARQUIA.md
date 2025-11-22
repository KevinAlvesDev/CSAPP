# Guia de Atualização para Modelo Hierárquico

## Status Atual

✅ **Concluído:**
1. Estrutura hierárquica criada no banco de dados (fases, grupos, tarefas_h, subtarefas_h)
2. Dados migrados para todas as 20 implantações
3. Serviço `hierarquia_service.py` criado com funções para manipular hierarquia
4. Tabela `comentarios_h` criada
5. Rotas de API implementadas (`toggle_subtarefa_h`)
6. Frontend atualizado para exibir hierarquia de 4 níveis
7. Integração completa backend-frontend realizada

## Próximos Passos

### 1. Atualizar Backend - API Routes

Criar/atualizar rotas em `backend/project/blueprints/api.py`:

```python
from project.dominio.hierarquia_service import (
    toggle_subtarefa,
    calcular_progresso_implantacao,
    adicionar_comentario_tarefa,
    get_comentarios_tarefa
)

@api_bp.route('/toggle_subtarefa_h/<int:subtarefa_id>', methods=['POST'])
@login_required
def toggle_subtarefa_h(subtarefa_id):
    """Alterna o estado de uma subtarefa hierárquica"""
    resultado = toggle_subtarefa(subtarefa_id)
    
    if not resultado['ok']:
        return jsonify({'error': resultado.get('error')}), 400
    
    # Buscar implantacao_id para calcular progresso geral
    subtarefa = query_db(
        """
        SELECT f.implantacao_id
        FROM subtarefas_h st
        JOIN tarefas_h t ON t.id = st.tarefa_id
        JOIN grupos g ON g.id = t.grupo_id
        JOIN fases f ON f.id = g.fase_id
        WHERE st.id = %s
        """,
        (subtarefa_id,),
        one=True
    )
    
    if subtarefa:
        novo_progresso = calcular_progresso_implantacao(subtarefa['implantacao_id'])
        
        # Retornar HTML atualizado via HTMX
        return render_template(
            'partials/_subtarefa_item.html',
            subtarefa={'id': subtarefa_id, 'concluido': resultado['concluido']},
            progresso=novo_progresso
        )
    
    return jsonify(resultado)
```

### 2. Atualizar Frontend - Templates

Criar template `frontend/templates/partials/_hierarquia_completa.html`:

```html
<!-- Renderizar Fases -->
{% for fase in hierarquia.fases %}
<div class="fase-container mb-4">
    <h3 class="fase-titulo">{{ fase.nome }}</h3>
    
    <!-- Renderizar Grupos -->
    {% for grupo in fase.grupos %}
    <div class="grupo-container mb-3">
        <h4 class="grupo-titulo">{{ grupo.nome }}</h4>
        
        <!-- Renderizar Tarefas -->
        {% for tarefa in grupo.tarefas %}
        <div class="tarefa-container mb-2">
            <div class="tarefa-header">
                <strong>{{ tarefa.nome }}</strong>
                <span class="badge bg-{{ 'success' if tarefa.status == 'concluida' else 'warning' }}">
                    {{ tarefa.percentual_conclusao }}%
                </span>
            </div>
            
            <!-- Renderizar Subtarefas -->
            {% if tarefa.subtarefas %}
            <ul class="subtarefas-list">
                {% for subtarefa in tarefa.subtarefas %}
                <li class="subtarefa-item">
                    <input 
                        type="checkbox" 
                        {% if subtarefa.concluido %}checked{% endif %}
                        hx-post="/api/toggle_subtarefa_h/{{ subtarefa.id }}"
                        hx-target="#subtarefa-{{ subtarefa.id }}"
                        hx-swap="outerHTML"
                    >
                    <span id="subtarefa-{{ subtarefa.id }}">{{ subtarefa.nome }}</span>
                </li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endfor %}
</div>
{% endfor %}
```

### 3. Atualizar JavaScript

Atualizar `frontend/static/js/implantacao_detalhes.js`:

```javascript
// Adicionar listener para subtarefas hierárquicas
document.body.addEventListener('htmx:afterSwap', function(event) {
    const target = event.detail.target;
    
    // Atualizar progresso quando subtarefa é alterada
    if (target && target.id && target.id.startsWith('subtarefa-')) {
        // Progresso é atualizado via OOB swap
        console.log('Subtarefa atualizada');
    }
});
```

### 4. Integrar Hierarquia no implantacao_service.py

Substituir a função `_get_tarefas_and_comentarios` por:

```python
from project.dominio.hierarquia_service import get_hierarquia_implantacao

def _get_hierarquia_completa(impl_id):
    """Retorna a hierarquia completa da implantação"""
    return get_hierarquia_implantacao(impl_id)
```

E atualizar `get_implantacao_details` para retornar:

```python
return {
    'user_info': g.user,
    'implantacao': implantacao,
    'hierarquia': _get_hierarquia_completa(impl_id),  # Nova estrutura
    'progresso_porcentagem': progresso,
    # ... outros campos
}
```

## Arquivos que Precisam ser Atualizados

1. ✅ `backend/project/dominio/hierarquia_service.py` - CRIADO
2. ✅ `backend/project/blueprints/api.py` - ADICIONADO rotas para hierarquia
3. ✅ `backend/project/domain/implantacao_service.py` - SIMPLIFICADO para usar hierarquia
4. ✅ `frontend/templates/implantacao_detalhes.html` - ATUALIZADO para renderizar hierarquia
5. ✅ `frontend/templates/partials/_hierarquia_completa.html` - CRIADO
6. ✅ `frontend/static/js/implantacao_detalhes.js` - ATUALIZADO com suporte a subtarefas

## Comandos Úteis

### Verificar Dados no Banco
```sql
-- Ver estatísticas
SELECT 
    'Fases' as item, COUNT(*) as total FROM fases
UNION ALL
SELECT 'Grupos', COUNT(*) FROM grupos
UNION ALL
SELECT 'Tarefas', COUNT(*) FROM tarefas_h
UNION ALL
SELECT 'Subtarefas', COUNT(*) FROM subtarefas_h;

-- Ver hierarquia de uma implantação
SELECT 
    f.nome as fase,
    g.nome as grupo,
    t.nome as tarefa,
    COUNT(st.id) as subtarefas
FROM fases f
LEFT JOIN grupos g ON g.fase_id = f.id
LEFT JOIN tarefas_h t ON t.grupo_id = g.id
LEFT JOIN subtarefas_h st ON st.tarefa_id = t.id
WHERE f.implantacao_id = 1
GROUP BY f.id, g.id, t.id
ORDER BY f.ordem, g.id, t.ordem;
```

### Recriar Estrutura para Uma Implantação
```bash
.\.venv\Scripts\python.exe -c "from project import create_app; from scripts.popular_estrutura_hierarquica import popular_estrutura_hierarquica; app = create_app(); ctx = app.app_context(); ctx.push(); popular_estrutura_hierarquica(1); ctx.pop()"
```

## Notas Importantes

1. **Modelo Legado**: A tabela `tarefas` ainda existe e pode ser usada para "Obrigações para finalização" e "Pendências"
2. **Comentários**: Comentários agora devem usar `comentarios_h` que referencia `tarefas_h`
3. **Progresso**: O cálculo de progresso agora é baseado em subtarefas concluídas
4. **Performance**: Índices foram criados para otimizar queries hierárquicas

## Resultado Esperado

Após a atualização completa, a UI deve exibir:

```
📁 Welcome
  📂 Boas-vindas
    ✓ Contato Inicial Whatsapp/Grupo
    ✓ Reunião de Welcome

📁 Estruturação BD
  📂 Configuração Inicial
    📝 Criar Banco de Dados
    📝 Vincular a tela de apoio
  📂 Configurações Financeiras
    📝 Convênio de cobrança (33%)
      ☐ Cadastro do convênio de cobrança
      ✓ Convênio padrão no link de pagamento
      ☐ Inclusão de convênio no vendas online
```

Com checkboxes funcionais e progresso atualizado em tempo real!
