"""
Decorator para Auditoria
"""

import functools

from flask import g

from ..domain.audit_service import log_action


def audit(action: str, target_type: str):
    """
    Decorator para registrar auditoria automaticamente em endpoints.

    Uso:
    @audit(action='UPDATE_IMPLANTACAO', target_type='implantacao')
    def update_implantacao(id):
        ...

    Nota: Tenta extrair o target_id dos argumentos da função (primeiro argumento ou kwargs 'id'/'implantacao_id')
    """

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Executar a função original
            response = f(*args, **kwargs)

            try:
                # Tentar identificar o ID alvo
                target_id = None

                # Procura em kwargs comuns
                for key in ["id", "implantacao_id", "user_id", "item_id"]:
                    if key in kwargs:
                        target_id = kwargs[key]
                        break

                # Se não achou, tenta o primeiro argumento posicional se for simples
                if not target_id and args and isinstance(args[0], (int, str)):
                    target_id = args[0]

                # Se a resposta for JSON e contiver ID (ex: criação), usa ele
                if not target_id and hasattr(response, "get_json"):
                    try:
                        data = response.get_json()
                        if data and isinstance(data, dict):
                            target_id = data.get("id") or data.get("implantacao_id")
                    except:
                        pass

                # Registrar log
                if target_id:
                    log_action(
                        action=action,
                        target_type=target_type,
                        target_id=str(target_id),
                        user_email=getattr(g, "user_email", None),
                    )
            except Exception:
                # Auditoria não deve quebrar a requisição
                pass

            return response

        return wrapper

    return decorator
