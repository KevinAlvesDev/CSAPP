# project/constants.py
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
    # AJUSTE 4: NOVO MÓDULO ADICIONADO
    "Definição de carteira": [
        {'nome': "Definição de carteira", 'tag': "Ação interna"}
    ],
    # FIM DO AJUSTE 4
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

# --- Valor Padrão para Sim/Não (Booleans) ---
NAO_DEFINIDO_BOOL = "Não definido" 

# --- Opções para Seleção Sim/Não no Front-end ---
SIM_NAO_OPTIONS = [NAO_DEFINIDO_BOOL, "Sim", "Não"]

# --- Cargos e Perfis de Acesso ---
ADMIN_EMAIL = "kevinalveswp@gmail.com" 

# Cargos (Função na empresa, editável pelo usuário no perfil)
CARGOS_LIST = ["Júnior", "Pleno", "Sênior", "Estagiário"] 

# Perfis de Acesso (Permissão no sistema, editável apenas pelo Admin/Gerente/Coordenador)
PERFIL_ADMIN = "Administrador"
PERFIL_GERENTE = "Gerente"
PERFIL_COORDENADOR = "Coordenador"
PERFIL_IMPLANTADOR = "Implantador" # <-- NOME ALTERADO
PERFIL_VISUALIZADOR = "Visualizador"
PERFIS_ACESSO_LIST = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR, PERFIL_IMPLANTADOR, PERFIL_VISUALIZADOR] # <-- LISTA ATUALIZADA

PERFIS_COM_GESTAO = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR] 

# Perfis que podem criar implantações (Exclui visualizador e perfis NULL)
# <-- 'PERFIL_IMPLANTADOR' REMOVIDO DESTA LISTA
PERFIS_COM_CRIACAO = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]

# Perfis que podem ver a tela de Analytics (Gerentes e acima)
PERFIS_COM_ANALYTICS = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]


# INÍCIO DA CORREÇÃO (Dropdown "Nível de Receita")
NIVEIS_RECEITA = [
    "Prata (MRR go grupo abaixo de R$699,99)",
    "Ouro (MRR go grupo entre R$700,00 a R$999,99)",
    "Platina (MRR go grupo entre R$1.000,00 a R$1999,99)",
    "Diamante (MRR go grupo acima de R$2000,00)",
    "Grandes contas"
]
# FIM DA CORREÇÃO

SEGUIMENTOS_LIST = [
    "Natação", "Estúdio/Boutique", "Pilates", "Cross", "Low Cost", 
    "Full Service", "Escola", "Quadra de Areia", "Personal Trainer", "Outro"
]

TIPOS_PLANOS = ["Recorrência", "Normal", "Plano Personal", "Plano de Crédito", "Misto"]

MODALIDADES_LIST = ["Musculação", "Aulas Coletivas Gerais", "Natação", "Lutas", "Outros"]

HORARIOS_FUNCIONAMENTO = ["Livre", "Horário da Turma", "Personalizado"]

FORMAS_PAGAMENTO = ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "Cheque", "Pix", "Outra"]

SISTEMAS_ANTERIORES = [
    "ACTUAR DESK / WEB", "BH SYSTEM", "BOSS - QUALYFIT", "CLOUD GYM WEB", "Control Fit", 
    "DATA 4 YOU", "DATA FITNESS", "EASY MANAGER", "EVO", "FITNESS SCHOOL", "IFITNESS - FITSYSTEM", 
    "INFO SKY", "MU - MICRO UNIVERSITY", "MU WEB", "OPERFIT", "PLANILHA EXCEL - DADOS CADASTRAIS", 
    "POLISYSTEM - (DIGITAL GYM)", "Polisystem Web", "SAGAS", "SCA", "SCA WEB", "SECULLUM", 
    "TECNOFIT", "VYSOR", "NEXT FIT", "Não Possuia"
]

RECORRENCIA_USADA = [
    "Não", "Afinz", "Caixa", "Ceopag", "Cielo", "Getnet", "One Payment", "Pagar.me", 
    "PagBnk", "PinBank", "Rede", "Stone", "Strip", "Vind"
]