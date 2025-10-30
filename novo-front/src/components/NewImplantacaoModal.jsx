// Em: src/components/NewImplantacaoModal.jsx

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '../hooks/useMutation'; // O hook que acabámos de criar

// O seu backend espera 'agora', 'futura', ou 'modulo'
export default function NewImplantacaoModal({ show, onClose, tipoModal = 'agora' }) {
  const [nomeEmpresa, setNomeEmpresa] = useState('');
  const [dataInicioPrevisto, setDataInicioPrevisto] = useState('');
  
  const [tipo, setTipo] = useState(tipoModal);
  
  // --- CORREÇÃO AQUI (Linha 16) ---
  // Removido o '_' e corrigido para 'loading' e 'error' (para corresponder ao useMutation.js)
  const { callMutation, loading, error } = useMutation('/criar_implantacao');
  const navigate = useNavigate();

  // Atualiza o tipo se o prop mudar (quando o modal é reaberto)
  React.useEffect(() => {
    setTipo(tipoModal);
  }, [tipoModal]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!nomeEmpresa) return;

    const body = {
      nome_empresa: nomeEmpresa,
      tipo: tipo,
      data_inicio_previsto: tipo === 'futura' ? dataInicioPrevisto : null,
    };

    const result = await callMutation({ body, method: 'POST' });

    if (result && result.success) {
      // Sucesso! Limpa o formulário, fecha o modal e redireciona
      setNomeEmpresa('');
      setDataInicioPrevisto('');
      onClose();
      navigate(`/implantacao/${result.implantacao_id}`);
    }
  };

  if (!show) {
    return null; 
  }

  const isModulo = tipoModal === 'modulo';
  const title = isModulo ? 'Novo Módulo (Em Branco)' : 'Nova Implantação (Completa)';
  const buttonText = isModulo ? 'Criar Módulo' : 'Criar Implantação';
  
  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
        onClick={e => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">{title}</h2>
        
        <form onSubmit={handleSubmit}>
          {/* Nome da Empresa */}
          <div className="mt-4">
            <label htmlFor="nomeEmpresa" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Nome da Empresa
            </label>
            <input
              type="text"
              id="nomeEmpresa"
              value={nomeEmpresa}
              onChange={(e) => setNomeEmpresa(e.target.value)}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>

          {/* Seletor de Tipo (Apenas se NÃO for 'modulo') */}
          {!isModulo && (
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Tipo</label>
              <div className="mt-2 flex gap-4">
                <label className="flex items-center">
                  <input type="radio" name="tipo" value="agora" checked={tipo === 'agora'} onChange={(e) => setTipo(e.target.value)} className="focus:ring-blue-500" />
                  <span className="ml-2 text-gray-700 dark:text-gray-300">Imediata</span>
                </label>
                <label className="flex items-center">
                  <input type="radio" name="tipo" value="futura" checked={tipo === 'futura'} onChange={(e) => setTipo(e.target.value)} className="focus:ring-blue-500" />
                  <span className="ml-2 text-gray-700 dark:text-gray-300">Futura (Agendada)</span>
                </label>
              </div>
            </div>
          )}

          {/* Campo de Data (Apenas se for 'futura') */}
          {tipo === 'futura' && (
            <div className="mt-4">
              <label htmlFor="data_inicio_previsto" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Início Previsto
              </label>
              <input
                type="date"
                id="data_inicio_previsto"
                value={dataInicioPrevisto}
                onChange={(e) => setDataInicioPrevisto(e.target.value)}
                required
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
          )}
          
          {/* Mensagem de Erro (se houver) */}
          {error && (
            <div className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
              <strong>Erro:</strong> {error}
            </div>
          )}

          {/* Botões de Ação */}
          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 dark:border-gray-500 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {loading ? 'A criar...' : buttonText}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}