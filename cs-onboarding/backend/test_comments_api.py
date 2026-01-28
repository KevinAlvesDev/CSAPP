"""
Script de teste para verificar se a API de comentários está funcionando.
"""
import sys
sys.path.insert(0, '.')

from project import create_app
from project.db import query_db
from project.domain.checklist.comments import listar_comentarios_implantacao

app = create_app()

with app.app_context():
    print("=" * 60)
    print("TESTE DA FUNÇÃO listar_comentarios_implantacao")
    print("=" * 60)
    
    # Testar para implantação 2
    impl_id = 2
    
    result = listar_comentarios_implantacao(impl_id, page=1, per_page=20)
    
    print(f"Implantação ID: {impl_id}")
    print(f"Total de comentários: {result['total']}")
    print(f"Página: {result['page']}/{(result['total'] + result['per_page'] - 1) // result['per_page'] if result['total'] > 0 else 1}")
    print()
    
    if result['comments']:
        print("Comentários encontrados:")
        for c in result['comments']:
            print(f"  - ID: {c['id']}")
            print(f"    Texto: {str(c.get('texto', ''))[:50]}...")
            print(f"    Tarefa: {c.get('item_title', 'N/A')}")
            print(f"    Usuário: {c.get('usuario_nome', 'N/A')}")
            print()
    else:
        print("❌ NENHUM COMENTÁRIO ENCONTRADO!")
    
    print("=" * 60)
    print("✅ Teste concluído!")
