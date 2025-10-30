// Em: src/hooks/useApi.js

import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom'; // <--- Adiciona useLocation

// O URL base da sua API Flask
const API_BASE_URL = 'http://localhost:5000'; 

// Adiciona um parâmetro 'shouldRefetch' para controlar manualmente a re-busca
export function useApi(urlPath, shouldRefetch = false) { // <--- MODIFICADO
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const location = useLocation(); // <--- OBTÉM INFORMAÇÕES DA URL ATUAL

  // Função para construir o URL completo com parâmetros de busca
  const getFullUrl = () => {
    // Usa o pathname (ex: /dashboard) e o search (ex: ?cs_filter=...)
    return `${API_BASE_URL}${urlPath}${location.search}`; 
  };
  
  // Função que será retornada para forçar uma nova busca
  const refetch = () => {
      // Simplesmente re-executa o efeito com o mesmo URL (opcional, já que mudamos o useEffect)
      // O truque aqui é que o useEffect abaixo reage a mudanças no location.search
      // Para o caso de um POST forçar o refetch, usamos o shouldRefetch
      fetchData(getFullUrl());
  };


  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      const fullApiUrl = getFullUrl();
      
      try {
        const response = await fetch(fullApiUrl, {
          credentials: 'include', 
        });

        if (response.status === 401) {
          navigate('/login');
          return;
        }

        if (!response.ok) {
          throw new Error(`Erro na API: ${response.statusText}`);
        }

        const jsonData = await response.json();

        if (jsonData.success) {
          setData(jsonData);
        } else {
          throw new Error(jsonData.error || 'A API retornou um erro.');
        }

      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // O useEffect é re-executado quando o 'location.search' (parâmetros de filtro) muda.
    // Isso garante que a API é chamada novamente com os novos filtros.
  }, [location.search, navigate, urlPath]); // <--- DEPENDÊNCIAS CHAVE: location.search

  return { data, loading, error, refetch };
}