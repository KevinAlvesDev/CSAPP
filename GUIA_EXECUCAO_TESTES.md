# 📚 Guia de Execução de Testes - CSAPP

## 🎯 Objetivo

Este guia explica como executar, interpretar e manter a suíte de testes do projeto CSAPP.

---

## 🚀 Execução Rápida

### **Opção 1: Script Completo (Recomendado)**
```bash
python run_complete_tests.py
```

Este script:
- ✅ Verifica dependências (pytest, pytest-cov)
- ✅ Executa todos os testes
- ✅ Gera relatório detalhado
- ✅ Salva resultados em arquivo
- ✅ Mostra resumo visual

### **Opção 2: Pytest Direto**
```bash
# Todos os testes
python -m pytest tests/ -v

# Com coverage
python -m pytest tests/ --cov=backend/project --cov-report=html

# Apenas testes rápidos
python -m pytest tests/ -v --tb=short -x
```

---

## 📋 Testes por Categoria

### **1. Testes Unitários**
```bash
# Utilitários (23 testes)
python -m pytest tests/test_utils.py -v

# Paginação (14 testes)
python -m pytest tests/test_pagination.py -v

# Validação
python -m pytest tests/test_validation.py -v
```

### **2. Testes de Serviços**
```bash
# Dashboard
python -m pytest tests/test_dashboard_service.py -v

# Soft Delete
python -m pytest tests/test_soft_delete.py -v

# Performance (APM)
python -m pytest tests/test_performance.py -v

# Async Tasks
python -m pytest tests/test_async_tasks.py -v
```

### **3. Testes de API**
```bash
# API v1
python -m pytest tests/test_api_v1.py -v

# API geral
python -m pytest tests/test_api.py -v
```

### **4. Testes de Integração**
```bash
# End-to-end
python -m pytest tests/test_integration.py -v

# Autenticação
python -m pytest tests/test_auth.py -v

# Management
python -m pytest tests/test_management.py -v
```

---

## 🔍 Opções Úteis do Pytest

### **Verbosidade**
```bash
# Modo verbose (mostra cada teste)
pytest tests/ -v

# Modo muito verbose (mostra mais detalhes)
pytest tests/ -vv

# Modo quiet (apenas resumo)
pytest tests/ -q
```

### **Filtros**
```bash
# Executar apenas um teste específico
pytest tests/test_utils.py::TestFormatDateBr::test_format_date_br_with_datetime

# Executar testes que contêm "pagination" no nome
pytest tests/ -k pagination

# Executar apenas testes marcados (se houver markers)
pytest tests/ -m slow
```

### **Controle de Execução**
```bash
# Parar no primeiro erro
pytest tests/ -x

# Parar após N falhas
pytest tests/ --maxfail=3

# Executar testes em paralelo (requer pytest-xdist)
pytest tests/ -n auto
```

### **Output**
```bash
# Mostrar print() statements
pytest tests/ -s

# Traceback curto
pytest tests/ --tb=short

# Traceback longo
pytest tests/ --tb=long

# Sem traceback
pytest tests/ --tb=no
```

---

## 📊 Coverage (Cobertura de Código)

### **Gerar Relatório de Coverage**
```bash
# Terminal + HTML
python -m pytest tests/ \
    --cov=backend/project \
    --cov-report=term-missing \
    --cov-report=html

# Apenas HTML
python -m pytest tests/ \
    --cov=backend/project \
    --cov-report=html
```

### **Ver Relatório HTML**
```bash
# Windows
start htmlcov/index.html

# Mac
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html
```

### **Interpretar Coverage**
- **Verde (>80%)**: Boa cobertura ✅
- **Amarelo (50-80%)**: Cobertura média ⚠️
- **Vermelho (<50%)**: Baixa cobertura ❌

---

## 🎯 Interpretando Resultados

### **Teste Passou ✅**
```
tests/test_utils.py::TestFormatDateBr::test_format_date_br_with_datetime PASSED [100%]
```
- ✅ Teste executou sem erros
- ✅ Todas as assertions passaram

### **Teste Falhou ❌**
```
tests/test_utils.py::TestFormatDateBr::test_format_date_br_with_none FAILED [50%]

AssertionError: assert 'N/A' == ''
```
- ❌ Assertion falhou
- 📝 Mostra valor esperado vs valor real
- 🔍 Revisar lógica do teste ou código

### **Teste com Erro 💥**
```
ERROR tests/test_utils.py - ImportError: cannot import name 'calcular_progresso'
```
- 💥 Erro antes de executar o teste
- 🔍 Problema de import, sintaxe ou dependência

### **Teste Pulado ⏭️**
```
tests/test_utils.py::test_slow_function SKIPPED [75%]
```
- ⏭️ Teste marcado para pular (@pytest.mark.skip)
- ℹ️ Útil para testes em desenvolvimento

---

## 📈 Boas Práticas

### **Antes de Commitar**
```bash
# 1. Executar todos os testes
python -m pytest tests/ -v

# 2. Verificar coverage
python -m pytest tests/ --cov=backend/project --cov-report=term

# 3. Verificar se não há warnings
python -m pytest tests/ -v --strict-warnings
```

### **Durante Desenvolvimento**
```bash
# Executar apenas testes relacionados ao que você está mudando
python -m pytest tests/test_utils.py -v

# Modo watch (requer pytest-watch)
ptw tests/test_utils.py
```

### **Antes de Deploy**
```bash
# Executar suíte completa com coverage
python run_complete_tests.py

# Verificar relatório
start htmlcov/index.html

# Garantir 100% de sucesso
```

---

## 🐛 Debugging de Testes

### **Usar pdb (Python Debugger)**
```python
def test_minha_funcao():
    import pdb; pdb.set_trace()  # Breakpoint
    result = minha_funcao()
    assert result == expected
```

### **Executar com pdb automático**
```bash
# Para no primeiro erro
pytest tests/ --pdb

# Para em todos os erros
pytest tests/ --pdb --maxfail=999
```

### **Ver output completo**
```bash
# Mostra prints e logs
pytest tests/ -s -v
```

---

## 📝 Adicionando Novos Testes

### **Estrutura Básica**
```python
# tests/test_meu_modulo.py
import pytest
from project.meu_modulo import minha_funcao

class TestMinhaFuncao:
    """Testes para minha_funcao."""
    
    def test_caso_basico(self):
        """Testa caso básico."""
        result = minha_funcao(1, 2)
        assert result == 3
    
    def test_caso_edge(self):
        """Testa caso extremo."""
        result = minha_funcao(0, 0)
        assert result == 0
    
    def test_caso_erro(self):
        """Testa que erro é levantado."""
        with pytest.raises(ValueError):
            minha_funcao(-1, -1)
```

### **Fixtures**
```python
@pytest.fixture
def app():
    """Cria app para testes."""
    app = create_app()
    app.config['TESTING'] = True
    yield app
    # Cleanup aqui

def test_com_fixture(app):
    """Usa fixture."""
    assert app.config['TESTING'] is True
```

---

## 🎉 Checklist de Qualidade

Antes de considerar os testes completos:

- [ ] ✅ Todos os testes passam (100%)
- [ ] ✅ Coverage > 80% nos módulos críticos
- [ ] ✅ Testes de edge cases implementados
- [ ] ✅ Testes de erro implementados
- [ ] ✅ Testes de integração end-to-end
- [ ] ✅ Documentação dos testes atualizada
- [ ] ✅ Sem warnings no pytest
- [ ] ✅ Testes rápidos (< 5 minutos total)

---

## 🚀 Próximos Passos

1. ✅ Executar `python run_complete_tests.py`
2. ✅ Revisar relatório de coverage
3. ✅ Adicionar testes para áreas com baixa cobertura
4. ✅ Integrar testes no CI/CD
5. ✅ Configurar testes automáticos no GitHub Actions

---

**🎊 Com esta suíte de testes, o projeto CSAPP está completamente validado!** 🚀

