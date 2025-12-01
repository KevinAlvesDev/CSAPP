# PRD - Configuração de Deploy no Railway

**Data:** 01/12/2025
**Projeto:** CS Onboarding (Backend Python/Flask)
**Responsável:** Equipe de Desenvolvimento

---

## 1. Visão Geral
Este documento detalha as especificações técnicas e o processo de configuração do ambiente de produção da aplicação **CS Onboarding** na plataforma **Railway**. O objetivo é documentar a infraestrutura necessária para garantir que a aplicação seja implantada corretamente, com alta disponibilidade e integração contínua.

## 2. Arquitetura de Deploy

*   **Plataforma:** [Railway](https://railway.app/)
*   **Linguagem/Runtime:** Python 3.x
*   **Framework Web:** Flask
*   **Servidor WSGI:** Gunicorn
*   **Banco de Dados:** PostgreSQL (Gerenciado pelo Railway)
*   **Build System:** Nixpacks (Automático)

## 3. Arquivos de Configuração Críticos

A configuração do deploy depende estritamente dos seguintes arquivos presentes na raiz do repositório:

### 3.1. Procfile
Define o comando de inicialização do servidor web. O Railway utiliza este arquivo para saber como iniciar a aplicação.

```text
web: gunicorn "run:app" --bind 0.0.0.0:$PORT --preload --timeout 60
```

*   **web:** Define o tipo de processo.
*   **run:app:** Aponta para o objeto `app` dentro do arquivo `run.py`.
*   **--bind 0.0.0.0:$PORT:** Garante que a aplicação escute na porta fornecida pelo Railway.
*   **--preload:** Carrega o código da aplicação antes de criar os processos de trabalho (melhora performance).
*   **--timeout 60:** Aumenta o tempo limite para 60 segundos (útil para requisições lentas).

### 3.2. requirements.txt
Lista todas as dependências Python necessárias. O Railway instala automaticamente estes pacotes durante o build.
**Importante:** Deve conter `gunicorn` e `psycopg2-binary` (para conexão com PostgreSQL).

### 3.3. run.py
Script de entrada da aplicação. Responsável por inicializar a factory do Flask (`create_app`) e carregar as configurações.

## 4. Variáveis de Ambiente (Environment Variables)

Para que a aplicação funcione em produção, as seguintes variáveis devem ser configuradas no painel do Railway ("Variables"):

| Variável | Descrição | Valor Exemplo / Origem |
| :--- | :--- | :--- |
| `PORT` | Porta do servidor | *Injetado automaticamente pelo Railway* |
| `DATABASE_URL` | String de conexão do Banco | *Injetado automaticamente ao conectar o PostgreSQL* |
| `SECRET_KEY` | Chave criptográfica do Flask | Gerar hash seguro (ex: via `openssl rand -hex 32`) |
| `USE_SQLITE_LOCALLY` | Flag de Banco de Dados | `False` (para forçar uso do PostgreSQL) |
| `FLASK_ENV` | Ambiente de execução | `production` |

### Variáveis Opcionais (Integrações)
Se as funcionalidades estiverem ativas, configurar também:
*   `AUTH0_*` (Autenticação)
*   `CLOUDFLARE_*` (Uploads R2)
*   `SENTRY_*` (Monitoramento)
*   `CACHE_REDIS_URL` (Se usar Redis)

## 5. Processo de Configuração (Passo a Passo)

1.  **Criação do Projeto:**
    *   Acessar Railway Dashboard.
    *   Clicar em "New Project" > "Deploy from GitHub repo".
    *   Selecionar o repositório `CSAPP`.

2.  **Provisionamento do Banco de Dados:**
    *   No canvas do projeto, clicar com botão direito > "Database" > "PostgreSQL".
    *   Aguardar a criação do container do banco.

3.  **Configuração de Variáveis:**
    *   Acessar o serviço da aplicação (repo GitHub).
    *   Ir na aba "Variables".
    *   Adicionar `SECRET_KEY` e `USE_SQLITE_LOCALLY=False`.
    *   **Importante:** O Railway injeta automaticamente a `DATABASE_URL` se o serviço do banco estiver no mesmo projeto. Caso contrário, copiar a *Connection URL* do PostgreSQL e adicionar manualmente.

4.  **Build e Deploy:**
    *   O Railway detectará automaticamente o arquivo `Procfile` e `requirements.txt`.
    *   O build iniciará usando **Nixpacks**.
    *   Após o sucesso do build, o deploy será realizado.

5.  **Verificação:**
    *   Acessar a URL pública gerada pelo Railway (aba "Settings" > "Networking" > "Generate Domain").
    *   Verificar logs na aba "Deployments" > "View Logs" para garantir que o Gunicorn iniciou sem erros.

## 6. Manutenção e Logs

*   **Logs:** Acessíveis em tempo real pelo dashboard do Railway.
*   **Redeploy:** Qualquer push no branch `main` (ou outro configurado) dispara um novo deploy automático.
*   **Rollback:** É possível reverter para um deploy anterior na aba "Deployments".
