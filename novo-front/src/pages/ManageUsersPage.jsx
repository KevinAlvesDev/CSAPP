// Em: src/pages/ManageUsersPage.jsx

import React, { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useMutation } from '../hooks/useMutation';

// Componente para um único dropdown editável
function EditableDropdown({ id, initialValue, options, name, onSave }) {
  const [value, setValue] = useState(initialValue);
  const { callMutation, loading, error } = useMutation('/manage_users/atualizar_perfil');

  // Garante que o estado local reflita o valor inicial quando a lista for recarregada
  useEffect(() => {
    setValue(initialValue);
  }, [initialValue]);

  const handleSave = async () => {
    if (value === initialValue) return; // Nenhuma mudança
    
    // O corpo da requisição é a chave de usuário e o novo valor do campo
    const body = {
      usuario_id: id,
      [name]: value // Ex: 'cargo': 'Pleno' ou 'perfil_acesso': 'Admin'
    };

    const result = await callMutation({ body: body, method: 'POST' });

    if (result && result.success) {
      onSave(); // Avisa o pai para recarregar a lista
    } else {
      // Opcional: mostrar erro, mas por enquanto, apenas logamos
      console.error(error || "Falha ao salvar a alteração.");
      alert(error || `Falha ao atualizar ${name} para o usuário: ${id}`);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <select
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={loading}
        className="rounded-md border-gray-300 py-1 text-sm shadow-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white focus:border-blue-500 focus:ring-blue-500"
      >
        {/* Adiciona uma opção em branco ou padrão se o valor inicial não estiver nas opções */}
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
      <button
        onClick={handleSave}
        disabled={loading || value === initialValue}
        className="rounded-md bg-green-600 px-3 py-1 text-xs font-medium text-white shadow-sm hover:bg-green-700 disabled:opacity-50"
      >
        {loading ? '...' : 'Salvar'}
      </button>
    </div>
  );
}


export default function ManageUsersPage() {
  // 1. Hook para buscar dados
  const { data, loading, error, refetch } = useApi('/manage_users');
  
  // 2. Estado local
  const [users, setUsers] = useState([]);

  useEffect(() => {
    if (data && data.users) {
      setUsers(data.users);
    }
  }, [data]);

  // 3. Funções de Callback
  const handleUserUpdate = () => {
    refetch(); // Força a recarga da lista completa após uma edição
  };

  // 4. RENDERIZAÇÃO
  if (loading) {
    return <div className="text-center text-gray-700 dark:text-gray-300">A carregar usuários...</div>;
  }

  if (error) {
    return (
      <div className="rounded-md border border-red-300 bg-red-100 p-4 text-red-700">
        <strong>Erro ao carregar dados:</strong> {error}
      </div>
    );
  }

  const { cargos_options = [], perfis_acesso_options = [] } = data || {};
  
  if (!data?.is_manager) {
    return (
      <div className="rounded-md border border-yellow-300 bg-yellow-100 p-4 text-yellow-700">
        Acesso negado. Você precisa de permissões de gestão para ver esta página.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="rounded-lg bg-white p-6 shadow-md dark:bg-gray-800">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-white">
          Gerenciamento de Usuários
        </h1>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">Nome</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">E-mail (ID)</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">Cargo</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">Acesso</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-800">
              {users.map((user) => (
                <tr key={user.usuario}>
                  <td className="whitespace-nowrap px-6 py-4 font-medium text-gray-900 dark:text-white">
                    {user.nome}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {user.usuario}
                  </td>
                  <td className="px-6 py-4">
                    <EditableDropdown
                      id={user.usuario}
                      initialValue={user.cargo}
                      options={cargos_options}
                      name="cargo"
                      onSave={handleUserUpdate}
                    />
                  </td>
                  <td className="px-6 py-4">
                    <EditableDropdown
                      id={user.usuario}
                      initialValue={user.perfil_acesso}
                      options={perfis_acesso_options}
                      name="perfil_acesso"
                      onSave={handleUserUpdate}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {/* Informação do último carregamento */}
        <p className="mt-6 text-xs text-gray-400 dark:text-gray-600">
          Dados carregados em: {new Date().toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}