import re
from datetime import datetime, timedelta
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from project import create_app


def create_app_for_tests():
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
    from project.db import init_db, execute_db, query_db
    with app.app_context():
        init_db()
        execute_db(
            "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, status) VALUES (%s, %s, %s, %s)",
            ('admin@pacto.com', 'Empresa Teste', 'onboarding', 'andamento')
        )
        impl = query_db("SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1", one=True)
        impl_id = impl['id']
        execute_db(
            "INSERT INTO checklist_items (parent_id, title, completed, level, ordem, implantacao_id, tipo_item) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (None, 'ANOTAÇÕES PÓS-WELCOME', False, 2, 1, impl_id, 'tarefa')
        )
        item = query_db("SELECT id FROM checklist_items WHERE implantacao_id = %s ORDER BY id DESC LIMIT 1", (impl_id,), one=True)
        return impl_id, item['id']


def get_timeline(app, impl_id):
    from project.db import query_db
    with app.app_context():
        return query_db(
            "SELECT tipo_evento, detalhes FROM timeline_log WHERE implantacao_id = %s ORDER BY id DESC",
            (impl_id,)
        ) or []


def assert_no_item_number(text):
    if re.search(r"Item\s+\d+", text):
        raise AssertionError(f"Texto contém número de item: {text}")


def run():
    app = create_app_for_tests()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'admin@pacto.com', 'name': 'Administrador', 'sub': 'dev|local'}

    impl_id, item_id = setup_implantacao_and_item(app)
    # Toggle true
    res = client.post(f"/api/checklist/toggle/{item_id}", json={"completed": True})
    assert res.status_code == 200
    logs = get_timeline(app, impl_id)
    last = next(l for l in logs if l['tipo_evento'] == 'tarefa_alterada')
    assert last['detalhes'].startswith("Status: ")
    assert_no_item_number(last['detalhes'])

    # Responsável
    res = client.patch(f"/api/checklist/item/{item_id}/responsavel", json={"responsavel": "João"})
    assert res.status_code == 200
    logs = get_timeline(app, impl_id)
    last = next(l for l in logs if l['tipo_evento'] == 'responsavel_alterado')
    assert "Responsável:" in last['detalhes'] and "→" in last['detalhes']
    assert_no_item_number(last['detalhes'])

    # Prazo
    nova = (datetime.now() + timedelta(days=3)).isoformat()
    res = client.patch(f"/api/checklist/item/{item_id}/prazos", json={"nova_previsao": nova})
    assert res.status_code == 200
    logs = get_timeline(app, impl_id)
    last = next(l for l in logs if l['tipo_evento'] == 'prazo_alterado')
    assert last['detalhes'].startswith("Nova previsão:")
    assert_no_item_number(last['detalhes'])

    # Comentário novo
    res = client.post(f"/api/checklist/comment/{item_id}", json={"texto": "observação", "visibilidade": "interno"})
    assert res.status_code == 200
    logs = get_timeline(app, impl_id)
    last_new = next(l for l in logs if l['tipo_evento'] == 'novo_comentario')
    assert last_new['detalhes'].startswith("Comentário criado")
    assert_no_item_number(last_new['detalhes'])

    # Comentário excluído
    comentario_id = res.get_json()['comentario']['id']
    res_del = client.delete(f"/api/checklist/comment/{comentario_id}")
    assert res_del.status_code == 200
    logs = get_timeline(app, impl_id)
    last_del = next(l for l in logs if l['tipo_evento'] == 'comentario_excluido')
    assert last_del['detalhes'].startswith("Comentário excluído")
    assert_no_item_number(last_del['detalhes'])

    # Excluir tarefa
    res = client.post(f"/api/checklist/delete/{item_id}")
    assert res.status_code == 200
    logs = get_timeline(app, impl_id)
    last = next(l for l in logs if l['tipo_evento'] == 'tarefa_excluida')
    assert last['detalhes'].startswith("Tarefa excluída — ")
    assert_no_item_number(last['detalhes'])

    print("OK: timeline logs consistentes e sem número de item")


if __name__ == '__main__':
    run()
