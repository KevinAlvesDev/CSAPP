# 🛡️ Guia de Fortalecimento e Qualidade do Projeto

## 📋 Índice

1. [Novos Recursos Implementados](#novos-recursos-implementados)
2. [Checklist de Qualidade](#checklist-de-qualidade)
3. [Padrões de Código](#padrões-de-código)
4. [Tratamento de Erros](#tratamento-de-erros)
5. [Validação de Dados](#validação-de-dados)
6. [Logging e Monitoramento](#logging-e-monitoramento)
7. [Segurança](#segurança)
8. [Performance](#performance)
9. [Testes](#testes)

---

## 🆕 Novos Recursos Implementados

### 1. Sistema de Tratamento de Erros (`common/error_handlers.py`)

**Decorators disponíveis:**

```python
from ..common.error_handlers import handle_api_errors, handle_view_errors, require_fields

# Para endpoints de API (retorna JSON)
@handle_api_errors
def minha_api():
    ...

# Para views HTML (redireciona com flash)
@handle_view_errors
def minha_view():
    ...

# Validar campos obrigatórios em JSON
@require_fields('nome', 'email')
def criar_usuario():
    ...
```

**Benefícios:**
- ✅ Respostas de erro padronizadas
- ✅ Logs automáticos de exceções
- ✅ Mensagens amigáveis para usuários
- ✅ Debug info em desenvolvimento

### 2. Validadores de Dados (`common/validators.py`)

**Classe DataValidator com métodos:**

```python
from ..common.validators import DataValidator

# Validar email
email = DataValidator.validate_email("user@example.com")

# Validar CNPJ
cnpj = DataValidator.validate_cnpj("12.345.678/0001-90")

# Validar telefone
phone = DataValidator.validate_phone("(11) 98765-4321")

# Validar data
date = DataValidator.validate_date("2024-01-15")

# Validar inteiro com range
idade = DataValidator.validate_integer(25, min_value=0, max_value=150)

# Validar string com tamanho
nome = DataValidator.validate_string("João", min_length=2, max_length=100)

# Validar escolha
status = DataValidator.validate_choice("ativo", ['ativo', 'inativo'])

# Sanitizar HTML
texto_limpo = DataValidator.sanitize_html(texto_usuario)
```

**Benefícios:**
- ✅ Validações consistentes em todo o projeto
- ✅ Mensagens de erro claras
- ✅ Formatação automática (CNPJ, telefone)
- ✅ Proteção contra XSS

### 3. Logging Estruturado (`common/structured_logging.py`)

**StructuredLogger:**

```python
from ..common.structured_logging import StructuredLogger, audit_logger

logger = StructuredLogger('meu_modulo')

# Logs com contexto automático (user, IP, request_id)
logger.info("Operação realizada", extra_field="valor")
logger.warning("Atenção necessária")
logger.error("Erro ocorreu", exc_info=True)

# Auditoria de ações
audit_logger.log_user_action(
    action='create',
    resource_type='implantacao',
    resource_id=123,
    details={'nome': 'Academia XYZ'}
)

# Log de permissões
audit_logger.log_permission_check(
    resource_type='implantacao',
    resource_id=123,
    required_permission='edit',
    granted=True
)
```

**Decorators de logging:**

```python
from ..common.structured_logging import log_function_call, log_database_query

# Logar entrada/saída de funções
@log_function_call()
def processar_dados():
    ...

# Logar queries de banco
@log_database_query("SELECT")
def buscar_usuarios():
    ...

# Logar chamadas externas
@log_external_api_call("OAMD")
def consultar_oamd():
    ...
```

---

## ✅ Checklist de Qualidade

### Antes de Commitar Código

- [ ] **Código compila sem erros**
  ```bash
  python -m py_compile arquivo.py
  ```

- [ ] **Validações implementadas**
  - [ ] Todos os inputs de usuário são validados
  - [ ] Tipos de dados verificados
  - [ ] Ranges de valores validados

- [ ] **Tratamento de erros**
  - [ ] Try/except em operações que podem falhar
  - [ ] Mensagens de erro amigáveis
  - [ ] Logs de erros implementados

- [ ] **Segurança**
  - [ ] SQL injection prevenido (queries parametrizadas)
  - [ ] XSS prevenido (sanitização de HTML)
  - [ ] CSRF tokens em formulários
  - [ ] Autenticação/autorização verificada

- [ ] **Performance**
  - [ ] Queries otimizadas (índices, JOINs eficientes)
  - [ ] Paginação implementada em listas
  - [ ] Cache usado quando apropriado

- [ ] **Logging**
  - [ ] Ações críticas logadas
  - [ ] Erros logados com contexto
  - [ ] Logs estruturados

- [ ] **Documentação**
  - [ ] Docstrings em funções públicas
  - [ ] Comentários em lógica complexa
  - [ ] README atualizado se necessário

---

## 📝 Padrões de Código

### 1. Estrutura de Função de Serviço

```python
def minha_funcao_service(param1, param2, user_email=None):
    """
    Descrição clara do que a função faz.
    
    Args:
        param1: Descrição do parâmetro
        param2: Descrição do parâmetro
        user_email: Email do usuário (opcional)
        
    Returns:
        dict: Descrição do retorno
        
    Raises:
        ValueError: Quando validação falha
        PermissionError: Quando sem permissão
    """
    # 1. Validações de entrada
    param1 = DataValidator.validate_string(param1, max_length=100)
    param2 = DataValidator.validate_integer(param2, min_value=1)
    
    # 2. Verificações de permissão
    if not tem_permissao(user_email):
        raise PermissionError("Sem permissão para esta operação")
    
    # 3. Lógica de negócio
    try:
        resultado = processar(param1, param2)
        
        # 4. Auditoria
        audit_logger.log_user_action(
            action='process',
            resource_type='recurso',
            details={'param1': param1}
        )
        
        return {'ok': True, 'data': resultado}
        
    except Exception as e:
        logger.error(f"Erro ao processar: {e}", exc_info=True)
        raise
```

### 2. Estrutura de Endpoint de API

```python
@api_bp.route('/recurso', methods=['POST'])
@login_required
@limiter.limit("60 per minute")
@handle_api_errors
@require_fields('campo1', 'campo2')
def criar_recurso():
    """Cria um novo recurso."""
    data = request.get_json()
    
    # Validar dados
    campo1 = DataValidator.validate_string(data['campo1'])
    campo2 = DataValidator.validate_integer(data['campo2'])
    
    # Chamar serviço
    result = criar_recurso_service(
        campo1=campo1,
        campo2=campo2,
        user_email=g.user_email
    )
    
    return jsonify(result), 201
```

### 3. Estrutura de View HTML

```python
@main_bp.route('/pagina')
@login_required
@handle_view_errors
def minha_pagina():
    """Renderiza página."""
    # Buscar dados
    dados = buscar_dados_service(g.user_email)
    
    # Renderizar
    return render_template('pagina.html', dados=dados)
```

---

## 🚨 Tratamento de Erros

### Hierarquia de Exceções

```python
# Usar exceções específicas
ValueError          # Validação de dados
PermissionError     # Sem permissão
FileNotFoundError   # Recurso não encontrado
ConnectionError     # Erro de conexão
TimeoutError        # Timeout
Exception           # Erro genérico (último recurso)
```

### Boas Práticas

```python
# ✅ BOM
try:
    resultado = operacao_arriscada()
except ValueError as e:
    logger.warning(f"Validação falhou: {e}")
    raise
except ConnectionError as e:
    logger.error(f"Erro de conexão: {e}", exc_info=True)
    # Tentar fallback
    resultado = fallback_operation()

# ❌ RUIM
try:
    resultado = operacao_arriscada()
except:  # Nunca usar except genérico sem especificar
    pass  # Nunca silenciar erros
```

---

## ✔️ Validação de Dados

### Sempre Validar

1. **Entrada de usuário** (formulários, APIs)
2. **Dados de APIs externas**
3. **Dados de arquivos**
4. **Parâmetros de URL**

### Exemplo Completo

```python
def processar_implantacao(data):
    """Processa dados de implantação com validação completa."""
    
    # Validar campos obrigatórios
    nome = DataValidator.validate_string(
        data.get('nome'),
        min_length=3,
        max_length=200,
        required=True
    )
    
    # Validar CNPJ (opcional)
    cnpj = DataValidator.validate_cnpj(
        data.get('cnpj'),
        required=False
    )
    
    # Validar email
    email = DataValidator.validate_email(
        data.get('email'),
        required=True
    )
    
    # Validar data
    data_inicio = DataValidator.validate_date(
        data.get('data_inicio'),
        required=False
    )
    
    # Validar escolha
    status = DataValidator.validate_choice(
        data.get('status'),
        choices=['nova', 'andamento', 'finalizada'],
        required=True
    )
    
    return {
        'nome': nome,
        'cnpj': cnpj,
        'email': email,
        'data_inicio': data_inicio,
        'status': status
    }
```

---

## 📊 Logging e Monitoramento

### Níveis de Log

- **DEBUG**: Informações detalhadas para debugging
- **INFO**: Eventos normais (login, criação de recurso)
- **WARNING**: Situações incomuns mas não erros
- **ERROR**: Erros que precisam atenção
- **CRITICAL**: Falhas graves do sistema

### O Que Logar

```python
# ✅ Logar
- Ações de usuário (criar, editar, deletar)
- Erros e exceções
- Chamadas a APIs externas
- Queries lentas (> 1s)
- Tentativas de acesso não autorizado
- Mudanças em dados críticos

# ❌ Não Logar
- Senhas
- Tokens de autenticação
- Dados sensíveis (CPF, cartão de crédito)
- Informações pessoais desnecessárias
```

---

## 🔒 Segurança

### Checklist de Segurança

- [ ] **SQL Injection**
  ```python
  # ✅ BOM - Queries parametrizadas
  query_db("SELECT * FROM users WHERE email = %s", (email,))
  
  # ❌ RUIM - String concatenation
  query_db(f"SELECT * FROM users WHERE email = '{email}'")
  ```

- [ ] **XSS (Cross-Site Scripting)**
  ```python
  # ✅ BOM - Sanitizar HTML
  texto_limpo = DataValidator.sanitize_html(user_input)
  
  # Templates Jinja escapam automaticamente
  {{ user_input }}  # Seguro
  {{ user_input | safe }}  # Perigoso! Só use se confiável
  ```

- [ ] **CSRF**
  ```html
  <!-- ✅ BOM - Token CSRF em formulários -->
  <form method="POST">
    {{ csrf_token() }}
    ...
  </form>
  ```

- [ ] **Autenticação**
  ```python
  # ✅ BOM - Sempre verificar
  @login_required
  def rota_protegida():
      ...
  ```

- [ ] **Autorização**
  ```python
  # ✅ BOM - Verificar permissões
  if g.perfil.get('perfil_acesso') not in PERFIS_COM_GESTAO:
      raise PermissionError("Sem permissão")
  ```

---

## ⚡ Performance

### Otimizações

1. **Paginação**
   ```python
   # ✅ BOM
   @validate_pagination(max_per_page=100)
   def listar():
       page = request.validated_page
       per_page = request.validated_per_page
       ...
   ```

2. **Cache**
   ```python
   from ..config.cache_config import cache
   
   @cache.cached(timeout=600, key_prefix='lista_usuarios')
   def listar_usuarios():
       ...
   ```

3. **Índices no Banco**
   ```sql
   CREATE INDEX idx_implantacoes_status ON implantacoes(status);
   CREATE INDEX idx_implantacoes_usuario ON implantacoes(usuario_cs);
   ```

4. **Queries Eficientes**
   ```python
   # ✅ BOM - Uma query com JOIN
   SELECT i.*, p.nome FROM implantacoes i 
   LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
   
   # ❌ RUIM - N+1 queries
   for impl in implantacoes:
       perfil = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (impl.usuario_cs,))
   ```

---

## 🧪 Testes

### Estrutura de Teste

```python
import pytest
from ..domain.meu_service import minha_funcao

def test_minha_funcao_sucesso():
    """Testa caso de sucesso."""
    result = minha_funcao(param1="valor", param2=123)
    assert result['ok'] == True
    assert 'data' in result

def test_minha_funcao_validacao_falha():
    """Testa validação de entrada."""
    with pytest.raises(ValueError):
        minha_funcao(param1="", param2=-1)

def test_minha_funcao_sem_permissao():
    """Testa verificação de permissão."""
    with pytest.raises(PermissionError):
        minha_funcao(param1="valor", user_email="sem_permissao@test.com")
```

---

## 📚 Recursos Adicionais

### Arquivos Criados

1. `backend/project/common/error_handlers.py` - Tratamento de erros
2. `backend/project/common/validators.py` - Validação de dados
3. `backend/project/common/structured_logging.py` - Logging estruturado

### Como Usar

```python
# Em qualquer serviço ou endpoint
from ..common.error_handlers import handle_api_errors
from ..common.validators import DataValidator
from ..common.structured_logging import StructuredLogger, audit_logger

logger = StructuredLogger(__name__)

@handle_api_errors
def minha_funcao(data):
    # Validar
    email = DataValidator.validate_email(data['email'])
    
    # Processar
    resultado = processar(email)
    
    # Auditar
    audit_logger.log_user_action('process', 'email', email)
    
    # Logar
    logger.info("Processamento concluído", email=email)
    
    return {'ok': True, 'resultado': resultado}
```

---

**Última atualização**: 2024-12-12  
**Versão**: 1.0

