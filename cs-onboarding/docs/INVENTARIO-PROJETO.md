# 📁 Inventário Completo do Projeto CS-Onboarding

> Gerado em: 2024-12-28
> Atualizado: 2024-12-28
> Total de arquivos: ~180 (excluindo .git, __pycache__, node_modules, .venv)

---

## 📊 Resumo por Categoria

| Categoria | Arquivos | Status |
|-----------|----------|--------|
| Backend - Core | 8 | 🔍 Pendente análise |
| Backend - Blueprints | 7 | 🔍 Pendente análise |
| Backend - Domain Services | 20+ | 🔍 Pendente análise |
| Backend - Database | 3 | 🔍 Pendente análise |
| Frontend - JavaScript | 18 | 🔴 Prioridade (problemas encontrados) |
| Frontend - CSS | 5 → 15 | ✅ REFATORADO |
| Frontend - Templates | 30+ | 🔄 EM REFATORAÇÃO (Macros criadas) |
| Tests | 18 | 🔍 Pendente análise |
| Migrations | 12 | ✅ OK |
| Config/Docs | 15+ | ✅ OK |

---

## 🔴 PRIORIDADE 1: Frontend JavaScript (Problemas Identificados)

### Arquivos com Problemas Conhecidos

| Arquivo | Linhas | Problema | Status |
|---------|--------|----------|--------|
| `frontend/static/js/implantacao_detalhes_ui.js` | 1768 | Arquivo muito grande, código duplicado | 🔴 Crítico |
| `frontend/static/js/modal_detalhes_empresa.js` | 1163 | Código duplicado com implantacao_detalhes_ui.js | 🔴 Crítico |
| `frontend/static/js/checklist_renderer.js` | ~1300 | Arquivo grande, parcialmente refatorado | 🟡 Médio |
| `frontend/static/js/common.js` | ? | Funções globais misturadas | 🟡 Médio |
| `frontend/static/js/planos_editor.js` | ? | A analisar | 🔍 Pendente |

### Arquivos OK (já refatorados)

| Arquivo | Status |
|---------|--------|
| `frontend/static/js/services/api-service.js` | ✅ SOLID |
| `frontend/static/js/services/checklist-api.js` | ✅ SOLID |
| `frontend/static/js/services/checklist-service.js` | ✅ SOLID |
| `frontend/static/js/services/notification-service.js` | ✅ SOLID |
| `frontend/static/js/core/service-container.js` | ✅ SOLID |

---

## 📁 Lista Completa de Arquivos

### Backend - Core (`backend/`)
```
backend/project/__init__.py           # App factory principal
backend/project/config.py             # Configurações
backend/project/constants.py          # Constantes globais
backend/project/extensions.py         # Extensões Flask
```

### Backend - Blueprints (`backend/project/blueprints/`)
```
backend/project/blueprints/__init__.py
backend/project/blueprints/actions.py      # Ações de CRUD
backend/project/blueprints/analytics.py    # Dashboard gerencial
backend/project/blueprints/api.py          # API REST
backend/project/blueprints/auth.py         # Autenticação
backend/project/blueprints/main.py         # Rotas principais
backend/project/blueprints/perfis_bp.py    # Perfis de acesso
backend/project/blueprints/planos_bp.py    # Planos de sucesso
```

### Backend - Domain Services (`backend/project/domain/`)
```
# Services principais (facades)
backend/project/domain/checklist_service.py
backend/project/domain/dashboard_service.py
backend/project/domain/external_service.py
backend/project/domain/gamification_service.py
backend/project/domain/hierarquia_service.py
backend/project/domain/implantacao_service.py
backend/project/domain/management_service.py
backend/project/domain/notification_service.py
backend/project/domain/perfis_service.py
backend/project/domain/planos_sucesso_service.py

# Módulos SOLID (já refatorados)
backend/project/domain/checklist/       # 5 arquivos
backend/project/domain/dashboard/       # 3 arquivos
backend/project/domain/external/        # 5 arquivos
backend/project/domain/gamification/    # 6 arquivos
backend/project/domain/hierarquia/      # 4 arquivos
backend/project/domain/implantacao/     # 6 arquivos
backend/project/domain/management/      # 3 arquivos
backend/project/domain/planos/          # 5 arquivos
```

### Backend - Database (`backend/project/database/`)
```
backend/project/database/__init__.py
backend/project/database/connection.py
backend/project/database/schema.py
```

### Backend - Outros
```
backend/project/common/exceptions.py
backend/project/config/logging_config.py
backend/project/config/settings.py
backend/project/mail/email_utils.py
backend/project/monitoring/performance_monitoring.py
backend/project/security/api_security.py
backend/project/security/middleware.py
backend/project/tasks/async_tasks.py
```

### Frontend - JavaScript (`frontend/static/js/`)
```
# 🔴 A REFATORAR (problemas identificados)
frontend/static/js/implantacao_detalhes_ui.js    # 1768 linhas - MUITO GRANDE
frontend/static/js/modal_detalhes_empresa.js     # 1163 linhas - CÓDIGO DUPLICADO
frontend/static/js/checklist_renderer.js         # ~1300 linhas

# 🟡 A ANALISAR
frontend/static/js/agenda_ui.js
frontend/static/js/common.js
frontend/static/js/fetch_retry.js
frontend/static/js/modal_selecionar_plano.js
frontend/static/js/notifications.js
frontend/static/js/planos_editor.js
frontend/static/js/planos_sucesso_ui.js
frontend/static/js/table_sort.js
frontend/static/js/bug_prevention_service.js
frontend/static/js/test_save_button.js

# ✅ JÁ REFATORADOS (SOLID)
frontend/static/js/services/api-service.js
frontend/static/js/services/checklist-api.js
frontend/static/js/services/checklist-service.js
frontend/static/js/services/notification-service.js
frontend/static/js/core/service-container.js

# 📝 TESTES
frontend/static/js/tests/checklist-service.test.js
frontend/static/js/tests/test-framework.js
frontend/static/js/tests/test-runner.html
```

### Frontend - CSS (`frontend/static/css/`)
```
frontend/static/css/style.css
frontend/static/css/theme.css
frontend/static/css/implantacao_detalhes.css
frontend/static/css/login.css
frontend/static/css/preview_plano.css
```

### Frontend - Templates (`frontend/templates/`)
```
# Principais
frontend/templates/base.html
frontend/templates/dashboard.html
frontend/templates/implantacao_detalhes.html
frontend/templates/login.html
frontend/templates/analytics.html
frontend/templates/agenda.html
frontend/templates/manage_users.html
frontend/templates/perfil.html
frontend/templates/perfis_lista.html
frontend/templates/perfis_editor.html
frontend/templates/planos_sucesso.html
frontend/templates/plano_sucesso_editor.html
frontend/templates/cancelamentos.html
frontend/templates/gamification_*.html

# Modals
frontend/templates/modals/_detalhes_empresa.html
frontend/templates/modals/_gamificacao_regras.html
frontend/templates/modals/_gerenciar_usuarios.html
frontend/templates/modals/_perfil.html
frontend/templates/modals/_perfil_content.html

# Partials
frontend/templates/partials/_comment_*.html
frontend/templates/partials/_modal_selecionar_plano.html
frontend/templates/partials/_plano_card.html
frontend/templates/partials/_plano_preview.html
frontend/templates/partials/_progress_total_bar.html
frontend/templates/partials/_task_item.html
frontend/templates/partials/_task_item_wrapper.html

# Macros
frontend/templates/macros/buttons.html
frontend/templates/macros/cards.html
frontend/templates/macros/forms.html
frontend/templates/macros/dashboard.html  # ✅ NOVO - macros para dashboard
```

### Tests (`tests/`)
```
tests/test_analytics_aliases.py
tests/test_auth_routes.py
tests/test_auth_routes_unittest.py
tests/test_checklist_endpoints.py
tests/test_comments_tags_behavior.py
tests/test_consultar_empresa.py
tests/test_criar_implantacao.py
tests/test_environments.py
tests/test_modal_dates.py
tests/test_modal_detalhes_persistencia.py
tests/test_responsavel_prazos.py
tests/test_success_plan_full_flow.py
tests/test_tag_update.py
tests/test_timeline_consistency.py
tests/test_timeline_full_coverage.py
tests/test_timeline_logs.py
# + scripts auxiliares
```

### Migrations (`migrations/`)
```
migrations/versions/001_create_checklist_items_table.py
migrations/versions/002_add_plano_id_to_checklist_items.py
migrations/versions/003_add_tag_data_conclusao_to_subtarefas_h.py
migrations/versions/004_add_campos_consolidacao_checklist.py
migrations/versions/005_remover_tabelas_antigas.py
migrations/versions/006_create_status_history_table.py
migrations/versions/007_add_checklist_item_id_to_comentarios.py
migrations/versions/008_add_cancelamento_fields_to_implantacoes.py
# + scripts SQL
```

### Config/Docs (raiz)
```
run.py
requirements.txt
pyproject.toml
Procfile
gunicorn_config.py
PRODUCTION.md
GUIA_TUNEL_OAMD.md
PLANO-PERFIS-PERMISSOES.md
STATUS-PERFIS-IMPLEMENTACAO.md
FUNCIONALIDADE-CLONAR-PLANO.md
MELHORIAS-PLANOS-SUCESSO.md
*.bat, *.sh
```

---

## 🎯 Plano de Refatoração

### Fase 1: Frontend JavaScript (URGENTE)
1. [ ] `implantacao_detalhes_ui.js` - Dividir em módulos menores
2. [ ] `modal_detalhes_empresa.js` - Consolidar lógica duplicada
3. [ ] `checklist_renderer.js` - Completar refatoração

### Fase 2: Frontend Outros
4. [ ] `common.js` - Mover para services
5. [ ] `planos_editor.js` - Analisar e refatorar
6. [ ] `planos_sucesso_ui.js` - Analisar e refatorar

### Fase 3: Backend (se necessário)
7. [ ] Revisar services principais
8. [ ] Verificar duplicações

---

## 📝 Notas

- Arquivos marcados com 🔴 têm problemas conhecidos
- Arquivos marcados com 🟡 precisam análise
- Arquivos marcados com ✅ já foram refatorados
- Arquivos marcados com 🔍 pendente análise inicial
