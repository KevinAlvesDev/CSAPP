"""
Alias de compatibilidade para o pacote backend.project.
Mantém `from project ...` funcionando após mover o backend para `backend/project`.
"""

import importlib
import sys

# Importa o pacote real
_backend_project = importlib.import_module('backend.project')

# Reexporta atributos de nível superior comuns
create_app = getattr(_backend_project, 'create_app')

# Mapeia submódulos usados pelos testes e pela aplicação
_SUBMODULES = [
    'api',
    'extensions',
    'logging_config',
    'constants',
    'validation',
    'utils',
    'db',
    'services',
    'task_definitions',
    'blueprints',
]

for name in _SUBMODULES:
    mod = importlib.import_module(f'backend.project.{name}')
    sys.modules[f'project.{name}'] = mod

def __getattr__(name):
    return getattr(_backend_project, name)

def __dir__():
    return sorted(set(dir(_backend_project)))