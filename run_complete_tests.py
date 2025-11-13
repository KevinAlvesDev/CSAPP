#!/usr/bin/env python
# run_complete_tests.py
# Script completo para executar todos os testes com relatório detalhado

import subprocess
import sys
import os
from datetime import datetime
import json


def print_header(text):
    """Imprime cabeçalho formatado."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def check_dependencies():
    """Verifica se pytest e pytest-cov estão instalados."""
    print_header("Verificando Dependências")
    
    try:
        import pytest
        print("✅ pytest instalado")
    except ImportError:
        print("❌ pytest não encontrado. Instalando...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pytest'])
    
    try:
        import pytest_cov
        print("✅ pytest-cov instalado")
    except ImportError:
        print("❌ pytest-cov não encontrado. Instalando...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pytest-cov'])


def run_tests_with_coverage():
    """Executa todos os testes com coverage."""
    print_header("EXECUTANDO TODOS OS TESTES COM COVERAGE")
    
    # Executa pytest com verbose e coverage
    result = subprocess.run([
        sys.executable, '-m', 'pytest',
        'tests/',
        '-v',
        '--tb=short',
        '--color=yes',
        '--cov=backend/project',
        '--cov-report=term-missing',
        '--cov-report=html:htmlcov',
        '--cov-report=json:coverage.json',
        '-p', 'no:warnings',
        '--maxfail=5'  # Para após 5 falhas
    ])
    
    return result.returncode


def run_specific_test_suites():
    """Executa suítes de testes específicas."""
    test_suites = [
        ('Testes Unitários (Utils)', 'tests/test_utils.py'),
        ('Testes de Validação', 'tests/test_validation.py'),
        ('Testes de Paginação', 'tests/test_pagination.py'),
        ('Testes de Soft Delete', 'tests/test_soft_delete.py'),
        ('Testes de Dashboard', 'tests/test_dashboard_service.py'),
        ('Testes de Performance', 'tests/test_performance.py'),
        ('Testes de Async Tasks', 'tests/test_async_tasks.py'),
        ('Testes de API v1', 'tests/test_api_v1.py'),
        ('Testes de Integração', 'tests/test_integration.py'),
        ('Testes de API', 'tests/test_api.py'),
        ('Testes de Auth', 'tests/test_auth.py'),
        ('Testes de Logging', 'tests/test_logging.py'),
        ('Testes de Management', 'tests/test_management.py'),
    ]
    
    results = {}
    
    for name, test_file in test_suites:
        if os.path.exists(test_file):
            print(f"\n🧪 Executando: {name}...")
            
            result = subprocess.run([
                sys.executable, '-m', 'pytest',
                test_file,
                '-v',
                '--tb=line',
                '-p', 'no:warnings'
            ], capture_output=True, text=True)
            
            results[name] = {
                'returncode': result.returncode,
                'output': result.stdout,
                'file': test_file
            }
            
            # Mostra resumo
            if result.returncode == 0:
                print(f"   ✅ PASSOU")
            else:
                print(f"   ❌ FALHOU")
        else:
            print(f"   ⚠️  Arquivo não encontrado: {test_file}")
            results[name] = {
                'returncode': -1,
                'output': 'Arquivo não encontrado',
                'file': test_file
            }
    
    return results


def generate_report(results):
    """Gera relatório de testes."""
    print_header("RELATÓRIO DE TESTES")
    
    total = len([r for r in results.values() if r['returncode'] != -1])
    passed = sum(1 for r in results.values() if r['returncode'] == 0)
    failed = sum(1 for r in results.values() if r['returncode'] > 0)
    skipped = sum(1 for r in results.values() if r['returncode'] == -1)
    
    print(f"📊 Total de Suítes: {total}")
    print(f"✅ Passou: {passed}")
    print(f"❌ Falhou: {failed}")
    print(f"⚠️  Pulado: {skipped}")
    
    if total > 0:
        print(f"📈 Taxa de Sucesso: {(passed/total*100):.1f}%\n")
    
    print("Detalhes por Suíte:")
    print("-" * 80)
    
    for name, result in results.items():
        if result['returncode'] == 0:
            status = "✅ PASSOU"
        elif result['returncode'] == -1:
            status = "⚠️  PULADO"
        else:
            status = "❌ FALHOU"
        
        print(f"{name:50} {status}")
    
    print("-" * 80)
    
    # Salva relatório em arquivo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'test_report_{timestamp}.txt'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"RELATÓRIO DE TESTES - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total de Suítes: {total}\n")
        f.write(f"Passou: {passed}\n")
        f.write(f"Falhou: {failed}\n")
        f.write(f"Pulado: {skipped}\n")
        
        if total > 0:
            f.write(f"Taxa de Sucesso: {(passed/total*100):.1f}%\n\n")
        
        f.write("Detalhes por Suíte:\n")
        f.write("-" * 80 + "\n")
        
        for name, result in results.items():
            if result['returncode'] == 0:
                status = "PASSOU"
            elif result['returncode'] == -1:
                status = "PULADO"
            else:
                status = "FALHOU"
            
            f.write(f"{name:50} {status}\n")
            
            if result['returncode'] > 0:
                f.write(f"\nArquivo: {result['file']}\n")
                f.write("Output:\n")
                f.write(result['output'])
                f.write("\n" + "-" * 80 + "\n")
    
    print(f"\n📄 Relatório salvo em: {report_file}")
    
    # Verifica coverage se existir
    if os.path.exists('coverage.json'):
        try:
            with open('coverage.json', 'r') as f:
                cov_data = json.load(f)
                total_cov = cov_data.get('totals', {}).get('percent_covered', 0)
                print(f"📊 Coverage Total: {total_cov:.1f}%")
                print(f"📁 Relatório HTML: htmlcov/index.html")
        except:
            pass
    
    return passed == total


def main():
    """Função principal."""
    print_header(f"SUÍTE COMPLETA DE TESTES - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verifica dependências
    check_dependencies()
    
    # Executa testes por suíte
    results = run_specific_test_suites()
    all_passed = generate_report(results)
    
    print_header("CONCLUSÃO")
    
    if all_passed:
        print("🎉 TODOS OS TESTES PASSARAM! 🎉")
        print("\n✅ O projeto está validado e pronto para produção!")
        print("\n📚 Próximos passos:")
        print("   1. Revisar coverage em: htmlcov/index.html")
        print("   2. Executar migrations: python -m alembic upgrade head")
        print("   3. Deploy em produção")
        return 0
    else:
        print("⚠️  ALGUNS TESTES FALHARAM")
        print("\n❌ Revise os erros no relatório e corrija antes de fazer deploy.")
        print(f"\n📄 Veja detalhes em: test_report_*.txt")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

