// Em: src/components/CommentBox.jsx

import React, { useState } from 'react';
import { useFileUploadMutation } from '../hooks/useFileUploadMutation';
import { useMutation } from '../hooks/useMutation';

// Ícone de Lixeira para excluir
function TrashIcon() {
  return (
    <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M16.5 4.478v.227a48.816 48.816 0 01-8.832 4.634l-.001.001-2.017 1.009a.75.75 0 00-.364.646v5.416a.75.75 0 00.564.722l8.832-4.417a.75.75 0 00.364-.646V4.478a.75.75 0 00-1.22-.592l-2.201 1.101a51.31 51.31 0 00-1.634.817l-1.396.698 8.832-4.416a.75.75 0 00.564.722zM3 4.25a.75.75 0 00-.722.564l-2.017 1.009a.75.75 0 00-.364.646v5.416a.75.75 0 00.564.722l10.032-5.016a.75.75 0 00.364-.646V4.478a.75.75 0 00-1.22-.592L7.22 4.985l-1.634.817L4.19 6.498 3 7.094V4.25z" clipRule="evenodd" />
    </svg>
  );
}

export default function CommentBox({ taskId, initialComments = [], onCommentChange }) {
  // Estado para a lista de comentários (iniciada com os props)
  const [comments, setComments] = useState(initialComments);
  // Estado para o novo comentário
  const [newCommentText, setNewCommentText] = useState('');
  const [newCommentImage, setNewCommentImage] = useState(null);
  const [error, setError] = useState(null);

  // Hook para Adicionar Comentário (com upload)
  const { callMutation: addComment, loading: isAdding } = useFileUploadMutation('/api/adicionar_comentario');
  
  // Hook para Excluir Comentário (JSON simples)
  const { callMutation: deleteComment, loading: isDeleting } = useMutation('/api/excluir_comentario');

  const handleAddComment = async (e) => {
    e.preventDefault();
    setError(null);
    if (!newCommentText && !newCommentImage) return;

    // 1. Criar o FormData
    const formData = new FormData();
    formData.append('tarefa_id', taskId);
    formData.append('comentario_texto', newCommentText);
    if (newCommentImage) {
      formData.append('imagem_file', newCommentImage);
    }

    // 2. Chamar a API
    const result = await addComment(formData);

    if (result && result.success && result.comentario) {
      // 3. Sucesso: Adiciona o novo comentário ao estado local
      setComments(prev => [result.comentario, ...prev]);
      setNewCommentText('');
      setNewCommentImage(null);
      e.target.reset(); // Limpa o input de arquivo
      onCommentChange(); // Avisa o pai (para atualizar a barra de progresso, se necessário)
    } else {
      setError(result?.error || "Falha ao adicionar comentário.");
    }
  };

  const handleDeleteComment = async (commentId) => {
    if (window.confirm("Tem certeza que deseja excluir este comentário?")) {
      const result = await deleteComment({
        body: { comentario_id: commentId },
        method: 'POST'
      });
      if (result && result.success) {
        // Sucesso: Remove o comentário do estado local
        setComments(prev => prev.filter(c => c.id !== commentId));
        onCommentChange();
      } else {
        setError(result?.error || "Falha ao excluir comentário.");
      }
    }
  };
  
  const isLoading = isAdding || isDeleting;

  return (
    <div className="border-t border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
      
      {/* 1. Formulário para Adicionar Comentário */}
      <form onSubmit={handleAddComment} className="mb-4">
        <label htmlFor={`comment-text-${taskId}`} className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
          Adicionar Comentário
        </label>
        <textarea
          id={`comment-text-${taskId}`}
          rows="2"
          value={newCommentText}
          onChange={(e) => setNewCommentText(e.target.value)}
          placeholder="Escreva um comentário..."
          className="mb-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
        />
        <div className="flex items-center justify-between gap-4">
          <input
            type="file"
            onChange={(e) => setNewCommentImage(e.target.files[0])}
            className="text-sm text-gray-500
                       file:mr-4 file:rounded-full file:border-0
                       file:bg-blue-50 file:px-4 file:py-2
                       file:text-sm file:font-semibold file:text-blue-700
                       hover:file:bg-blue-100 dark:text-gray-400 dark:file:bg-blue-900 dark:file:text-blue-200"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
          >
            {isAdding ? 'Enviando...' : 'Enviar'}
          </button>
        </div>
        {error && (
          <p className="mt-2 text-sm text-red-600">{error}</p>
        )}
      </form>

      {/* 2. Lista de Comentários Existentes */}
      <h5 className="mb-2 text-sm font-semibold text-gray-800 dark:text-white">
        Histórico ({comments.length})
      </h5>
      <div className="max-h-60 space-y-3 overflow-y-auto pr-2">
        {comments.length === 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400">Nenhum comentário nesta tarefa.</p>
        )}
        {comments.map((comment) => (
          <div key={comment.id} className="rounded-md bg-white p-3 shadow-sm dark:bg-gray-800">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">
                {comment.usuario_nome}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {comment.data_criacao_fmt_d}
              </span>
            </div>
            {comment.comentario && (
              <p className="mt-2 text-sm text-gray-800 dark:text-gray-200">
                {comment.comentario}
              </p>
            )}
            {comment.imagem_url && (
              <a href={comment.imagem_url} target="_blank" rel="noopener noreferrer" className="mt-2 block">
                <img 
                  src={comment.imagem_url} 
                  alt="Anexo" 
                  className="max-h-40 rounded-md border border-gray-200 dark:border-gray-700" 
                />
              </a>
            )}
            {/* Botão Excluir Comentário */}
            <button
              onClick={() => handleDeleteComment(comment.id)}
              disabled={isLoading}
              className="mt-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs text-red-600 hover:bg-red-100 disabled:opacity-50 dark:hover:bg-red-900"
            >
              <TrashIcon /> Excluir
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}