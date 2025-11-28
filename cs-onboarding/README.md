# CS Onboarding Platform

Plataforma web completa para gerenciamento de processos de implantação (onboarding) de clientes, desenvolvida para equipes de Customer Success.

## 📋 Sobre o Projeto

O **CS Onboarding** é uma aplicação Flask que permite gestores criarem e atribuírem implantações aos membros da equipe, com acompanhamento completo através de checklists, comentários, timeline de atividades e gamificação.

### Principais Funcionalidades

- **Dashboard Intuitivo**: Visualização de implantações por status (Novas, Em Andamento, Atrasadas, Futuras, Concluídas, Paradas)
- **Gestão de Implantações**: Checklists personalizáveis, comentários com upload de imagens, drag-and-drop
- **Analytics**: KPIs, gráficos interativos, relatórios de performance
- **Gamificação**: Sistema de pontuação e rankings para motivar a equipe
- **Gestão de Usuários**: Perfis, permissões granulares, upload de fotos
- **Integração com Google Calendar**: Sincronização automática de agendamentos

## 🚀 Stack Tecnológica

### Backend
- **Python 3.10+**
- **Flask 3.1.2** - Framework web
- **PostgreSQL** - Banco de dados (produção)
- **SQLite** - Banco de dados (desenvolvimento)
- **Gunicorn** - Servidor WSGI

### Frontend
- **HTML5 + Jinja2** - Templates
- **Bootstrap 5** - Framework CSS
- **JavaScript ES6+** - Interatividade
- **Chart.js** - Gráficos e visualizações

### Integrações
- **Auth0** - Autenticação OAuth
- **Cloudflare R2** - Storage de arquivos (compatível S3)
- **Google OAuth** - Integração com Google Calendar
- **Sentry** - Monitoramento de erros (opcional)

## 📦 Instalação

### Pré-requisitos

- Python 3.10 ou superior
- pip (gerenciador de pacotes Python)
- PostgreSQL (para produção) ou SQLite (para desenvolvimento)

### Passos de Instalação

1. **Clone o repositório**
```bash
git clone https://github.com/seu-usuario/CSAPP.git
cd CSAPP
```

2. **Crie e ative um ambiente virtual**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente**
```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite o arquivo .env com suas credenciais
# Obrigatório: FLASK_SECRET_KEY, AUTH0_* (se usar Auth0), R2_* (se usar uploads)
```

5. **Inicialize o banco de dados**
```bash
# Para SQLite (desenvolvimento)
python run.py
# O banco será criado automaticamente

# Para PostgreSQL (produção)
# Configure DATABASE_URL no .env
# Execute as migrations
alembic upgrade head
```

6. **Execute a aplicação**
```bash
# Desenvolvimento
python run.py

# Produção
gunicorn "run:app" --bind 0.0.0.0:5000 --preload --timeout 60
```

7. **Acesse a aplicação**
```
http://localhost:5000
```

## 🔧 Configuração

### Modo Desenvolvimento (SQLite)

No arquivo `.env`, configure:
```env
USE_SQLITE_LOCALLY=True
DEBUG=True
AUTH0_ENABLED=False  # Opcional: desabilita Auth0 para dev local
```

### Modo Produção (PostgreSQL)

No arquivo `.env`, configure:
```env
DATABASE_URL=postgresql://user:password@host:port/database
USE_SQLITE_LOCALLY=False
DEBUG=False
AUTH0_ENABLED=True
```

## 📁 Estrutura do Projeto

```
CSAPP/
├── backend/
│   ├── project/
│   │   ├── blueprints/      # Rotas e endpoints
│   │   ├── common/          # Utilitários compartilhados
│   │   ├── config/          # Configurações
│   │   ├── core/            # Core do sistema
│   │   ├── database/        # Conexões e pools
│   │   ├── domain/          # Lógica de negócio
│   │   ├── integrations/    # Integrações externas
│   │   ├── monitoring/      # Monitoramento
│   │   ├── security/        # Segurança
│   │   └── tasks/           # Tarefas assíncronas
│   └── tools/               # Scripts e ferramentas
├── frontend/
│   ├── static/
│   │   ├── css/            # Estilos
│   │   ├── js/             # JavaScript
│   │   └── imagens/        # Imagens
│   └── templates/          # Templates HTML
├── migrations/             # Migrations Alembic
├── docs/                   # Documentação
├── run.py                  # Entry point
├── requirements.txt        # Dependências
├── Procfile               # Config Heroku/Deploy
├── alembic.ini            # Config Alembic
└── .env                    # Variáveis de ambiente (não versionado)
```

## 🔐 Segurança

- **Autenticação**: OAuth via Auth0 ou Google
- **CSRF Protection**: Flask-WTF
- **Rate Limiting**: Flask-Limiter
- **Security Headers**: Flask-Talisman
- **Sanitização**: Validação de inputs
- **Logging**: Logs detalhados de ações críticas

## 📊 Migrations

O projeto usa **Alembic** para gerenciamento de migrations:

```bash
# Criar uma nova migration
alembic revision --autogenerate -m "Descrição da mudança"

# Aplicar migrations
alembic upgrade head

# Reverter migration
alembic downgrade -1
```

## 🧪 Testes

```bash
# Execute os testes
pytest

# Com cobertura
pytest --cov=project
```

## 📝 Documentação Adicional

- [Especificação Completa](docs/SPECIFICATION.md) - Documento técnico detalhado
- [Roadmap de Melhorias](docs/ROADMAP_MELHORIAS.md) - Planejamento de features
- [API Endpoints](docs/API_ENDPOINTS.md) - Documentação da API REST

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto é proprietário e confidencial.

## 👥 Equipe

Desenvolvido pela equipe de Customer Success.

## 📞 Suporte

Para dúvidas ou problemas, entre em contato com a equipe de desenvolvimento.

---

**Versão**: 1.0.0  
**Última Atualização**: Novembro 2025

