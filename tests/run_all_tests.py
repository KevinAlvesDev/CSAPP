import pytest
import sys
import os

# Adiciona o diretório CSAPP ao path do Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Importa todos os módulos de teste
from test_validation import TestValidation
from test_logging import TestLoggingConfig, TestLoggerIntegration
from test_auth import TestAuth, TestAuthLogging
from test_api import TestAPIValidation, TestAPITarefas, TestAPIComentarios, TestAPILogging
from test_management import TestManagement, TestManagementLogging

def run_all_tests():
    """Executa todos os testes"""
    print("Executando todos os testes...")
    
    # Configuração do pytest
    pytest_args = [
        '-v',  # Verbose
        '--tb=short',  # Traceback curto
        '--color=yes',  # Cores no output
        os.path.dirname(__file__)  # Diretório dos testes
    ]
    
    # Executa os testes
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ Todos os testes passaram!")
    else:
        print(f"\n❌ Alguns testes falharam. Código de saída: {exit_code}")
    
    return exit_code

if __name__ == '__main__':
    run_all_tests()