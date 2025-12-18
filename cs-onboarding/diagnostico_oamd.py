"""
Script de Diagnóstico: Validação de Consulta OAMD
Testa a consulta ao banco externo e mostra EXATAMENTE o que está sendo retornado
"""
import os
import sys
import json
from datetime import datetime

# Configurar ambiente
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['DEBUG'] = 'True'
os.environ['FLASK_SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

from backend.project import create_app
from backend.project.domain.external_service import consultar_empresa_oamd
from backend.project.domain.implantacao_service import consultar_dados_oamd

app = create_app()

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_dict(d, indent=0):
    """Imprime dicionário de forma legível"""
    for k, v in d.items():
        if isinstance(v, dict):
            print("  " * indent + f"{k}:")
            print_dict(v, indent + 1)
        elif isinstance(v, list):
            print("  " * indent + f"{k}: {v}")
        else:
            print("  " * indent + f"{k}: {v}")

# ID Favorecido para testar (você mencionou 11350)
ID_FAVORECIDO = input("\nDigite o ID Favorecido para testar (ex: 11350): ").strip()

if not ID_FAVORECIDO:
    print("❌ ID Favorecido é obrigatório!")
    sys.exit(1)

with app.app_context():
    print_section("DIAGNÓSTICO DE CONSULTA OAMD")
    print(f"\n🔍 Consultando ID Favorecido: {ID_FAVORECIDO}")
    print(f"⏰ Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # ========================================
    # ETAPA 1: Consulta Direta ao Banco Externo
    # ========================================
    print_section("ETAPA 1: Consulta Direta ao Banco Externo")
    
    try:
        result = consultar_empresa_oamd(id_favorecido=ID_FAVORECIDO)
        
        if not result.get('ok'):
            print(f"\n❌ ERRO: {result.get('error')}")
            print(f"Status Code: {result.get('status_code')}")
            sys.exit(1)
        
        print("\n✅ Consulta bem-sucedida!")
        
        # Dados brutos da empresa
        print_section("DADOS BRUTOS DO BANCO EXTERNO (empresa)")
        empresa = result.get('empresa', {})
        
        print(f"\n📊 Total de campos retornados: {len(empresa)}")
        print("\n🔑 Campos e valores:")
        print("-" * 80)
        
        # Ordenar por nome do campo para facilitar leitura
        for key in sorted(empresa.keys()):
            value = empresa[key]
            # Destacar campos de data
            if any(x in key.lower() for x in ['data', 'inicio', 'final', 'producao', 'implantacao', 'cadastro']):
                print(f"📅 {key:<30} = {value}")
            else:
                print(f"   {key:<30} = {value}")
        
        # Dados mapeados
        print_section("DADOS MAPEADOS (mapped)")
        mapped = result.get('mapped', {})
        
        print("\n🗺️  Mapeamento realizado:")
        print("-" * 80)
        for key, value in mapped.items():
            if value:
                print(f"✅ {key:<30} = {value}")
            else:
                print(f"⚠️  {key:<30} = (vazio)")
        
        # ========================================
        # ETAPA 2: Processamento pelo Serviço
        # ========================================
        print_section("ETAPA 2: Processamento pelo Serviço de Implantação")
        
        # Simular o que acontece quando aplicamos os dados
        print("\n📦 Dados que seriam persistidos (persistibles):")
        print("-" * 80)
        
        persistibles = {
            'id_favorecido': empresa.get('codigo') or empresa.get('codigofinanceiro'),
            'chave_oamd': mapped.get('chave_oamd'),
            'cnpj': mapped.get('cnpj'),
            'data_cadastro': mapped.get('data_cadastro'),
            'status_implantacao': mapped.get('status_implantacao'),
        }
        
        # Verificar se as datas estão sendo capturadas
        if 'inicioimplantacao' in empresa:
            persistibles['inicio_implantacao'] = empresa['inicioimplantacao']
        if 'finalimplantacao' in empresa:
            persistibles['final_implantacao'] = empresa['finalimplantacao']
        if 'inicioproducao' in empresa:
            persistibles['inicio_producao'] = empresa['inicioproducao']
        
        for key, value in persistibles.items():
            if value:
                print(f"✅ {key:<30} = {value}")
            else:
                print(f"❌ {key:<30} = (NÃO ENCONTRADO)")
        
        # ========================================
        # ETAPA 3: Análise de Datas
        # ========================================
        print_section("ETAPA 3: Análise Específica de Datas")
        
        print("\n🔍 Buscando campos de data no banco externo...")
        print("-" * 80)
        
        date_fields = {}
        for key, value in empresa.items():
            if any(x in key.lower() for x in ['data', 'inicio', 'final', 'producao', 'implantacao', 'cadastro']):
                date_fields[key] = value
        
        if date_fields:
            print(f"\n📅 Encontrados {len(date_fields)} campos relacionados a datas:")
            for key, value in date_fields.items():
                print(f"   {key:<40} = {value}")
        else:
            print("\n⚠️  NENHUM campo de data encontrado!")
        
        # Verificar mapeamento de datas
        print("\n🗺️  Status do mapeamento de datas:")
        print("-" * 80)
        
        date_mappings = {
            'data_inicio_producao': mapped.get('data_inicio_producao'),
            'data_inicio_efetivo': mapped.get('data_inicio_efetivo'),
            'data_final_implantacao': mapped.get('data_final_implantacao'),
            'data_cadastro': mapped.get('data_cadastro'),
        }
        
        for field, value in date_mappings.items():
            if value:
                print(f"✅ {field:<30} = {value}")
            else:
                print(f"❌ {field:<30} = NÃO MAPEADO")
        
        # ========================================
        # ETAPA 4: Recomendações
        # ========================================
        print_section("ETAPA 4: Recomendações")
        
        issues = []
        
        # Verificar se datas foram mapeadas
        if not mapped.get('data_inicio_efetivo'):
            issues.append("⚠️  Data de Início da Implantação não foi mapeada")
        if not mapped.get('data_inicio_producao'):
            issues.append("⚠️  Data de Início em Produção não foi mapeada")
        if not mapped.get('data_final_implantacao'):
            issues.append("⚠️  Data Final da Implantação não foi mapeada")
        
        if issues:
            print("\n🚨 PROBLEMAS ENCONTRADOS:")
            for issue in issues:
                print(f"   {issue}")
            
            print("\n💡 POSSÍVEIS SOLUÇÕES:")
            print("   1. Verificar se os campos existem no banco externo com nomes diferentes")
            print("   2. Adicionar os nomes corretos no mapeamento (external_service.py)")
            print("   3. Verificar se os dados existem para este ID Favorecido")
        else:
            print("\n✅ Todas as datas foram mapeadas corretamente!")
        
        # ========================================
        # ETAPA 5: Salvar Resultado
        # ========================================
        print_section("ETAPA 5: Salvando Resultado")
        
        output_file = f"diagnostico_oamd_{ID_FAVORECIDO}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        diagnostic_data = {
            'id_favorecido': ID_FAVORECIDO,
            'timestamp': datetime.now().isoformat(),
            'empresa_raw': empresa,
            'mapped': mapped,
            'persistibles': persistibles,
            'date_fields_found': date_fields,
            'issues': issues
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(diagnostic_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Resultado salvo em: {output_file}")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n" + "="*80)
print("  DIAGNÓSTICO CONCLUÍDO")
print("="*80 + "\n")
