import psycopg2

# Tabelas esperadas baseado no schema.py
expected_tables = [
    'alembic_version',
    'checklist_items',
    'checklist_prazos_history',  # Pode estar faltando
    'checklist_responsavel_history',
    'checklist_status_history',  # ESTA ESTÁ FALTANDO!
    'comentarios',
    'comentarios_h',
    'fases',
    'gamificacao_metricas_mensais',
    'gamificacao_regras',
    'grupos',
    'implantacoes',
    'perfil_usuario',
    'planos_fases',
    'planos_grupos',
    'planos_subtarefas',
    'planos_sucesso',
    'planos_tarefas',
    'smtp_settings',
    'subtarefas_h',
    'tarefas',
    'tarefas_h',
    'timeline_log',
    'usuarios',
]

conn = psycopg2.connect('postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
existing_tables = set([r[0] for r in cur.fetchall()])

print("=== TABELAS FALTANDO ===")
missing = set(expected_tables) - existing_tables
for t in sorted(missing):
    print(f"  FALTANDO: {t}")

print("\n=== TABELAS EXISTENTES ===")
for t in sorted(existing_tables):
    print(f"  OK: {t}")

conn.close()
