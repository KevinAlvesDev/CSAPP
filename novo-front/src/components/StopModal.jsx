// Em: src/components/StopModal.jsx

import React, { useState } from 'react';

// Este modal recebe:
// - show: (boolean) se deve ser exibido
// - onClose: (função) para fechar o modal
// - onSubmit: (função) que é chamada com o 'motivo'
// - loading: (boolean) para desativar os botões
export default function StopModal({ show, onClose, onSubmit, loading = false }) {
  const [motivo, setMotivo] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!motivo.trim()) return;
    onSubmit(motivo);
  };

  if (!show) {
    return null;
  }

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
        onClick={e => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Parar Implantação</h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Por favor, insira o motivo da parada. Esta ação moverá a implantação para a lista de "Paradas".
        </p>
        
        <form onSubmit={handleSubmit}>
          <div className="mt-4">
            <label htmlFor="motivo_parada" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Motivo da Parada
            </label>
            <textarea
              id="motivo_parada"
              rows="3"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>
          
          <div className="mt-6 flex justify-end gap-3">
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
              disabled={loading || !motivo.trim()}
              className="rounded-md border border-transparent bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {loading ? 'A parar...' : 'Confirmar Parada'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}