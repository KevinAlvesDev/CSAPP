// Em: src/pages/ProfilePage.jsx

import React, { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useFileUploadMutation } from '../hooks/useFileUploadMutation';

// Lista de cargos, baseada no seu constants.py
const CARGOS_LISTA = ["Júnior", "Pleno", "Sênior", "Estagiário"];

export default function ProfilePage() {
  // 1. Hooks de dados
  // Busca os dados do perfil atual
  const { data: apiData, loading: isLoadingData, refetch } = useApi('/perfil');
  // Prepara a mutação (upload) para o endpoint de atualização
  const { callMutation, loading: isUploading, error: uploadError } = useFileUploadMutation('/perfil/atualizar');

  // 2. Estado do Formulário
  const [nome, setNome] = useState('');
  const [cargo, setCargo] = useState('');
  const [fotoFile, setFotoFile] = useState(null); // O novo arquivo de imagem
  const [fotoPreview, setFotoPreview] = useState(null); // URL de preview da nova imagem
  const [successMessage, setSuccessMessage] = useState(null);

  // 3. Efeito para popular o formulário quando os dados da API chegarem
  useEffect(() => {
    if (apiData && apiData.perfil) {
      setNome(apiData.perfil.nome || '');
      setCargo(apiData.perfil.cargo || '');
      // O preview inicial é a foto de perfil atual
      setFotoPreview(apiData.perfil.foto_url || null);
    }
  }, [apiData]);

  // 4. Handler para quando o usuário seleciona uma nova foto
  const handleFotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFotoFile(file);
      // Cria um URL temporário para o preview da imagem
      setFotoPreview(URL.createObjectURL(file));
    }
  };

  // 5. Handler para submeter o formulário
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSuccessMessage(null);

    // A API espera FormData
    const formData = new FormData();
    formData.append('nome', nome);
    formData.append('cargo', cargo);
    if (fotoFile) {
      formData.append('foto_url', fotoFile);
    }

    const result = await callMutation(formData);

    if (result && result.success) {
      setSuccessMessage("Perfil atualizado com sucesso!");
      setFotoFile(null); // Limpa o arquivo selecionado
      refetch(); // Busca os dados do perfil novamente
    }
    // O 'uploadError' do hook será exibido automaticamente
  };
  
  if (isLoadingData) {
    return <div className="text-center text-gray-700 dark:text-gray-300">A carregar perfil...</div>;
  }
  
  const currentFoto = apiData?.perfil?.foto_url;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="rounded-lg bg-white p-6 shadow-md dark:bg-gray-800">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-white">
          Editar Perfil
        </h1>
        
        <form onSubmit={handleSubmit}>
          {/* Mensagens de Sucesso ou Erro */}
          {successMessage && (
            <div className="mb-4 rounded-md bg-green-100 p-3 text-sm text-green-700">
              {successMessage}
            </div>
          )}
          {uploadError && (
            <div className="mb-4 rounded-md bg-red-100 p-3 text-sm text-red-700">
              <strong>Erro:</strong> {uploadError}
            </div>
          )}

          <div className="space-y-4">
            {/* Preview da Foto */}
            <div className="flex flex-col items-center">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Foto de Perfil</label>
              <img
                src={fotoPreview || 'https://via.placeholder.com/150'} // Imagem placeholder
                alt="Preview do Perfil"
                className="mt-2 h-32 w-32 rounded-full object-cover"
              />
              <input
                type="file"
                accept="image/png, image/jpeg, image/gif"
                onChange={handleFotoChange}
                className="mt-4 text-sm text-gray-500
                           file:mr-4 file:rounded-full file:border-0
                           file:bg-blue-50 file:px-4 file:py-2
                           file:text-sm file:font-semibold file:text-blue-700
                           hover:file:bg-blue-100 dark:text-gray-400 dark:file:bg-blue-900 dark:file:text-blue-200"
              />
            </div>

            {/* Nome */}
            <div>
              <label htmlFor="nome" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Nome Completo
              </label>
              <input
                type="text"
                id="nome"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                required
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
            
            {/* Cargo */}
            <div>
              <label htmlFor="cargo" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Cargo
              </label>
              <select
                id="cargo"
                value={cargo}
                onChange={(e) => setCargo(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option value="">-- Selecione seu cargo --</option>
                {CARGOS_LISTA.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>
          
          {/* Botão Salvar */}
          <div className="mt-8 flex justify-end">
            <button
              type="submit"
              disabled={isUploading}
              className="rounded-md border border-transparent bg-blue-600 px-6 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {isUploading ? 'Salvando...' : 'Salvar Alterações'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}