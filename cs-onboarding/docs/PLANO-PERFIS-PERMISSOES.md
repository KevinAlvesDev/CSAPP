# 🎯 PLANO DE IMPLEMENTAÇÃO: Sistema de Perfis e Permissões

## 📋 VISÃO GERAL

Sistema completo de **RBAC (Role-Based Access Control)** com interface visual para gerenciar perfis de acesso e suas permissões.

---

## 🏗️ ARQUITETURA

### **Fluxo de Navegação:**
```
/perfis
  ├─ Lista de Perfis (Cards)
  │   ├─ [Administrador] → /perfis/1/editar
  │   ├─ [Implantador] → /perfis/2/editar
  │   └─ [+ Novo Perfil] → /perfis/novo
  │
  └─ Editor de Permissões
      ├─ Dados do Perfil (Nome, Descrição, Cor)
      ├─ Grid de Permissões (Checkboxes)
      └─ [Salvar] → Volta para /perfis
```

---

## 📊 ESTRUTURA DE DADOS

### **Tabelas:**
1. **perfis_acesso** - Perfis do sistema
2. **recursos** - Funcionalidades disponíveis
3. **permissoes** - Relação Many-to-Many

### **Perfis Padrão:**
- **Administrador** (vermelho) - Todas as permissões
- **Implantador** (azul) - Sem gerenciar usuários/perfis
- **Visualizador** (cinza) - Apenas visualização

### **Categorias de Recursos:**
- Dashboard (2 recursos)
- Implantações (6 recursos)
- Checklist (5 recursos)
- Planos de Sucesso (7 recursos)
- Usuários (5 recursos)
- Perfis de Acesso (6 recursos)

**Total:** 31 recursos mapeados

---

## 🎨 TELA 1: Lista de Perfis

### **Layout:**
```
┌─────────────────────────────────────────────────────┐
│  Perfis de Acesso                    [+ Novo Perfil]│
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ 🛡️ Admin     │  │ 👤 Implant.  │  │ 👁️ Visual│ │
│  │              │  │              │  │          │ │
│  │ 31/31 perm.  │  │ 20/31 perm.  │  │ 8/31 per.│ │
│  │ 5 usuários   │  │ 12 usuários  │  │ 3 usuár. │ │
│  │              │  │              │  │          │ │
│  │ [Editar]     │  │ [Editar]     │  │ [Editar] │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### **Funcionalidades:**
- ✅ Cards visuais com cor do perfil
- ✅ Contador de permissões
- ✅ Contador de usuários
- ✅ Botão "Editar" → vai para Tela 2
- ✅ Botão "Novo Perfil" → vai para Tela 2 (modo criação)
- ✅ Badge "Sistema" para perfis não editáveis

---

## 🎨 TELA 2: Editor de Permissões

### **Layout:**
```
┌─────────────────────────────────────────────────────┐
│  ← Voltar    Editando: Administrador                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Dados do Perfil:                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │ Nome: [Administrador_______________]        │  │
│  │ Descrição: [Acesso total ao sistema_____]   │  │
│  │ Cor: [🎨 #dc3545]  Ícone: [🛡️ shield-check]│  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
│  Permissões: (25/31 selecionadas)                  │
│  [Marcar Todas] [Desmarcar Todas] [Buscar...]      │
│                                                     │
│  ┌─ Dashboard ─────────────────────── (2/2) ☑ ─┐  │
│  │  ☑ Visualizar Dashboard                      │  │
│  │  ☑ Exportar Relatórios                       │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌─ Implantações ──────────────────── (5/6) ☑ ─┐  │
│  │  ☑ Listar Implantações                       │  │
│  │  ☑ Visualizar Detalhes                       │  │
│  │  ☑ Criar Implantação                         │  │
│  │  ☑ Editar Implantação                        │  │
│  │  ☐ Excluir Implantação                       │  │
│  │  ☑ Finalizar Implantação                     │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌─ Checklist ─────────────────────── (4/5) ☑ ─┐  │
│  │  ☑ Visualizar Checklist                      │  │
│  │  ☑ Marcar Tarefas                            │  │
│  │  ☑ Adicionar Comentários                     │  │
│  │  ☑ Editar Tarefas                            │  │
│  │  ☐ Excluir Tarefas                           │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ... (mais categorias)                              │
│                                                     │
│  [Cancelar]                      [Salvar Permissões]│
└─────────────────────────────────────────────────────┘
```

### **Funcionalidades:**
- ✅ Formulário de dados do perfil
- ✅ Checkboxes agrupados por categoria
- ✅ Checkbox "Marcar Todas" por categoria
- ✅ Contador de permissões por categoria
- ✅ Busca de permissões
- ✅ Botões "Marcar Todas" / "Desmarcar Todas" global
- ✅ Preview de mudanças
- ✅ Validação antes de salvar

---

## 🔧 BACKEND

### **Arquivos a Criar:**

#### **1. Models (`models/perfil.py`):**
```python
class Perfil:
    - get_all()
    - get_by_id()
    - create()
    - update()
    - delete()
    - get_permissoes()
    - set_permissoes()
```

#### **2. Services (`domain/perfis_service.py`):**
```python
- listar_perfis()
- obter_perfil_completo()
- criar_perfil()
- atualizar_perfil()
- excluir_perfil()
- atualizar_permissoes()
- verificar_permissao(user_id, recurso_codigo)
```

#### **3. Blueprint (`blueprints/perfis_bp.py`):**
```python
GET  /perfis                    # Lista de perfis
GET  /perfis/novo               # Formulário novo perfil
GET  /perfis/<id>               # Detalhes do perfil
GET  /perfis/<id>/editar        # Editor de permissões
POST /perfis                    # Criar perfil
PUT  /perfis/<id>               # Atualizar perfil
DELETE /perfis/<id>             # Excluir perfil
POST /perfis/<id>/permissoes    # Atualizar permissões
GET  /api/recursos              # Lista de recursos (JSON)
```

---

## 🎨 FRONTEND

### **Arquivos a Criar:**

#### **1. Templates:**
- `perfis_lista.html` - Tela 1 (lista de perfis)
- `perfis_editor.html` - Tela 2 (editor de permissões)
- `partials/_perfil_card.html` - Card de perfil
- `partials/_permissao_categoria.html` - Grupo de permissões

#### **2. JavaScript:**
- `perfis_ui.js` - Lógica da interface
  - Marcar/desmarcar checkboxes
  - Busca de permissões
  - Salvar via AJAX
  - Validações

#### **3. CSS:**
- Estilos para cards de perfis
- Grid de permissões
- Cores e ícones

---

## 🔒 INTEGRAÇÃO COM AUTENTICAÇÃO

### **Decorator de Permissões:**
```python
@requires_permission('planos.create')
def criar_plano():
    # Verifica se o usuário tem permissão
    # Antes de executar a ação
```

### **Template Helper:**
```jinja
{% if tem_permissao('planos.edit') %}
    <button>Editar</button>
{% endif %}
```

### **JavaScript Helper:**
```javascript
if (window.temPermissao('planos.delete')) {
    // Mostrar botão de excluir
}
```

---

## 📝 CHECKLIST DE IMPLEMENTAÇÃO

### **Fase 1: Banco de Dados** ✅
- [x] Script SQL criado
- [ ] Executar no banco
- [ ] Validar dados iniciais

### **Fase 2: Backend**
- [ ] Models (perfil.py, recurso.py, permissao.py)
- [ ] Services (perfis_service.py)
- [ ] Blueprint (perfis_bp.py)
- [ ] Decorator de permissões
- [ ] Testes

### **Fase 3: Frontend - Tela 1**
- [ ] Template lista de perfis
- [ ] Cards visuais
- [ ] Navegação

### **Fase 4: Frontend - Tela 2**
- [ ] Template editor
- [ ] Grid de permissões
- [ ] JavaScript interativo
- [ ] Salvar via AJAX

### **Fase 5: Integração**
- [ ] Aplicar decorator nas rotas existentes
- [ ] Atualizar templates com verificações
- [ ] Migrar usuários para perfis
- [ ] Testes end-to-end

---

## ⏱️ ESTIMATIVA DE TEMPO

| Fase | Tempo | Complexidade |
|------|-------|--------------|
| 1. Banco de Dados | 10 min | Baixa |
| 2. Backend | 30 min | Média |
| 3. Frontend Tela 1 | 20 min | Baixa |
| 4. Frontend Tela 2 | 30 min | Média |
| 5. Integração | 20 min | Média |
| **TOTAL** | **~2 horas** | **Média** |

---

## 🚀 PRÓXIMO PASSO

**Estou pronto para começar!**

**Quer que eu:**
1. ✅ Execute o script SQL no banco
2. ✅ Crie o backend completo
3. ✅ Crie as telas (frontend)
4. ✅ Integre tudo

**Ou prefere revisar o plano primeiro?**

---

**Data:** 2025-12-28  
**Versão:** 1.0.0  
**Status:** 📋 **PLANEJAMENTO COMPLETO**
