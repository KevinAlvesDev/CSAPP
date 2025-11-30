"""
Estrutura hierárquica padrão para implantações.
"""

ESTRUTURA_PADRAO = {
    "fases": [
        {
            "nome": "Welcome",
            "ordem": 1,
            "grupos": [
                {
                    "nome": "Boas-vindas",
                    "tarefas": [
                        {
                            "nome": "Contato Inicial Whatsapp/Grupo",
                            "subtarefas": []
                        },
                        {
                            "nome": "Reunião de Welcome",
                            "subtarefas": []
                        }
                    ]
                }
            ]
        },
        {
            "nome": "Estruturação BD",
            "ordem": 2,
            "grupos": [
                {
                    "nome": "Configuração Inicial",
                    "tarefas": [
                        {
                            "nome": "Criar Banco de Dados",
                            "subtarefas": []
                        },
                        {
                            "nome": "Vincular a tela de apoio",
                            "subtarefas": []
                        },
                        {
                            "nome": "Criar plano de sucesso",
                            "subtarefas": []
                        },
                        {
                            "nome": "Ajustar Suporte para Celula Baby",
                            "subtarefas": []
                        },
                        {
                            "nome": "Criar Aplicativo",
                            "subtarefas": []
                        },
                        {
                            "nome": "Nota fiscal",
                            "subtarefas": []
                        }
                    ]
                },
                {
                    "nome": "Configurações Financeiras",
                    "tarefas": [
                        {
                            "nome": "Convênio de cobrança",
                            "subtarefas": [
                                "Cadastro do convênio de cobrança",
                                "Convênio padrão no link de pagamento (empresa)",
                                "Inclusão de convênio no vendas online"
                            ]
                        }
                    ]
                },
                {
                    "nome": "Configurações do Sistema",
                    "tarefas": [
                        {
                            "nome": "Configurar Logo da Empresa",
                            "subtarefas": [
                                "Configuração de modalidade",
                                "Configuração de pacote",
                                "Configuração de plano",
                                "Configuração de turma",
                                "Configuração de produtos",
                                "Configuração de diaria",
                                "Configuração de Freepass",
                                "Configuração WellHub",
                                "Configuração Totalpass"
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "nome": "Validar estruturação",
            "ordem": 3,
            "grupos": []
        },
        {
            "nome": "Implantação em andamento",
            "ordem": 4,
            "grupos": [
                {
                    "nome": "Treinamentos ADM",
                    "tarefas": [
                        {
                            "nome": "treinamento ADM Estrutural",
                            "subtarefas": [
                                "Cadastro de colaborador / usuario",
                                "Como cadastrar um novo cliente",
                                "A importância do Boletim de Visitas",
                                "Negociação de Contrato",
                                "Formas de Pagamento (tela de recebimento)",
                                "Venda Avulsa (Produto ou Serviço)",
                                "Venda Avulsa de Diária",
                                "FreePass",
                                "Fechamento de Caixa por Operador",
                                "Renovação de contrato",
                                "Assinatura de contrato"
                            ]
                        },
                        {
                            "nome": "Treinamento ADM Operacional 1",
                            "subtarefas": [
                                "Alteração de vencimento da parcelas",
                                "Estorno de contrato",
                                "Férias",
                                "Atestado médico",
                                "Retorno de atestado e férias",
                                "Trancamento",
                                "Retorno de trancamento",
                                "Retorno de trancamento vencido"
                            ]
                        },
                        {
                            "nome": "Treinamento ADM Operacional 2",
                            "subtarefas": [
                                "Cancelamento com transferância",
                                "Cancelamento com devolução",
                                "Cancelamento com devolução (Base mensal)",
                                "Cancelamento de planos recorrentes",
                                "Cancelamento para planos bolsa",
                                "Bônus",
                                "Alteração de horário",
                                "Manutenção de modalidade"
                            ]
                        },
                        {
                            "nome": "Treinamento ADM Gerencial",
                            "subtarefas": [
                                "BI Grupo de Risco",
                                "BI Pendência de Clientes",
                                "BI Índice de Renovação",
                                "BI Conversão de Vendas",
                                "BI Metas Financeiras de Vendas",
                                "BI Ticket Médio de Planos",
                                "BI Cobranças por Convênio",
                                "BI Aulas Experimentais",
                                "BI Controle de Operações de Exceções",
                                "BI Inadimplência",
                                "BI de Gestão de Acessos",
                                "BI Wellhub",
                                "BI Ciclo de Vida do Cliente"
                            ]
                        }
                    ]
                },
                {
                    "nome": "Vendas Online",
                    "tarefas": [
                        {
                            "nome": "Vendas Online",
                            "subtarefas": [
                                "Configuração de planos site",
                                "Configurações engrenagem vendas online",
                                "Teste de vendas de planos / produtos online"
                            ]
                        }
                    ]
                },
                {
                    "nome": "Importação",
                    "tarefas": [
                        {
                            "nome": "Importação de dados",
                            "subtarefas": [
                                "Importação de dados",
                                "Verificação de importação interna",
                                "Verificação de importação cliente"
                            ]
                        }
                    ]
                },
                {
                    "nome": "Treinamentos Técnicos",
                    "tarefas": [
                        {
                            "nome": "Teinamento tecnico (treino/agenda/Cross)",
                            "subtarefas": [
                                "Pacto APP",
                                "Cadastro de Aparelhos",
                                "Cadastro de Atividades",
                                "Cadastro de Categorias",
                                "Cadastro de Fichas Predefinidas",
                                "Cadastro de Programas Predefinidas",
                                "Cadastro de Niveis",
                                "Montagem de ficha para o aluno",
                                "Montar avaliação fisica",
                                "BI treino",
                                "BI Avaliação Fisica",
                                "Agenda de aulas",
                                "Agenda de serviços"
                            ]
                        },
                        {
                            "nome": "Treinamento CRM",
                            "subtarefas": [
                                "Cadastro Gestão de carteiras",
                                "Cadastro Feriado",
                                "Cadastro Meta Extra",
                                "Cadastro Objeção",
                                "Cadastro Script",
                                "Cadastro Email para o contato em grupo",
                                "Cadastro Contato em grupo ( email,sms, app)",
                                "Como usar no meta diria - Script",
                                "Como usar no meta diria - Tipos de contato",
                                "Como usar no meta diria - Selecionar pesquisa",
                                "Como usar no meta diria - fazer indicação",
                                "Como usar no meta diria - Agendamento",
                                "Como usar no meta diria - Objeção",
                                "Como usar no meta diria - Simples Resgistro",
                                "Como usar no meta diria - Historico de Contato/Historico de Objeções",
                                "Operação Meta diaria - Leads Hoje",
                                "Operação Meta diaria - Leads Acumuladas",
                                "Operação Meta diaria - Agend. Presenciais",
                                "Operação Meta diaria - Agendados de Amanhã",
                                "Operação Meta diaria - Visitantes 24h",
                                "Operação Meta diaria - Renovação",
                                "Operação Meta diaria - Desistentes",
                                "Operação Meta diaria - Indicações",
                                "Operação Meta diaria - Aluno Gympass",
                                "Operação Meta diaria - Grupo de Risco",
                                "Operação Meta diaria - Vencidos",
                                "Operação Meta diaria - Pós Venda",
                                "Operação Meta diaria - Faltosos",
                                "Operação Meta diaria - Aniversariantes",
                                "Operação Meta diaria - Indicações",
                                "Operação Meta diaria - Receptivo",
                                "BI CRM"
                            ]
                        },
                        {
                            "nome": "Treinamento financeiro",
                            "subtarefas": [
                                "Cadastro de Contas",
                                "Cadastro das Taxas de Cartão",
                                "Cadastro de plano de contas",
                                "Cadastro das Centro de custos",
                                "Cadastro de Rateio integração",
                                "Configurações extras",
                                "Abrir/Fechar Caixa",
                                "Consulta/Reabertura de Caixa",
                                "Resumo de Contas",
                                "Gestão de Recebíveis (Movimentação)",
                                "Lote",
                                "Relatório Fluxo de Caixa",
                                "Lançamento de conta a pagar",
                                "Lançamento de conta a receber",
                                "BI Financeiro",
                                "Relatorios (demosntrativo financeiro / DRE)",
                                "Tipos de retornos",
                                "transações no cartão de credito"
                            ]
                        },
                        {
                            "nome": "Treinamento modulo graduação",
                            "subtarefas": [
                                "Atividades",
                                "Cadastro de ficha tecnica",
                                "Avaliçõa de progresso",
                                "Business Intelligence"
                            ]
                        }
                    ]
                },
                {
                    "nome": "Integrações",
                    "tarefas": [
                        {
                            "nome": "PactoPay",
                            "subtarefas": []
                        },
                        {
                            "nome": "Game Off Results",
                            "subtarefas": [
                                "Principal",
                                "Monitoramento",
                                "Graficos",
                                "Relatórios",
                                "Dados do grupo",
                                "Geolocalização",
                                "Geme por unidades",
                                "Regiões"
                            ]
                        }
                    ]
                },
                {
                    "nome": "Suporte",
                    "tarefas": [
                        {
                            "nome": "Reunião tira-dúvida geral",
                            "subtarefas": []
                        }
                    ]
                }
            ]
        },
        {
            "nome": "Conclusão onboarding",
            "ordem": 5,
            "grupos": [
                {
                    "nome": "Finalização",
                    "tarefas": [
                        {
                            "nome": "Concluir Processos Internos",
                            "subtarefas": [
                                "Conclusão do plano de sucesso",
                                "Proposito do cliente na tela de apoio",
                                "Detalhes da empresa na tela de apoio",
                                "Fotos na tela de apoio",
                                "Documentos implantação na tela de apoio",
                                "Pesquisa de NPS HeWelp enviada",
                                "Conclusão no Gymbot"
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}
