# CS Onboarding — Sistema de Gestão de Implantação de Clientes

> Plataforma completa para gerenciar o processo de onboarding (implantação) de novos clientes, incluindo checklists, gamificação, analytics e integração com ferramentas externas.

---

## 📋 Índice

- [Arquitetura](#arquitetura)
- [Tecnologias](#tecnologias)
- [Setup Local](#setup-local)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Como Rodar](#como-rodar)
- [Testes](#testes)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Deploy](#deploy)
- [Documentação Adicional](#documentação-adicional)

---

## 🏗️ Arquitetura

```
┌──────────────────────────────────────────────────┐
│                    Frontend                       │
│  (Jinja2 Templates + Vanilla JS + CSS)           │
│  ┌──────┐ ┌──────────┐ ┌───────────┐            │
│  │ Auth │ │ Dashboard │ │ Checklist │  ...        │
│  └──────┘ └──────────┘ └───────────┘            │
└──────────────────┬───────────────────────────────┘
                   │ HTTP/AJAX
┌──────────────────▼───────────────────────────────┐
│                Flask Backend                      │
│  ┌────────────────────────────────────────┐      │
│  │ Blueprints (Routes/Controllers)        │      │
│  │  auth, main, api, checklist, planos... │      │
│  └────────────────┬───────────────────────┘      │
│  ┌────────────────▼───────────────────────┐      │
│  │ Domain Services (Business Logic)       │      │
│  │  implantacao, checklist, gamification  │      │
│  │  auth, analytics, planos, notifications│      │
│  └────────────────┬───────────────────────┘      │
│  ┌────────────────▼───────────────────────┐      │
│  │ Data Layer (DB Abstraction)            │      │
│  │  query_db, execute_db, query_helpers   │      │
│  └────────────────────────────────────────┘      │
└──────────────────┬───────────────────────────────┘
                   │
    ┌──────────────┼──────────────────┐
    ▼              ▼                  ▼
┌────────┐  ┌───────────┐    ┌──────────────┐
│ SQLite │  │ PostgreSQL│    │ External DB  │
│ (Dev)  │  │ (Prod)    │    │ (OAMD/SSH)   │
└────────┘  └───────────┘    └──────────────┘
```

### Componentes Externos Integrados
- **Auth0** — Autenticação principal em produção
- **Google OAuth** — Login alternativo + Google Calendar
- **Cloudflare R2** — Storage de arquivos/uploads
- **Sentry** — Monitoramento de erros
- **SMTP/SendGrid** — Envio de emails/notificações

---

## 🛠️ Tecnologias

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Backend | Python + Flask | 3.11+ / 3.1.x |
| Frontend | Jinja2 + Vanilla JS + CSS | — |
| DB Produção | PostgreSQL | 14+ |
| DB Local | SQLite | 3 |
| Auth | Auth0 + Google OAuth | — |
| Storage | Cloudflare R2 (S3-compatible) | — |
| Cache | Flask-Caching (Redis opcional) | — |
| Monitoramento | Sentry | — |

---

## 🚀 Setup Local

### Pré-requisitos
- **Python 3.11+** instalado
- **Git** configurado
- (Opcional) **PostgreSQL** se quiser testar com banco real
- (Opcional) **Redis** para cache

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd cs-onboarding
```

### 2. Criar ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

```bash
# Copiar o arquivo de exemplo
cp .env.example .env

# Gerar uma SECRET_KEY segura
python -c "import secrets; print(secrets.token_hex(32))"

# Cole a chave gerada no campo SECRET_KEY do .env
```

### 5. Rodar a aplicação

```bash
python run.py
```

A aplicação estará disponível em `http://localhost:5000`.

> **Nota:** Em modo local (SQLite), o sistema cria automaticamente um usuário admin (`admin@admin.com` / `admin123@`) e desabilita Auth0.

---

## 🔐 Variáveis de Ambiente

### Obrigatórias (todos os ambientes)

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `SECRET_KEY` | Chave secreta Flask | `hex de 64 chars` |

### Obrigatórias (produção)

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `DATABASE_URL` | URI do PostgreSQL | `postgresql://user:pass@host:5432/db` |

### Autenticação (opcional em dev)

| Variável | Descrição |
|----------|-----------|
| `AUTH0_ENABLED` | `true` para ativar Auth0 |
| `AUTH0_DOMAIN` | Domínio Auth0 |
| `AUTH0_CLIENT_ID` | Client ID Auth0 |
| `AUTH0_CLIENT_SECRET` | Client Secret Auth0 |
| `GOOGLE_CLIENT_ID` | Client ID Google OAuth |
| `GOOGLE_CLIENT_SECRET` | Client Secret Google OAuth |
| `GOOGLE_REDIRECT_URI` | URI de callback Google |

### Storage (opcional)

| Variável | Descrição |
|----------|-----------|
| `CLOUDFLARE_ENDPOINT_URL` | Endpoint R2 |
| `CLOUDFLARE_ACCESS_KEY_ID` | Access Key R2 |
| `CLOUDFLARE_SECRET_ACCESS_KEY` | Secret Key R2 |
| `CLOUDFLARE_BUCKET_NAME` | Nome do bucket |
| `CLOUDFLARE_PUBLIC_URL` | URL pública do bucket |

### Email (opcional)

| Variável | Descrição |
|----------|-----------|
| `EMAIL_DRIVER` | `smtp` ou `sendgrid` |
| `SMTP_HOST` | Host SMTP |
| `SMTP_PORT` | Porta (padrão: 587) |
| `SMTP_USER` | Usuário SMTP |
| `SMTP_PASSWORD` | Senha SMTP |
| `SMTP_FROM` | Email remetente |

### Desenvolvimento

| Variável | Descrição | Default |
|----------|-----------|---------|
| `USE_SQLITE_LOCALLY` | Usar SQLite local | `True` |
| `DEBUG` | Modo debug | `True` |
| `PORT` | Porta do servidor | `5000` |

> Veja `.env.example` para a lista completa.

---

## 🧪 Testes

```bash
# Instalar dependências de teste
pip install pytest pytest-cov pytest-mock

# Rodar todos os testes
pytest

# Com cobertura de código
pytest --cov=backend/project --cov-report=html

# Apenas testes unitários
pytest tests/unit/ -v

# Apenas testes de integração
pytest tests/integration/ -v -m integration

# Excluir testes lentos
pytest -m "not slow"
```

---

## 📁 Estrutura do Projeto

```
cs-onboarding/
├── backend/
│   ├── project/
│   │   ├── __init__.py          # App factory (create_app)
│   │   ├── blueprints/          # Routes/Controllers
│   │   │   ├── auth.py          # Autenticação
│   │   │   ├── main.py          # Dashboard/páginas principais
│   │   │   ├── api.py           # API interna
│   │   │   ├── api_v1.py        # API v1 (externa)
│   │   │   ├── checklist_api.py # API de checklist
│   │   │   ├── onboarding/      # Módulo de onboarding
│   │   │   ├── grandes_contas/  # Módulo grandes contas
│   │   │   └── ...
│   │   ├── common/              # Utilities compartilhadas
│   │   │   ├── utils.py         # Helpers gerais
│   │   │   ├── validation.py    # Validação de dados
│   │   │   ├── query_helpers.py # Helpers de SQL
│   │   │   └── ...
│   │   ├── config/              # Configurações
│   │   │   ├── config.py        # Config principal
│   │   │   ├── cache_config.py  # Cache settings
│   │   │   ├── logging_config.py# Logging setup
│   │   │   ├── secrets_validator.py # Validação de secrets
│   │   │   └── log_sanitizer.py # Sanitização de logs
│   │   ├── database/            # Camada de dados
│   │   ├── domain/              # Lógica de negócio (services)
│   │   │   ├── implantacao/     # Serviço de implantação
│   │   │   ├── checklist/       # Serviço de checklist
│   │   │   ├── gamification/    # Serviço de gamificação
│   │   │   ├── planos/          # Serviço de planos  
│   │   │   └── ...
│   │   ├── monitoring/          # Performance monitoring
│   │   └── security/            # Middleware de segurança
│   └── migrations/              # Migrations de schema
├── frontend/
│   ├── static/
│   │   ├── css/                 # Estilos
│   │   ├── js/                  # JavaScript
│   │   └── imagens/             # Assets
│   └── templates/               # Templates Jinja2
├── migrations/                  # Alembic migrations
├── docs/                        # Documentação
│   ├── adr/                     # Architecture Decision Records
│   └── PLANO_DE_ACAO.md         # Plano de melhorias
├── .env.example                 # Variáveis de ambiente (exemplo)
├── .pre-commit-config.yaml      # Pre-commit hooks
├── pyproject.toml               # Configuração de ferramentas
├── requirements.txt             # Dependências Python
├── run.py                       # Entry point
└── Procfile                     # Deploy config
```

---

## 🚢 Deploy

### Railway / Render

A aplicação usa Gunicorn em produção (definido no `Procfile`):

```
web: gunicorn backend.project:create_app() --bind 0.0.0.0:$PORT
```

### Variáveis obrigatórias para deploy:
1. `SECRET_KEY` — Gere uma chave única para produção
2. `DATABASE_URL` — URI do PostgreSQL
3. Configure Auth0 ou Google OAuth para autenticação
4. (Opcional) Configure R2, SMTP, Sentry

---

## 📚 Documentação Adicional

- [CONTRIBUTING.md](./CONTRIBUTING.md) — Guia de contribuição
- [docs/adr/](./docs/adr/) — Architecture Decision Records
- [docs/PLANO_DE_ACAO.md](./docs/PLANO_DE_ACAO.md) — Plano de melhorias
- [.env.example](./.env.example) — Template de variáveis de ambiente

---

## 📝 Licença

Projeto proprietário — uso interno.
