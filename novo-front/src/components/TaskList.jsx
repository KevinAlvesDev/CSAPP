// Em: src/components/TaskList.jsx

import React, { useState } from 'react';
import CommentBox from './CommentBox'; // <--- 1. IMPORTAR O NOVO COMPONENTE

// (Componente Ícone Checkbox - sem alterações)
function CheckboxIcon({ concluida }) { /* ... (código do ícone) ... */ }

// Ícone de Comentários
function CommentIcon() {
  return (
    <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M10 2c-4.418 0-8 3.134-8 7 0 1.76.784 3.37 2.074 4.545a.75.75 0 01.114.545.75.75 0 00-.114.545A4.717 4.717 0 001.2 18.09c.351.066.709.11 1.076.11 4.418 0 8-3.134 8-7s-3.582-7-8-7zM2 9a6.5 6.5 0 0111.93-2.973.75.75 0 001.06-1.06A8 8 0 102 9z" clipRule="evenodd" />
      <path d="M15.06 13.153A8.453 8.453 0 0118.8 8.5c0-3.866-3.582-7-8-7a.75.75 0 000 1.5c3.59 0 6.5 2.694 6.5 5.5 0 1.413-.57 2.697-1.506 3.653a.75.75 0 10.932 1.18z" />
    </svg>
  );
}

export default function TaskList({ title, tasks = [], onToggleTask, onDeleteTask, onCommentChange, isUpdating = false }) {
  
  // --- 2. NOVO ESTADO ---
  // Guarda o ID da tarefa que está com os comentários expandidos
  const [expandedTaskId, setExpandedTaskId] = useState(null);

  if (tasks.length === 0) {
    return null;
  }

  const handleTaskClick = (e, task) => {
    // Impede o toggle se clicarmos no botão de excluir ou de comentários
    if (e.target.closest('button')) {
      return;
    }
    if (onToggleTask && !isUpdating) {
      onToggleTask(task.id, task.concluida);
    }
  };

  const handleDeleteClick = (task) => {
    if (onDeleteTask && !isUpdating) {
      if (window.confirm(`Tem certeza que deseja excluir a tarefa: "${task.tarefa_filho}"?`)) {
        onDeleteTask(task.id);
      }
    }
  };
  
  // --- 3. NOVA FUNÇÃO ---
  // Controla qual caixa de comentários está aberta
  const handleToggleComments = (taskId) => {
    setExpandedTaskId(prevId => (prevId === taskId ? null : taskId)); // Abre/Fecha
  };

  return (
    <div className="rounded-lg bg-white shadow-md dark:bg-gray-800">
      <h3 className="border-b border-gray-200 p-4 text-lg font-semibold text-gray-800 dark:border-gray-700 dark:text-white">
        {title}
      </h3>
      <ul className="divide-y divide-gray-200 dark:divide-gray-700">
        {tasks.map((task) => (
          // Usamos React.Fragment para agrupar a <li> e o <CommentBox>
          <React.Fragment key={task.id}>
            <li 
              onClick={(e) => handleTaskClick(e, task)}
              className={`
                flex items-center justify-between p-4 
                ${onToggleTask ? 'cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-700' : ''}
                ${isUpdating ? 'cursor-not-allowed opacity-70' : ''}
                ${task.concluida ? 'opacity-60' : ''}
              `}
            >
              {/* Lado Esquerdo: Checkbox e Nome */}
              <div className="flex min-w-0 items-center gap-3">
                <CheckboxIcon concluida={task.concluida} />
                <span className={`truncate font-medium ${task.concluida ? 'text-gray-500 line-through dark:text-gray-400' : 'text-gray-900 dark:text-white'}`}>
                  {task.tarefa_filho}
                </span>
              </div>

              {/* Lado Direito: Tag, Botão Comentário e Botão Excluir */}
              <div className="flex flex-shrink-0 items-center gap-2">
                {task.tag && (
                  <span className="inline-flex rounded-full bg-blue-100 px-2 text-xs font-semibold leading-5 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                    {task.tag}
                  </span>
                )}
                
                {/* --- 4. BOTÃO DE COMENTÁRIOS (NOVO) --- */}
                <button
                  onClick={() => handleToggleComments(task.id)}
                  disabled={isUpdating}
                  className={`flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium
                              ${expandedTaskId === task.id 
                                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200' 
                                : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'}`}
                  title="Comentários"
                >
                  <CommentIcon />
                  {task.comentarios?.length || 0}
                </button>

                {onDeleteTask && (
                  <button
                    onClick={() => handleDeleteClick(task)}
                    disabled={isUpdating}
                    className="rounded-full p-1 text-gray-400 transition-colors hover:bg-red-100 hover:text-red-600 disabled:opacity-50 dark:hover:bg-red-900"
                    title="Excluir Tarefa"
                  >
                    {/* (Ícone de Lixeira) */}
                    <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" /></svg>
                  </button>
                )}
              </div>
            </li>
            
            {/* --- 5. RENDERIZAÇÃO CONDICIONAL DO COMMENTBOX --- */}
            {expandedTaskId === task.id && (
              <li> {/* (Renderiza dentro de um <li> para ser HTML válido) */}
                <CommentBox 
                  taskId={task.id} 
                  initialComments={task.comentarios}
                  onCommentChange={onCommentChange} // Passa a função do pai
                />
              </li>
            )}
          </React.Fragment>
        ))}
      </ul>
    </div>
  );
}