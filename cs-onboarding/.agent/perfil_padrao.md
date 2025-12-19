# Sistema de Perfis de Acesso - Regras Atualizadas

## ✅ Perfis e Permissões

### 🔹 Implantador (Perfil Padrão)
**Acesso**:
- ✅ Dashboard (apenas suas próprias implantações)
- ✅ Perfil

**Restrições**:
- ❌ NÃO pode criar implantações
- ❌ NÃO pode criar módulos
- ❌ NÃO vê implantações de outros usuários
- ❌ NÃO tem acesso a Planos de Sucesso
- ❌ NÃO tem acesso a Usuários

---

### 🔹 Coordenador
**Acesso**:
- ✅ Dashboard (todas as implantações)
- ✅ Perfil
- ✅ Planos de Sucesso (permissão total)
- ✅ Usuários (permissão total)

**Permissões**:
- ✅ Criar implantações
- ✅ Criar módulos
- ✅ Editar implantações
- ✅ Excluir implantações
- ✅ Gerenciar usuários
- ✅ Alterar perfis de outros usuários

---

### 🔹 Gerente
**Acesso**:
- ✅ Dashboard (todas as implantações)
- ✅ Perfil
- ✅ Planos de Sucesso (permissão total)
- ✅ Usuários (permissão total)

**Permissões**:
- ✅ Criar implantações
- ✅ Criar módulos
- ✅ Editar implantações
- ✅ Excluir implantações
- ✅ Gerenciar usuários
- ✅ Alterar perfis de outros usuários

---

### 🔹 Administrador
**Acesso**:
- ✅ Dashboard (todas as implantações)
- ✅ Perfil
- ✅ Planos de Sucesso (permissão total)
- ✅ Usuários (permissão total)

**Permissões**:
- ✅ Criar implantações
- ✅ Criar módulos
- ✅ Editar implantações
- ✅ Excluir implantações
- ✅ Gerenciar usuários
- ✅ Alterar perfis de outros usuários
- ✅ Proteção especial (ADMIN_EMAIL não pode ser alterado/excluído)

---

## 📋 Resumo de Permissões

| Funcionalidade | Implantador | Coordenador | Gerente | Administrador |
|----------------|:-----------:|:-----------:|:-------:|:-------------:|
| **Dashboard** | ✅ (só suas) | ✅ (todas) | ✅ (todas) | ✅ (todas) |
| **Perfil** | ✅ | ✅ | ✅ | ✅ |
| **Planos de Sucesso** | ❌ | ✅ | ✅ | ✅ |
| **Usuários** | ❌ | ✅ | ✅ | ✅ |
| **Criar Implantação** | ❌ | ✅ | ✅ | ✅ |
| **Criar Módulo** | ❌ | ✅ | ✅ | ✅ |
| **Editar Implantação** | ❌ | ✅ | ✅ | ✅ |
| **Excluir Implantação** | ❌ | ✅ | ✅ | ✅ |

---

## 🔧 Implementação Técnica

### Constantes Criadas (`constants.py`)

```python
# Perfis com permissão de gestão completa
PERFIS_COM_GESTAO = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]

# Perfis que podem criar implantações e módulos
PERFIS_COM_CRIACAO = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]

# Perfis que veem todas as implantações no dashboard
PERFIS_VER_TODAS_IMPLANTACOES = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]

# Perfis com acesso à página de Usuários
PERFIS_GERENCIAR_USUARIOS = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]

# Perfis com acesso ao Plano de Sucesso
PERFIS_PLANO_SUCESSO = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]
```

### Menu Lateral (`base.html`)

```html
{# Sempre visível para todos #}
- Dashboard
- Perfil

{# Apenas para Coordenador, Gerente e Administrador #}
{% if g.perfil and g.perfil.perfil_acesso in g.PERFIS_COM_GESTAO %}
  - Planos de Sucesso
  - Usuários
{% endif %}
```

### Proteção de Rotas (`management.py`)

```python
@management_bp.before_request
@permission_required(PERFIS_GERENCIAR_USUARIOS)
def before_request():
    """Protege todas as rotas de gerenciamento. 
    Acesso: Admin, Gerente, Coordenador."""
    pass
```

---

## 🎯 Perfil Padrão

**Novos usuários** recebem automaticamente o perfil **"Implantador"** ao fazer login pela primeira vez.

**Exceção**: `ADMIN_EMAIL` sempre recebe **"Administrador"** automaticamente.

---

## 📝 Arquivos Modificados

1. `backend/project/constants.py` - Novas constantes de permissão
2. `backend/project/domain/auth_service.py` - Perfil padrão Implantador
3. `backend/project/blueprints/management.py` - Proteção de rotas
4. `backend/project/config/config.py` - PERFIS_DE_ACESSO configurado
5. `frontend/templates/base.html` - Menu lateral com permissões

---

**Status**: ✅ Implementado e funcionando
