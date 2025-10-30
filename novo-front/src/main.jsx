// Em: src/main.jsx

import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import App from './App.jsx'
import LoginPage from './pages/Login.jsx';
import DashboardPage from './pages/Dashboard.jsx';
import ImplantacaoDetalhesPage from './pages/ImplantacaoDetalhes.jsx';
import ProfilePage from './pages/ProfilePage.jsx'; 
import ManageUsersPage from './pages/ManageUsersPage.jsx'; // <--- 1. IMPORTAR A NOVA PÁGINA
import './index.css'

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />, 
    children: [
      {
        path: "/", 
        element: <DashboardPage />,
      },
      {
        path: "/implantacao/:id",
        element: <ImplantacaoDetalhesPage />,
      },
      {
        path: "/perfil",
        element: <ProfilePage />,
      },
      // --- 2. ADICIONAR A NOVA ROTA DE GERENCIAMENTO ---
      {
        path: "/manage_users",
        element: <ManageUsersPage />,
      },
    ],
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
]);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)