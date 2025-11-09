# Testes Automatizados para CSAPP

Este diretório contém testes automatizados para o sistema CSAPP.

## Estrutura dos Testes

- `test_validation.py` - Testes para funções de validação (email, inteiro, data, etc.)
- `test_logging.py` - Testes para o sistema de logs e ContextFilter
- `test_auth.py` - Testes para o módulo de autenticação
- `test_api.py` - Testes para operações da API (tarefas, comentários)
- `test_management.py` - Testes para o módulo de gerenciamento de usuários
- `run_all_tests.py` - Script para executar todos os testes

## Executando os Testes

### Executar todos os testes:
```bash
python run_all_tests.py
```

### Executar testes específicos:
```bash
# Testes de validação
python -m pytest test_validation.py -v

# Testes de autenticação
python -m pytest test_auth.py -v

# Testes de API
python -m pytest test_api.py -v

# Testes de gerenciamento
python -m pytest test_management.py -v

# Testes de logging
python -m pytest test_logging.py -v
```

### Executar com cobertura:
```bash
python -m pytest --cov=../project --cov-report=html
```

## Requisitos

- Python 3.7+
- pytest
- pytest-cov (opcional, para cobertura)

## Instalação das dependências

```bash
pip install pytest pytest-cov
```

## Características dos Testes

### Testes de Validação
- Validação de email
- Validação de números inteiros
- Validação de datas
- Sanitização de strings

### Testes de Logging
- ContextFilter com e sem contexto Flask
- Configuração de níveis de log
- Criação de diretórios de log
- Integração com loggers específicos

### Testes de Autenticação
- Autenticação com usuário válido
- Autenticação sem usuário
- Requisitos de admin
- Verificação de permissões
- Logs de segurança

### Testes de API
- Operações de tarefas (toggle, exclusão)
- Operações de comentários (adicionar, excluir)
- Validações de entrada
- Logs de operações
- Logs de segurança

### Testes de Gerenciamento
- Listagem de usuários
- Atualização de perfis
- Exclusão de usuários
- Validações de segurança
- Logs de operações administrativas

## Exemplos de Uso

```python
# Exemplo de teste de validação
from test_validation import TestValidation

test = TestValidation()
test.test_validate_email_valid()  # Testa email válido
test.test_validate_email_invalid()  # Testa email inválido

# Exemplo de teste de logging
from test_logging import TestLoggingConfig

test = TestLoggingConfig()
test.test_context_filter_with_flask_context()  # Testa ContextFilter
```

## Notas Importantes

1. Os testes usam mocks para simular o banco de dados e o contexto Flask
2. Os logs são testados usando mocks para verificar as chamadas corretas
3. As validações testam tanto casos válidos quanto inválidos
4. Os testes de segurança verificam permissões e acessos negados

## Solução de Problemas

### Erro de importação
Se houver erros de importação, certifique-se de que:
1. O diretório CSAPP está no PYTHONPATH
2. Os módulos do projeto estão corretamente instalados
3. O arquivo `__init__.py` existe no diretório tests

### Erro de contexto Flask
Alguns testes requerem contexto Flask. Eles são automaticamente configurados com `test_request_context()`.

### Erro de banco de dados
Os testes usam mocks para o banco de dados. Se houver erros, verifique se os mocks estão corretamente configurados.