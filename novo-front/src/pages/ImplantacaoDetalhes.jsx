// Em: src/pages/ImplantacaoDetalhes.jsx

import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi'; 
import { useMutation } from '../hooks/useMutation';
import TaskList from '../components/TaskList'; 
import StopModal from '../components/StopModal';
import EditImplantacaoModal from '../components/EditImplantacaoModal';
import AddTaskForm from '../components/AddTaskForm'; 

// --- Componente ActionButtons (Completo) ---
function ActionButtons({ impl, onUpdate, onStopClick, onEditClick, onAddTaskClick }) {
  const navigate = useNavigate();
  
  // Hooks de mutação para ações de clique único
  const { callMutation: finalizarImpl, loading: loadingFinalizar } = useMutation(`/implantacao/${impl.id}/finalizar`);
  const { callMutation: retomarImpl, loading: loadingRetomar } = useMutation(`/implantacao/${impl.id}/retomar`);
  const { callMutation: reabrirImpl, loading: loadingReabrir } = useMutation(`/implantacao/${impl.id}/reabrir`);

  const handleAction = async (actionCallback) => {
    if (window.confirm("Tem a certeza?")) {
      const result = await actionCallback({ method: 'POST' });
      if (result && result.success) {
        onUpdate(result.implantacao); // Atualiza o estado da página
      }
    }
  };
  
  const handleVoltar = () => {
    navigate('/'); // Volta para o dashboard
  };

  const status = impl?.status;
  const loading = loadingFinalizar || loadingRetomar || loadingReabrir;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        onClick={onEditClick} // <-- Abre o modal de edição
        className="rounded-md bg-gray-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-gray-700"
      >
        Editar Detalhes
      </button>

      {/* Botão Novo (Adicionar Tarefa) */}
      <button
        onClick={onAddTaskClick}
        className="rounded-md bg-green-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-green-700"
      >
        Adicionar Tarefa
      </button>

      {/* Botões Condicionais baseados no Status */}
      {status === 'andamento' && (
        <>
          <button
            onClick={onStopClick} // <-- Abre o modal de parada
            disabled={loading}
            className="rounded-md bg-yellow-500 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-yellow-600 disabled:opacity-50"
          >
            Parar
          </button>
          <button
            onClick={() => handleAction(finalizarImpl)}
            disabled={loading}
            className="rounded-md bg-green-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-green-700 disabled:opacity-50"
          >
            Finalizar
          </button>
        </>
      )}

      {status === 'parada' && (
        <button
          onClick={() => handleAction(retomarImpl)}
          disabled={loading}
          className="rounded-md bg-green-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-green-700 disabled:opacity-50"
        >
          Retomar Implantação
        </button>
      )}

      {status === 'finalizada' && (
        <button
          onClick={() => handleAction(reabrirImpl)}
          disabled={loading}
          className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
        >
          Reabrir Implantação
        </button>
      )}
      
      {(status === 'finalizada' || status === 'parada') && (
         <button
            onClick={handleVoltar}
            className="rounded-md bg-gray-200 px-3 py-2 text-sm font-medium text-gray-800 hover:bg-gray-300"
          >
            Voltar ao Dashboard
          </button>
      )}
    </div>
  );
}


// --- Página Principal de Detalhes (Completa) ---
export default function ImplantacaoDetalhesPage() {
  const { id } = useParams();
  // Renomeamos 'refetch' para 'refetchPage' para clareza
  const { data: initialData, loading: pageLoading, error: pageError, refetch: refetchPage } = useApi(`/implantacao/${id}`);
  
  // Hooks de mutação
  const { callMutation: updateTask, loading: isTaskUpdating } = useMutation('/api/atualizar_tarefa');
  const { callMutation: pararImpl, loading: loadingParar } = useMutation(`/implantacao/${id}/parar`);
  const { callMutation: addTask, loading: isTaskAdding } = useMutation(`/implantacao/${id}/adicionar_tarefa`);
  const { callMutation: deleteTask, loading: isTaskDeleting } = useMutation('/api/excluir_tarefa');

  // Estado local
  const [impl, setImpl] = useState(null);
  const [tarefasObrigatorias, setTarefasObrigatorias] = useState([]);
  const [tarefasTreinamento, setTarefasTreinamento] = useState({});
  const [tarefasPendencias, setTarefasPendencias] = useState([]);
  
  // Estado dos Modais
  const [isStopModalOpen, setIsStopModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isAddTaskModalOpen, setIsAddTaskModalOpen] = useState(false); 
  
  const isUpdatingTasks = isTaskUpdating || isTaskAdding || isTaskDeleting;

  // Popula o estado local
  useEffect(() => {
    if (initialData) {
      setImpl(initialData.implantacao); 
      setTarefasObrigatorias(initialData.tarefas_agrupadas_obrigatorio?.["Obrigações para finalização"] || []);
      setTarefasTreinamento(initialData.tarefas_agrupadas_treinamento || {});
      setTarefasPendencias(initialData.tarefas_agrupadas_pendencias?.[initialData.modulo_pendencias_nome] || []);
    }
  }, [initialData]);

  // Função chamada quando uma mutação (Editar, Parar, etc.) é bem-sucedida
  const handleImplantacaoUpdate = (updatedImplantacao) => {
    setImpl(updatedImplantacao);
  };

  // Funções dos modais (Stop e Edit)
  const handleStopSubmit = async (motivo) => {
    const result = await pararImpl({ body: { motivo_parada: motivo }, method: 'POST' });
    if (result && result.success) {
      handleImplantacaoUpdate(result.implantacao);
      setIsStopModalOpen(false); 
    }
  };
  const handleEditSuccess = (updatedImplantacao) => {
    handleImplantacaoUpdate(updatedImplantacao);
    setIsEditModalOpen(false);
  };
  
  // Funções de Tarefa (Toggle, Delete, Add)
  const handleToggleTask = async (taskId, currentStatus) => {
    const newStatus = !currentStatus;
    const result = await updateTask({ body: { tarefa_id: taskId, concluida: newStatus ? 1 : 0 }, method: 'POST' });
    if (result && result.success) {
      const updateTaskInList = (tasks) => tasks.map(t => t.id === taskId ? { ...t, concluida: newStatus } : t);
      setTarefasObrigatorias(prev => updateTaskInList(prev));
      setTarefasPendencias(prev => updateTaskInList(prev));
      setTarefasTreinamento(prev => {
        const newState = { ...prev };
        for (const moduloNome in newState) {
          newState[moduloNome] = updateTaskInList(newState[moduloNome]);
        }
        return newState;
      });
      refetchPage(); // Atualiza a barra de progresso
    }
  };
  
  const handleDeleteTask = async (taskId) => {
    const result = await deleteTask({ body: { tarefa_id: taskId }, method: 'POST' });
    if (result && result.success) {
      const removeTaskFromList = (tasks) => tasks.filter(t => t.id !== taskId);
      setTarefasObrigatorias(prev => removeTaskFromList(prev));
      setTarefasPendencias(prev => removeTaskFromList(prev));
      setTarefasTreinamento(prev => {
        const newState = { ...prev };
        for (const moduloNome in newState) {
          newState[moduloNome] = removeTaskFromList(newState[moduloNome]);
        }
        return newState;
      });
      refetchPage(); // Atualiza a barra de progresso
    }
  };

  const handleAddTask = async (formData) => {
    const result = await addTask({
      body: formData, 
      method: 'POST'
    });

    if (result && result.success && result.nova_tarefa) {
      const novaTarefa = result.nova_tarefa;
      const modulo = novaTarefa.tarefa_pai;
      
      if (modulo === "Obrigações para finalização") {
        setTarefasObrigatorias(prev => [...prev, novaTarefa]);
      } else if (modulo === initialData?.modulo_pendencias_nome) {
        setTarefasPendencias(prev => [...prev, novaTarefa]);
      } else {
        setTarefasTreinamento(prev => ({
          ...prev,
          [modulo]: [...(prev[modulo] || []), novaTarefa]
        }));
      }
      refetchPage(); // Atualiza a barra de progresso
      return true; // Sucesso
    }
    return false; // Falha
  };

  // --- FUNÇÃO ADICIONADA (Para os comentários) ---
  // Esta função é chamada pelo CommentBox e pelo TaskList para atualizar o progresso
  const handleContentChange = () => {
    refetchPage(); // Simplesmente busca os dados da página novamente
  };


  // --- RENDERIZAÇÃO ---
  if (pageLoading || !impl) { 
    return (
      <div className="text-center text-gray-700 dark:text-gray-300">
        A carregar dados da implantação...
      </div>
    );
  }

  if (pageError) {
    return (
      <div className="rounded-md border border-red-300 bg-red-100 p-4 text-red-700">
        <strong>Erro ao carregar dados:</strong> {pageError}
      </div>
    );
  }
  
  const progresso = initialData?.progresso_porcentagem || 0;
  const todosModulos = initialData?.todos_modulos || [];
  
  return (
    <div className="flex flex-col gap-6">
      
      <div>
        <Link to="/" className="text-sm font-medium text-blue-600 hover:underline dark:text-blue-400">
          &larr; Voltar para o Dashboard
        </Link>
      </div>

      <div className="rounded-lg bg-white p-6 shadow-md dark:bg-gray-800">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          {impl.nome_empresa} 
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Status: <span className="font-semibold text-blue-600">{impl.status}</span>
        </p>
        <div className="mt-4">
          <div className="mb-1 flex justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Progresso</span>
            <span className="text-sm font-medium text-blue-700 dark:text-blue-300">{progresso}%</span>
          </div>
          <div className="w-full rounded-full bg-gray-200 dark:bg-gray-700">
            <div 
              className="rounded-full bg-blue-600 p-0.5 text-center text-xs font-medium leading-none text-blue-100" 
              style={{ width: `${progresso}%` }}
            >
              {progresso > 10 ? `${progresso}%` : ''}
            </div>
          </div>
        </div>
        
        <div className="mt-6 border-t border-gray-200 pt-4 dark:border-gray-700">
          <ActionButtons 
            impl={impl}
            onUpdate={handleImplantacaoUpdate}
            onStopClick={() => setIsStopModalOpen(true)}
            onEditClick={() => setIsEditModalOpen(true)}
            onAddTaskClick={() => setIsAddTaskModalOpen(true)}
          />
        </div>
      </div>
      
      {/* Checklists */}
      <div className="flex flex-col gap-6">
        <TaskList 
          title="Obrigações para Finalização" 
          tasks={tarefasObrigatorias} 
          onToggleTask={handleToggleTask}
          onDeleteTask={handleDeleteTask}
          onCommentChange={handleContentChange} // <-- Adicionado
          isUpdating={isUpdatingTasks}    
        />
        
        {Object.keys(tarefasTreinamento).map((moduloNome) => (
          <TaskList 
            key={moduloNome}
            title={moduloNome} 
            tasks={tarefasTreinamento[moduloNome]} 
            onToggleTask={handleToggleTask}
            onDeleteTask={handleDeleteTask}
            onCommentChange={handleContentChange} // <-- Adicionado
            isUpdating={isUpdatingTasks}
          />
        ))}

        <TaskList 
          title="Pendências" 
          tasks={tarefasPendencias} 
          onToggleTask={handleToggleTask}
          onDeleteTask={handleDeleteTask}
          onCommentChange={handleContentChange} // <-- Adicionado
          isUpdating={isUpdatingTasks}
        />
      </div>
      
      {/* Modais (Renderizados mas ocultos) */}
      <AddTaskForm
        show={isAddTaskModalOpen}
        onClose={() => setIsAddTaskModalOpen(false)}
        modulos={todosModulos}
        onSubmit={handleAddTask}
        loading={isTaskAdding}
      />
      <StopModal 
        show={isStopModalOpen}
        onClose={() => setIsStopModalOpen(false)}
        onSubmit={handleStopSubmit}
        loading={loadingParar}
      />
      <EditImplantacaoModal
        show={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        implantacao={impl}
        constants={initialData?.constants || {}} 
        onSuccess={handleEditSuccess}
      />
    </div>
  );
}