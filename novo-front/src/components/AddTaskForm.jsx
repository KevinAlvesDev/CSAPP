// Em: src/components/AddTaskForm.jsx

import React, { useState, useEffect } from 'react';

// --- ADICIONADO ---
// Definir as opções de tag
const TAG_OPTIONS = ["Ação interna", "Reunião"];

export default function AddTaskForm({ show, onClose, modulos = [], onSubmit, loading = false }) {
  const [nome, setNome] = useState('');
  const [tag, setTag] = useState(''); // O valor padrão é uma string vazia (sem tag)
  
  const pendenciasModule = modulos.find(m => m.includes("Pendências")) || modulos[0] || '';
  const [modulo, setModulo] = useState(pendenciasModule);

  // Efeito para resetar o módulo padrão quando o modal for aberto
  useEffect(() => {
    if (show) {
      setModulo(pendenciasModule);
    }
  }, [show, pendenciasModule]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!nome.trim() || !modulo) return;
    
    // Chama a função 'onSubmit' (que é o 'handleAddTask' do pai)
    const success = await onSubmit({
      tarefa_filho: nome,
      tarefa_pai: modulo,
      tag: tag // Passa a tag selecionada (ou string vazia)
    });
    
    // Se deu certo, limpa o formulário e fecha o modal
    if (success) {
      setNome('');
      setTag(''); // Reseta a tag
      onClose();
    }
  };
  
  if (!show) {
    return null;
  }

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      onClick={onClose} // Fecha ao clicar fora
    >
      <div 
        className="w-full max-w-2xl rounded-lg bg-white shadow-xl dark:bg-gray-800"
        onClick={e => e.stopPropagation()} // Impede que o clique dentro feche
      >
        <form onSubmit={handleSubmit}>
          {/* Header */}
          <div className="border-b border-gray-200 p-4 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Adicionar Nova Tarefa
            </h2>
          </div>

          {/* Body */}
          <div className="p-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
              {/* Módulo */}
              <div className="md:col-span-1">
                <label htmlFor="modulo" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Módulo
                </label>
                <select
                  id="modulo"
                  value={modulo}
                  onChange={(e) => setModulo(e.target.value)}
                  required
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                  {modulos.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              {/* Nome da Tarefa */}
              <div className="md:col-span-2">
                <label htmlFor="nome" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Nome da Tarefa
                </label>
                <input
                  type="text"
                  id="nome"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  required
                  placeholder="Ex: Reunião de Kick-Off"
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
              </div>
              
              {/* --- CAMPO TAG MODIFICADO --- */}
              <div className="md:col-span-1">
                <label htmlFor="tag" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Etiqueta (Opcional)
                </label>
                <select
                  id="tag"
                  value={tag}
                  onChange={(e) => setTag(e.target.value)}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                  <option value="">-- Selecione --</option> 
                  {TAG_OPTIONS.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
              {/* --- FIM DA MODIFICAÇÃO --- */}

            </div>
          </div>

          {/* Footer (Botões) */}
          <div className="flex justify-end gap-3 border-t border-gray-200 p-4 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-50 dark:border-gray-500 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-md border border-transparent bg-green-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {loading ? 'Adicionando...' : 'Adicionar Tarefa'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}