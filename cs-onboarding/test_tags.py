from backend.project import create_app
from backend.project.domain.tags_analytics import get_tags_by_user_chart_data

app = create_app()

with app.app_context():
    result = get_tags_by_user_chart_data()
    
    print("=" * 60)
    print("RELATÓRIO DE TAGS - TESTE")
    print("=" * 60)
    print(f"\nUsuários encontrados: {result['labels']}")
    print(f"\nTags encontradas:")
    for dataset in result['datasets']:
        print(f"  - {dataset['label']}: {sum(dataset['data'])} tarefas")
    
    print(f"\n{'='*60}")
    print(f"TOTAIS:")
    print(f"  Total de tarefas: {result['total_tasks']}")
    print(f"  Total de usuários: {result['total_users']}")
    print(f"  Total de tags: {result['total_tags']}")
    print("=" * 60)
    
    if result['datasets']:
        print("\nDetalhamento por usuário:")
        for i, user in enumerate(result['labels']):
            print(f"\n{user}:")
            for dataset in result['datasets']:
                count = dataset['data'][i]
                if count > 0:
                    print(f"  - {dataset['label']}: {count}")
