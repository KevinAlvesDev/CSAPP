# project/constants.py
# Definições Globais
# (Definições de tarefas movidas para project/task_definitions.py)

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
CARGOS_LIST = ["Júnior", "Pleno", "Sênior"] 

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