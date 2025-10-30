// Em: src/App.jsx

import React, { useState } from 'react';
import { Outlet, Link } from 'react-router-dom';
import NewImplantacaoModal from './components/NewImplantacaoModal';

function App() {
  const logoutUrl = 'http://localhost:5000/logout';
  const [modalType, setModalType] = useState(null);

  const handleOpenModal = (tipo) => {
    if (tipo === 'agora' || tipo === 'futura') {
      setModalType('agora');
    } else {
      setModalType('modulo');
    }
  };

  const handleCloseModal = () => {
    setModalType(null);
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 transition-colors">
      
      <header className="bg-white shadow-md dark:bg-gray-800">
        <nav className="container mx-auto flex items-center justify-between p-4">
          <div>
            <Link to="/" className="text-xl font-bold text-blue-600 dark:text-blue-400">
              CS Onboarding
            </Link>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleOpenModal('agora')}
              className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
            >
              Nova Implantação
            </button>
            <button
              onClick={() => handleOpenModal('modulo')}
              className="rounded-md bg-gray-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-gray-700"
            >
              Novo Módulo
            </button>
            
            {/* --- NOVO LINK: Gerenciamento de Usuários --- */}
            <Link 
              to="/manage_users"
              className="rounded-md px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-200 dark:text-purple-400 dark:hover:bg-purple-700"
            >
              Gerenciar Usuários
            </Link>
            {/* ------------------------------------------ */}
            
            <Link 
              to="/perfil"
              className="rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Editar Perfil
            </Link>

            <a 
              href={logoutUrl}
              className="rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Sair
            </a>
          </div>
        </nav>
      </header>

      <main className="container mx-auto p-4 md:p-8">
        <Outlet />
      </main>
      
      <NewImplantacaoModal 
        show={modalType !== null} 
        onClose={handleCloseModal}
        tipoModal={modalType || 'agora'}
      />

    </div>
  )
}

export default App