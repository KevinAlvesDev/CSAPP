"""
Script para consultar o banco de produção e criar índices de performance.
"""

import psycopg2
from psycopg2.extras import RealDictCursor

# String de conexão do Railway
DATABASE_URL = "postgresql://postgres:sChnKAdWRKtVXxTIDcQSPKKYrEMbTxNi@switchyard.proxy.rlwy.net:48993/railway"

def listar_tabelas():
    """Lista todas as tabelas do banco."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """)
    
    tabelas = cur.fetchall()
    
    print("=" * 60)
    print("TABELAS NO BANCO DE PRODUÇÃO:")
    print("=" * 60)
    for t in tabelas:
        print(f"  - {t['table_name']}")
    
    cur.close()
    conn.close()
    
    return [t['table_name'] for t in tabelas]


def listar_indices_existentes(tabela):
    """Lista índices existentes em uma tabela."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = %s
    """, (tabela,))
    
    indices = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [i['indexname'] for i in indices]


def criar_indices_performance():
    """Cria índices de performance nas tabelas principais."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("\n" + "=" * 60)
    print("CRIANDO ÍNDICES DE PERFORMANCE")
    print("=" * 60)
    
    indices = [
        # Tabela: perfil_usuario
        ("idx_perfil_usuario_email", "CREATE INDEX IF NOT EXISTS idx_perfil_usuario_email ON perfil_usuario(usuario)"),
        ("idx_perfil_usuario_ativo", "CREATE INDEX IF NOT EXISTS idx_perfil_usuario_ativo ON perfil_usuario(ativo)"),
        
        # Tabela: implantacoes
        ("idx_implantacoes_status", "CREATE INDEX IF NOT EXISTS idx_implantacoes_status ON implantacoes(status)"),
        ("idx_implantacoes_usuario_cs", "CREATE INDEX IF NOT EXISTS idx_implantacoes_usuario_cs ON implantacoes(usuario_cs)"),
        ("idx_implantacoes_empresa", "CREATE INDEX IF NOT EXISTS idx_implantacoes_nome_empresa ON implantacoes(nome_empresa)"),
        ("idx_implantacoes_ativo", "CREATE INDEX IF NOT EXISTS idx_implantacoes_ativo ON implantacoes(ativo)"),
        
        # Tabela: timeline_log
        ("idx_timeline_log_implantacao", "CREATE INDEX IF NOT EXISTS idx_timeline_log_implantacao ON timeline_log(implantacao_id)"),
        ("idx_timeline_log_data", "CREATE INDEX IF NOT EXISTS idx_timeline_log_data ON timeline_log(data_criacao)"),
        
        # Tabela: checklist_items
        ("idx_checklist_items_implantacao", "CREATE INDEX IF NOT EXISTS idx_checklist_items_implantacao ON checklist_items(implantacao_id)"),
        ("idx_checklist_items_status", "CREATE INDEX IF NOT EXISTS idx_checklist_items_status ON checklist_items(status)"),
        
        # Tabela: comentarios_h
        ("idx_comentarios_h_checklist", "CREATE INDEX IF NOT EXISTS idx_comentarios_h_checklist ON comentarios_h(checklist_item_id)"),
        ("idx_comentarios_h_data", "CREATE INDEX IF NOT EXISTS idx_comentarios_h_data ON comentarios_h(data_criacao)"),
        
        # Índices compostos para queries comuns
        ("idx_implantacoes_status_ativo", "CREATE INDEX IF NOT EXISTS idx_implantacoes_status_ativo ON implantacoes(status, ativo)"),
        ("idx_timeline_log_impl_data", "CREATE INDEX IF NOT EXISTS idx_timeline_log_impl_data ON timeline_log(implantacao_id, data_criacao)"),
    ]
    
    for nome_indice, sql in indices:
        try:
            print(f"\n[INFO] Criando índice: {nome_indice}")
            cur.execute(sql)
            conn.commit()
            print(f"[OK] Índice criado: {nome_indice}")
        except Exception as e:
            print(f"[AVISO] {nome_indice}: {e}")
            conn.rollback()
    
    cur.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("[OK] ÍNDICES CRIADOS COM SUCESSO!")
    print("=" * 60)


if __name__ == '__main__':
    print("\nCONSULTANDO BANCO DE PRODUCAO...\n")
    
    # Listar tabelas
    tabelas = listar_tabelas()
    
    # Criar índices
    criar_indices_performance()
    
    print("\nPROCESSO CONCLUIDO!\n")
