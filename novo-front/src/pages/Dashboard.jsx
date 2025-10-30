// Em: src/pages/Dashboard.jsx

import React, { useState } from 'react';
import { useApi } from '../hooks/useApi'; 
import MetricCard from '../components/MetricCard'; 
import { Link, useNavigate, useLocation } from 'react-router-dom'; // <--- ADICIONA useNavigate e useLocation

// (Componente ImplantacoesTable - sem alterações no corpo)
function ImplantacoesTable({ title, implantacoes = [], statusColor = 'bg-gray-500' }) {
  const navigate = useNavigate();

  const handleRowClick = (id) => {
    navigate(`/implantacao/${id}`);
  };

  if (implantacoes.length === 0) {
    return (
      <div className="rounded-md border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-2 text-lg font-semibold text-gray-800 dark:text-white">{title}</h3>
        <p className="text-gray-500 dark:text-gray-400">Nenhuma implantação encontrada.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-white shadow-md dark:bg-gray-800">
      <h3 className="border-b border-gray-200 p-4 text-lg font-semibold text-gray-800 dark:border-gray-700 dark:text-white">
        {title} ({implantacoes.length})
      </h3>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">Empresa</th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">Dias</th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">Progresso</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-800">
            {implantacoes.map((impl) => (
              <tr 
                key={impl.id} 
                onClick={() => handleRowClick(impl.id)}
                className="cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <td className="whitespace-nowrap px-6 py-4">
                  <span className="font-medium text-blue-600 hover:underline dark:text-blue-400">
                    {impl.nome_empresa}
                  </span>
                </td>
                <td className="whitespace-nowrap px-6 py-4">
                  <span className="inline-flex rounded-full bg-gray-100 px-2 text-xs font-semibold leading-5 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                    {impl.dias_passados} dias
                  </span>
                </td>
                <td className="whitespace-nowrap px-6 py-4">
                  <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 text-white ${statusColor}`}>
                    {impl.progresso}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// --- O Componente Principal do Dashboard ---
export default function DashboardPage() {
  // 1. O HOOK useApi AGORA USA A URL, e o 'location.search' (dentro do hook) lida com os filtros.
  const { data, loading, error } = useApi('/dashboard');
  
  // 2. OBTEM PARÂMETROS DA URL
  const location = useLocation();
  const navigate = useNavigate();
  
  // Extrai o valor atual de 'cs_filter' da URL para inicializar o estado do formulário
  const currentSearchParams = new URLSearchParams(location.search);
  const initialCsFilter = currentSearchParams.get('cs_filter') || 'todos';

  // Estado local para o formulário de filtro
  const [csFilter, setCsFilter] = useState(initialCsFilter);

  // 3. HANDLER DE SUBMISSÃO DO FILTRO
  const handleFilterSubmit = (e) => {
    e.preventDefault();
    
    // Navega para a nova URL com o filtro
    if (csFilter === 'todos') {
      navigate(location.pathname); // Se for 'todos', limpa o filtro na URL
    } else {
      navigate(`?cs_filter=${csFilter}`);
    }
  };

  // 4. ESTADO DE LOADING, ERRO e SUCESSO (Como antes)
  if (loading) {
    return (
      <div className="text-center text-gray-700 dark:text-gray-300">
        A carregar dados do dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-red-300 bg-red-100 p-4 text-red-700">
        <strong>Erro ao carregar dados:</strong> {error}
      </div>
    );
  }

  const m = data?.metrics || {};
  const i = data || {};
  
  // Dados para o filtro de gerente
  const isManager = data?.is_manager || false;
  const allCsUsers = data?.all_cs_users || [];

  return (
    <div className="flex flex-col gap-6">
      
      {/* --- NOVO BLOCO: FILTRO DO GERENTE (Recurso 3) --- */}
      {isManager && (
        <div className="rounded-lg bg-white p-4 shadow-md dark:bg-gray-800">
          <h6 className="mb-3 border-b pb-2 text-sm font-semibold text-gray-800 dark:border-gray-700 dark:text-white">
            Filtros da Carteira
          </h6>
          <form onSubmit={handleFilterSubmit}>
            <div className="flex items-end gap-3">
              <div className="flex-grow">
                <label htmlFor="cs_filter" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Filtrar Colaborador CS
                </label>
                <select
                  id="cs_filter"
                  name="cs_filter"
                  value={csFilter}
                  onChange={(e) => setCsFilter(e.target.value)}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                  <option value="todos">
                    -- Visualizar Toda a Carteira --
                  </option>
                  {allCsUsers.map((cs) => (
                    <option key={cs.usuario} value={cs.usuario}>
                      {cs.nome} ({cs.usuario})
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="submit"
                className="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
              >
                Aplicar Filtro
              </button>
            </div>
          </form>
        </div>
      )}
      {/* --- FIM DO BLOCO DE FILTRO --- */}


      {/* Secção 1: Resumo Rápido */}
      <div>
        <h2 className="mb-3 text-xl font-semibold text-gray-800 dark:text-white">Resumo Rápido</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
          <MetricCard title="Em Andamento" value={m.impl_andamento_total || 0} colorClass="text-blue-600 dark:text-blue-400" />
          <MetricCard title="Atrasadas (> 25d)" value={m.implantacoes_atrasadas || 0} colorClass="text-red-600 dark:text-red-400" />
          <MetricCard title="Futuras" value={m.implantacoes_futuras || 0} colorClass="text-cyan-600 dark:text-cyan-400" />
          <MetricCard title="Concluídas" value={m.impl_finalizadas || 0} colorClass="text-green-600 dark:text-green-400" />
          <MetricCard title="Paradas" value={m.impl_paradas || 0} colorClass="text-yellow-600 dark:text-yellow-400" />
        </div>
      </div>

      {/* Secção 2: Tabelas (Usamos 'i' para as listas) */}
      <div>
        <h2 className="mb-3 text-xl font-semibold text-gray-800 dark:text-white">Listas de Implantação</h2>
        {/* --- NOVO: Implementamos as Abas (Tabs) que você já tinha no HTML --- */}
        {/* (Simplificado: renderizamos todas as tabelas em sequência por agora) */}
        
        <div className="flex flex-col gap-6">
          <ImplantacoesTable 
            title="Em Andamento" 
            implantacoes={i.implantacoes_andamento} 
            statusColor="bg-blue-500"
          />
          <ImplantacoesTable 
            title="Atrasadas" 
            implantacoes={i.implantacoes_atrasadas} 
            statusColor="bg-red-500"
          />
          <ImplantacoesTable 
            title="Futuras" 
            implantacoes={i.implantacoes_futuras} 
            statusColor="bg-cyan-500"
          />
          <ImplantacoesTable 
            title="Paradas" 
            implantacoes={i.implantacoes_paradas} 
            statusColor="bg-yellow-500"
          />
          <ImplantacoesTable 
            title="Concluídas" 
            implantacoes={i.implantacoes_finalizadas} 
            statusColor="bg-green-500"
          />
        </div>
      </div>
      
    </div>
  );
}