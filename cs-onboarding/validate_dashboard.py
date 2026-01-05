"""
Script para comparar as duas versões do dashboard
"""

# Campos que DEVEM estar presentes em cada implantação
REQUIRED_FIELDS = [
    'id',
    'status',
    'progresso',
    'dias_passados',
    'ultima_atividade_text',
    'ultima_atividade_dias',
    'ultima_atividade_status',
    'valor_monetario_float',
    'data_criacao_iso',
    'data_inicio_efetivo_iso',
    'data_inicio_producao_iso',
    'data_final_implantacao_iso',
]

# Campos condicionais por status
CONDITIONAL_FIELDS = {
    'parada': ['dias_parada'],
    'futura': ['data_inicio_previsto_fmt_d', 'atrasada_para_iniciar'],
}

# Funcionalidades que DEVEM existir
REQUIRED_FEATURES = [
    'Cache (get/set)',
    'Paginação (page/per_page)',
    'UPDATE perfil_usuario',
    'Fallback dias_passados',
    'JOIN ultima_atividade',
    'calculate_days_passed()',
    'calculate_days_parada()',
    'format_relative_time()',
    'format_date_iso_for_json()',
    'format_date_br()',
    'Limpeza \\xa0 no status',
    'Migração atrasada → andamento',
]

print("=" * 80)
print("CHECKLIST DE COMPATIBILIDADE - Dashboard Otimizado")
print("=" * 80)
print("\n✓ = Implementado")
print("✗ = FALTANDO")
print("\n" + "=" * 80)
print("\nCAMPOS OBRIGATÓRIOS:")
for field in REQUIRED_FIELDS:
    print(f"  [ ] {field}")

print("\nCAMPOS CONDICIONAIS:")
for status, fields in CONDITIONAL_FIELDS.items():
    print(f"  Status '{status}':")
    for field in fields:
        print(f"    [ ] {field}")

print("\nFUNCIONALIDADES:")
for feature in REQUIRED_FEATURES:
    print(f"  [ ] {feature}")

print("\n" + "=" * 80)
print("\nPara validar manualmente:")
print("1. Abra dashboard_service.py")
print("2. Abra dashboard/data.py")
print("3. Compare linha por linha")
print("4. Marque cada item acima como ✓ ou ✗")
print("=" * 80)
