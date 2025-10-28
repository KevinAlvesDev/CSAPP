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

# Perfis de Acesso (Permissão no sistema, editável apenas pelo Admin/Coordenador)
PERFIL_ADMIN = "Administrador"
# PERFIL_GERENTE = "Gerente" # REMOVIDO
PERFIL_COORDENADOR = "Coordenador"
PERFIL_IMPLANTADOR = "Implantador" 
# PERFIL_VISUALIZADOR = "Visualizador" # REMOVIDO
PERFIS_ACESSO_LIST = [PERFIL_ADMIN, PERFIL_COORDENADOR, PERFIL_IMPLANTADOR] # LISTA ATUALIZADA

PERFIS_COM_GESTAO = [PERFIL_ADMIN, PERFIL_COORDENADOR] # Perfis de Gestão (Admin e Coord)

# Perfis que podem criar implantações (Admin e Coord)
PERFIS_COM_CRIACAO = [PERFIL_ADMIN, PERFIL_COORDENADOR]

# Perfis que podem ver a tela de Analytics (Coordenadores e acima)
PERFIS_COM_ANALYTICS = [PERFIL_ADMIN, PERFIL_COORDENADOR]


# NOVAS CONSTANTES PARA DETALHES DA EMPRESA
NIVEIS_RECEITA = [
    "Diamante (MRR > R$ 2.000,00)",
    "Platina (MRR R$ 1.000,00 - R$ 2.000,00)",
    "Ouro (MRR R$ 500,00 - R$ 1.000,00)",
    "Prata (MRR < R$ 500,00)"
]

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