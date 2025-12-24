/**
 * Modal Detalhes da Empresa Logic
 * Extracted from base.html for better maintainability.
 */

(function () {
    'use strict';

    console.log('🔧 modal_detalhes_empresa.js CARREGADO');

    let tomSelectInstances = {};
    let lastTriggerEl = null;

    // =========================================================================
    // DATA CONSISTENCY CHECKER - Automated Validation System
    // =========================================================================
    const DataConsistencyChecker = {
        enabled: false, // Disabled to prevent interference with form data
        serverData: null,
        displayedData: null,

        captureServerData(impl) {
            if (!this.enabled) return;

            this.serverData = {
                responsavel_cliente: impl.responsavel_cliente || '',
                cargo_responsavel: impl.cargo_responsavel || '',
                telefone_responsavel: impl.telefone_responsavel || '',
                email_responsavel: impl.email_responsavel || '',
                id_favorecido: impl.id_favorecido || '',
                chave_oamd: impl.chave_oamd || '',
                tela_apoio_link: impl.tela_apoio_link || '',
                valor_atribuido: impl.valor_atribuido != null ? String(impl.valor_atribuido) : '',
                status_implantacao_oamd: impl.status_implantacao_oamd || '',
                nivel_atendimento: impl.nivel_atendimento || '',
                catraca: impl.catraca || '',
                modelo_catraca: impl.modelo_catraca || '',
                facial: impl.facial || '',
                modelo_facial: impl.modelo_facial || '',
                wellhub: impl.wellhub || '',
                totalpass: impl.totalpass || '',
                cnpj: impl.cnpj || '',
                sistema_anterior: impl.sistema_anterior || '',
                recorrencia_usa: impl.recorrencia_usa || '',
                importacao: impl.importacao || '',
                boleto: impl.boleto || '',
                nota_fiscal: impl.nota_fiscal || '',
                diaria: impl.diaria || '',
                freepass: impl.freepass || '',
                alunos_ativos: impl.alunos_ativos != null ? String(impl.alunos_ativos) : '',
                informacao_infra: impl.informacao_infra || '',
                modalidades: impl.modalidades || '',
                horarios_func: impl.horarios_func || '',
                formas_pagamento: impl.formas_pagamento || '',
                seguimento: impl.seguimento || '',
                tipos_planos: impl.tipos_planos || ''
            };

            console.log('✅ [Consistency] Server data captured:', Object.keys(this.serverData).length, 'fields');
        },

        captureDisplayedData(modal) {
            if (!this.enabled) return;

            const getValue = (selector) => {
                const el = modal.querySelector(selector);
                if (!el) return '';

                // Handle TomSelect multi-select
                if (el.tomselect) {
                    const values = el.tomselect.getValue();
                    return Array.isArray(values) ? values.join(',') : String(values);
                }

                return el.value || '';
            };

            this.displayedData = {
                responsavel_cliente: getValue('#modal-responsavel_cliente'),
                cargo_responsavel: getValue('#modal-cargo_responsavel'),
                telefone_responsavel: getValue('#modal-telefone_responsavel'),
                email_responsavel: getValue('#modal-email_responsavel'),
                id_favorecido: getValue('#modal-id_favorecido'),
                chave_oamd: getValue('#modal-chave_oamd'),
                tela_apoio_link: getValue('#modal-tela_apoio_link'),
                valor_atribuido: getValue('#modal-valor_atribuido'),
                status_implantacao_oamd: getValue('#modal-status_implantacao'),
                nivel_atendimento: getValue('#modal-nivel_atendimento'),
                catraca: getValue('#modal-catraca'),
                modelo_catraca: getValue('#modal-modelo_catraca'),
                facial: getValue('#modal-facial'),
                modelo_facial: getValue('#modal-modelo_facial'),
                wellhub: getValue('#modal-wellhub'),
                totalpass: getValue('#modal-totalpass'),
                cnpj: getValue('#modal-cnpj'),
                sistema_anterior: getValue('#modal-sistema_anterior'),
                recorrencia_usa: getValue('#modal-recorrencia_usa'),
                importacao: getValue('#modal-importacao'),
                boleto: getValue('#modal-boleto'),
                nota_fiscal: getValue('#modal-nota_fiscal'),
                diaria: getValue('#modal-diaria'),
                freepass: getValue('#modal-freepass'),
                alunos_ativos: getValue('#modal-alunos_ativos'),
                informacao_infra: getValue('#modal-informacao_infra'),
                modalidades: getValue('#modal-modalidades'),
                horarios_func: getValue('#modal-horarios_func'),
                formas_pagamento: getValue('#modal-formas_pagamento'),
                seguimento: getValue('#modal-seguimento'),
                tipos_planos: getValue('#modal-tipos_planos')
            };

            console.log('📋 [Consistency] Displayed data captured:', Object.keys(this.displayedData).length, 'fields');
        },

        validate() {
            if (!this.enabled || !this.serverData || !this.displayedData) {
                console.warn('⚠️ [Consistency] Validation skipped - missing data');
                return true;
            }

            const inconsistencies = [];

            for (const key in this.serverData) {
                const serverValue = String(this.serverData[key] || '').trim();
                const displayedValue = String(this.displayedData[key] || '').trim();

                if (serverValue !== displayedValue) {
                    inconsistencies.push({
                        field: key,
                        server: serverValue,
                        displayed: displayedValue,
                        diff: `"${serverValue}" → "${displayedValue}"`
                    });
                }
            }

            if (inconsistencies.length > 0) {
                console.group('❌ [Consistency] INCONSISTÊNCIAS DETECTADAS!');
                console.error(`${inconsistencies.length} campo(s) diferem do servidor:`);
                console.table(inconsistencies);
                console.groupEnd();

                // Visual alert in development
                if (window.showToast) {
                    showToast(
                        `⚠️ INCONSISTÊNCIA: ${inconsistencies.length} campo(s) diferem do servidor! Verifique o console.`,
                        'error',
                        8000
                    );
                }

                return false;
            }

            console.log('✅ [Consistency] Validação completa - Todos os campos consistentes!');
            return true;
        },

        reset() {
            this.serverData = null;
            this.displayedData = null;
            console.log('🔄 [Consistency] Reset');
        }
    };

    // Expose globally for debugging
    window.DataConsistencyChecker = DataConsistencyChecker;

    // Initialize TomSelect for multi-select fields
    const initializeMultiTagInput = (selector, dataValue) => {
        const modalDetalhesEmpresa = document.getElementById('modalDetalhesEmpresa');
        if (!modalDetalhesEmpresa) return;

        const selectElement = modalDetalhesEmpresa.querySelector(selector);
        if (!selectElement) return;

        if (tomSelectInstances[selector]) {
            try { tomSelectInstances[selector].destroy(); } catch (_) { }
            delete tomSelectInstances[selector];
        }

        // Also check if element already has TomSelect attached directly
        if (selectElement.tomselect) {
            try { selectElement.tomselect.destroy(); } catch (_) { }
        }

        const values = (typeof dataValue === 'string' && dataValue)
            ? dataValue.split(',').map(s => s.trim()).filter(s => s.length > 0)
            : [];

        // Initialize TomSelect
        const tomSelect = new TomSelect(selectElement, {
            create: true,
            persist: false,
            delimiter: ',',
            items: [],
            plugins: ['remove_button'], // Optional: add remove button for better UX
            onInitialize: function () {
                // Add existing values as options if they don't exist
                values.forEach(value => {
                    if (!this.options.hasOwnProperty(value)) {
                        this.addOption({ value: value, text: value });
                    }
                });
                this.setValue(values);
            }
        });

        tomSelectInstances[selector] = tomSelect;
    };

    // Initialize TomSelect for single-select fields (if needed in future, kept for compatibility)
    const initializeSingleTagInput = (selector, dataValue) => {
        const modalDetalhesEmpresa = document.getElementById('modalDetalhesEmpresa');
        if (!modalDetalhesEmpresa) return;

        const selectElement = modalDetalhesEmpresa.querySelector(selector);
        if (!selectElement) return;

        if (tomSelectInstances[selector]) {
            try { tomSelectInstances[selector].destroy(); } catch (_) { }
            delete tomSelectInstances[selector];
        }

        // Also check if element already has TomSelect attached directly
        if (selectElement.tomselect) {
            try { selectElement.tomselect.destroy(); } catch (_) { }
        }

        const tomSelect = new TomSelect(selectElement, {
            create: true,
            persist: false,
            items: []
        });

        if (dataValue && !tomSelect.options.hasOwnProperty(dataValue)) {
            tomSelect.addOption({ value: dataValue, text: dataValue });
        }

        tomSelect.setValue(dataValue);
        tomSelectInstances[selector] = tomSelect;
    };

    // Main initialization
    document.addEventListener('DOMContentLoaded', function () {
        const modalDetalhesEmpresa = document.getElementById('modalDetalhesEmpresa');
        if (!modalDetalhesEmpresa) return;

        // Phone input event listeners (replacing inline handlers)
        const telefoneInput = modalDetalhesEmpresa.querySelector('#modal-telefone_responsavel');
        if (telefoneInput) {
            telefoneInput.addEventListener('input', function () {
                if (window.formatarTelefone) window.formatarTelefone(this);
            });
            telefoneInput.addEventListener('blur', function () {
                if (window.validarTelefoneCompleto) window.validarTelefoneCompleto(this);
            });
        }

        // Modal Show Event - REFACTORED FOR DEFINITIVE FIX
        modalDetalhesEmpresa.addEventListener('show.bs.modal', async function (event) {
            const safeSet = function (selOrEl, value, root) {
                const el = typeof selOrEl === 'string' ? (root || document).querySelector(selOrEl) : selOrEl;
                if (!el) return;
                try {
                    // Handle checkbox/radio
                    if (el.type === 'checkbox' || el.type === 'radio') {
                        // Logic for checkbox/radio if needed, currently safeSet seems used for values
                    }
                    el.value = value;
                } catch (_) { }
            };

            const button = event.relatedTarget;
            lastTriggerEl = button || null;

            // Helper to get data attributes safely
            const getData = (key, defaultVal = '') => {
                const val = button && button.getAttribute ? button.getAttribute(`data-${key}`) : null;
                return (val === 'null' || val === 'undefined' || val === null || val === 'None' || val === undefined || val === '') ? defaultVal : val;
            };

            const modal = event.target || modalDetalhesEmpresa;

            // Determine Implantacao ID
            let implId = getData('id');
            if (!implId) {
                const hiddenIdEl = modal.querySelector('#modal-implantacao_id');
                implId = hiddenIdEl && hiddenIdEl.value ? hiddenIdEl.value : implId;
            }
            if (!implId) {
                const m = (location.pathname || '').match(/\/implantacao\/(\d+)/);
                implId = m && m[1] ? m[1] : implId;
            }

            // Set implantacao ID immediately
            safeSet('#modal-implantacao_id', implId, modal);

            const normalizeToISO = (s) => {
                if (!s) return '';
                const t = String(s).trim();
                let m = t.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
                if (m) return `${m[3]}-${m[2]}-${m[1]}`;
                m = t.match(/^(\d{4})-(\d{2})-(\d{2})/);
                if (m) return `${m[1]}-${m[2]}-${m[3]}`;
                return '';
            };

            const setFpDate = (fp, s) => {
                const iso = normalizeToISO(s);
                if (fp && iso) {
                    fp.setDate(iso, true, 'Y-m-d');
                }
            };

            const isDetailsPage = document.getElementById('checklist-area-treinamento');
            safeSet('#modal-redirect_to', isDetailsPage ? 'detalhes' : 'dashboard', modal);

            // CRITICAL FIX: Always fetch fresh data from server first
            if (implId) {
                // Show loading state
                const modalBody = modal.querySelector('.modal-body');
                const originalContent = modalBody ? modalBody.innerHTML : '';
                if (modalBody) {
                    modalBody.style.opacity = '0.5';
                    modalBody.style.pointerEvents = 'none';
                }

                try {
                    // Cache-busting: add timestamp to force fresh data
                    const timestamp = new Date().getTime();
                    const response = await fetch(`/api/v1/implantacoes/${implId}?_t=${timestamp}`, {
                        headers: {
                            'Cache-Control': 'no-cache, no-store, must-revalidate',
                            'Pragma': 'no-cache'
                        }
                    });

                    if (!response.ok) {
                        throw new Error('Falha ao carregar implantação');
                    }

                    const j = await response.json();

                    if (!j || !j.ok || !j.data || !j.data.implantacao) {
                        throw new Error('Dados inválidos retornados');
                    }

                    const impl = j.data.implantacao;

                    // Additional safety check
                    if (typeof impl !== 'object' || impl === null) {
                        throw new Error('Objeto de implantação inválido');
                    }

                    // Populate ALL fields from server (definitive source of truth)
                    safeSet('#modal-responsavel_cliente', impl.responsavel_cliente || '', modal);
                    safeSet('#modal-cargo_responsavel', impl.cargo_responsavel || '', modal);
                    safeSet('#modal-telefone_responsavel', impl.telefone_responsavel || '', modal);
                    safeSet('#modal-email_responsavel', impl.email_responsavel || '', modal);
                    safeSet('#modal-id_favorecido', impl.id_favorecido || '', modal);
                    safeSet('#modal-chave_oamd', impl.chave_oamd || '', modal);
                    safeSet('#modal-tela_apoio_link', impl.tela_apoio_link || '', modal);
                    safeSet('#modal-valor_atribuido', (impl.valor_atribuido != null ? String(impl.valor_atribuido) : ''), modal);
                    // Formatar valor_monetario para exibição: 1000.00 -> R$ 1.000,00
                    if (impl.valor_monetario != null && impl.valor_monetario !== '') {
                        let val = parseFloat(impl.valor_monetario);
                        if (!isNaN(val)) {
                            let formatted = 'R$ ' + val.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                            safeSet('#modal-valor_monetario', formatted, modal);
                        } else {
                            safeSet('#modal-valor_monetario', impl.valor_monetario, modal);
                        }
                    } else {
                        safeSet('#modal-valor_monetario', '', modal);
                    }
                    safeSet('#modal-status_implantacao', impl.status_implantacao_oamd || '', modal);
                    safeSet('#modal-nivel_atendimento', impl.nivel_atendimento || '', modal);
                    safeSet('#modal-catraca', impl.catraca || '', modal);
                    safeSet('#modal-modelo_catraca', impl.modelo_catraca || '', modal);
                    safeSet('#modal-facial', impl.facial || '', modal);
                    safeSet('#modal-modelo_facial', impl.modelo_facial || '', modal);
                    safeSet('#modal-wellhub', impl.wellhub || '', modal);
                    safeSet('#modal-totalpass', impl.totalpass || '', modal);
                    safeSet('#modal-cnpj', impl.cnpj || '', modal);
                    safeSet('#modal-sistema_anterior', impl.sistema_anterior || '', modal);
                    safeSet('#modal-recorrencia_usa', impl.recorrencia_usa || '', modal);
                    safeSet('#modal-importacao', impl.importacao || '', modal);
                    safeSet('#modal-boleto', impl.boleto || '', modal);
                    safeSet('#modal-nota_fiscal', impl.nota_fiscal || '', modal);
                    safeSet('#modal-diaria', impl.diaria || '', modal);
                    safeSet('#modal-freepass', impl.freepass || '', modal);
                    safeSet('#modal-alunos_ativos', (impl.alunos_ativos != null ? String(impl.alunos_ativos) : ''), modal);
                    safeSet('#modal-informacao_infra', impl.informacao_infra || '', modal);
                    safeSet('#modal-resp_estrategico_nome', impl.resp_estrategico_nome || '', modal);
                    safeSet('#modal-resp_onb_nome', impl.resp_onb_nome || '', modal);
                    safeSet('#modal-contatos', impl.contatos || '', modal);
                    safeSet('#modal-resp_estrategico_obs', impl.resp_estrategico_obs || '', modal);

                    // Set dates
                    setFpDate(window.fpInicioEfetivo, impl.data_inicio_efetivo);
                    setFpDate(window.fpInicioProd, impl.data_inicio_producao);
                    setFpDate(window.fpFinalImpl, impl.data_final_implantacao);

                    // Data Cadastro
                    if (impl.data_criacao) {
                        const iso = impl.data_criacao;
                        const p = iso.split('T')[0].split('-');
                        if (p.length === 3) {
                            safeSet('#modal-data_cadastro', p[2].padStart(2, '0') + '/' + p[1].padStart(2, '0') + '/' + p[0], modal);
                        }
                    }

                    // CRITICAL: Initialize TomSelect ONLY AFTER data is loaded
                    initializeMultiTagInput('#modal-modalidades', impl.modalidades || '');
                    initializeMultiTagInput('#modal-horarios_func', impl.horarios_func || '');
                    initializeMultiTagInput('#modal-formas_pagamento', impl.formas_pagamento || '');
                    initializeMultiTagInput('#modal-seguimento', impl.seguimento || '');
                    initializeMultiTagInput('#modal-tipos_planos', impl.tipos_planos || '');

                    // Toggle dependent fields
                    const catracaSel = modal.querySelector('#modal-catraca');
                    const facialSel = modal.querySelector('#modal-facial');
                    const catracaRow = modal.querySelector('#row-catraca-modelo');
                    const facialRow = modal.querySelector('#row-facial-modelo');
                    const catracaModelo = modal.querySelector('#modal-modelo_catraca');
                    const facialModelo = modal.querySelector('#modal-modelo_facial');

                    const toggleModelo = (sel, row, input) => {
                        const isSim = (sel && (sel.value || '').trim().toLowerCase() === 'sim');
                        if (row) row.style.display = isSim ? '' : 'none';
                        if (input) {
                            input.required = !!isSim;
                            if (!isSim) {
                                input.removeAttribute('aria-invalid');
                            }
                        }
                    };

                    toggleModelo(catracaSel, catracaRow, catracaModelo);
                    toggleModelo(facialSel, facialRow, facialModelo);

                    // Format phone after setting value
                    if (window.formatarTelefone) {
                        formatarTelefone(modal.querySelector('#modal-telefone_responsavel'));
                    }

                    // Remove loading state
                    if (modalBody) {
                        modalBody.style.opacity = '1';
                        modalBody.style.pointerEvents = 'auto';
                    }

                    // CONSISTENCY CHECK: Capture server data
                    DataConsistencyChecker.captureServerData(impl);

                    // Wait for TomSelect to fully initialize (100ms should be enough)
                    await new Promise(resolve => setTimeout(resolve, 100));

                    // CONSISTENCY CHECK: Capture displayed data
                    DataConsistencyChecker.captureDisplayedData(modal);

                    // CONSISTENCY CHECK: Validate
                    DataConsistencyChecker.validate();

                    // CRITICAL: Save snapshot ONLY AFTER data is fully loaded
                    if (window.__modalDetalhesInitDone) {
                        window.__modalDetalhesInitDone();
                    }

                } catch (error) {
                    console.error('Error loading implantacao data:', error);

                    // Remove loading state on error
                    if (modalBody) {
                        modalBody.style.opacity = '1';
                        modalBody.style.pointerEvents = 'auto';
                    }

                    // Fallback: try to populate from data-attributes
                    safeSet('#modal-responsavel_cliente', getData('responsavel'), modal);
                    safeSet('#modal-cargo_responsavel', getData('cargo'), modal);
                    safeSet('#modal-telefone_responsavel', getData('telefone'), modal);
                    safeSet('#modal-email_responsavel', getData('email'), modal);
                    safeSet('#modal-id_favorecido', getData('id-favorecido'), modal);
                    safeSet('#modal-chave_oamd', getData('chave-oamd'), modal);
                    safeSet('#modal-tela_apoio_link', getData('tela-apoio-link'), modal);
                    safeSet('#modal-nivel_receita', getData('nivel-receita'), modal);

                    initializeMultiTagInput('#modal-modalidades', getData('modalidades'));
                    initializeMultiTagInput('#modal-horarios_func', getData('horarios-func'));
                    initializeMultiTagInput('#modal-formas_pagamento', getData('formas-pagamento'));
                    initializeMultiTagInput('#modal-seguimento', getData('seguimento'));
                    initializeMultiTagInput('#modal-tipos_planos', getData('tipos-planos'));

                    safeSet('#modal-diaria', getData('diaria', 'Não definido'), modal);
                    safeSet('#modal-freepass', getData('freepass', 'Não definido'), modal);
                    safeSet('#modal-alunos_ativos', getData('alunos-ativos', '0'), modal);
                    safeSet('#modal-sistema_anterior', getData('sistema-anterior'), modal);
                    safeSet('#modal-recorrencia_usa', getData('recorrencia-usa'), modal);
                    safeSet('#modal-importacao', getData('importacao', 'Não definido'), modal);
                    safeSet('#modal-boleto', getData('boleto', 'Não definido'), modal);
                    safeSet('#modal-nota_fiscal', getData('nota-fiscal', 'Não definido'), modal);
                    safeSet('#modal-catraca', getData('catraca', 'Não preenchido'), modal);
                    safeSet('#modal-facial', getData('facial', 'Não preenchido'), modal);
                    safeSet('#modal-modelo_catraca', getData('modelo-catraca'), modal);
                    safeSet('#modal-modelo_facial', getData('modelo-facial'), modal);

                    if (window.formatarTelefone) {
                        formatarTelefone(modal.querySelector('#modal-telefone_responsavel'));
                    }

                    if (window.__modalDetalhesInitDone) {
                        window.__modalDetalhesInitDone();
                    }
                }
            } else {
                // No implId, just initialize empty
                if (window.__modalDetalhesInitDone) {
                    window.__modalDetalhesInitDone();
                }
            }
        });

        // Cleanup TomSelect somente após o modal ser realmente ocultado

        // Form Change Detection & Validation Logic
        (function () {
            let formInitialValues = {};
            let formHasChanges = false;
            let isClosingAfterConfirm = false;
            let justSaved = false;
            let initializing = false;
            const modalForm = modalDetalhesEmpresa.querySelector('form');

            if (!modalForm) return;

            function saveFormInitialValues() {
                formInitialValues = {};
                const inputs = modalForm.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        formInitialValues[input.name || input.id] = input.checked;
                    } else if (input.tagName === 'SELECT' && input.multiple) {
                        const vals = Array.from(input.selectedOptions).map(o => String(o.value).trim()).filter(Boolean);
                        formInitialValues[input.name || input.id] = vals.join(',');
                    } else {
                        formInitialValues[input.name || input.id] = input.value;
                    }
                });
                formHasChanges = false;
                window.__saveFormSnapshot = saveFormInitialValues;
            }

            function checkFormChanges() {
                formHasChanges = false;
                const inputs = modalForm.querySelectorAll('input, select, textarea');
                for (let input of inputs) {
                    const key = input.name || input.id;
                    if (key === 'redirect_to' || key === 'modal-redirect_to' || key === 'csrf_token') {
                        continue;
                    }
                    let currentValue;
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        currentValue = input.checked;
                    } else if (input.tagName === 'SELECT' && input.multiple) {
                        const vals = Array.from(input.selectedOptions).map(o => String(o.value).trim()).filter(Boolean);
                        currentValue = vals.join(',');
                    } else {
                        currentValue = input.value;
                    }
                    if (formInitialValues[key] !== currentValue) {
                        formHasChanges = true;
                        break;
                    }
                }
                return formHasChanges;
            }

            function validateFormFields() {
                const emailInput = modalForm.querySelector('#modal-email_responsavel');
                if (emailInput && emailInput.value && emailInput.value.trim() !== '') {
                    const emailValue = emailInput.value.trim();
                    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
                    if (!emailRegex.test(emailValue)) {
                        return {
                            valid: false,
                            field: emailInput,
                            message: 'O campo "E-mail Resp." contém um valor inválido. Digite um email válido (exemplo: nome@dominio.com)'
                        };
                    }
                }

                if (!modalForm.checkValidity()) {
                    const firstInvalid = modalForm.querySelector(':invalid');
                    if (firstInvalid) {
                        return {
                            valid: false,
                            field: firstInvalid,
                            message: 'Há campos com valores inválidos. Corrija os erros antes de continuar.'
                        };
                    }
                }

                return {
                    valid: true
                };
            }

            function processarDatas() {
                const toIso = (br) => {
                    if (!br || typeof br !== 'string') return '';
                    // Se já estiver em formato ISO YYYY-MM-DD, retorna como está
                    if (/^\d{4}-\d{2}-\d{2}$/.test(br)) return br;

                    const m = br.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
                    if (!m) return br;
                    const dd = m[1],
                        mm = m[2],
                        yyyy = m[3];
                    return `${yyyy}-${mm}-${dd}`;
                };

                const inicioEfetivo = modalForm.querySelector('#modal-inicio_efetivo') || modalForm.querySelector('[name="data_inicio_efetivo"]');
                const dataInicioProd = modalForm.querySelector('#modal-data_inicio_producao') || modalForm.querySelector('[name="data_inicio_producao"]');
                const dataFinalImpl = modalForm.querySelector('#modal-data_final_implantacao') || modalForm.querySelector('[name="data_final_implantacao"]');

                if (inicioEfetivo && inicioEfetivo.value) inicioEfetivo.value = toIso(inicioEfetivo.value);
                if (dataInicioProd && dataInicioProd.value) dataInicioProd.value = toIso(dataInicioProd.value);
                if (dataFinalImpl && dataFinalImpl.value) dataFinalImpl.value = toIso(dataFinalImpl.value);
            }
            console.log('🔧 Criando window.__submitModalFormDetalhes...');
            // CRITICAL FIX: Make this accessible to click handler outside this scope
            window.__submitModalFormDetalhes = async () => {
                console.log('🚀 [DEBUG] __submitModalFormDetalhes CHAMADA!');
                console.log('🚀 [DEBUG] modalForm:', modalForm);

                const validation = validateFormFields();
                console.log('🚀 [DEBUG] Validation result:', validation);

                if (!validation.valid) {
                    console.error('❌ [DEBUG] Validação falhou:', validation.message);
                    if (validation.field) {
                        validation.field.focus();
                        validation.field.reportValidity();
                    }
                    if (window.showToast) {
                        showToast(validation.message, 'error');
                    }
                    return false;
                }

                console.log('✅ [DEBUG] Validação OK, processando datas...');
                processarDatas();

                // CRITICAL FIX: Remove readonly from all fields before submission
                // Readonly fields are NOT submitted in FormData
                const readonlyFields = modalForm.querySelectorAll('[readonly]');
                const readonlyFieldsList = Array.from(readonlyFields);
                console.log('🚀 [DEBUG] Readonly fields encontrados:', readonlyFieldsList.length);
                readonlyFieldsList.forEach(field => {
                    field.removeAttribute('readonly');
                    field.dataset._wasReadonly = 'true';
                });

                try {
                    const redir = modalForm.querySelector('#modal-redirect_to');
                    if (redir) redir.value = 'modal';
                } catch (_) { }
                const actionUrl = modalForm.getAttribute('action') || (typeof modalForm.action === 'string' ? modalForm.action : '/actions/atualizar_detalhes_empresa');
                const formData = new FormData(modalForm);

                // Restore readonly attribute after FormData creation
                readonlyFieldsList.forEach(field => {
                    if (field.dataset._wasReadonly === 'true') {
                        field.setAttribute('readonly', 'readonly');
                        delete field.dataset._wasReadonly;
                    }
                });

                const saveBtn = document.querySelector('#modalDetalhesEmpresa .btn-salvar-detalhes');

                // Save original state
                if (saveBtn) {
                    saveBtn.disabled = true;
                    saveBtn.dataset._originalText = saveBtn.innerHTML;
                    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvando...';
                }

                try {
                    const res = await fetch(actionUrl, {
                        method: 'POST',
                        headers: { 'Accept': 'application/json' },
                        body: formData,
                        credentials: 'same-origin'
                    });

                    let ok = res.ok;
                    let j = null;
                    try { j = await res.json(); ok = ok && j && j.ok; } catch (_) { }

                    if (ok) {
                        formHasChanges = false;
                        justSaved = true;
                        saveFormInitialValues();

                        // Show success state
                        if (saveBtn) {
                            saveBtn.innerHTML = '<i class="bi bi-check-circle me-2"></i>✅ Salvo com sucesso!';
                            saveBtn.classList.remove('btn-primary');
                            saveBtn.classList.add('btn-success');
                        }

                        if (window.showToast) showToast('✅ Detalhes salvos com sucesso!', 'success');

                        const ts = document.getElementById('oamd-last-update');
                        const tspan = document.getElementById('oamd-last-update-time');
                        if (ts && tspan) {
                            const now = new Date();
                            tspan.innerText = `${now.toLocaleDateString()} ${now.toLocaleTimeString()}`;
                            ts.style.display = '';
                        }

                        try { if (typeof window.reloadTimeline === 'function') window.reloadTimeline(); } catch (_) { }

                        try {
                            if (lastTriggerEl) {
                                const getVal = (sel) => {
                                    const el = modalForm.querySelector(sel);
                                    return el ? (el.value || '') : '';
                                };
                                lastTriggerEl.setAttribute('data-responsavel', getVal('#modal-responsavel_cliente'));
                                lastTriggerEl.setAttribute('data-cargo', getVal('#modal-cargo_responsavel'));
                                lastTriggerEl.setAttribute('data-telefone', getVal('#modal-telefone_responsavel'));
                                lastTriggerEl.setAttribute('data-email', getVal('#modal-email_responsavel'));
                                lastTriggerEl.setAttribute('data-id-favorecido', getVal('#modal-id_favorecido'));
                                lastTriggerEl.setAttribute('data-chave-oamd', getVal('#modal-chave_oamd'));
                                lastTriggerEl.setAttribute('data-tela-apoio-link', getVal('#modal-tela_apoio_link'));
                                lastTriggerEl.setAttribute('data-nivel-receita', getVal('#modal-nivel_receita'));
                                lastTriggerEl.setAttribute('data-modalidades', getVal('#modal-modalidades'));
                                lastTriggerEl.setAttribute('data-horarios-func', getVal('#modal-horarios_func'));
                                lastTriggerEl.setAttribute('data-formas-pagamento', getVal('#modal-formas_pagamento'));
                                lastTriggerEl.setAttribute('data-seguimento', getVal('#modal-seguimento'));
                                lastTriggerEl.setAttribute('data-tipos-planos', getVal('#modal-tipos_planos'));
                                lastTriggerEl.setAttribute('data-diaria', getVal('#modal-diaria'));
                                lastTriggerEl.setAttribute('data-freepass', getVal('#modal-freepass'));
                                lastTriggerEl.setAttribute('data-alunos-ativos', getVal('#modal-alunos_ativos'));
                                lastTriggerEl.setAttribute('data-sistema-anterior', getVal('#modal-sistema_anterior'));
                                lastTriggerEl.setAttribute('data-recorrencia-usa', getVal('#modal-recorrencia_usa'));
                                lastTriggerEl.setAttribute('data-importacao', getVal('#modal-importacao'));
                                lastTriggerEl.setAttribute('data-boleto', getVal('#modal-boleto'));
                                lastTriggerEl.setAttribute('data-nota-fiscal', getVal('#modal-nota_fiscal'));
                                lastTriggerEl.setAttribute('data-catraca', getVal('#modal-catraca'));
                                lastTriggerEl.setAttribute('data-facial', getVal('#modal-facial'));
                                lastTriggerEl.setAttribute('data-modelo-catraca', getVal('#modal-modelo_catraca'));
                                lastTriggerEl.setAttribute('data-modelo-facial', getVal('#modal-modelo_facial'));
                                lastTriggerEl.setAttribute('data-valor-atribuido', getVal('#modal-valor_atribuido'));
                                lastTriggerEl.setAttribute('data-resp-estrategico-nome', getVal('#modal-resp_estrategico_nome'));
                                lastTriggerEl.setAttribute('data-resp-onb-nome', getVal('#modal-resp_onb_nome'));
                                lastTriggerEl.setAttribute('data-contatos', getVal('#modal-contatos'));
                                lastTriggerEl.setAttribute('data-resp-estrategico-obs', getVal('#modal-resp_estrategico-obs'));
                                lastTriggerEl.setAttribute('data-inicio-efetivo-iso', getVal('#modal-inicio_efetivo'));
                                lastTriggerEl.setAttribute('data-inicio-producao', getVal('#modal-data_inicio_producao'));
                                lastTriggerEl.setAttribute('data-final-implantacao', getVal('#modal-data_final_implantacao'));
                            }
                        } catch (_) { }

                        // Auto-close modal after 1.5 seconds
                        setTimeout(() => {
                            const modal = bootstrap.Modal.getInstance(document.getElementById('modalDetalhesEmpresa'));
                            if (modal) modal.hide();
                        }, 1500);

                    } else {
                        // Show specific error message
                        const errorMsg = (j && j.error) || 'Erro ao salvar detalhes';
                        if (window.showToast) showToast(`❌ ${errorMsg}`, 'error');

                        // Show error state on button
                        if (saveBtn) {
                            saveBtn.innerHTML = '<i class="bi bi-x-circle me-2"></i>❌ Erro ao salvar';
                            saveBtn.classList.remove('btn-primary');
                            saveBtn.classList.add('btn-danger');
                        }
                    }
                } catch (error) {
                    console.error('Save error:', error);
                    if (window.showToast) showToast('❌ Erro de conexão. Verifique sua internet e tente novamente.', 'error');

                    // Show error state on button
                    if (saveBtn) {
                        saveBtn.innerHTML = '<i class="bi bi-x-circle me-2"></i>❌ Erro de conexão';
                        saveBtn.classList.remove('btn-primary');
                        saveBtn.classList.add('btn-danger');
                    }
                } finally {
                    // Reset button after 2 seconds
                    if (saveBtn) {
                        setTimeout(() => {
                            saveBtn.disabled = false;
                            saveBtn.innerHTML = saveBtn.dataset._originalText || 'Salvar Alterações';
                            saveBtn.classList.remove('btn-success', 'btn-danger');
                            saveBtn.classList.add('btn-primary');
                            delete saveBtn.dataset._originalText;
                        }, 2000);
                    }
                }
            };

            modalForm.addEventListener('submit', function (e) {
                if (isClosingAfterConfirm) {
                    e.preventDefault();
                    return false;
                }
                e.preventDefault();
                if (window.__submitModalFormDetalhes) {
                    window.__submitModalFormDetalhes();
                }
            });

            modalDetalhesEmpresa.addEventListener('show.bs.modal', function () {
                isClosingAfterConfirm = false;
                justSaved = false;
                initializing = true;
                const finishInit = () => { saveFormInitialValues(); initializing = false; };
                window.__modalDetalhesInitDone = finishInit;
                setTimeout(finishInit, 500);
            });

            modalDetalhesEmpresa.addEventListener('hide.bs.modal', async function (e) {
                if (isClosingAfterConfirm) {
                    return;
                }
                if (justSaved) {
                    justSaved = false;
                    return;
                }

                checkFormChanges();

                if (formHasChanges) {
                    e.preventDefault();

                    const validation = validateFormFields();

                    if (!validation.valid) {
                        if (validation.field) {
                            validation.field.focus();
                            validation.field.reportValidity();
                        }

                        if (window.showToast) {
                            showToast(validation.message, 'error');
                        } else {
                            alert(validation.message);
                        }

                        const bsModal = bootstrap.Modal.getInstance(modalDetalhesEmpresa);
                        if (bsModal) {
                            bsModal.show();
                        }
                        return;
                    }

                    let confirmed = false;
                    if (window.showConfirm) {
                        confirmed = await showConfirm({
                            title: 'Descartar Alterações?',
                            message: 'Você fez alterações no formulário. Deseja descartar as alterações e fechar o modal?',
                            confirmText: 'Descartar',
                            cancelText: 'Cancelar',
                            type: 'warning',
                            icon: 'bi-exclamation-triangle-fill'
                        });
                    } else {
                        confirmed = confirm('Você fez alterações no formulário. Deseja descartar as alterações e fechar o modal?');
                    }

                    if (!confirmed) {
                        e.preventDefault();
                        const bsModal = bootstrap.Modal.getInstance(modalDetalhesEmpresa);
                        if (bsModal) {
                            bsModal.show();
                        }
                        return;
                    }

                    isClosingAfterConfirm = true;
                    formHasChanges = false;

                    const bsModal = bootstrap.Modal.getInstance(modalDetalhesEmpresa);
                    if (bsModal) {
                        bsModal.hide();
                    }
                }
            });

            modalDetalhesEmpresa.addEventListener('hidden.bs.modal', function () {
                if (isClosingAfterConfirm) {
                    const inputs = modalForm.querySelectorAll('input, select, textarea');
                    inputs.forEach(input => {
                        const key = input.name || input.id;
                        if (formInitialValues.hasOwnProperty(key)) {
                            if (input.type === 'checkbox' || input.type === 'radio') {
                                input.checked = formInitialValues[key] || false;
                            } else {
                                input.value = formInitialValues[key] || '';
                            }
                        }
                    });
                }

                formHasChanges = false;
                isClosingAfterConfirm = false;
                formInitialValues = {};

                // destruir instâncias TomSelect somente agora
                for (const selector in tomSelectInstances) {
                    if (tomSelectInstances[selector]) {
                        try { tomSelectInstances[selector].destroy(); } catch (_) { }
                    }
                }
                tomSelectInstances = {};
            });

            modalForm.addEventListener('input', function () {
                if (!initializing) checkFormChanges();
            });

            modalForm.addEventListener('change', function () {
                if (!initializing) checkFormChanges();
                // react to catraca/facial selection changes
                const modal = document.getElementById('modalDetalhesEmpresa');
                if (modal) {
                    const catracaSel = modal.querySelector('#modal-catraca');
                    const facialSel = modal.querySelector('#modal-facial');
                    const catracaRow = modal.querySelector('#row-catraca-modelo');
                    const facialRow = modal.querySelector('#row-facial-modelo');
                    const catracaModelo = modal.querySelector('#modal-modelo_catraca');
                    const facialModelo = modal.querySelector('#modal-modelo_facial');
                    const toggleModelo = (sel, row, input) => {
                        const isSim = (sel && (sel.value || '').trim().toLowerCase() === 'sim');
                        if (row) row.style.display = isSim ? '' : 'none';
                        if (input) input.required = !!isSim;
                    };
                    toggleModelo(catracaSel, catracaRow, catracaModelo);
                    toggleModelo(facialSel, facialRow, facialModelo);
                }
            });

            document.addEventListener('click', function (e) {
                const submitBtn = e.target.closest('#modalDetalhesEmpresa .btn-salvar-detalhes');
                console.log('🖱️ [DEBUG] Click detectado. submitBtn:', submitBtn);

                if (submitBtn && modalForm) {
                    console.log('✅ [DEBUG] Botão Salvar clicado! Chamando __submitModalFormDetalhes...');
                    e.preventDefault();
                    e.stopPropagation();
                    // Call the globally accessible function
                    if (window.__submitModalFormDetalhes) {
                        console.log('✅ [DEBUG] window.__submitModalFormDetalhes existe, chamando...');
                        window.__submitModalFormDetalhes();
                    } else {
                        console.error('❌ [DEBUG] window.__submitModalFormDetalhes NÃO EXISTE!');
                    }
                } else {
                    if (!submitBtn) console.log('ℹ️ [DEBUG] Não é o botão salvar');
                }
            });

            document.addEventListener('click', async function (e) {
                const consultarBtn = e.target.closest('#btn-consultar-oamd');
                if (!consultarBtn) return;

                // Pegar ID da implantação
                const implIdEl = modalForm.querySelector('#modal-implantacao_id');
                let implId = implIdEl && implIdEl.value ? implIdEl.value : '';
                if (!implId) {
                    const mc = document.getElementById('main-content');
                    if (mc && mc.dataset && mc.dataset.implantacaoId) implId = mc.dataset.implantacaoId;
                }
                if (!implId) {
                    const m = (location.pathname || '').match(/\/implantacao\/(\d+)/);
                    if (m && m[1]) implId = m[1];
                }

                // NOVO: Pegar ID Favorecido do modal
                const idFavorecidoEl = modalForm.querySelector('#modal-id_favorecido');
                const idFavorecido = idFavorecidoEl && idFavorecidoEl.value ? idFavorecidoEl.value.trim() : '';

                // Se não temos nem implId nem idFavorecido, não podemos consultar
                if (!implId && !idFavorecido) {
                    if (window.showToast) showToast('Informe o ID Favorecido para consultar', 'warning');
                    return;
                }

                // Construir URL com fallback
                let url = `/api/v1/oamd/implantacoes/${implId || 0}/consulta`;
                if (idFavorecido) {
                    url += `?id_favorecido=${encodeURIComponent(idFavorecido)}`;
                }

                const loader = document.getElementById('btn-consultar-oamd-loader');
                const icon = document.getElementById('btn-consultar-oamd-icon');
                if (loader) loader.classList.remove('d-none');
                if (icon) icon.classList.add('d-none');
                consultarBtn.disabled = true;
                try {
                    // Use fetchWithRetry for automatic retry on failures
                    const res = await fetchWithRetry(
                        url,
                        { headers: { 'Accept': 'application/json' } },
                        3,  // 3 retries
                        15000  // 15s timeout per attempt
                    );
                    const j = await res.json();
                    if (!res.ok || !j.ok || !j.data || !j.data.found) throw new Error(j.error || 'Falha na consulta');
                    const d = j.data;
                    window.__oamdApplying = true;
                    const setIfEmpty = (sel, val) => {
                        const el = modalForm.querySelector(sel);
                        if (!el) return;
                        const cur = (el.value || '').trim();
                        if (!cur && val != null && String(val).trim() !== '') {
                            el.value = String(val).trim();
                        }
                    };
                    const toBr = (iso) => {
                        if (!iso) return '';
                        const m = String(iso).trim().match(/^([0-9]{4})-([0-9]{2})-([0-9]{2})$/);
                        return m ? `${m[3]}/${m[2]}/${m[1]}` : '';
                    };
                    setIfEmpty('#modal-id_favorecido', d.persistibles.id_favorecido);
                    setIfEmpty('#modal-chave_oamd', d.persistibles.chave_oamd);
                    setIfEmpty('#modal-cnpj', d.persistibles.cnpj);
                    setIfEmpty('#modal-status_implantacao', d.persistibles.status_implantacao);
                    setIfEmpty('#modal-nivel_atendimento', d.persistibles.nivel_atendimento);
                    const dc = toBr(d.persistibles.data_cadastro);
                    if (dc) setIfEmpty('#modal-data_cadastro', dc);
                    const setFp = (fp, isoSel, inputSel) => {
                        const iso = d.persistibles[isoSel];
                        if (fp && typeof fp.setDate === 'function' && iso) fp.setDate(iso, true, 'Y-m-d');
                        else if (iso) {
                            const el = modalForm.querySelector(inputSel);
                            if (el) el.value = toBr(iso);
                        }
                    };
                    setFp(window.fpInicioEfetivo, 'data_inicio_efetivo', '#modal-inicio_efetivo');
                    setFp(window.fpFinalImpl, 'data_final_implantacao', '#modal-data_final_implantacao');
                    setFp(window.fpInicioProd, 'data_inicio_producao', '#modal-data_inicio_producao');
                    const forceSet = (sel, val) => {
                        const el = modalForm.querySelector(sel);
                        if (!el) return;
                        el.value = (val == null) ? '' : String(val).trim();
                    };
                    forceSet('#modal-informacao_infra', d.derived.informacao_infra);
                    let link = d.derived.tela_apoio_link;
                    if ((!link || !link.trim()) && d.derived.informacao_infra) {
                        const digits = String(d.derived.informacao_infra).match(/(\d+)/);
                        if (digits && digits[1]) link = `http://zw${digits[1]}.pactosolucoes.com.br/app`;
                    }
                    forceSet('#modal-tela_apoio_link', link);
                    if (typeof window.__saveFormSnapshot === 'function') window.__saveFormSnapshot();
                    const ts = document.getElementById('oamd-last-update');
                    const tspan = document.getElementById('oamd-last-update-time');
                    if (ts && tspan) {
                        const now = new Date();
                        tspan.innerText = `${now.toLocaleDateString()} ${now.toLocaleTimeString()}`;
                        ts.style.display = '';
                    }
                    try {
                        // Só tentar aplicar se a implantação existir no banco
                        if (implId && implId !== '0' && parseInt(implId) > 0) {
                            const csrfEl = modalForm.querySelector('input[name="csrf_token"]');
                            const csrf = csrfEl ? csrfEl.value : '';
                            await fetch(`/api/v1/oamd/implantacoes/${implId}/aplicar`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                                body: JSON.stringify({})
                            }).then(r => r.json()).then(ap => {
                                if (ap && ap.ok) {
                                    if (window.showToast) showToast('Dados do OAMD aplicados', 'success');
                                } else {
                                    if (window.showToast) showToast((ap && ap.error) || 'Falha ao aplicar dados', 'error');
                                }
                            }).catch(() => { });
                        } else {
                            // Implantação não existe ainda, apenas mostrar sucesso da consulta
                            if (window.showToast) showToast('Dados consultados com sucesso. Salve os detalhes para persistir.', 'success');
                        }
                    } catch (_) { }
                } catch (err) {
                    if (window.showToast) showToast(err.message || 'Erro na consulta', 'error');
                } finally {
                    window.__oamdApplying = false;
                    consultarBtn.disabled = false;
                    if (loader) loader.classList.add('d-none');
                    if (icon) icon.classList.remove('d-none');
                }
            });

        })();

        // Init Calendars
        (function initModalCalendars() {
            if (!window.flatpickr) return;
            var makeConfig = function () {
                return {
                    dateFormat: 'Y-m-d',
                    altInput: true,
                    altFormat: 'd/m/Y',
                    allowInput: false,
                    locale: flatpickr.l10ns.default || flatpickr.l10ns.pt,
                    parseDate: function (datestr) {
                        var m = datestr && datestr.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
                        if (!m) return null;
                        var d = parseInt(m[1], 10);
                        var mo = parseInt(m[2], 10) - 1;
                        var y = parseInt(m[3], 10);
                        var dd = new Date(y, mo, d);
                        if (dd.getDate() !== d || dd.getMonth() !== mo || dd.getFullYear() !== y) return null;
                        return dd;
                    }
                };
            };
            var ensureInstance = function (selector) {
                var el = document.querySelector(selector);
                if (!el) return null;
                if (el._flatpickr) return el._flatpickr;
                return window.flatpickr(el, makeConfig());
            };

            window.fpInicioEfetivo = ensureInstance('#modal-inicio_efetivo');
            window.fpInicioProd = ensureInstance('#modal-data_inicio_producao');
            window.fpFinalImpl = ensureInstance('#modal-data_final_implantacao');
        })();

        // Controlar botão "Abrir Tela de Apoio"
        (function initTelaApoioButton() {
            const inputTelaApoio = document.querySelector('#modal-tela_apoio_link');
            const btnAbrirTelaApoio = document.querySelector('#btn-abrir-tela-apoio');

            if (!inputTelaApoio || !btnAbrirTelaApoio) return;

            const updateButton = function () {
                const url = (inputTelaApoio.value || '').trim();
                if (url && url.startsWith('http')) {
                    btnAbrirTelaApoio.href = url;
                    btnAbrirTelaApoio.style.display = '';
                } else {
                    btnAbrirTelaApoio.href = '#';
                    btnAbrirTelaApoio.style.display = 'none';
                }
            };

            inputTelaApoio.addEventListener('input', updateButton);
            inputTelaApoio.addEventListener('change', updateButton);
            updateButton(); // Inicializar
        })();
    });

})();
