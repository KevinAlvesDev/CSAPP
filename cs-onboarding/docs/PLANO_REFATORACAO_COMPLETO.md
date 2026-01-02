# 📋 Plano Completo de Refatoração - Eliminar N+1 e Duplicação

**Data:** 2026-01-02  
**Status:** EM ANDAMENTO

---

## 🎯 OBJETIVO

Refatorar TODOS os 20+ arquivos com queries para:
1. Eliminar N+1 queries
2. Eliminar duplicação de código
3. Melhorar performance em 10-100x

---

## 📊 ARQUIVOS IDENTIFICADOS (Por Prioridade)

### 🔴 **PRIORIDADE CRÍTICA** (Impacto Alto)

#### 1. ✅ `domain/dashboard/data.py` - CONCLUÍDO
- **Problema:** Loop com 300+ queries
- **Solução:** Criado `dashboard_service_v2.py`
- **Status:** ✅ Feito com feature toggle

#### 2. ⏳ `domain/implantacao_service.py` (20 queries)
- **Problema:** `_get_progress()` chamado em loop
- **Solução:** Calcular no SQL
- **Status:** PRÓXIMO

#### 3. ⏳ `domain/implantacao/status.py` (20 queries)
- **Problema:** Múltiplas queries para atualizar status
- **Solução:** Batch updates
- **Status:** PENDENTE

#### 4. ⏳ `domain/implantacao/progress.py` (10 queries)
- **Problema:** Cálculo de progresso individual
- **Solução:** Usar query_helpers
- **Status:** PENDENTE

---

### 🟡 **PRIORIDADE ALTA** (Impacto Médio)

#### 5. ⏳ `domain/planos/crud.py` (16 queries)
- **Problema:** Queries em loops
- **Solução:** JOINs e batch
- **Status:** PENDENTE

#### 6. ⏳ `domain/checklist/comments.py` (11 queries)
- **Problema:** Busca comentários um por um
- **Solução:** Buscar todos de uma vez
- **Status:** PENDENTE

#### 7. ⏳ `domain/checklist/tree.py` (6 queries)
- **Problema:** Subqueries correlacionadas
- **Solução:** LEFT JOIN
- **Status:** PENDENTE

#### 8. ⏳ `domain/notification_service.py` (10 queries)
- **Problema:** Notificações em loop
- **Solução:** Batch processing
- **Status:** PENDENTE

---

### 🟢 **PRIORIDADE MÉDIA** (Impacto Baixo)

#### 9-20. Outros arquivos
- `domain/analytics/dashboard.py`
- `domain/gamification/metrics.py`
- `domain/perfis_service.py`
- `domain/auth_service.py`
- Etc...

---

## 🛠️ ESTRATÉGIA DE REFATORAÇÃO

### **Para Cada Arquivo:**

1. **Analisar** queries atuais
2. **Identificar** N+1 e duplicação
3. **Criar** versão otimizada
4. **Adicionar** feature toggle
5. **Testar** localmente
6. **Documentar** mudanças
7. **Commit** individual

---

## 📈 PROGRESSO

- ✅ **Fase 1:** Helpers + Dashboard (CONCLUÍDO)
- ⏳ **Fase 2:** Implantação Service (EM ANDAMENTO)
- ⏳ **Fase 3:** Checklist (PENDENTE)
- ⏳ **Fase 4:** Planos (PENDENTE)
- ⏳ **Fase 5:** Outros (PENDENTE)

**Progresso Total:** 5% (1 de 20 arquivos)

---

## ⏱️ ESTIMATIVA

- Arquivos críticos (4): 2 dias
- Arquivos alta prioridade (4): 2 dias
- Arquivos média prioridade (12): 3 dias

**Total:** ~1 semana de trabalho focado

---

## 🎯 PRÓXIMO PASSO

Refatorar `domain/implantacao_service.py`
