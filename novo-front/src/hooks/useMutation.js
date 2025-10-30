// Em: src/hooks/useMutation.js

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE_URL = 'http://localhost:5000';

/**
 * Hook para lidar com mutações (POST, PUT, DELETE) na API.
 * Retorna uma função para chamar a mutação e o estado (loading, error).
 */
export function useMutation(urlPath) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const callMutation = async ({ body, method = 'POST' }) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}${urlPath}`, {
        method: method,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        // Envia os cookies de sessão (Auth0)
        credentials: 'include', 
        body: JSON.stringify(body),
      });

      // Se a sessão expirou
      if (response.status === 401) {
        navigate('/login');
        return null; // Interrompe a execução
      }

      const jsonData = await response.json();

      if (!response.ok || !jsonData.success) {
        throw new Error(jsonData.error || `Erro na API: ${response.statusText}`);
      }

      // Sucesso! Retorna os dados da API (ex: o objeto recém-criado)
      return jsonData;

    } catch (err) {
      setError(err.message);
      return null; // Indica falha
    } finally {
      setLoading(false);
    }
  };

  return { callMutation, loading, error };
}