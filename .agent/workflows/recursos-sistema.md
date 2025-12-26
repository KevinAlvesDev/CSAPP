# 📋 Recursos Disponíveis no Sistema CS Onboarding

## 🎯 Visão Geral
Este documento mapeia TODOS os recursos disponíveis para o implantador no sistema CS Onboarding.

---

## 1. 📊 DASHBOARD

### Abas Disponíveis:
- **Novas**: Implantações aguardando início
- **Em Andamento**: Implantações ativas
- **Paradas**: Implantações pausadas (com motivo)
- **Futuras**: Implantações agendadas
- **Sem Previsão**: Implantações sem data de início
- **Concluídas**: Implantações finalizadas
- **Canceladas**: Implantações canceladas
- **Módulos**: Implantações de módulos específicos

### Métricas Exibidas:
- Total por status
- Valor monetário por status
- Dias em andamento
- Progresso (%)
- Última atividade

---

## 2. 🏢 IMPLANTAÇÕES

### Status Possíveis:
1. `nova` - Criada, aguardando início
2. `andamento` - Em execução
3. `parada` - Pausada temporariamente
4. `futura` - Agendada para o futuro
5. `sem_previsao` - Sem data definida
6. `finalizada` - Concluída
7. `cancelada` - Cancelada

### Dados da Implantação:
**Básicos:**
- Nome da empresa
- Tipo (completa/módulo)
- Usuário CS responsável
- Valor monetário

**Datas:**
- Data de criação
- Data início previsto
- Data início efetivo
- Data previsão término
- Data início produção
- Data final implantação
- Data finalização
- Data cancelamento

**Cliente:**
- Responsável cliente
- Cargo responsável
- Telefone responsável
- Email responsável
- Contatos adicionais

**Técnico:**
- ID Favorecido (OAMD)
- Chave OAMD
- Nível de receita
- Informação de infraestrutura
- Tela de apoio (link)
- Sistema anterior
- Importação de dados

**Negócio:**
- Seguimento
- Tipos de planos
- Modalidades
- Horários de funcionamento
- Formas de pagamento
- Diária (sim/não)
- Freepass (sim/não)
- Alunos ativos (quantidade)
- Catraca (sim/não)
- Facial (sim/não)
- Recorrência USA
- Boleto
- Nota fiscal

**Responsáveis:**
- Resp. Estratégico (nome)
- Resp. ONB (nome)
- Observações estratégicas

**Parada/Cancelamento:**
- Motivo da parada
- Motivo do cancelamento
- Comprovante de cancelamento (URL)

**Plano de Sucesso:**
- ID do plano atribuído
- Data de atribuição do plano

---

## 3. ✅ TAREFAS (Checklist Items)

### Estrutura Hierárquica:
- **Módulo** (level 0)
  - **Fase** (level 1)
    - **Tarefa** (level 2, tipo_item='tarefa')
      - **Subtarefa** (level 3, tipo_item='subtarefa')

### Campos de Tarefa:
- Título
- Descrição
- Responsável
- Status (`pendente`, `em_andamento`, `concluida`)
- Completed (boolean)
- Percentual de conclusão
- Obrigatória (boolean)
- Tag (`Reunião`, `Ação interna`, etc.)
- Ordem
- Comentário
- Data de conclusão
- Previsão original
- Nova previsão
- Data de criação
- Data de atualização

### Tags Disponíveis:
- `Reunião` - Reuniões com cliente
- `Ação interna` - Ações internas da equipe
- (Outras tags personalizadas)

---

## 4. 📝 PLANOS DE SUCESSO

### Estrutura:
- Nome do plano
- Descrição
- Criado por
- Data de criação
- Data de atualização
- Dias de duração (prazo padrão)
- Ativo (boolean)

### Hierarquia do Plano:
- Módulos
  - Fases
    - Tarefas
      - Subtarefas

---

## 5. 💬 COMENTÁRIOS

### Tipos:
- Comentários em tarefas
- Comentários em subtarefas
- Visibilidade: `interno` ou `cliente`
- Suporte a imagens (URL)
- Flag `noshow` (ocultar)

---

## 6. 📅 TIMELINE (Histórico)

### Eventos Registrados:
- `status_alterado` - Mudança de status
- `implantacao_criada` - Criação
- `auto_finalizada` - Finalização automática
- `prazo_alterado` - Alteração de prazo
- Outros eventos personalizados

### Dados do Log:
- Tipo de evento
- Usuário que executou
- Detalhes (texto)
- Data/hora

---

## 7. 🎮 GAMIFICAÇÃO

### Métricas Automáticas:
- Implantações finalizadas no mês
- TMA médio (dias)
- Implantações iniciadas no mês
- Reuniões concluídas/dia (média)
- Ações internas concluídas/dia (média)

### Métricas Manuais:
- Nota de qualidade (%)
- Assiduidade (%)
- Planos de sucesso (%)
- Satisfação do processo (%)
- Reclamações (quantidade)
- Perda de prazo (quantidade)
- Elogios
- Recomendações
- Certificações
- Treinamentos Pacto (participação/aplicação)
- Reuniões presenciais
- Cancelamentos por responsabilidade
- Não envolvimento
- Descrição incompreensível
- Hora extra
- Perda SLA grupo
- Finalização incompleta
- Não preenchimento

---

## 8. 📊 ANALYTICS

### Dashboards Disponíveis:
- **Gerencial**: Visão geral da equipe
- **Cancelamentos**: Análise de cancelamentos

### Métricas:
- Por período
- Por implantador
- Por status
- Valores monetários
- Tendências

---

## 9. 🔐 PERFIL DO USUÁRIO

### Dados:
- Nome
- Email (login)
- Foto (URL)
- Cargo
- Perfil de acesso (`Implantador`, `Coordenador`, `Gerente`, `Administrador`)
- Último check externo (OAMD)

---

## 10. 🔔 NOTIFICAÇÕES (Atual)

### Notificações Implementadas:
1. Tarefas atrasadas por empresa
2. Implantações novas aguardando
3. Implantações concluídas esta semana
4. Resumo semanal (tarefas/reuniões/ações)
5. Resumo de segunda-feira

---

## 11. 🎯 AÇÕES DISPONÍVEIS

### Para Implantações:
- Criar nova implantação
- Iniciar implantação
- Agendar início futuro
- Parar implantação (com motivo)
- Retomar implantação
- Finalizar implantação
- Reabrir implantação
- Cancelar implantação
- Editar detalhes da empresa
- Sincronizar com OAMD

### Para Tarefas:
- Criar tarefa/subtarefa
- Marcar como concluída
- Alterar responsável
- Definir/alterar prazo
- Adicionar comentário
- Anexar imagem
- Reordenar tarefas
- Excluir tarefa

### Para Planos:
- Criar plano de sucesso
- Editar plano
- Atribuir plano a implantação
- Visualizar estrutura do plano

---

## 12. 🔍 FILTROS E BUSCAS

### Dashboard:
- Filtrar por implantador (gestores)
- Ordenar por dias (crescente/decrescente)
- Filtrar por aba/status

### Timeline:
- Filtrar por tipo de evento
- Filtrar por período
- Buscar por texto
- Exportar CSV

---

## 13. 📈 CÁLCULOS AUTOMÁTICOS

### Progresso:
- Baseado em tarefas concluídas vs total
- Atualização em tempo real

### Dias:
- Dias em andamento
- Dias parada
- Dias até o prazo

### Última Atividade:
- Baseado em `timeline_log`
- Cores: verde (<1 dia), amarelo (1-3 dias), vermelho (>3 dias)

---

## 14. 🎨 INTERFACE

### Temas:
- Modo claro
- Modo escuro

### Responsividade:
- Desktop
- Tablet
- Mobile

---

## 15. 🔗 INTEGRAÇÕES

### OAMD (Sistema Externo):
- Consulta de dados da empresa
- Sincronização de informações
- Via ID Favorecido

---

## 16. 📱 RECURSOS ADICIONAIS

### Agenda:
- Visualização de eventos
- Filtros por período

### Exportações:
- Timeline em CSV
- Relatórios de gamificação

### Gestão (Admin/Gerente):
- Gerenciar usuários
- Configurar regras de gamificação
- Visualizar métricas da equipe

---

## 🎯 PRÓXIMOS PASSOS

Com base neste mapeamento, podemos criar notificações inteligentes para:
- Prazos de planos de sucesso
- Tarefas obrigatórias pendentes
- Implantações sem responsável definido
- Comentários não respondidos
- Mudanças de responsável
- Métricas de gamificação
- E muito mais...
