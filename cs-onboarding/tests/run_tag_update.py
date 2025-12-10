from datetime import datetime


def create_app_for_tests():
    import sys
    import os
    os.environ['FLASK_ENV'] = 'development'
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, root)
    from backend.project import create_app
    app = create_app({
        'TESTING': True,
        'DEBUG': True,
        'USE_SQLITE_LOCALLY': True,
        'AUTH0_ENABLED': False,
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })
    return app


def setup_implantacao_and_item(app):
    from backend.project.db import init_db, execute_db, query_db
    with app.app_context():
        init_db()
        execute_db(
            "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, status) VALUES (%s, %s, %s, %s)",
            ('admin@pacto.com', 'Empresa Teste', 'onboarding', 'andamento')
        )
        impl = query_db("SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1", one=True)
        impl_id = impl['id']
        execute_db(
            "INSERT INTO checklist_items (parent_id, title, completed, level, ordem, implantacao_id, tipo_item, tag) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (None, 'Tarefa com Tag', False, 2, 1, impl_id, 'tarefa', 'Ação interna')
        )
        item = query_db("SELECT id FROM checklist_items WHERE implantacao_id = %s ORDER BY id DESC LIMIT 1", (impl_id,), one=True)
        return impl_id, item['id']


def get_timeline(app, impl_id):
    from backend.project.db import query_db
    with app.app_context():
        return query_db(
            "SELECT tipo_evento, detalhes FROM timeline_log WHERE implantacao_id = %s ORDER BY id DESC",
            (impl_id,)
        ) or []


def main():
    app = create_app_for_tests()
    client = app.test_client()
    impl_id, item_id = setup_implantacao_and_item(app)
    # sanity: toggle should work (auth auto)
    res_toggle = client.post(f"/api/checklist/toggle/{item_id}", json={"completed": True})
    print("toggle status:", res_toggle.status_code)
    for tag in ("Cliente", "Reunião", "Ação interna"):
        res = client.patch(f"/api/checklist/item/{item_id}/tag", json={"tag": tag})
        print("tag status:", res.status_code, res.get_json())
        assert res.status_code == 200, f"Falha ao atualizar tag para {tag}"
        data = res.get_json()
        assert data.get('ok') and data.get('tag') == tag
    from backend.project.db import query_db
    with app.app_context():
        item = query_db("SELECT tag FROM checklist_items WHERE id = %s", (item_id,), one=True)
        assert item and item.get('tag') == 'Ação interna', "Tag final não persistida"
    print("OK: tag atualizada e persistida corretamente")
    print("OK: atualização de tag e log de timeline válidos")


if __name__ == '__main__':
    main()
