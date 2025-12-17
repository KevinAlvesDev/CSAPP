import os


def create_app_for_tests():
    import sys
    import os as _os
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    sys.path.insert(0, root)
    from backend.project import create_app
    dsn = _os.environ.get('EXTERNAL_DB_URL') or 'postgresql+psycopg2://cs_pacto:pacto%40db@oamd.pactosolucoes.com.br:5432/OAMD'
    app = create_app({
        'TESTING': True,
        'DEBUG': True,
        'USE_SQLITE_LOCALLY': True,
        'AUTH0_ENABLED': False,
        'SECRET_KEY': 'test-secret',
        'EXTERNAL_DB_URL': dsn,
        'WTF_CSRF_ENABLED': False,
    })
    return app


def setup_implantacao(app, id_favorecido: int):
    from backend.project.db import execute_db
    from backend.project.database.schema import init_db
    with app.app_context():
        init_db()
        execute_db("INSERT OR IGNORE INTO usuarios(usuario, senha) VALUES(?, ?)", ('admin@pacto.com', 'x'))
        execute_db("INSERT OR IGNORE INTO perfil_usuario(usuario, nome, perfil_acesso) VALUES(?, ?, ?)", ('admin@pacto.com', 'Admin', 'Administrador'))
        execute_db(
            "INSERT INTO implantacoes(usuario_cs, nome_empresa, tipo, id_favorecido, chave_oamd) VALUES(?, ?, ?, ?, ?)",
            ('admin@pacto.com', 'Empresa Teste OAMD', 'onboarding', str(id_favorecido), None)
        )
        # pegar id
        from backend.project.db import query_db
        row = query_db("SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1", one=True)
        return row['id']


def main():
    app = create_app_for_tests()
    # usar um id_favorecido existente (ex.: 10602) vindo da tabela empresafinanceiro
    impl_id = setup_implantacao(app, 11287)
    from backend.project.blueprints.api_v1 import consultar_oamd_implantacao
    from flask import g
    with app.test_request_context(f"/api/v1/oamd/implantacoes/{impl_id}/consulta", method='GET'):
        g.user_email = 'admin@pacto.com'
        g.perfil = {'perfil_acesso': 'Administrador'}
        resp = consultar_oamd_implantacao(impl_id)
        # resp é (Response, status) ou Response
        try:
            status = resp[1]
            data = resp[0].get_json()
        except Exception:
            status = getattr(resp, 'status_code', None)
            data = resp.get_json() if hasattr(resp, 'get_json') else None
        print("status:", status)
        print("ok:", data.get('ok'))
        d = data.get('data') or {}
        print("informacao_infra:", (d.get('derived') or {}).get('informacao_infra'))
        print("tela_apoio_link:", (d.get('derived') or {}).get('tela_apoio_link'))


if __name__ == '__main__':
    main()
