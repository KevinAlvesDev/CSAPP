"""
Script de Validação de Segurança
Verifica vulnerabilidades comuns no código
"""

import os
import re
import sys
from pathlib import Path

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def check_sql_injection(backend_path):
    """Verifica possíveis SQL injections"""
    print_header("VERIFICANDO SQL INJECTION")
    
    issues = []
    
    # Padrões perigosos
    patterns = [
        (r'execute_db\(f"', 'execute_db com f-string'),
        (r'query_db\(f"', 'query_db com f-string'),
        (r'\.format\(.*WHERE', 'string.format() em query SQL'),
        (r'%\s*%', 'string interpolation % em SQL'),
    ]
    
    for py_file in Path(backend_path).rglob('*.py'):
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for pattern, desc in patterns:
                if re.search(pattern, content):
                    issues.append(f"{py_file.name}: {desc}")
    
    if issues:
        for issue in issues:
            print_error(issue)
        return False
    else:
        print_success("Nenhuma vulnerabilidade de SQL injection encontrada")
        return True

def check_hardcoded_secrets(backend_path):
    """Verifica secrets hardcoded"""
    print_header("VERIFICANDO SECRETS HARDCODED")
    
    issues = []
    
    # Padrões suspeitos
    patterns = [
        (r'password\s*=\s*["\'][^"\']+["\']', 'Password hardcoded'),
        (r'api_key\s*=\s*["\'][^"\']+["\']', 'API key hardcoded'),
        (r'secret\s*=\s*["\'][^"\']+["\']', 'Secret hardcoded'),
        (r'token\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', 'Token hardcoded'),
    ]
    
    exclude_files = ['config.py', 'constants.py', 'test_']
    
    for py_file in Path(backend_path).rglob('*.py'):
        if any(ex in py_file.name for ex in exclude_files):
            continue
            
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                for pattern, desc in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        if 'os.environ' not in line and 'config.get' not in line:
                            issues.append(f"{py_file.name}:{i} - {desc}")
    
    if issues:
        for issue in issues:
            print_warning(issue)
        return False
    else:
        print_success("Nenhum secret hardcoded encontrado")
        return True

def check_permission_decorators(backend_path):
    """Verifica se rotas sensíveis têm decorators de permissão"""
    print_header("VERIFICANDO DECORATORS DE PERMISSÃO")
    
    issues = []
    
    # Rotas que devem ter proteção
    sensitive_routes = ['delete', 'update', 'create', 'admin', 'manage']
    
    for py_file in Path(backend_path / 'project' / 'blueprints').glob('*.py'):
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if '@' in line and '.route(' in line:
                    # Verificar se é rota sensível
                    route_line = line
                    if any(sens in route_line.lower() for sens in sensitive_routes):
                        # Verificar se tem decorator de proteção nas linhas anteriores
                        prev_lines = '\n'.join(lines[max(0, i-5):i])
                        if not any(dec in prev_lines for dec in ['@login_required', '@permission_required', '@admin_required']):
                            issues.append(f"{py_file.name}:{i+1} - Rota sensível sem proteção: {route_line.strip()}")
    
    if issues:
        for issue in issues:
            print_warning(issue)
        return False
    else:
        print_success("Todas as rotas sensíveis têm decorators de proteção")
        return True

def check_csrf_protection(backend_path):
    """Verifica proteção CSRF"""
    print_header("VERIFICANDO PROTEÇÃO CSRF")
    
    # Verificar se CSRF está inicializado
    init_file = backend_path / 'project' / '__init__.py'
    
    with open(init_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'CSRFProtect' in content and 'csrf.init_app' in content:
        print_success("CSRF Protection está inicializado")
        return True
    else:
        print_error("CSRF Protection NÃO está inicializado")
        return False

def check_input_validation(backend_path):
    """Verifica validação de entrada"""
    print_header("VERIFICANDO VALIDAÇÃO DE ENTRADA")
    
    issues = []
    
    # Procurar por request.form ou request.json sem validação
    for py_file in Path(backend_path / 'project' / 'blueprints').glob('*.py'):
        with open(py_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            for i, line in enumerate(lines):
                if 'request.form.get' in line or 'request.json' in line or 'request.get_json' in line:
                    # Verificar se há validação nas próximas 5 linhas
                    next_lines = '\n'.join(lines[i:min(i+5, len(lines))])
                    if not any(val in next_lines for val in ['if not', 'validate', 'ValueError', 'try:', 'except']):
                        issues.append(f"{py_file.name}:{i+1} - Possível falta de validação de entrada")
    
    if issues:
        for issue in issues[:10]:  # Mostrar apenas os primeiros 10
            print_warning(issue)
        if len(issues) > 10:
            print_warning(f"... e mais {len(issues) - 10} avisos")
        return False
    else:
        print_success("Validação de entrada parece adequada")
        return True

def check_error_handling(backend_path):
    """Verifica tratamento de erros"""
    print_header("VERIFICANDO TRATAMENTO DE ERROS")
    
    issues = []
    
    for py_file in Path(backend_path / 'project').rglob('*.py'):
        if 'test_' in py_file.name:
            continue
            
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Procurar por except: pass (bad practice)
            if re.search(r'except.*:\s*pass', content):
                issues.append(f"{py_file.name} - except: pass encontrado (má prática)")
    
    if issues:
        for issue in issues:
            print_warning(issue)
        return False
    else:
        print_success("Tratamento de erros parece adequado")
        return True

def main():
    """Executa todas as verificações"""
    print_header("VALIDAÇÃO DE SEGURANÇA - CS ONBOARDING")
    
    # Determinar caminho do backend
    backend_path = Path(__file__).parent / 'backend'
    
    if not backend_path.exists():
        print_error(f"Diretório backend não encontrado: {backend_path}")
        sys.exit(1)
    
    print(f"Analisando: {backend_path}\n")
    
    # Executar verificações
    results = {
        'SQL Injection': check_sql_injection(backend_path),
        'Hardcoded Secrets': check_hardcoded_secrets(backend_path),
        'Permission Decorators': check_permission_decorators(backend_path),
        'CSRF Protection': check_csrf_protection(backend_path),
        'Input Validation': check_input_validation(backend_path),
        'Error Handling': check_error_handling(backend_path),
    }
    
    # Resumo
    print_header("RESUMO DA VALIDAÇÃO")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = f"{Colors.GREEN}✓ PASSOU{Colors.END}" if result else f"{Colors.RED}✗ FALHOU{Colors.END}"
        print(f"{check:.<40} {status}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} verificações passaram{Colors.END}\n")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ TODAS AS VERIFICAÇÕES PASSARAM!{Colors.END}")
        return 0
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ ALGUMAS VERIFICAÇÕES FALHARAM{Colors.END}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
