# CS Onboarding

Sistema de gestão de implantações para Customer Success.

---

## 🚀 Quick Start (Dev Local)

### 1. Clone e instale dependências

```bash
git clone https://github.com/seu-usuario/cs-onboarding.git
cd cs-onboarding

# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente (Windows)
.venv\Scripts\activate

# Ativar ambiente (Linux/Mac)
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
# Copiar exemplo de configuração
copy .env.example .env   # Windows
cp .env.example .env     # Linux/Mac
```

Edite o arquivo `.env` e configure:
- `SECRET_KEY` - chave secreta do Flask
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - para login Google OAuth
- Outras configurações conforme necessário

### 3. Rodar o servidor

```bash
python run.py
```

Acesse: **http://localhost:5000**

---

## 📁 Estrutura do Projeto

```
cs-onboarding/
├── backend/           # Flask app, blueprints, services
│   └── project/
│       ├── blueprints/   # Rotas (main, api, auth, etc.)
│       ├── domain/       # Lógica de negócio (SOLID)
│       └── database/     # Conexão e schema
├── frontend/          # Templates e assets
│   ├── static/
│   │   ├── css/          # Estilos (modular)
│   │   └── js/           # JavaScript
│   └── templates/        # Jinja2 templates
├── migrations/        # Alembic migrations
├── tests/             # Testes automatizados
├── docs/              # Documentação interna
└── run.py             # Entry point
```

---

## 🔧 Comandos Úteis

| Comando | Descrição |
|---------|-----------|
| `python run.py` | Rodar servidor de desenvolvimento |
| `pytest` | Rodar testes |
| `alembic upgrade head` | Aplicar migrations |

---

## 📚 Documentação

Documentação adicional está em `docs/`:

- [Guia do Túnel OAMD](docs/GUIA_TUNEL_OAMD.md)
- [Plano de Perfis e Permissões](docs/PLANO-PERFIS-PERMISSOES.md)
- [Inventário do Projeto](docs/INVENTARIO-PROJETO.md)

---

## 🌐 Deploy (Produção)

Ver [PRODUCTION.md](PRODUCTION.md) para instruções de deploy.
