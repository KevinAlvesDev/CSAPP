MODULO_OBRIGATORIO = "Obrigações para finalização"
CHECKLIST_OBRIGATORIO_ITEMS = [
    "Fotos da unidade",
    "Detalhes da Empresa",
    "Responsável do cliente",
    "Inicio em produção",
    "Plano de Sucesso",
    "Controle de acesso",
    "Importação concluída",
    "Nota Fiscal",
    "Recorrência",
    "Boleto",
    "Vendas Online",
    "App Treino",
    "Fechar grupo no WhatsApp"
]
MODULO_PENDENCIAS = "Pendências"

TAREFAS_TREINAMENTO_PADRAO = {
    "Welcome": [
        {"nome": "Contato Inicial Whatsapp/Grupo", "tag": "Ação interna"},
        {"nome": "Reunião de Welcome", "tag": "Reunião"}
    ],
    "Estruturação BD": [
        {"nome": "Criar Banco de Dados", "tag": "Ação interna"},
        {"nome": "Vincular a tela de apoio", "tag": "Ação interna"},
        {"nome": "Criar plano de sucesso", "tag": "Ação interna"},
        {"nome": "Ajustar Suporte para Celula Baby", "tag": "Ação interna"},
        {"nome": "Criar Aplicativo", "tag": "Ação interna"},
        {"nome": "Nota fiscal", "tag": "Ação interna"},
        {"nome": "Convênio de cobrança", "tag": "Ação interna"},
        {"nome": "Configurar Logo da Empresa", "tag": "Ação interna"}
    ],
    "Validar estruturação": [
    ],
    "Implantação em andamento": [
        {"nome": "Treinamento ADM Estrutural", "tag": "Reunião"},
        {"nome": "Treinamento ADM Operacional 1", "tag": "Reunião"},
        {"nome": "Treinamento ADM Operacional 2", "tag": "Reunião"},
        {"nome": "Vendas Online", "tag": "Reunião"},
        {"nome": "Importação de dados", "tag": "Ação interna"},
        {"nome": "Treinamento ADM Gerencial", "tag": "Reunião"},
        {"nome": "Teinamento tecnico  (treino/agenda/Cross)", "tag": "Reunião"},
        {"nome": "Treinamento CRM", "tag": "Reunião"},
        {"nome": "Treinamento financeiro", "tag": "Reunião"},
        {"nome": "Treinamento modulo graduação", "tag": "Reunião"},
        {"nome": "PactoPay", "tag": "Reunião"},
        {"nome": "Game Off Results", "tag": "Reunião"},
        {"nome": "Reunião tira-dúvida geral", "tag": "Reunião"}
    ],
    "Conclusão onboarding": [
        {"nome": "Concluir Processos Internos", "tag": "Ação interna"}
    ]
}

TASK_TIPS = {
    'reunião de kick-off': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Primeiro acesso ao sistema</li><li>Campos obrigatórios e necessários</li><li>Cadastro de usuários e colaboradores</li><li>Cadastro de produtos</li><li>Direcionamento de tarefas</li><li>Solicitação de backup</li></ul></div>",
    'reunião de welcome': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Primeiro acesso ao sistema</li><li>Campos obrigatórios e necessários</li><li>Cadastro de usuários e colaboradores</li><li>Cadastro de produtos</li><li>Direcionamento de tarefas</li><li>Solicitação de backup</li></ul></div>",
    'módulo adm|treinamento operacional 1': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Como cadastrar um novo cliente</li><li>A importância do Boletim de Visitas</li><li>Negociação de Contrato</li><li>Formas de Pagamento (tela de recebimento)</li><li>Venda Avulsa (Produto ou Serviço)</li><li>Venda Avulsa de Diária</li><li>FreePass</li><li>Fechamento de Caixa por Operador</li></ul></div>",
    'treinamento adm operacional 1': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Como cadastrar um novo cliente</li><li>A importância do Boletim de Visitas</li><li>Negociação de Contrato</li><li>Formas de Pagamento (tela de recebimento)</li><li>Venda Avulsa (Produto ou Serviço)</li><li>Venda Avulsa de Diária</li><li>FreePass</li><li>Fechamento de Caixa por Operador</li></ul></div>",
    'módulo adm|treinamento operacional 2': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Renovação de contrato</li><li>Assinatura de contrato</li><li>Alteração de vencimento da parcelas</li><li>Estorno de contrato</li><li>Férias</li><li>Atestado médico</li><li>Retorno de atestado e férias</li><li>Trancamento</li><li>Retorno de trancamento</li><li>Retorno de trancamento vencido</li><li>Cancelamento com transferância</li><li>Cancelamento com devolução</li><li>Cancelamento com devolução (Base mensal)</li><li>Cancelamento de planos recorrentes</li><li>Cancelamento para planos bolsa</li><li>Bônus</li><li>Alteração de horário</li><li>Manutenção de modalidade</li></ul></div>",
    'treinamento adm operacional 2': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Renovação de contrato</li><li>Assinatura de contrato</li><li>Alteração de vencimento da parcelas</li><li>Estorno de contrato</li><li>Férias</li><li>Atestado médico</li><li>Retorno de atestado e férias</li><li>Trancamento</li><li>Retorno de trancamento</li><li>Retorno de trancamento vencido</li><li>Cancelamento com transferância</li><li>Cancelamento com devolução</li><li>Cancelamento com devolução (Base mensal)</li><li>Cancelamento de planos recorrentes</li><li>Cancelamento para planos bolsa</li><li>Bônus</li><li>Alteração de horário</li><li>Manutenção de modalidade</li></ul></div>",
    'módulo adm|verificação de importação': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Ativar BI de verificação</li><li>Ensinar aos usuários a jornada de verificação</li></ul></div>",
    'importação de dados': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Ativar BI de verificação</li><li>Ensinar aos usuários a jornada de verificação</li></ul></div>",
    'módulo adm|treinamento gerencial': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>BI Grupo de Risco</li><li>BI Pendência de Clientes</li><li>BI Índice de Renovação</li><li>BI Conversão de Vendas</li><li>BI Metas Financeiras de Vendas</li><li>BI Ticket Médio de Planos</li><li>BI Cobranças por Convênio</li><li>BI Aulas Experimentais</li><li>BI Controle de Operações de Exceções</li><li>BI Inadimplência</li><li>BI de Gestão de Acessos</li><li>BI Wellhub</li><li>BI Ciclo de Vida do Cliente</li></ul></div>",
    'treinamento adm gerencial': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>BI Grupo de Risco</li><li>BI Pendência de Clientes</li><li>BI Índice de Renovação</li><li>BI Conversão de Vendas</li><li>BI Metas Financeiras de Vendas</li><li>BI Ticket Médio de Planos</li><li>BI Cobranças por Convênio</li><li>BI Aulas Experimentais</li><li>BI Controle de Operações de Exceções</li><li>BI Inadimplência</li><li>BI de Gestão de Acessos</li><li>BI Wellhub</li><li>BI Ciclo de Vida do Cliente</li></ul></div>",
    'módulo treino|estrutural': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Apresentação do Treino</li><li>Perfil de acesso no treino</li><li>Como editar usuários</li><li>Cadastros de aparelhos</li><li>Cadastros de atividades</li><li>Níveis</li><li>Fichas pré-definidas</li><li>Programas pré-definidos</li><li>Cadastro de disponibilidade (Agenda de Serviços)</li><li>Agendamento de aluno</li></ul></div>",
    'teinamento tecnico  (treino/agenda/cross)': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Apresentação do Treino</li><li>Perfil de acesso no treino</li><li>Como editar usuários</li><li>Cadastros de aparelhos</li><li>Cadastros de atividades</li><li>Níveis</li><li>Fichas pré-definidas</li><li>Programas pré-definidos</li><li>Cadastro de disponibilidade (Agenda de Serviços)</li><li>Agendamento de aluno</li></ul></div>",
    'módulo treino|operacional': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Tela de prescrição de treino</li><li>Perfil do aluno</li><li>Montagem de treino individual</li></ul></div>",
    'módulo treino|gerencial': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Treinos vencidos</li><li>Alunos sem treino</li><li>Treinos a vencer</li><li>Contratos a vencer</li><li>Treinos em dia</li><li>Alunos com treino</li><li>Execução de treinos nos últimos 30 dias</li><li>Avaliação média do treino dos alunos</li><li>Alunos com aviso médico</li><li>Andamento</li></ul></div>",
    'módulo treino|app treino': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Feed</li><li>Treino</li><li>Aulas</li><li>Dashboard (Professor)</li></ul></div>",
    'app treino': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Feed</li><li>Treino</li><li>Aulas</li><li>Dashboard (Professor)</li></ul></div>",
    'módulo crm|estrutural': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Gestão de carteiras</li><li>Concluído em 10/10/2025</li><li>Feriado</li><li>Meta Extra</li><li>Objeção</li><li>Script</li><li>Email para o contato em grupo</li><li>Contato em grupo (email, sms, app)</li></ul></div>",
    'treinamento crm': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Gestão de carteiras</li><li>Concluído em 10/10/2025</li><li>Feriado</li><li>Meta Extra</li><li>Objeção</li><li>Script</li><li>Email para o contato em grupo</li><li>Contato em grupo (email, sms, app)</li></ul></div>",
    'módulo crm|operacional': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Leads Hoje</li><li>Leads Acumuladas</li><li>Agend. Presenciais</li><li>Agendados de Amanhã</li><li>Visitantes 24h</li><li>Renovação</li><li>Desistentes</li><li>Indicações</li><li>Aluno Gympass</li><li>Grupo de Risco</li><li>Vencidos</li><li>Pós Venda</li><li>Aniversariantes</li><li>Indicações</li><li>Receptivo</li></ul></div>",
    'módulo crm|gerencial': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>BI CRM</li><li>Metas de vendas (meta, atingida, Respescagem)</li><li>Metas de Fidelização (meta, atingida, Respescagem)</li><li>Resultado (Meta, Atingida)</li><li>Objeções (Por Quabtidade, Por fase)</li><li>Desempenho Mensal dos Colaboradores</li><li>Agendamento de Ligações Pendente</li><li>Indicações Sem Contato</li><li>Contato Receptivo</li><li>Clientes Com Objeção Definitiva</li></ul></div>",
    'módulo financeiro|financeiro simplificado': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Financeiro Simplificado x Avançado</li><li>Plano de Contas</li><li>Centro de Custos</li><li>Rateio Integração</li><li>Fornecedores</li><li>Configurações</li><li>Lançamento de Contas a Pagar/Receber</li><li>Relatório de Contas a Pagar/Receber</li><li>Relatório Demonstrativo Financeiro</li><li>Relatório DRE Financeiro</li><li>Relatório Fluxo de Caixa</li><li>Gestão de Recebíveis</li><li>BI Financeiro</li></ul></div>",
    'treinamento financeiro': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Financeiro Simplificado x Avançado</li><li>Plano de Contas</li><li>Centro de Custos</li><li>Rateio Integração</li><li>Fornecedores</li><li>Configurações</li><li>Lançamento de Contas a Pagar/Receber</li><li>Relatório de Contas a Pagar/Receber</li><li>Relatório Demonstrativo Financeiro</li><li>Relatório DRE Financeiro</li><li>Relatório Fluxo de Caixa</li><li>Gestão de Recebíveis</li><li>BI Financeiro</li></ul></div>",
    'módulo financeiro|financeiro avançado': "<div class='text-start'><div class='fw-semibold mb-1'>Checklist:</div><ul class='mb-0 ps-3'><li>Cadastro de Contas</li><li>Cadastro das Taxas de Cartão</li><li>Configurações extras</li><li>Abrir/Fechar Caixa</li><li>Consulta/Reabertura de Caixa</li><li>Resumo de Contas</li><li>Gestão de Recebíveis (Movimentação)</li><li>Lote</li><li>Relatório Fluxo de Caixa</li></ul></div>"
}
