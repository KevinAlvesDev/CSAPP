"""
Script de Diagnóstico: Validação de Consulta OAMD
Uso: python diagnostico_oamd_auto.py <ID_FAVORECIDO>
Exemplo: python diagnostico_oamd_auto.py 11350
"""
import os
import sys
import json
from datetime import datetime

if len(sys.argv) < 2:
    print("❌ Uso: python diagnostico_oamd_auto.py <ID_FAVORECIDO>")
    print("Exemplo: python diagnostico_oamd_auto.py 11350")
    sys.exit(1)

ID_FAVORECIDO = sys.argv[1]

# Configurar ambiente
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['DEBUG'] = 'True'
os.environ['FLASK_SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

from backend.project import create_app
from backend.project.domain.external_service import consultar_empresa_oamd

app = create_app()

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

with app.app_context():
    print_section("DIAGNÓSTICO DE CONSULTA OAMD")
    print(f"\n🔍 Consultando ID Favorecido: {ID_FAVORECIDO}")
    print(f"⏰ Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    try:
        result = consultar_empresa_oamd(id_favorecido=ID_FAVORECIDO)
        
        if not result.get('ok'):
            print(f"\n❌ ERRO: {result.get('error')}")
            print(f"Status Code: {result.get('status_code')}")
            sys.exit(1)
        
        print("\n✅ Consulta bem-sucedida!")
        
        empresa = result.get('empresa', {})
        mapped = result.get('mapped', {})
        
        # ========================================
        # DADOS BRUTOS
        # ========================================
        print_section("DADOS BRUTOS DO BANCO EXTERNO")
        print(f"\n📊 Total de campos: {len(empresa)}")
        print("\n🔑 Campos relacionados a DATAS:")
        print("-" * 80)
        
        date_fields = {}
        for key in sorted(empresa.keys()):
            value = empresa[key]
            if any(x in key.lower() for x in ['data', 'inicio', 'final', 'producao', 'implantacao', 'cadastro']):
                date_fields[key] = value
                print(f"📅 {key:<40} = {value}")
        
        if not date_fields:
            print("⚠️  NENHUM campo de data encontrado!")
        
        # ========================================
        # DADOS MAPEADOS
        # ========================================
        print_section("DADOS MAPEADOS")
        print("\n🗺️  Status do mapeamento:")
        print("-" * 80)
        
        important_fields = {
            'data_inicio_producao': 'Início em Produção',
            'data_inicio_efetivo': 'Início da Implantação',
            'data_final_implantacao': 'Fim da Implantação',
            'data_cadastro': 'Data de Cadastro',
            'chave_oamd': 'Chave OAMD',
            'cnpj': 'CNPJ',
            'status_implantacao': 'Status',
        }
        
        for field, label in important_fields.items():
            value = mapped.get(field)
            if value:
                print(f"✅ {label:<30} = {value}")
            else:
                print(f"❌ {label:<30} = NÃO MAPEADO")
        
        # ========================================
        # ANÁLISE
        # ========================================
        print_section("ANÁLISE E RECOMENDAÇÕES")
        
        issues = []
        
        if not mapped.get('data_inicio_efetivo'):
            issues.append("Data de Início da Implantação não mapeada")
        if not mapped.get('data_inicio_producao'):
            issues.append("Data de Início em Produção não mapeada")
        
        if issues:
            print("\n🚨 PROBLEMAS:")
            for issue in issues:
                print(f"   ⚠️  {issue}")
            
            print("\n💡 CAMPOS DE DATA DISPONÍVEIS NO BANCO EXTERNO:")
            for key in date_fields.keys():
                print(f"   - {key}")
            
            print("\n📝 AÇÃO NECESSÁRIA:")
            print("   Adicionar os nomes corretos no mapeamento (external_service.py linhas 137-139)")
        else:
            print("\n✅ Todas as datas importantes foram mapeadas!")
        
        # ========================================
        # SALVAR
        # ========================================
        output_file = f"diagnostico_oamd_{ID_FAVORECIDO}.json"
        
        diagnostic_data = {
            'id_favorecido': ID_FAVORECIDO,
            'timestamp': datetime.now().isoformat(),
            'empresa_raw': empresa,
            'mapped': mapped,
            'date_fields_found': date_fields,
            'issues': issues
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(diagnostic_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultado salvo em: {output_file}")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n" + "="*80)
print("  DIAGNÓSTICO CONCLUÍDO")
print("="*80 + "\n")
