# Definições Globais
MODULO_OBRIGATORIO = "Obrigações para finalização"
CHECKLIST_OBRIGATORIO_ITEMS = [
    "Fotos da unidade", "Propósito", "Descrição do Grupo", "Detalhes da Empresa",
    "Inicio em produção", "Documento", "Detalhes da Empresa no Dashboard",
    "Ticket catraca", "Atendimento OADM", "Módulo OAMD", "Plano de Sucesso",
    "Fechar grupo no WhatsApp"
]
MODULO_PENDENCIAS = "Pendências"

TAREFAS_TREINAMENTO_PADRAO = {
    "Welcome": [
        {'nome': "Contato Inicial Whatsapp/Grupo", 'tag': "Ação interna"},
        {'nome': "Criar Banco de Dados", 'tag': "Ação interna"},
        {'nome': "Criar Usuário do Proprietário", 'tag': "Ação interna"},
        {'nome': "Reunião de Kick-Off", 'tag': "Reunião"}
    ],
    "Estruturação de BD": [
        {'nome': "Configurar planos", 'tag': "Ação interna"},
        {'nome': "Configurar modelo de contrato", 'tag': "Ação interna"},
        {'nome': "Configurar logo da empresa", 'tag': "Ação interna"},
        {'nome': "Convênio de cobrança", 'tag': "Ação interna"},
        {'nome': "Nota Fiscal", 'tag': "Ação interna"}
    ],
    "Importação de dados": [
        {'nome': "Jira de implantação de dados", 'tag': "Ação interna"},
        {'nome': "Importação de cartões de crédito", 'tag': "Ação interna"}
    ],
    "Módulo ADM": [
        {'nome': "Treinamento Operacional 1", 'tag': "Reunião"},
        {'nome': "Treinamento Operacional 2", 'tag': "Reunião"},
        {'nome': "Treinamento Gerencial", 'tag': "Reunião"},
        {'nome': "WellHub", 'tag': "Ação interna"},
        {'nome': "TotalPass", 'tag': "Ação interna"},
        {'nome': "Pacto Flow", 'tag': "Reunião"},
        {'nome': "Vendas Online", 'tag': "Reunião"},
        {'nome': "Verificação de Importação", 'tag': "Reunião"},
        {'nome': "Controle de acesso", 'tag': "Reunião"},
        {'nome': "App Pacto", 'tag': "Reunião"}
    ],
    "Módulo Treino": [
        {'nome': "Estrutural", 'tag': "Reunião"},
        {'nome': "Operacional", 'tag': "Reunião"},
        {'nome': "Agenda", 'tag': "Reunião"},
        {'nome': "Treino Gerencial", 'tag': "Reunião"},
        {'nome': "App Treino", 'tag': "Reunião"},
        {'nome': "Avaliação Física", 'tag': "Reunião"},
        {'nome': "Retira Fichas", 'tag': "Reunião"}
    ],
    "Módulo CRM": [
        {'nome': "Estrutural", 'tag': "Reunião"},
        {'nome': "Operacional", 'tag': "Reunião"},
        {'nome': "Gerencial", 'tag': "Reunião"},
        {'nome': "GymBot", 'tag': "Reunião"},
        {'nome': "Conversas IA", 'tag': "Reunião"}
    ],
    "Módulo Financeiro": [
        {'nome': "Financeiro Simplificado", 'tag': "Reunião"},
        {'nome': "Financeiro Avançado", 'tag': "Reunião"},
        {'nome': "FyPay", 'tag': "Reunião"}
    ],
    "Conclusão": [
        {'nome': "Tira dúvidas", 'tag': "Reunião"},
        {'nome': "Concluir processos internos", 'tag': "Ação interna"}
    ]
}

JUSTIFICATIVAS_PARADA = [
    "Pausa solicitada pelo cliente",
    "Aguardando dados / material do cliente",
    "Cliente em viagem / Férias",
    "Aguardando pagamento / Questões financeiras",
    "Revisão interna de processos",
    "Outro (detalhar nos comentários da implantação)"
]

CARGOS_RESPONSAVEL = [
    "Proprietário(a)", "Sócio(a)", "Gerente", "Coordenador(a)",
    "Analista de TI", "Financeiro", "Outro"
]

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

CARGOS_LIST = ["Júnior", "Pleno", "Sênior"]