# 📚 GUIA DE USO - NOVAS FUNCIONALIDADES

**Projeto:** CSAPP (CS Onboarding Platform)  
**Data:** 13 de Janeiro de 2025

---

## 🚀 INSTALAÇÃO E CONFIGURAÇÃO

### 1. Instalar Novas Dependências

```bash
pip install -r requirements.txt
```

**Novas dependências adicionadas:**
- `Flask-Compress==1.15` - Compressão de respostas
- (Outras já instaladas no round 1)

---

### 2. Executar Migrations

```bash
# Aplicar todas as migrations
python -m alembic upgrade head

# Verificar status
python -m alembic current

# Ver histórico
python -m alembic history
```

**Migrations criadas:**
- `002_add_performance_indexes.py` - Índices de performance
- `003_add_soft_delete.py` - Suporte a soft delete

---

## 📊 NOVAS FUNCIONALIDADES

### 1. **Paginação no Dashboard**

#### Como usar no código:

```python
from project.pagination import Pagination, get_page_args

# Em uma rota:
@app.route('/dashboard')
def dashboard():
    page, per_page = get_page_args()  # Extrai page e per_page da URL
    
    # Chama serviço com paginação
    data, pagination = get_dashboard_data(
        user_email=g.user_email,
        page=page,
        per_page=per_page
    )
    
    return render_template('dashboard.html', 
                         data=data, 
                         pagination=pagination)
```

#### Como usar no template:

```html
<!-- Inclui o componente de paginação -->
{% include 'partials/_pagination.html' %}
```

#### Como usar na URL:

```
http://localhost:5000/dashboard?page=2&per_page=50
```

---

### 2. **Soft Delete (Exclusão Lógica)**

#### Como usar:

```python
from project.soft_delete import soft_delete, restore, get_deleted_records, hard_delete

# Excluir (soft) - pode ser restaurado
soft_delete('implantacoes', 123)

# Restaurar
restore('implantacoes', 123)

# Listar registros excluídos
deleted = get_deleted_records('implantacoes', limit=100)

# Excluir permanentemente (CUIDADO!)
hard_delete('implantacoes', 123)  # IRREVERSÍVEL!

# Limpar registros antigos (excluídos há mais de 30 dias)
from project.soft_delete import cleanup_old_deleted_records
cleanup_old_deleted_records('implantacoes', days=30)
```

#### Filtrar registros não excluídos em queries:

```python
from project.soft_delete import exclude_deleted

# Adiciona filtro automaticamente
query = "SELECT * FROM implantacoes WHERE usuario_cs = %s"
query = exclude_deleted(query)
# Resultado: "SELECT * FROM implantacoes WHERE usuario_cs = %s AND deleted_at IS NULL"
```

---

### 3. **Tarefas Assíncronas (Email, Notificações)**

#### Como usar:

```python
from project.async_tasks import send_email_async, send_notification_async, BackgroundTask

# Enviar email assíncrono
send_email_async(
    subject='Novo comentário',
    body_html='<p>Você tem um novo comentário!</p>',
    recipients=['user@example.com'],
    reply_to='cs@example.com',
    from_name='CS Team'
)

# Executar qualquer função em background
def my_slow_function(arg1, arg2):
    # Faz algo demorado...
    pass

BackgroundTask.run_with_app_context(my_slow_function, arg1='value1', arg2='value2')
```

---

### 4. **API Versionada (v1)**

#### Endpoints disponíveis:

```bash
# Health check
GET /api/v1/health

# Listar implantações (com paginação)
GET /api/v1/implantacoes?page=1&per_page=50&status=andamento

# Detalhes de uma implantação
GET /api/v1/implantacoes/123
```

#### Exemplo de uso com JavaScript:

```javascript
// Listar implantações
fetch('/api/v1/implantacoes?page=1&per_page=50')
    .then(res => res.json())
    .then(data => {
        console.log('Implantações:', data.data);
        console.log('Paginação:', data.pagination);
    });

// Detalhes de implantação
fetch('/api/v1/implantacoes/123')
    .then(res => res.json())
    .then(data => {
        console.log('Implantação:', data.data.implantacao);
        console.log('Tarefas:', data.data.tarefas);
    });
```

---

### 5. **Monitoramento de Performance (APM)**

#### Visualizar métricas:

```bash
# Acesse (apenas como admin):
http://localhost:5000/admin/metrics
```

#### Resposta JSON:

```json
{
    "total_requests": 1000,
    "recent_metrics": [...],
    "summary": {
        "total_requests": 1000,
        "avg_duration_ms": 45.2,
        "max_duration_ms": 1250.5,
        "min_duration_ms": 5.1,
        "avg_queries_per_request": 3.5,
        "total_queries": 3500,
        "slow_requests": 12,
        "error_requests": 5
    }
}
```

#### Monitorar funções específicas:

```python
from project.performance_monitoring import monitor_function

@monitor_function
def my_slow_function():
    # Se demorar > 500ms, será logado automaticamente
    pass
```

---

### 6. **Testes de Integração**

#### Executar testes:

```bash
# Executar todos os testes
pytest tests/test_integration.py -v

# Executar teste específico
pytest tests/test_integration.py::TestImplantacaoFlowIntegration::test_criar_implantacao_completo -v

# Com coverage
pytest tests/test_integration.py --cov=backend/project --cov-report=html
```

---

## 🔧 CONFIGURAÇÕES

### Compressão de Respostas

Configurado automaticamente em `backend/project/__init__.py`:

```python
app.config['COMPRESS_LEVEL'] = 6  # Nível de compressão (1-9)
app.config['COMPRESS_MIN_SIZE'] = 500  # Comprime apenas > 500 bytes
```

### Rate Limiting

Limites configurados por endpoint:

- `/api/toggle_tarefa` - 100 por minuto
- `/api/adicionar_comentario` - 20 por minuto
- `/excluir_comentario` - 30 por minuto
- `/excluir_tarefa` - 50 por minuto
- `/login` - 30 por minuto

---

## 📊 MONITORAMENTO

### Logs de Performance

Requests lentos (> 1 segundo) são automaticamente logados:

```
WARNING: Slow request: GET /dashboard took 1.25s (15 queries)
```

### Métricas Coletadas

- ✅ Tempo de resposta por endpoint
- ✅ Número de queries por request
- ✅ Cache hits/misses
- ✅ Erros e exceções
- ✅ Usuário que fez a request

---

## 🎯 BOAS PRÁTICAS

### 1. Sempre use paginação em listagens grandes

```python
# ❌ NÃO FAÇA:
all_data = query_db("SELECT * FROM implantacoes")

# ✅ FAÇA:
page, per_page = get_page_args()
data, pagination = get_dashboard_data(user_email, page=page, per_page=per_page)
```

### 2. Use soft delete em vez de DELETE físico

```python
# ❌ NÃO FAÇA:
execute_db("DELETE FROM implantacoes WHERE id = %s", (impl_id,))

# ✅ FAÇA:
soft_delete('implantacoes', impl_id)
```

### 3. Use tarefas assíncronas para operações lentas

```python
# ❌ NÃO FAÇA (bloqueante):
send_email(subject, body, recipients)  # Usuário espera 2-5s

# ✅ FAÇA (assíncrono):
send_email_async(subject, body, recipients)  # Retorna imediatamente
```

---

## 🚨 TROUBLESHOOTING

### Problema: Migrations não aplicam

```bash
# Verificar status
python -m alembic current

# Forçar upgrade
python -m alembic upgrade head

# Se falhar, verificar logs
python -m alembic upgrade head --sql  # Mostra SQL sem executar
```

### Problema: Métricas não aparecem

Certifique-se de estar logado como admin:

```python
# Verificar perfil
SELECT perfil_acesso FROM perfil_usuario WHERE usuario = 'seu@email.com';
# Deve retornar 'Admin'
```

---

## 📝 CHANGELOG

**v2.0.0** (13/01/2025)
- ✅ Resolvido problema N+1 em queries
- ✅ Implementada paginação
- ✅ Email assíncrono
- ✅ 7 índices de performance
- ✅ Rate limiting granular
- ✅ Testes de integração
- ✅ Soft delete
- ✅ Compressão de respostas
- ✅ API versioning (v1)
- ✅ APM básico

---

**Dúvidas?** Consulte os arquivos de documentação:
- `MELHORIAS_ROUND_2_IMPLEMENTADAS.md` - Detalhes técnicos
- `PROXIMAS_MELHORIAS.md` - Melhorias futuras

