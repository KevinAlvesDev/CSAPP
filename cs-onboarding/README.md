# CS Onboarding

Sistema de gestão de onboarding de clientes.

## Sumário

- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Executando a Aplicação](#executando-a-aplicação)
- [Banco de Dados Externo](#banco-de-dados-externo)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Desenvolvimento](#desenvolvimento)
- [Troubleshooting](#troubleshooting)

## Requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Git
- OpenSSH Client (necessário apenas para acesso ao banco externo)

### Verificar instalações

```bash
python --version
pip --version
git --version
ssh -V
```

## Instalação

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd app-pacto/CSAPP/cs-onboarding
```

### 2. Criar ambiente virtual

```bash
python -m venv venv
```

### 3. Ativar ambiente virtual

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Instalar dependências

```bash
pip install -r requirements.txt
```

## Configuração

### 1. Criar arquivo de variáveis de ambiente

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

### 2. Gerar SECRET_KEY

Execute o comando abaixo para gerar uma chave secreta:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Editar arquivo .env

Abra o arquivo `.env` e configure as seguintes variáveis:

```bash
# OBRIGATÓRIO - Cole a chave gerada no passo anterior
SECRET_KEY=sua-chave-gerada-aqui

# Configurações básicas
PORT=5000
DEBUG=True
USE_SQLITE_LOCALLY=True
```

### Configuração Mínima

Para desenvolvimento local, apenas a `SECRET_KEY` é obrigatória. As demais configurações já possuem valores padrão adequados.

### Configurações Opcionais

#### Banco de Dados PostgreSQL (Produção)

```bash
DATABASE_URL=postgresql://usuario:senha@localhost:5432/nome_do_banco
USE_SQLITE_LOCALLY=False
```

#### Banco de Dados Externo (OAMD)

Necessário apenas para funcionalidades de integração. Veja seção [Banco de Dados Externo](#banco-de-dados-externo).

```bash
EXTERNAL_DB_URL=postgresql://cs_pacto:pacto@db@localhost:5433/oamd
```

#### Autenticação Auth0

```bash
AUTH0_ENABLED=True
AUTH0_DOMAIN=seu-dominio.auth0.com
AUTH0_CLIENT_ID=seu-client-id
AUTH0_CLIENT_SECRET=seu-client-secret
AUTH0_BASE_URL=http://localhost:5000
```

#### Google OAuth (Calendar)

```bash
GOOGLE_CLIENT_ID=seu-google-client-id
GOOGLE_CLIENT_SECRET=seu-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback
```

#### Cloudflare R2 Storage

```bash
CLOUDFLARE_ENDPOINT_URL=https://seu-account-id.r2.cloudflarestorage.com
CLOUDFLARE_ACCESS_KEY_ID=seu-access-key-id
CLOUDFLARE_SECRET_ACCESS_KEY=seu-secret-access-key
CLOUDFLARE_BUCKET_NAME=nome-do-bucket
```

#### Cache Redis

```bash
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
```

#### Monitoramento Sentry

```bash
SENTRY_DSN=https://seu-dsn@sentry.io/projeto-id
SENTRY_ENVIRONMENT=development
```

## Executando a Aplicação

### 1. Ativar ambiente virtual (se não estiver ativo)

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 2. Iniciar aplicação

```bash
python run.py
```

### 3. Acessar aplicação

Abra o navegador em: http://localhost:5000

### Parar a aplicação

Pressione `Ctrl+C` no terminal.

## Banco de Dados Externo

O banco de dados externo OAMD é necessário apenas para funcionalidades de integração com sistemas legados. Para desenvolvimento local básico, não é obrigatório.

### Pré-requisitos

- Credenciais SSH para `pacto@pactosolucoes.com.br`
- OpenSSH Client instalado

### Configurar túnel SSH

#### Opção 1: Script BAT (Windows)

```bash
ABRIR_TUNEL.bat
```

Mantenha a janela aberta durante o uso.

#### Opção 2: Script Python

```bash
python abrir_tunel.py
```

#### Opção 3: Comando SSH direto

```bash
ssh -N -L 5433:localhost:5432 pacto@pactosolucoes.com.br
```

### Configurar no .env

Com o túnel ativo, adicione ao arquivo `.env`:

```bash
EXTERNAL_DB_URL=postgresql://cs_pacto:pacto@db@localhost:5433/oamd
```

### Reiniciar aplicação

Após configurar o túnel e o `.env`, reinicie a aplicação:

```bash
# Parar com Ctrl+C
python run.py
```

### Notas importantes

- O túnel SSH deve permanecer ativo durante todo o uso do banco externo
- A porta local 5433 não pode estar em uso
- Se o túnel cair, reconecte antes de usar funcionalidades de integração

## Estrutura do Projeto

```
cs-onboarding/
├── backend/                    # Código backend
│   └── project/
│       ├── blueprints/         # Rotas e endpoints da API
│       ├── core/               # Configurações e extensões
│       ├── domain/             # Lógica de negócio
│       └── models/             # Modelos de dados (SQLAlchemy)
├── frontend/                   # Frontend
│   ├── static/                 # Arquivos estáticos (CSS, JS, imagens)
│   └── templates/              # Templates HTML (Jinja2)
├── migrations/                 # Migrações de banco de dados (Alembic)
├── scripts/                    # Scripts utilitários
├── .env                        # Variáveis de ambiente (não versionado)
├── .env.example                # Exemplo de configuração
├── requirements.txt            # Dependências Python
└── run.py                      # Ponto de entrada da aplicação
```

## Desenvolvimento

### Migrações de Banco de Dados

#### Criar nova migração

Após modificar modelos em `backend/project/models/`:

```bash
alembic revision --autogenerate -m "descrição da mudança"
```

#### Aplicar migrações

```bash
alembic upgrade head
```

#### Reverter última migração

```bash
alembic downgrade -1
```

### Atualizar dependências

Após atualizar código do repositório:

```bash
git pull
pip install -r requirements.txt
alembic upgrade head
```

### Adicionar nova dependência

```bash
pip install nome-do-pacote
pip freeze > requirements.txt
```

### Executar em modo debug

O modo debug já está ativado por padrão em desenvolvimento (`DEBUG=True` no `.env`).

Para desativar:

```bash
# No arquivo .env
DEBUG=False
```

### Logs

Os logs da aplicação são exibidos no terminal onde `run.py` está executando.

Para logs mais detalhados, mantenha `DEBUG=True`.

## Troubleshooting

### Erro: "SECRET_KEY não configurado"

**Causa:** Arquivo `.env` não existe ou `SECRET_KEY` não está definido.

**Solução:**

1. Copie `.env.example` para `.env`
2. Gere uma chave: `python -c "import secrets; print(secrets.token_hex(32))"`
3. Cole a chave no campo `SECRET_KEY` do arquivo `.env`

### Erro: "Módulo não encontrado"

**Causa:** Dependências não instaladas ou ambiente virtual não ativado.

**Solução:**

```bash
# Ativar ambiente virtual
.\venv\Scripts\activate          # Windows
source venv/bin/activate         # Linux/Mac

# Instalar dependências
pip install -r requirements.txt
```

### Erro: "Porta 5000 já em uso"

**Causa:** Outra aplicação está usando a porta 5000.

**Solução:**

Altere a porta no arquivo `.env`:

```bash
PORT=5001
```

Ou finalize o processo que está usando a porta 5000.

### Erro: "Não foi possível conectar ao banco de dados"

**Causa:** Configuração incorreta de banco de dados.

**Solução para SQLite (desenvolvimento):**

Verifique no `.env`:

```bash
USE_SQLITE_LOCALLY=True
```

**Solução para PostgreSQL:**

Verifique se:
- PostgreSQL está rodando
- Credenciais em `DATABASE_URL` estão corretas
- Banco de dados existe

### Erro: "Túnel SSH não conecta"

**Causa:** Credenciais SSH incorretas ou servidor inacessível.

**Solução:**

1. Verifique credenciais SSH
2. Teste conexão: `ssh pacto@pactosolucoes.com.br`
3. Verifique se porta 5433 não está em uso: `netstat -an | findstr 5433` (Windows) ou `lsof -i :5433` (Linux/Mac)
4. Verifique conectividade com o servidor

### Erro: "ImportError" ao executar run.py

**Causa:** Estrutura de diretórios incorreta ou módulo faltando.

**Solução:**

1. Verifique se está no diretório correto: `cs-onboarding/`
2. Verifique se `backend/project/` existe
3. Reinstale dependências: `pip install -r requirements.txt`

### Aplicação inicia mas retorna erro 500

**Causa:** Erro na aplicação ou configuração incorreta.

**Solução:**

1. Verifique logs no terminal
2. Ative modo debug no `.env`: `DEBUG=True`
3. Verifique se todas as variáveis obrigatórias estão configuradas
4. Verifique se banco de dados está acessível

### Erro ao fazer upload de arquivos

**Causa:** Cloudflare R2 não configurado.

**Solução:**

Para desenvolvimento local, uploads funcionam sem R2. Se necessário configurar:

```bash
CLOUDFLARE_ENDPOINT_URL=https://seu-account-id.r2.cloudflarestorage.com
CLOUDFLARE_ACCESS_KEY_ID=seu-access-key-id
CLOUDFLARE_SECRET_ACCESS_KEY=seu-secret-access-key
CLOUDFLARE_BUCKET_NAME=nome-do-bucket
```

### Ambiente virtual não ativa (Windows)

**Causa:** Política de execução do PowerShell.

**Solução:**

Execute como Administrador:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Ou use Command Prompt (cmd) ao invés de PowerShell.

### Erro: "python: command not found"

**Causa:** Python não instalado ou não está no PATH.

**Solução:**

1. Instale Python 3.8+ de https://www.python.org/downloads/
2. Durante instalação, marque "Add Python to PATH"
3. Reinicie o terminal

### Banco de dados SQLite corrompido

**Causa:** Interrupção durante escrita ou erro no banco.

**Solução:**

```bash
# Backup do banco atual (se houver dados importantes)
# Procure por arquivos .db na raiz do projeto

# Deletar banco corrompido
# Windows
del *.db

# Linux/Mac
rm *.db

# Reiniciar aplicação (criará novo banco)
python run.py
```

## Variáveis de Ambiente

### Obrigatórias

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| SECRET_KEY | Chave secreta Flask | `abc123...` (64 caracteres) |

