import os

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

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

NAO_DEFINIDO_BOOL = "Não definido"

SIM_NAO_OPTIONS = [NAO_DEFINIDO_BOOL, "Sim", "Não"]

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'kevinpereira@pactosolucoes.com.br')

CARGOS_LIST = ["Júnior", "Pleno", "Sênior"]

PERFIL_ADMIN = "Administrador"
PERFIL_GERENTE = "Gerente"
PERFIL_COORDENADOR = "Coordenador"
PERFIL_IMPLANTADOR = "Implantador"

PERFIS_ACESSO_LIST = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR, PERFIL_IMPLANTADOR]

# Perfis com permissão de gestão completa (criar, editar, excluir implantações)
PERFIS_COM_GESTAO = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]

# Perfis que podem criar implantações e módulos
PERFIS_COM_CRIACAO = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]

# Perfis com acesso ao Dashboard Gerencial (Analytics)
PERFIS_COM_ANALYTICS = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]

# Perfis que veem todas as implantações no dashboard
PERFIS_VER_TODAS_IMPLANTACOES = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]

# Perfis com acesso à página de Usuários (manage-users)
PERFIS_GERENCIAR_USUARIOS = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]

# Perfis com acesso ao Plano de Sucesso
PERFIS_PLANO_SUCESSO = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]

NIVEIS_RECEITA = [
    "Prata (MRR abaixo de R$699,99)",
    "Ouro (MRR entre R$700,00 a R$999,99)",
    "Platina (MRR entre R$1.000,00 a R$1999,99)",
    "Diamante (MRR acima de R$2000,00)",
    "Grandes contas"
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

MODULO_OPCOES = {
    'nota_fiscal': 'Nota fiscal',
    'vendas_online': 'Vendas Online',
    'app_treino': 'App Treino',
    'recorrencia': 'Recorrência'
}
