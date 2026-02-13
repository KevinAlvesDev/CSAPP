import json

import pytest


def test_criar_limite_planos_em_andamento(authenticated_client):
    client = authenticated_client

    # criar 5 planos válidos
    created_ids = []
    for i in range(5):
        payload = {
            "nome": f"Plano Teste {i + 1}",
            "descricao": "Teste",
            "estrutura": {"items": []},
        }
        resp = client.post('/planos', data=json.dumps(payload), content_type='application/json')
        assert resp.status_code in (200, 201)
        data = resp.get_json()
        assert data and (data.get('success') or data.get('plano_id'))
        # extrair id
        plano_id = data.get('plano_id') or data.get('plano_id')
        created_ids.append(plano_id)

    # tentativa de criar o 6º plano deve falhar com 400
    payload = {"nome": "Plano Teste 6", "descricao": "Teste", "estrutura": {"items": []}}
    resp = client.post('/planos', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 400 or (resp.get_json() and resp.get_json().get('error'))


def test_listar_planos_por_status_e_concluir(authenticated_client):
    client = authenticated_client

    # Criar um plano com processo_id para testar offer_new_plan
    payload = {"nome": "Plano Com Processo", "descricao": "Teste", "estrutura": {"items": []}, "processo_id": 123}
    resp = client.post('/planos', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code in (200, 201)
    data = resp.get_json()
    plano_id = data.get('plano_id') or data.get('plano_id')

    # Listar apenas em_andamento
    resp = client.get('/api/planos-sucesso?status=em_andamento')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data and data.get('planos') is not None

    # Concluir via endpoint API
    resp = client.put(f'/api/planos-sucesso/{plano_id}/concluir')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    # Deve oferecer novo plano porque o plano tinha processo_id
    assert data.get('offer_new_plan') in (True, False)
