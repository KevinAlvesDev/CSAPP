import re
from datetime import datetime, timedelta

import pytest


def create_app_for_tests():
    from cs_onboarding.backend.project import create_app
    app = create_app({
        'TESTING': True,
        'DEBUG': True,
        'USE_SQLITE_LOCALLY': True,
        'AUTH0_ENABLED': False,
        'SECRET_KEY': 'test-secret',
    })
    return app


def setup_implantacao_and_item(app):
    from cs_onboarding.backend.project.db import init_db, execute_db, query_db
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
    from cs_onboarding.backend.project.db import query_db
    with app.app_context():
        return query_db(
            "SELECT tipo_evento, detalhes FROM timeline_log WHERE implantacao_id = %s ORDER BY id DESC",
            (impl_id,)
        ) or []


@pytest.mark.parametrize("completed", [True, False])
def test_toggle_logs_objective_no_item_number(completed):
    app = create_app_for_tests()
    client = app.test_client()
    impl_id, item_id = setup_implantacao_and_item(app)
    res = client.post(f"/api/checklist/toggle/{item_id}", json={"completed": completed})
    assert res.status_code == 200
    logs = get_timeline(app, impl_id)
    assert any(l['tipo_evento'] == 'tarefa_alterada' for l in logs)
    last = next(l for l in logs if l['tipo_evento'] == 'tarefa_alterada')
    assert re.search(r"Status: (Concluída|Pendente) — ", last['detalhes'])
    assert not re.search(r"Item\s+\d+", last['detalhes'])


def test_responsavel_log_objective():
    app = create_app_for_tests()
    client = app.test_client()
    impl_id, item_id = setup_implantacao_and_item(app)
    res = client.patch(f"/api/checklist/item/{item_id}/responsavel", json={"responsavel": "João"})
    assert res.status_code == 200
    logs = get_timeline(app, impl_id)
    last = next(l for l in logs if l['tipo_evento'] == 'responsavel_alterado')
    assert "Responsável:" in last['detalhes'] and "→" in last['detalhes']
    assert not re.search(r"Item\s+\d+", last['detalhes'])


def test_prazo_log_objective():
    app = create_app_for_tests()
    client = app.test_client()
    impl_id, item_id = setup_implantacao_and_item(app)
    nova = (datetime.now() + timedelta(days=3)).isoformat()
    res = client.patch(f"/api/checklist/item/{item_id}/prazos", json={"nova_previsao": nova})
    assert res.status_code == 200
    logs = get_timeline(app, impl_id)
    last = next(l for l in logs if l['tipo_evento'] == 'prazo_alterado')
    assert last['detalhes'].startswith("Nova previsão:")
    assert not re.search(r"Item\s+\d+", last['detalhes'])


def test_comments_new_and_delete_logs_objective():
    app = create_app_for_tests()
    client = app.test_client()
    impl_id, item_id = setup_implantacao_and_item(app)
    res = client.post(f"/api/checklist/comment/{item_id}", json={"texto": "observação", "visibilidade": "interno"})
    assert res.status_code == 200
    logs = get_timeline(app, impl_id)
    assert any(l['tipo_evento'] == 'novo_comentario' for l in logs)
    last_new = next(l for l in logs if l['tipo_evento'] == 'novo_comentario')
    assert last_new['detalhes'].startswith("Comentário criado")
    assert not re.search(r"Item\s+\d+", last_new['detalhes'])

    # delete via checklist API
    comentario_id = res.get_json()['comentario']['id']
    res_del = client.delete(f"/api/checklist/comment/{comentario_id}")
    assert res_del.status_code == 200
    logs = get_timeline(app, impl_id)
    last_del = next(l for l in logs if l['tipo_evento'] == 'comentario_excluido')
    assert last_del['detalhes'].startswith("Comentário excluído")
    assert not re.search(r"Item\s+\d+", last_del['detalhes'])


def test_delete_item_log_objective():
    app = create_app_for_tests()
    client = app.test_client()
    impl_id, item_id = setup_implantacao_and_item(app)
    res = client.post(f"/api/checklist/delete/{item_id}")
    assert res.status_code == 200
    logs = get_timeline(app, impl_id)
    last = next(l for l in logs if l['tipo_evento'] == 'tarefa_excluida')
    assert last['detalhes'].startswith("Tarefa excluída — ")
    assert not re.search(r"Item\s+\d+", last['detalhes'])

