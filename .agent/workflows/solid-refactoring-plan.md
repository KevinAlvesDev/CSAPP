# Plano de Refatoração SOLID - CS Onboarding

## 📊 Status Atual
- **Cobertura SOLID**: ~5%
- **Meta**: 100%
- **Linhas totais**: 18.693
- **Arquivos Python**: ~55

---

## 🏗️ Estrutura de Diretórios Alvo

```
backend/project/
├── domain/
│   ├── implantacao/          ✅ FEITO
│   │   ├── __init__.py
│   │   ├── progress.py
│   │   ├── status.py
│   │   ├── crud.py
│   │   └── details.py
│   │
│   ├── planos/               📋 FASE 2
│   │   ├── __init__.py
│   │   ├── crud.py           # criar, atualizar, excluir planos
│   │   ├── aplicar.py        # aplicar plano a implantação
│   │   ├── estrutura.py      # fases, tarefas, subtarefas
│   │   └── validacao.py      # validações de plano
│   │
│   ├── checklist/            📋 FASE 3
│   │   ├── __init__.py
│   │   ├── tree.py           # árvore de checklist
│   │   ├── items.py          # CRUD de itens
│   │   ├── comments.py       # comentários
│   │   └── completion.py     # conclusão de tarefas
│   │
│   ├── analytics/            📋 FASE 4
│   │   ├── __init__.py
│   │   ├── kpis.py           # métricas de KPI
│   │   ├── reports.py        # relatórios
│   │   └── exports.py        # exportação de dados
│   │
│   ├── gamification/         📋 FASE 5
│   │   ├── __init__.py
│   │   ├── points.py         # pontuação
│   │   ├── ranking.py        # rankings
│   │   └── achievements.py   # conquistas
│   │
│   └── shared/               📋 FASE 6
│       ├── validators.py     # validações comuns
│       ├── formatters.py     # formatação de datas, etc
│       └── cache.py          # cache utilities
│
├── blueprints/               📋 FASE 7-8
│   ├── api/
│   │   ├── __init__.py
│   │   ├── implantacao.py
│   │   ├── checklist.py
│   │   └── ...
│   └── ...
```

---

## 📅 Cronograma de Fases

### ✅ FASE 1: Implantação Service (CONCLUÍDA)
**Cobertura**: 0% → 5%
- [x] Criar estrutura `domain/implantacao/`
- [x] Mover funções de progresso → `progress.py`
- [x] Mover funções de status → `status.py`
- [x] Mover funções CRUD → `crud.py`
- [x] Mover funções de detalhes → `details.py`
- [x] Criar `__init__.py` com re-exports
- [x] Testar compatibilidade

---

### 📋 FASE 2: Planos de Sucesso Service
**Arquivo**: `planos_sucesso_service.py` (1420 linhas)
**Cobertura**: 5% → 13%
**Estimativa**: 2-3 sessões

#### Módulos a criar:
| Módulo | Responsabilidade | Funções |
|--------|------------------|---------|
| `crud.py` | CRUD de planos | criar_plano, atualizar_plano, excluir_plano, listar_planos |
| `aplicar.py` | Aplicação de planos | aplicar_plano_implantacao, remover_plano_implantacao |
| `estrutura.py` | Estrutura do plano | criar_fase, criar_tarefa, criar_subtarefa, reordenar |
| `validacao.py` | Validações | validar_estrutura, validar_plano_completo |

#### Passos:
- [ ] Analisar funções existentes
- [ ] Mapear dependências
- [ ] Criar diretório `domain/planos/`
- [ ] Migrar funções de CRUD
- [ ] Migrar funções de estrutura
- [ ] Migrar funções de aplicação
- [ ] Migrar funções de validação
- [ ] Criar `__init__.py` com re-exports
- [ ] Atualizar imports no arquivo original
- [ ] Testar todas as rotas

---

### 📋 FASE 3: Checklist Service
**Arquivo**: `checklist_service.py` (1283 linhas)
**Cobertura**: 13% → 20%
**Estimativa**: 2-3 sessões

#### Módulos a criar:
| Módulo | Responsabilidade |
|--------|------------------|
| `tree.py` | Construção de árvore hierárquica |
| `items.py` | CRUD de itens de checklist |
| `comments.py` | Comentários em itens |
| `completion.py` | Marcar como concluído/pendente |

#### Passos:
- [ ] Analisar funções existentes
- [ ] Criar diretório `domain/checklist/`
- [ ] Migrar funções por responsabilidade
- [ ] Testar

---

### 📋 FASE 4: Analytics Service
**Arquivo**: `analytics_service.py` (825 linhas)
**Cobertura**: 20% → 24%
**Estimativa**: 1-2 sessões

#### Módulos a criar:
| Módulo | Responsabilidade |
|--------|------------------|
| `kpis.py` | Cálculo de KPIs |
| `reports.py` | Geração de relatórios |
| `exports.py` | Exportação para CSV/Excel |

---

### 📋 FASE 5: Gamification Service
**Arquivo**: `gamification_service.py` (787 linhas)
**Cobertura**: 24% → 28%
**Estimativa**: 1-2 sessões

#### Módulos a criar:
| Módulo | Responsabilidade |
|--------|------------------|
| `points.py` | Sistema de pontos |
| `ranking.py` | Rankings e leaderboards |
| `achievements.py` | Conquistas e badges |

---

### 📋 FASE 6: Blueprints de Ações
**Arquivo**: `implantacao_actions.py` (810 linhas)
**Cobertura**: 28% → 32%
**Estimativa**: 1-2 sessões

---

### 📋 FASE 7: API Blueprint
**Arquivo**: `api.py` (599 linhas)
**Cobertura**: 32% → 35%
**Estimativa**: 1 sessão

---

### 📋 FASE 8: Blueprints Restantes
**Arquivos**: `checklist_api.py`, `auth.py`, `planos_bp.py`, `agenda.py`, `analytics.py`, `gamification.py`
**Cobertura**: 35% → 50%
**Estimativa**: 2-3 sessões

---

### 📋 FASE 9: Serviços Médios
**Arquivos**: `dashboard_service.py`, `hierarquia_service.py`
**Cobertura**: 50% → 55%
**Estimativa**: 1 sessão

---

### 📋 FASE 10: Shared/Common
**Arquivos**: `validators.py`, `utils.py`, `email_utils.py`
**Cobertura**: 55% → 60%
**Estimativa**: 1 sessão

---

### 📋 FASE 11: Arquivos Restantes
**Arquivos**: Config, database, security, etc.
**Cobertura**: 60% → 100%
**Estimativa**: 2-3 sessões

---

## 🔧 Metodologia de Refatoração

### Para cada arquivo:

1. **Análise** (5 min)
   - Listar todas as funções
   - Identificar responsabilidades
   - Mapear dependências

2. **Design** (5 min)
   - Definir módulos a criar
   - Agrupar funções por responsabilidade

3. **Migração** (15-30 min por módulo)
   - Criar novo arquivo
   - Copiar funções
   - Ajustar imports internos
   - Criar re-exports

4. **Limpeza** (5 min)
   - Remover funções duplicadas do original
   - Adicionar imports dos novos módulos

5. **Teste** (5 min)
   - Verificar imports
   - Testar servidor
   - Verificar rotas no navegador

---

## ⚡ Comandos Úteis

### Iniciar fase
```
/solid-fase-2
```

### Verificar status
```powershell
# Contar linhas por arquivo
Get-ChildItem -Path "backend\project\domain" -Filter "*.py" -Recurse | 
ForEach-Object { [PSCustomObject]@{Path=$_.Name; Lines=(Get-Content $_.FullName).Count} } | 
Sort-Object Lines -Descending
```

### Testar imports
```powershell
python -c "from backend.project.domain import <modulo>; print('OK')"
```

---

## 📈 Tracking de Progresso

| Fase | Arquivo | Linhas | Status | Cobertura |
|------|---------|--------|--------|-----------|
| 1 | implantacao_service | 798 | ✅ Feito | 5% |
| 2 | planos_sucesso_service | 1420 | ⏳ Pendente | 13% |
| 3 | checklist_service | 1283 | ⏳ Pendente | 20% |
| 4 | analytics_service | 825 | ⏳ Pendente | 24% |
| 5 | gamification_service | 787 | ⏳ Pendente | 28% |
| 6 | implantacao_actions | 810 | ⏳ Pendente | 32% |
| 7 | api.py | 599 | ⏳ Pendente | 35% |
| 8 | blueprints restantes | ~2200 | ⏳ Pendente | 50% |
| 9 | serviços médios | ~800 | ⏳ Pendente | 55% |
| 10 | shared/common | ~1000 | ⏳ Pendente | 60% |
| 11 | restantes | ~7000 | ⏳ Pendente | 100% |

---

## 📝 Notas

- Sempre manter compatibilidade via re-exports
- Testar servidor após cada migração
- Commitar após cada fase completa
- Documentar dependências encontradas
