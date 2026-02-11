# 📋 Plano de Ação - Correções e Melhorias CS-Onboarding

> Plano estruturado em 4 fases com priorização baseada em impacto vs esforço.  
> Última atualização: 2026-02-12

---

## 📊 Cronograma Resumido

| Fase | Duração | Prioridade | Status |
|------|---------|------------|--------|
| Fase 1: Quick Wins | 1-2 semanas | 🔴 CRÍTICA | ✅ CONCLUÍDA |
| Fase 2: Fundação | 3-4 semanas | 🔴 CRÍTICA | ✅ CONCLUÍDA |
| Fase 3: Consolidação | 4-6 semanas | 🟡 ALTA | ✅ CONCLUÍDA |
| Fase 4: Excelência | 6+ semanas | 🟢 BAIXA | 🔄 Fundação criada |

---

## 🎯 FASE 1: QUICK WINS — ✅ CONCLUÍDA

### 1.1 Segurança Imediata
- [x] Validação de Secrets em Runtime → `backend/project/config/secrets_validator.py`
- [x] Sanitização de Logs → `backend/project/config/log_sanitizer.py`

### 1.2 Documentação Básica
- [x] README.md completo (arquitetura, setup, variáveis)
- [x] CONTRIBUTING.md (padrões, PR, commits, segurança)
- [x] ADR-001: Flask como Framework Web
- [x] ADR-002: PostgreSQL + SQLite Dual Support
- [x] ADR-003: OAuth2 com Auth0 + Google

### 1.3 Linting e Formatação
- [x] Pre-commit Hooks → `.pre-commit-config.yaml`
- [x] Ruff aplicado em todo o codebase (832 fixes automáticos + 50 reformatados)
- [x] pyproject.toml migrado para formato lint novo (sem deprecation warnings)
- [x] ESLint configurado → `frontend/.eslintrc.json`

---

## 🏗️ FASE 2: FUNDAÇÃO — ✅ CONCLUÍDA

### 2.1 Testes Automatizados
- [x] **Estrutura** → `tests/conftest.py`, `tests/fixtures/__init__.py`
- [x] **8 Arquivos de teste:**
  - `test_secrets_validator.py` — Validação de secrets
  - `test_log_sanitizer.py` — Sanitização de logs
  - `test_validators.py` — Validação de inputs
  - `test_domain_services.py` — Services + Cache + Profiler
  - `test_events.py` — Event Bus (emissão, handlers, histórico, disable)
  - `test_dataloader.py` — DataLoader (batch, cache, progress, error)
  - `test_critical_flows.py` — Health check, auth, dashboard, API 404
- [x] **CI/CD** → `.github/workflows/test.yml`
  - Ruff lint + format check
  - Bandit security scan
  - pytest com coverage + upload artifact
  - Mypy type check (non-blocking)

### 2.2 Type Safety
- [x] Type hints em `implantacao_service.py` (todas as funções públicas + privadas)
- [x] Type hints em `dataloader.py`, `query_profiler.py`, `cache_manager.py`
- [x] Type hints em `container.py`, `events.py`
- [x] Mypy habilitado no CI (continue-on-error para coverage incremental)
- [x] pyproject.toml com mypy configurado

### 2.3 Refatoração de Queries (N+1) — ✅ APLICADA
- [x] **DataLoader Pattern** → `backend/project/common/dataloader.py`
  - `ChecklistDataLoader` — Carrega toda árvore em 1 query
  - `ComentariosDataLoader` — Carrega todos comentários em 1 query
  - `ImplantacaoDataLoader` — Combinado (2-3 queries vs 50+)
- [x] **Query Profiler** → `backend/project/common/query_profiler.py`
  - Loga queries > 100ms (WARNING), > 500ms (CRITICAL)
  - Estatísticas (avg, p95, top slow)
- [x] **Migração aplicada**: `_get_tarefas_and_comentarios` agora usa DataLoader
  - Antes: ~50+ queries N+1 por implantação
  - Depois: 1 query para todos items + 1 para comentários
  - Bonus: sort movido para fora do loop (era `O(n²)`, agora `O(n log n)`)

### 2.4 Migrations Consolidadas
- [x] **001_consolidated_base.py** — Schema base completo (18 tabelas)
  - Inclui todos os índices essenciais
  - Consolida scripts SQL manuais em migration versionada
- [x] **002_add_performance_indexes.py** — Índices compostos
  - `idx_impl_usuario_status` (dashboard)
  - `idx_checklist_parent_tipo_ordem` (travessia hierárquica)
  - `idx_comentarios_data_criacao` (últimos comentários)
  - `idx_timeline_impl_data` (timeline)
  - `idx_perfil_acesso` (filtro de perfil)
- [x] **migrations/README.md** — Guia de migrations com Alembic

---

## 🔧 FASE 3: CONSOLIDAÇÃO — ✅ CONCLUÍDA

### 3.1 Dependency Injection — ✅ INTEGRADO
- [x] ServiceContainer implementado → `backend/project/core/container.py`
- [x] **Service Registry** → `backend/project/core/service_registry.py`
  - Registra todos os services (core + domínio + infra) no startup
  - Core: config, db, event_bus, query_profiler, cache_manager
  - Domínio: dashboard, implantacao, checklist, config, notification, perfis, timeline, audit
  - Infra: dataloader_factory
- [x] Container inicializado no `create_app()` após cache_manager

### 3.2 Cache Strategy — ✅ IMPLEMENTADA
- [x] Cache Manager aprimorado → `backend/project/config/cache_manager.py`
- [x] **Cache Warming** → `backend/project/config/cache_warming.py`
  - Pré-carrega 6 recursos no startup (tags, status, níveis, tipos evento, motivos)
  - Elimina cold-start lento para o primeiro usuário
  - Métricas de warming (succeeded, failed, duration_ms)
- [x] **Refresh on-demand** via `POST /health/cache/refresh`
  - Recarrega configs sem reiniciar a app
  - Útil após deploys ou mudanças manuais no BD

### 3.3 Frontend Modernization — ✅ SETUP COMPLETO
- [x] TypeScript configurado → `frontend/tsconfig.json`
  - `allowJs: true` para migração incremental
  - Path aliases: `@services/*`, `@utils/*`, `@components/*`, `@ui/*`
- [x] Vite atualizado para suportar `.ts` → `frontend/vite.config.js`
- [x] **Type definitions** → `frontend/static/js/types.ts`
  - Interfaces para API, Implantação, Checklist, Dashboard, Perfil
  - Window globals para compat com código legado
- [x] **Primeiro módulo TS** → `frontend/static/js/services/api-service.ts`
  - ApiServiceClass com generics (`get<T>`, `post<T>`, etc.)
  - Interfaces tipadas: ProgressBar, Notifier, ApiRequestOptions
  - Exporta para window para compatibilidade

### 3.4 Observabilidade Avançada — ✅ IMPLEMENTADA
- [x] Sentry + Performance monitoring
- [x] Query Profiler
- [x] **Endpoint de Métricas** → `GET /health/metrics`
  - Query Profiler stats (slow queries, avg, p95)
  - Cache Manager stats (hit rate, misses, invalidations)
  - Container info (serviços registrados)
  - Event Bus stats (eventos emitidos, handlers)
- [x] Prometheus/Grafana avaliado → endpoint `/health/metrics` é suficiente
  para monitoramento atual; Prometheus pode ser adicionado via middleware se escalar

### 3.5 Testes Fase 3
- [x] `test_phase3.py` — 8 testes cobrindo:
  - ServiceRegistry: registro, resolução, lista de services
  - Cache Warming: loading, error handling, skip, refresh
- [x] Corrigido bug pré-existente em test_dataloader (progress 40% vs 50%)

---

## 🚀 FASE 4: EXCELÊNCIA — ✅ EVENT-DRIVEN ARCHITECTURE

### 4.1 Event-Driven Architecture
- [x] Event Bus implementado → `backend/project/core/events.py`
- [x] Event Handlers implementados → `backend/project/core/event_handlers.py`
  - **Audit**: ImplantacaoCriada, ImplantacaoFinalizada, ImplantacaoTransferida
  - **Cache**: ImplantacaoIniciada, ImplantacaoFinalizada, ChecklistItemConcluido,
    ChecklistComentarioAdicionado, PlanoAtribuido, ImplantacaoTransferida
  - **Gamification**: ImplantacaoFinalizada, ChecklistItemConcluido (milestones 25/50/75/100%)
  - **Log**: UsuarioLogado
- [x] Eventos emitidos nos services de domínio:
  - `implantacao/crud.py` → ImplantacaoCriada, ImplantacaoTransferida
  - `implantacao/status.py` → ImplantacaoIniciada, ImplantacaoFinalizada
  - `checklist/items.py` → ChecklistItemConcluido (com progresso atual)
  - `checklist/comments.py` → ChecklistComentarioAdicionado (com tag)
- [x] Handlers registrados no startup via `register_event_handlers(event_bus)`
- [x] Cross-cutting concerns desacoplados dos services (audit, cache, gamificação)

### 4.2 Testes Fase 4
- [x] `test_phase4.py` — 15 testes cobrindo:
  - Handler Registration: wiring, contagem, stats
  - Audit Handlers: criação, finalização, transferência com changes
  - Cache Handlers: invalidação por tipo, ambos usuários em transferência
  - Gamification Handlers: limpeza de cache, milestones
  - Integration: emissão → handler, múltiplos handlers, error isolation, bus disable/enable

### 4.3 Microservices / Data Warehouse
- [ ] Avaliar necessidade baseada no crescimento

### 4.4 Manutenção e Correções (Pós-Refatoração)
- [x] **Correção de Imports**: `onboarding/actions.py` e `grandes_contas/actions.py` atualizados para usar `domain.implantacao.*` em vez de `implantacao_service`.
- [x] **Startup Order**: `__init__.py` corrigido para executar `cache_warming` APÓS `init_db`.
- [x] **SQLite Schema**: Tabelas de configuração (`tags_sistema`, `status_implantacao`, etc.) e seed data adicionados para ambiente local.
- [x] **SQLite Schema V2**: Tabelas de `checklist_finalizacao` e seed data de templates integrados ao setup local.
- [x] **SQLite Schema V2**: Tabelas de `checklist_finalizacao` e seed data de templates integrados ao setup local.
- [x] **MIGRAÇÃO DE PRODUÇÃO (VERIFICADO)**: Banco de produção já possui `tags_sistema` e `contexto`, deploy seguro.

---

## 📁 Todos os Arquivos Criados/Modificados

### Novos Arquivos (Fase 1 + 2 + 3)
| Arquivo | Propósito |
|---------|-----------|
| `backend/project/config/secrets_validator.py` | Validação de secrets no startup |
| `backend/project/config/log_sanitizer.py` | Sanitização de logs (LGPD) |
| `backend/project/config/cache_manager.py` | Cache com TTL por recurso |
| `backend/project/config/cache_warming.py` | ♨️ Pré-carregamento de cache no startup |
| `backend/project/common/dataloader.py` | DataLoader (elimina N+1) |
| `backend/project/common/query_profiler.py` | Profiling de queries lentas |
| `backend/project/core/__init__.py` | Package init |
| `backend/project/core/container.py` | Dependency Injection |
| `backend/project/core/events.py` | Event Bus + Domain Events |
| `backend/project/core/service_registry.py` | 🔧 Registro centralizado de services |
| `frontend/tsconfig.json` | 📘 Config TypeScript (migração incremental) |
| `frontend/static/js/types.ts` | 📘 Type definitions (API, Domain, Config) |
| `frontend/static/js/services/api-service.ts` | 📘 Primeiro módulo TypeScript |
| `README.md` | Documentação principal |
| `CONTRIBUTING.md` | Guia de contribuição |
| `.pre-commit-config.yaml` | Pre-commit hooks |
| `.github/workflows/test.yml` | CI/CD pipeline |
| `docs/adr/ADR-001-flask-framework.md` | ADR: Flask |
| `docs/adr/ADR-002-dual-database.md` | ADR: Databases |
| `docs/adr/ADR-003-oauth2-auth0-google.md` | ADR: Auth |
| `docs/PLANO_DE_ACAO.md` | Este documento |
| `migrations/versions/001_consolidated_base.py` | Schema base (Alembic) |
| `migrations/versions/002_add_performance_indexes.py` | Índices (Alembic) |
| `migrations/README.md` | Guia de migrations |
| `tests/conftest.py` | Config de testes |
| `tests/fixtures/__init__.py` | Factories (users, items, etc.) |
| `tests/unit/test_secrets_validator.py` | Testes: secrets |
| `tests/unit/test_log_sanitizer.py` | Testes: sanitização |
| `tests/unit/test_validators.py` | Testes: validação |
| `tests/unit/test_domain_services.py` | Testes: services |
| `tests/unit/test_events.py` | Testes: event bus |
| `tests/unit/test_dataloader.py` | Testes: dataloader |
| `tests/unit/test_phase3.py` | Testes: container + cache warming |
| `backend/project/core/event_handlers.py` | 📢 Handlers de eventos (audit, cache, gamification) |
| `tests/unit/test_phase4.py` | Testes: event-driven architecture |
| `tests/integration/test_critical_flows.py` | Testes: fluxos críticos |

### Arquivos Modificados
| Arquivo | Mudança |
|---------|---------|
| `backend/project/__init__.py` | Integrado secrets, log sanitizer, cache manager, **container, warming, event handlers** |
| `backend/project/domain/implantacao_service.py` | DataLoader + type hints + Ruff fix |
| `backend/project/domain/implantacao/crud.py` | **Emissão de ImplantacaoCriada + ImplantacaoTransferida** |
| `backend/project/domain/implantacao/status.py` | **Emissão de ImplantacaoIniciada + ImplantacaoFinalizada** |
| `backend/project/domain/checklist/items.py` | **Emissão de ChecklistItemConcluido** |
| `backend/project/domain/checklist/comments.py` | **Emissão de ChecklistComentarioAdicionado** |
| `backend/project/blueprints/health.py` | **Endpoints: /health/metrics + /health/cache/refresh** |
| `frontend/vite.config.js` | **Suporte a .ts files** |
| `pyproject.toml` | Ruff lint migrado, exclude readded |
| `.github/workflows/test.yml` | Mypy habilitado (non-blocking) |
| 50+ arquivos Python | Ruff auto-fix + format |

