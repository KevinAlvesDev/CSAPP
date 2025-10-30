// Em: src/components/EditImplantacaoModal.jsx

import React, { useState, useEffect } from 'react';
import { useMutation } from '../hooks/useMutation';

// Componente de <select> reutilizável para o formulário
function FormSelect({ label, name, value, onChange, options = [], defaultOption = "Selecione..." }) {
  // A API espera 'null' se "Não definido" for selecionado, e não a string
  const handleChange = (e) => {
    const val = e.target.value === "Não definido" ? null : e.target.value;
    onChange({ target: { name, value: val } });
  };

  return (
    <div className="mb-3">
      <label htmlFor={name} className="form-label mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
      </label>
      <select
        id={name}
        name={name}
        value={value || ''} // Controla o <select>, tratando null/undefined
        onChange={handleChange}
        className="form-select mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
      >
        <option value="">{defaultOption}</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    </div>
  );
}

// Componente de <input> reutilizável
function FormInput({ label, name, value, onChange, type = "text", ...props }) {
  return (
    <div className="mb-3">
      <label htmlFor={name} className="form-label mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
      </label>
      <input
        type={type}
        id={name}
        name={name}
        value={value || ''} // Controla o <input>, tratando null/undefined
        onChange={onChange}
        className="form-control mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
        {...props}
      />
    </div>
  );
}


export default function EditImplantacaoModal({ show, onClose, implantacao, constants, onSuccess }) {
  const [formData, setFormData] = useState({});
  const { callMutation, loading, error } = useMutation(`/implantacao/${implantacao?.id}/atualizar_detalhes`);

  // 1. Popula o formulário quando o modal é aberto
  useEffect(() => {
    if (show && implantacao) {
      // Carrega o formulário com os dados atuais da implantação
      setFormData({
        responsavel_cliente: implantacao.responsavel_cliente,
        cargo_responsavel: implantacao.cargo_responsavel,
        telefone_responsavel: implantacao.telefone_responsavel,
        email_responsavel: implantacao.email_responsavel,
        data_inicio_producao: implantacao.data_inicio_producao_iso, // A API espera ISO
        data_final_implantacao: implantacao.data_final_implantacao_iso, // A API espera ISO
        id_favorecido: implantacao.id_favorecido,
        nivel_receita: implantacao.nivel_receita,
        chave_oamd: implantacao.chave_oamd,
        tela_apoio_link: implantacao.tela_apoio_link,
        seguimento: implantacao.seguimento,
        tipos_planos: implantacao.tipos_planos,
        modalidades: implantacao.modalidades,
        horarios_func: implantacao.horarios_func,
        formas_pagamento: implantacao.formas_pagamento,
        diaria: implantacao.diaria,
        freepass: implantacao.freepass,
        alunos_ativos: implantacao.alunos_ativos,
        sistema_anterior: implantacao.sistema_anterior,
        importacao: implantacao.importacao,
        recorrencia_usa: implantacao.recorrencia_usa,
        boleto: implantacao.boleto,
        nota_fiscal: implantacao.nota_fiscal,
        catraca: implantacao.catraca,
        facial: implantacao.facial,
        // (Campos ocultos do HTML base não foram incluídos por simplicidade)
      });
    }
  }, [show, implantacao]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Filtra apenas os campos que foram alterados (opcional, mas boa prática)
    // O backend já está preparado para receber JSON
    const result = await callMutation({ body: formData, method: 'POST' });

    if (result && result.success) {
      onSuccess(result.implantacao); // Passa a implantação atualizada de volta
      onClose(); // Fecha o modal
    }
    // O 'error' do hook será exibido
  };

  if (!show) return null;
  if (!constants) return <p>A carregar constantes...</p>; // Proteção

  const simNao = constants.SIM_NAO_OPTIONS || [];

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-3xl rounded-lg bg-white shadow-xl dark:bg-gray-800"
        onClick={e => e.stopPropagation()}
      >
        <form onSubmit={handleSubmit}>
          {/* Header */}
          <div className="border-b border-gray-200 p-4 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Detalhes da Empresa
            </h2>
          </div>

          {/* Body (Scrollável) */}
          <div className="max-h-[75vh] overflow-y-auto p-6">
            <h6 className="mb-3 text-sm font-semibold text-blue-600 dark:text-blue-400">Contatos e Responsáveis</h6>
            <div className="grid grid-cols-1 gap-x-4 md:grid-cols-3">
              <FormInput label="Resp. Cliente (Nome)" name="responsavel_cliente" value={formData.responsavel_cliente} onChange={handleChange} />
              <FormSelect label="Cargo Resp." name="cargo_responsavel" value={formData.cargo_responsavel} onChange={handleChange} options={constants.CARGOS_RESPONSAVEL} />
              <FormInput label="E-mail Resp." name="email_responsavel" value={formData.email_responsavel} onChange={handleChange} type="email" />
            </div>
            <div className="grid grid-cols-1 gap-x-4 md:grid-cols-3">
              <FormInput label="Telefone Resp." name="telefone_responsavel" value={formData.telefone_responsavel} onChange={handleChange} type="tel" />
            </div>

            <h6 className="mb-3 mt-4 text-sm font-semibold text-blue-600 dark:text-blue-400">Datas e Atributos</h6>
            <div className="grid grid-cols-1 gap-x-4 md:grid-cols-3">
              <FormInput label="Início Produção (Data)" name="data_inicio_producao" value={formData.data_inicio_producao} onChange={handleChange} type="date" />
              <FormInput label="Fim da Implantação (Data)" name="data_final_implantacao" value={formData.data_final_implantacao} onChange={handleChange} type="date" />
              <FormInput label="ID Favorecido" name="id_favorecido" value={formData.id_favorecido} onChange={handleChange} />
            </div>
             <div className="grid grid-cols-1 gap-x-4 md:grid-cols-3">
              <FormSelect label="Nível de Receita (MRR)" name="nivel_receita" value={formData.nivel_receita} onChange={handleChange} options={constants.NIVEIS_RECEITA} />
              <FormInput label="Chave OAMD" name="chave_oamd" value={formData.chave_oamd} onChange={handleChange} />
            </div>
            <FormInput label="Tela de Apoio (Link)" name="tela_apoio_link" value={formData.tela_apoio_link} onChange={handleChange} type="url" />

            <h6 className="mb-3 mt-4 text-sm font-semibold text-blue-600 dark:text-blue-400">Configurações Operacionais</h6>
            <div className="grid grid-cols-1 gap-x-4 md:grid-cols-3">
              <FormSelect label="Seguimento" name="seguimento" value={formData.seguimento} onChange={handleChange} options={constants.SEGUIMENTOS_LIST} />
              <FormSelect label="Tipos de Planos" name="tipos_planos" value={formData.tipos_planos} onChange={handleChange} options={constants.TIPOS_PLANOS} />
              <FormSelect label="Modalidades" name="modalidades" value={formData.modalidades} onChange={handleChange} options={constants.MODALIDADES_LIST} />
            </div>
            <div className="grid grid-cols-1 gap-x-4 md:grid-cols-2">
              <FormSelect label="Horários" name="horarios_func" value={formData.horarios_func} onChange={handleChange} options={constants.HORARIOS_FUNCIONAMENTO} />
              <FormSelect label="Pagamento" name="formas_pagamento" value={formData.formas_pagamento} onChange={handleChange} options={constants.FORMAS_PAGAMENTO} />
            </div>
            <div className="grid grid-cols-1 gap-x-4 md:grid-cols-3">
              <FormSelect label="Diária?" name="diaria" value={formData.diaria} onChange={handleChange} options={simNao} defaultOption="Não definido" />
              <FormSelect label="Freepass?" name="freepass" value={formData.freepass} onChange={handleChange} options={simNao} defaultOption="Não definido" />
              <FormInput label="Alunos Ativos" name="alunos_ativos" value={formData.alunos_ativos} onChange={handleChange} type="number" min="0" />
            </div>
            
            <h6 className="mb-3 mt-4 text-sm font-semibold text-blue-600 dark:text-blue-400">Sistemas e Integrações</h6>
            <div className="grid grid-cols-1 gap-x-4 md:grid-cols-2">
              <FormSelect label="Sistema Anterior" name="sistema_anterior" value={formData.sistema_anterior} onChange={handleChange} options={constants.SISTEMAS_ANTERIORES} />
              <FormSelect label="Recorrência (Empresa)" name="recorrencia_usa" value={formData.recorrencia_usa} onChange={handleChange} options={constants.RECORRENCIA_USADA} />
            </div>
            <div className="grid grid-cols-2 gap-x-4 md:grid-cols-3 lg:grid-cols-5">
              <FormSelect label="Importação?" name="importacao" value={formData.importacao} onChange={handleChange} options={simNao} defaultOption="Não definido" />
              <FormSelect label="Boleto?" name="boleto" value={formData.boleto} onChange={handleChange} options={simNao} defaultOption="Não definido" />
              <FormSelect label="Nota Fiscal?" name="nota_fiscal" value={formData.nota_fiscal} onChange={handleChange} options={simNao} defaultOption="Não definido" />
              <FormSelect label="Catraca?" name="catraca" value={formData.catraca} onChange={handleChange} options={simNao} defaultOption="Não definido" />
              <FormSelect label="Facial?" name="facial" value={formData.facial} onChange={handleChange} options={simNao} defaultOption="Não definido" />
            </div>

            {/* Mensagem de Erro */}
            {error && (
              <div className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
                <strong>Erro ao salvar:</strong> {error}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 border-t border-gray-200 p-4 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-50 dark:border-gray-500 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {loading ? 'A salvar...' : 'Salvar Alterações'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}