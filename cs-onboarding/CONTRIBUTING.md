# Guia de Contribuição — CS Onboarding

Obrigado por contribuir com o CS Onboarding! Este documento descreve os padrões e processos para manter a qualidade do código.

---

## 📋 Índice

- [Ambiente de Desenvolvimento](#ambiente-de-desenvolvimento)
- [Padrões de Código](#padrões-de-código)
- [Processo de PR](#processo-de-pr)
- [Convenção de Commits](#convenção-de-commits)
- [Revisão de Código](#revisão-de-código)

---

## 🛠️ Ambiente de Desenvolvimento

### Setup inicial

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd cs-onboarding

# 2. Crie o ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. Instale todas as dependências
pip install -r requirements.txt
pip install pre-commit ruff mypy  # Ferramentas de desenvolvimento

# 4. Configure o pre-commit
pre-commit install

# 5. Configure o .env
cp .env.example .env
# Edite o .env com suas configurações
```

### Pre-commit Hooks

O projeto usa pre-commit hooks para garantir qualidade. Eles rodam automaticamente em cada `git commit`:

```bash
# Instalar hooks
pre-commit install

# Rodar manualmente em todos os arquivos
pre-commit run --all-files

# Atualizar hooks
pre-commit autoupdate
```

---

## 📏 Padrões de Código

### Python (Backend)

- **Linter/Formatter**: [Ruff](https://docs.astral.sh/ruff/) (substitui flake8, isort, black)
- **Type Checker**: [Mypy](https://mypy.readthedocs.io/)
- **Estilo**: PEP 8 com line-length de 120 caracteres
- **Python Version**: 3.11+

#### Regras Ruff ativas

| Código | Descrição |
|--------|-----------|
| E | pycodestyle errors |
| F | pyflakes |
| W | pycodestyle warnings |
| I | isort (import sorting) |
| B | flake8-bugbear |
| C4 | flake8-comprehensions |
| UP | pyupgrade |
| SIM | flake8-simplify |

#### Executar manualmente

```bash
# Verificar erros
ruff check backend/ --fix

# Formatar código
ruff format backend/

# Type check
mypy backend/project --strict
```

#### Padrões de nomenclatura

```python
# ✅ Correto
def criar_implantacao_service(empresa: str, responsavel: str) -> dict:
    """Cria uma nova implantação."""
    ...

class ImplantacaoService:
    """Serviço de domínio para implantações."""
    ...

# Variáveis e funções: snake_case
nome_empresa = "Acme Corp"

# Classes: PascalCase
class ChecklistItem:
    ...

# Constantes: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
PERFIL_ADMIN = "Administrador"
```

#### Docstrings

Use docstrings em todas as funções públicas:

```python
def calcular_progresso(implantacao_id: int) -> dict:
    """
    Calcula o progresso de uma implantação.

    Args:
        implantacao_id: ID da implantação

    Returns:
        Dict com 'total', 'concluidos' e 'percentual'

    Raises:
        ValueError: Se implantação não existir
    """
    ...
```

### JavaScript (Frontend)

- **Linter**: ESLint com config Airbnb-base
- **Estilo**: Sem frameworks pesados (vanilla JS)
- **Nomenclatura**: camelCase para variáveis/funções, PascalCase para classes

```javascript
// ✅ Correto
const implantacaoId = 42;
function carregarDashboard() { ... }
class ModalManager { ... }

// ❌ Incorreto
var implantacao_id = 42;
function CarregarDashboard() { ... }
```

### SQL

- **Palavras-chave**: MAIÚSCULAS (`SELECT`, `FROM`, `WHERE`)
- **Aliases**: snake_case
- **Parametrização**: Sempre usar `%s` (nunca f-strings com valores do usuário)

```sql
-- ✅ Correto
SELECT i.id, i.nome_empresa, p.nome AS responsavel
FROM implantacoes i
LEFT JOIN perfil_usuario p ON p.usuario = i.responsavel
WHERE i.status = %s
ORDER BY i.created_at DESC;

-- ❌ NUNCA fazer isso (SQL Injection)
f"SELECT * FROM implantacoes WHERE id = {user_input}"
```

---

## 🔄 Processo de PR

### Workflow

```
1. Criar branch a partir de main
   └─ git checkout -b tipo/descricao-curta

2. Desenvolver com commits atômicos
   └─ git commit -m "feat: adiciona filtro por status no dashboard"

3. Push e abrir PR
   └─ git push origin tipo/descricao-curta

4. Code Review
   └─ Pelo menos 1 aprovação necessária

5. Merge
   └─ Squash and merge (manter histórico limpo)
```

### Nomes de Branch

```
feat/descricao       → Nova funcionalidade
fix/descricao        → Correção de bug
refactor/descricao   → Refatoração sem mudança de comportamento
docs/descricao       → Documentação
chore/descricao      → Tarefas de manutenção
hotfix/descricao     → Correção urgente em produção
```

### Template de PR

```markdown
## Descrição
[O que foi feito e por quê]

## Tipo de Mudança
- [ ] Nova funcionalidade
- [ ] Correção de bug
- [ ] Refatoração
- [ ] Documentação
- [ ] Hotfix

## Como Testar
[Passos para verificar a mudança]

## Screenshots (se aplicável)
[Imagens do antes/depois]

## Checklist
- [ ] Código segue os padrões do projeto
- [ ] Pre-commit hooks passam sem erros
- [ ] Testes adicionados/atualizados
- [ ] Documentação atualizada (se necessário)
```

---

## 📝 Convenção de Commits

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

### Formato

```
<tipo>(<escopo>): <descrição>

[corpo opcional]

[rodapé opcional]
```

### Tipos

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| `feat` | Nova funcionalidade | `feat(checklist): adiciona drag-and-drop de itens` |
| `fix` | Correção de bug | `fix(auth): corrige redirect após login` |
| `refactor` | Refatoração | `refactor(dashboard): extrai lógica para service` |
| `docs` | Documentação | `docs: atualiza README com setup local` |
| `style` | Formatação (sem mudança de lógica) | `style: aplica ruff format em todo backend` |
| `test` | Adição/correção de testes | `test(auth): adiciona testes de login` |
| `chore` | Manutenção | `chore: atualiza dependências` |
| `perf` | Performance | `perf(queries): otimiza N+1 no dashboard` |
| `ci` | CI/CD | `ci: adiciona workflow de testes` |
| `security` | Segurança | `security: adiciona sanitização de logs` |

### Escopos comuns

`auth`, `dashboard`, `checklist`, `implantacao`, `gamification`, `analytics`, `planos`, `api`, `db`, `config`, `frontend`

### Exemplos

```bash
# ✅ Bons commits
git commit -m "feat(checklist): adiciona sistema de comentários com email"
git commit -m "fix(auth): corrige loop infinito no callback do Auth0"
git commit -m "refactor(implantacao): extrai lógica de cálculo de tempo"
git commit -m "perf(dashboard): reduz queries de 47 para 3 com JOINs"
git commit -m "security: adiciona validação de secrets no startup"

# ❌ Commits ruins
git commit -m "fix bug"
git commit -m "atualização"
git commit -m "wip"
git commit -m "changes"
```

---

## 👀 Revisão de Código

### Checklist do Revisor

- [ ] **Funcionalidade**: O código faz o que é proposto?
- [ ] **Segurança**: Há SQL injection, XSS, ou vazamento de dados?
- [ ] **Performance**: Há queries N+1 ou loops desnecessários?
- [ ] **Legibilidade**: O código é fácil de entender?
- [ ] **Testes**: Os cenários principais estão cobertos?
- [ ] **Edge cases**: E se o input for nulo/vazio/muito grande?
- [ ] **Erro handling**: Exceções são tratadas adequadamente?

### Feedback

Use prefixos para clareza:

- `MUST:` — Obrigatório corrigir antes do merge
- `SHOULD:` — Fortemente recomendado
- `COULD:` — Sugestão de melhoria (não bloqueia merge)
- `NIT:` — Cosmético (formatação, naming)
- `QUESTION:` — Dúvida/entendimento

---

## 🔒 Segurança

### Regras Fundamentais

1. **NUNCA** commit secrets, tokens ou senhas no código
2. **NUNCA** use f-strings com input do usuário em SQL
3. **SEMPRE** valide inputs do usuário (backend)
4. **SEMPRE** use CSRF tokens em formulários
5. **SEMPRE** sanitize output em templates (Jinja2 faz por padrão)
6. Se encontrar um vazamento de segurança, reporte **imediatamente**

### Veja Também

- `backend/project/config/secrets_validator.py` — Validação de secrets
- `backend/project/config/log_sanitizer.py` — Sanitização de logs
- `backend/project/security/` — Middleware de segurança
