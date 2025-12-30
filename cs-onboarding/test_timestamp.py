import sys
sys.path.insert(0, 'backend')

from project import create_app
from project.db import query_db, execute_db
from datetime import datetime

app = create_app()

with app.app_context():
    impl_id = 6  # tttt
    
    # 1. Inserir um comentário AGORA
    print(f"=== Inserindo comentário AGORA ===")
    now = datetime.now()
    print(f"Horário atual: {now}")
    
    # Buscar um checklist_item desta implantação
    item = query_db("""
        SELECT id FROM checklist_items 
        WHERE implantacao_id = %s 
        LIMIT 1
    """, (impl_id,), one=True)
    
    if not item:
        print("ERRO: Nenhum checklist_item encontrado para esta implantação")
        sys.exit(1)
    
    item_id = item['id']
    print(f"Checklist item ID: {item_id}")
    
    # Inserir comentário
    execute_db("""
        INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, data_criacao, visibilidade)
        VALUES (%s, %s, %s, %s, %s)
    """, (item_id, 'kevin.alves@acadsystem.com.br', 'Teste de timestamp', now, 'interno'))
    
    print(f"✅ Comentário inserido com data_criacao = {now}")
    
    # 2. Buscar o último comentário usando a mesma query do dashboard
    print(f"\n=== Buscando último comentário (query do dashboard) ===")
    result = query_db("""
        SELECT 
            ci.implantacao_id,
            MAX(ch.data_criacao) as ultima_atividade
        FROM comentarios_h ch
        INNER JOIN checklist_items ci ON ch.checklist_item_id = ci.id
        WHERE ci.implantacao_id = %s
        GROUP BY ci.implantacao_id
    """, (impl_id,), one=True)
    
    if result:
        ultima_atividade = result['ultima_atividade']
        print(f"Última atividade retornada: {ultima_atividade}")
        print(f"Tipo: {type(ultima_atividade)}")
        
        # 3. Calcular diferença
        if isinstance(ultima_atividade, str):
            ultima_dt = datetime.strptime(ultima_atividade, '%Y-%m-%d %H:%M:%S')
        else:
            ultima_dt = ultima_atividade
            
        diff = now - ultima_dt
        print(f"\nDiferença: {diff}")
        print(f"Diferença em segundos: {diff.total_seconds()}")
        print(f"Diferença em dias: {diff.days}")
        
        # 4. Testar a função format_relative_time
        from project.domain.dashboard.utils import format_relative_time
        text, days, status = format_relative_time(ultima_atividade)
        print(f"\n=== Resultado format_relative_time ===")
        print(f"Texto: {text}")
        print(f"Dias: {days}")
        print(f"Status: {status}")
    else:
        print("ERRO: Nenhum comentário encontrado")
