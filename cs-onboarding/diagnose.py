from backend.project import create_app
from backend.project.db import query_db

app = create_app()

with app.app_context():
    print("=" * 80)
    print("DIAGNÓSTICO DO PROBLEMA")
    print("=" * 80)
    
    # 1. Verificar total de tarefas (sem filtros)
    result = query_db("SELECT COUNT(*) as total FROM checklist_items")
    print(f"\n1. Total de tarefas no banco: {result[0]['total'] if result else 0}")
    
    # 2. Verificar tarefas concluídas (sem tipo_item)
    result = query_db("""
        SELECT COUNT(*) as total 
        FROM checklist_items 
        WHERE completed = TRUE OR completed = 1
    """)
    print(f"2. Tarefas com completed = TRUE/1: {result[0]['total'] if result else 0}")
    
    # 3. Verificar tarefas com data_conclusao
    result = query_db("""
        SELECT COUNT(*) as total 
        FROM checklist_items 
        WHERE data_conclusao IS NOT NULL
    """)
    print(f"3. Tarefas com data_conclusao: {result[0]['total'] if result else 0}")
    
    # 4. Verificar tipos de item
    result = query_db("""
        SELECT tipo_item, COUNT(*) as count
        FROM checklist_items 
        GROUP BY tipo_item
    """)
    print(f"\n4. Tipos de item no banco:")
    if result:
        for row in result:
            print(f"   - {row['tipo_item'] or 'NULL'}: {row['count']}")
    
    # 5. Verificar tarefas concluídas SEM filtro de tipo_item
    result = query_db("""
        SELECT ci.id, ci.title, ci.completed, ci.data_conclusao, ci.tipo_item, ci.tag
        FROM checklist_items ci
        WHERE (ci.completed = TRUE OR ci.completed = 1)
          AND ci.data_conclusao IS NOT NULL
        LIMIT 10
    """)
    print(f"\n5. Primeiras 10 tarefas concluídas (qualquer tipo):")
    if result:
        for row in result:
            print(f"   - ID {row['id']}: {row['title'][:50]}")
            print(f"     Tipo: {row['tipo_item']}, Tag: {row['tag']}, Concluída: {row['completed']}")
    else:
        print("   Nenhuma tarefa encontrada!")
    
    # 6. Verificar se há implantações
    result = query_db("SELECT COUNT(*) as total FROM implantacoes")
    print(f"\n6. Total de implantações: {result[0]['total'] if result else 0}")
    
    # 7. Verificar query COMPLETA (a que está sendo usada)
    result = query_db("""
        SELECT 
            u.nome as user_name,
            COALESCE(ci.tag, 'Sem tag') as tag,
            COUNT(DISTINCT ci.id) as task_count,
            ci.tipo_item
        FROM checklist_items ci
        JOIN implantacoes i ON ci.implantacao_id = i.id
        JOIN perfil_usuario u ON i.usuario_cs = u.usuario
        WHERE (ci.completed = TRUE OR ci.completed = 1)
          AND ci.data_conclusao IS NOT NULL
        GROUP BY u.nome, ci.tag, ci.tipo_item
        LIMIT 20
    """)
    print(f"\n7. Query COMPLETA (sem filtro de tipo_item):")
    if result:
        for row in result:
            print(f"   - {row['user_name']}: {row['tag']} = {row['task_count']} (tipo: {row['tipo_item']})")
    else:
        print("   Nenhum resultado!")
    
    print("\n" + "=" * 80)
