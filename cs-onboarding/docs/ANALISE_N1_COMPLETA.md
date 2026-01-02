# 🔍 Análise Completa - Identificação de N+1 Real

**Data:** 2026-01-02 11:27

---

## ✅ ARQUIVOS JÁ OTIMIZADOS (Não precisam refatoração)

1. ✅ `domain/dashboard/data.py` - **OTIMIZADO** (`dashboard_service_v2.py`)
2. ✅ `domain/implantacao_service.py` - **OTIMIZADO** (`implantacao_service_v2.py`)
3. ✅ `domain/implantacao/status.py` - **JÁ EFICIENTE** (1-2 queries por função)
4. ✅ `domain/implantacao/progress.py` - **JÁ OTIMIZADO** (queries eficientes + cache)

---

## 🔴 ARQUIVOS COM N+1 REAL (Precisam refatoração)

### 5. `domain/planos/crud.py` (16 queries) - **CRÍTICO**
- Loops com queries para buscar itens de plano
- Precisa otimização

### 6. `domain/checklist/comments.py` (11 queries) - **ALTO**
- Busca comentários em loop
- Precisa otimização

### 7. `domain/checklist/tree.py` (6 queries) - **MÉDIO**
- Subqueries correlacionadas
- Precisa otimização

### 8. `domain/analytics/dashboard.py` (6 queries) - **MÉDIO**
- Filtros em Python ao invés de SQL
- Precisa otimização

### 9. `domain/gamification/metrics.py` (7 queries) - **MÉDIO**
- Loops com queries
- Precisa otimização

---

## 🟡 ARQUIVOS PARA ANÁLISE DETALHADA

10. `domain/notification_service.py` (10 queries)
11. `domain/perfis_service.py` (12 queries)
12. `domain/auth_service.py` (15 queries)
13. `domain/implantacao/crud.py` (10 queries)
14. `domain/management/admin.py` (8 queries)
15. `domain/hierarquia/tasks.py` (8 queries)
16. `domain/planos/aplicar.py` (7 queries)
17. `domain/hierarquia/comments.py` (7 queries)
18. `database/soft_delete.py` (6 queries)
19. `domain/checklist/history.py` (5 queries)
20. `domain/management/users.py` (5 queries)

---

## 📊 RESUMO

- **Já otimizados:** 4 arquivos (20%)
- **Precisam otimização:** 5 arquivos (25%)
- **Análise pendente:** 11 arquivos (55%)

---

## 🎯 ESTRATÉGIA REVISADA

Vou focar nos 5 arquivos críticos primeiro, depois analiso os 11 restantes.

**Próximo:** `domain/planos/crud.py`
