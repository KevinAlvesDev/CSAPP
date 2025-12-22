from backend.project import create_app
from backend.project.db import query_db

app = create_app()

with app.app_context():
    # Verificar total de tarefas concluídas
    result = query_db("""
        SELECT COUNT(*) as total 
        FROM checklist_items 
        WHERE completed = TRUE 
          AND data_conclusao IS NOT NULL 
          AND tipo_item = 'subtarefa'
    """)
    
    total = result[0]['total'] if result else 0
    print(f"Total de tarefas concluídas: {total}")
    
    # Verificar se há tags
    result2 = query_db("""
        SELECT DISTINCT tag, COUNT(*) as count
        FROM checklist_items 
        WHERE completed = TRUE 
          AND data_conclusao IS NOT NULL 
          AND tipo_item = 'subtarefa'
        GROUP BY tag
    """)
    
    print("\nTags encontradas:")
    if result2:
        for row in result2:
            print(f"  - {row['tag'] or 'Sem tag'}: {row['count']} tarefas")
    else:
        print("  Nenhuma tag encontrada")
    
    # Verificar usuários
    result3 = query_db("""
        SELECT u.nome, COUNT(DISTINCT ci.id) as count
        FROM checklist_items ci
        JOIN implantacoes i ON ci.implantacao_id = i.id
        JOIN perfil_usuario u ON i.usuario_cs = u.usuario
        WHERE ci.completed = TRUE 
          AND ci.data_conclusao IS NOT NULL 
          AND ci.tipo_item = 'subtarefa'
        GROUP BY u.nome
    """)
    
    print("\nUsuários com tarefas concluídas:")
    if result3:
        for row in result3:
            print(f"  - {row['nome']}: {row['count']} tarefas")
    else:
        print("  Nenhum usuário encontrado")
