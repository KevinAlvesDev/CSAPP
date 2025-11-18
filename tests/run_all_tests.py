import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# Garantir que o pacote 'project' (backend) esteja no PYTHONPATH
BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
os.environ.setdefault('PYTHONPATH', 'backend')

from test_validation import TestValidation
from test_logging import TestLoggingConfig, TestLoggerIntegration
from test_auth import TestAuth, TestAuthLogging
from test_api import TestAPIValidation, TestAPITarefas, TestAPIComentarios, TestAPILogging
from test_management import TestManagement, TestManagementLogging

def run_all_tests():
    """Executa todos os testes"""
    print("Executando todos os testes...")

    pytest_args = [
        '-v',\
        '--tb=short',\
        '--color=yes',\
        os.path.dirname(__file__)\
    ]

    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ Todos os testes passaram!")
    else:
        print(f"\n❌ Alguns testes falharam. Código de saída: {exit_code}")
    
    return exit_code

if __name__ == '__main__':
    run_all_tests()