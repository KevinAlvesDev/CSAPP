"""
Alias de compatibilidade para o pacote backend.project.
Mantém `from project ...` funcionando após mover o backend para `backend/project`.
"""

import importlib
import sys

_backend_project = importlib.import_module("backend.project")

create_app = getattr(_backend_project, "create_app")

_SUBMODULES = [
    "api",
    "extensions",
    "logging_config",
    "constants",
    "validation",
    "utils",
    "db",
    "db_pool",
    "domain",
    "task_definitions",
    "blueprints",
]

for name in _SUBMODULES:
    mod = importlib.import_module(f"backend.project.{name}")
    sys.modules[f"project.{name}"] = mod


def __getattr__(name):
    return getattr(_backend_project, name)


def __dir__():
    return sorted(set(dir(_backend_project)))
