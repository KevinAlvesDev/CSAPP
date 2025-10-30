// Em: src/hooks/useFileUploadMutation.js

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE_URL = 'http://localhost:5000';

/**
 * Hook para lidar com mutações (POST) que enviam FormData (arquivos).
 */
export function useFileUploadMutation(urlPath) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // O 'body' aqui deve ser um objeto FormData
  const callMutation = async (formData) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}${urlPath}`, {
        method: 'POST',
        // IMPORTANTE: Não definimos 'Content-Type'. O navegador
        // faz isso automaticamente para 'FormData' (com o 'boundary' correto).
        headers: {
          'Accept': 'application/json',
        },
        // Envia os cookies de sessão (Auth0)
        credentials: 'include', 
        body: formData, // Envia o FormData diretamente
      });

      if (response.status === 401) {
        navigate('/login');
        return null;
      }

      const jsonData = await response.json();

      if (!response.ok || !jsonData.success) {
        throw new Error(jsonData.error || `Erro na API: ${response.statusText}`);
      }

      return jsonData; // Sucesso!

    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { callMutation, loading, error };
}