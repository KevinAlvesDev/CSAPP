Documento de Especificação de Produto: CS Onboarding
1. OBJETO
O objeto deste documento é especificar a plataforma de software "CS Onboarding". Trata-se de uma aplicação web completa desenvolvida em Flask, projetada para gerenciar o processo de implantação (onboarding) de clientes por uma equipe de Customer Success (CS).

A plataforma permite que gestores criem e atribuam novas implantações aos membros da equipe (Implantadores). Cada implantador gerencia a sua carteira de clientes, acompanha o progresso através de checklists de tarefas detalhadas, regista comentários (com suporte a imagens) e move a implantação por um fluxo de status definido (de "Nova" a "Finalizada").

O sistema inclui módulos para Analytics, Gestão de Usuários e Gamificação para monitorizar a performance da equipa.

2. ESCOPO E FUNCIONALIDADES
O sistema deverá prover as seguintes funcionalidades:

2.1. Dashboard Principal (Visão do Usuário)

Exibição da página inicial após o login.

Visualização das implantações do usuário divididas em abas por status: "Novas", "Em Andamento", "Atrasadas", "Futuras", "Concluídas" e "Paradas".

Exibição de um resumo com a contagem total de implantações em cada status.

Permissão para perfis designados (PERFIS_COM_CRIACAO) criarem novas "Implantações Completas" ou "Módulos".

Capacidade de "Iniciar" implantações novas ou "Agendar Início Futuro".

2.2. Gestão de Implantação (Página de Detalhes)

Fornecimento de uma página de detalhes individual para cada implantação.

Disponibilização de checklists de tarefas divididas por módulos (ex: "Obrigações para finalização", "Welcome", "Módulo ADM", "Pendências").

Interatividade via API para marcar/desmarcar tarefas, adicionar/excluir comentários (com upload de imagens) e reordenar tarefas (drag-and-drop).

Registro automático de ações (criação, mudança de status, adição de tarefas) numa "Linha do Tempo".

Disponibilização de controlos de fluxo para "Parar", "Retomar", "Finalizar" ou "Reabrir" uma implantação, conforme o status atual.

2.3. Módulo Gerencial (Analytics)

Acesso restrito a perfis de gestão (PERFIS_COM_ANALYTICS).

Exibição de KPIs (Indicadores Chave de Performance) globais da equipa (ex: total de clientes, média de tempo de implantação, implantações atrasadas).

Fornecimento de filtros por Colaborador, Status e Período.

Renderização de gráficos (Chart.js) para Nível de Receita (MRR), Status dos Clientes e Rankings de performance.

2.4. Módulo de Gamificação

Interface para gestores (PERFIS_COM_GESTAO) inserirem métricas manuais por colaborador (ex: Nota de Qualidade, Assiduidade, Elogios, Penalidades).

Geração de um relatório (/gamification/report) que calcula e exibe a pontuação final, status de elegibilidade e detalhamento dos pontos de cada colaborador.

2.5. Gestão de Usuários e Perfis

Interface para usuários editarem o seu próprio perfil, incluindo nome, cargo e foto (com upload para o Cloudflare R2).

Interface para gestores (PERFIS_COM_GESTAO) visualizarem todos os usuários e alterarem o seu "Perfil de Acesso" (ex: 'Implantador', 'Gerente').

Funcionalidade restrita a "Administradores" para excluir usuários, removendo todos os seus dados e fotos associadas.

3. ESPECIFICAÇÕES TÉCNICAS
O software será desenvolvido utilizando a seguinte stack tecnológica:

Backend (Servidor): Python 3 com framework Flask.

Servidor de Aplicação (Produção): Gunicorn.

Frontend (Templates): HTML5 e Jinja2.

Estilização e UI: Bootstrap 5 e CSS customizado.

Interatividade (Cliente): JavaScript (ES6+) utilizando Fetch API e Chart.js.

Banco de Dados: Suporte dual-stack para PostgreSQL (Produção) e SQLite (Desenvolvimento).

Autenticação: Serviço externo Auth0 (OAuth).

Armazenamento de Arquivos: Serviço externo Cloudflare R2 (compatível com S3), gerenciado via Boto3.

Configuração de Ambiente: Gerenciada por variáveis de ambiente (arquivo .env).

4. REQUISITOS DE INSTALAÇÃO E CONFIGURAÇÃO
Para a execução local do sistema, os seguintes passos são necessários:

Dependências: Instalação de todas as bibliotecas Python listadas em requirements.txt.

Variáveis de Ambiente: Criação de um arquivo .env na raiz do projeto (CSAPP/), contendo as chaves de API para FLASK_SECRET_KEY, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_DOMAIN, e as credenciais do Cloudflare R2.

Banco de Dados:

Se DATABASE_URL não for fornecido no .env, o sistema utilizará o SQLite local (dashboard_simples.db).

A inicialização do schema deve ser feita executando o comando flask init-db.

Execução: A aplicação é iniciada executando python run.py.

5. ARQUITETURA DE COMPONENTES (ESTRUTURA DE ARQUIVOS)
O projeto está organizado da seguinte forma:

CSAPP/run.py: Ponto de entrada da aplicação.

CSAPP/Procfile: Configuração de deploy (Gunicorn).

CSAPP/requirements.txt: Dependências do projeto.

CSAPP/dashboard_simples.db: Banco de dados SQLite local (padrão de desenvolvimento).

CSAPP/project/: Diretório principal do código-fonte da aplicação Flask.

__init__.py: Fábrica de aplicação (função create_app).

config.py: Carregamento e gestão das variáveis de ambiente.

constants.py: Definições de negócio (listas de cargos, módulos de tarefas, perfis).

db.py: Lógica de conexão com o banco de dados e inicialização do schema.

extensions.py: Inicialização de serviços externos (Auth0, Boto3/R2).

services.py: Contém a lógica de negócio principal (cálculo de progresso, dados do dashboard, gamificação).

utils.py: Funções utilitárias (formatação de data, validação de arquivos).

blueprints/: Submódulos da aplicação:

analytics.py: Rotas do dashboard gerencial.

api.py: Endpoints RESTful para interações do frontend (ex: marcar tarefa).

auth.py: Rotas de autenticação (login, logout, callback Auth0).

gamification.py: Rotas para o sistema de gamificação.

main.py: Rotas principais (dashboard, detalhes da implantação).

management.py: Rotas para gestão de usuários.

profile.py: Rotas para edição de perfil do usuário.

CSAPP/static/: Arquivos estáticos (CSS, Imagens).

CSAPP/templates/: Arquivos de template HTML (Jinja2).

6. FLUXO DE TRABALHO DE IMPLANTAÇÕES

Estados principais:
- Nova: criada e aguardando início.
- Futura: agendada com data de início prevista.
- Em Andamento: iniciada com data de início efetivo.
- Parada: interrompida com data retroativa e motivo.
- Concluída: finalizada com todas as tarefas obrigatórias/treinamento concluídas.
- Atrasada: categoria derivada para implantações em andamento com tempo acima do limite.

Transições e validações:
- Nova → Em Andamento: permitido ao dono; registra data de início efetivo.
- Nova → Futura: agendamento requerido; grava data de início previsto.
- Futura → Em Andamento: permitido ao dono; limpa data prevista.
- Em Andamento → Parada: exige data da parada e motivo; registra na timeline.
- Parada → Em Andamento: retoma e limpa data de finalização/motivo da parada.
- Em Andamento → Concluída: só se tarefas obrigatórias/treinamento estiverem 100% concluídas.
- Finalizada → Em Andamento: reabertura permitida ao dono.

Regras de autorização e logs:
- Ações de status são permitidas ao dono da implantação ou perfis de gestão quando aplicável.
- Alterações registradas em timeline e nos logs da aplicação com usuário, implantação e resultado.
- Em desenvolvimento, o cache do dashboard é invalidado após cada alteração para refletir imediatamente.