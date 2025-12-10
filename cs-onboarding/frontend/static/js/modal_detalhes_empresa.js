/**
 * Modal Detalhes da Empresa Logic
 * Extracted from base.html for better maintainability.
 */

(function() {
    'use strict';

    let tomSelectInstances = {};

    // Initialize TomSelect for multi-select fields
    const initializeMultiTagInput = (selector, dataValue) => {
        const modalDetalhesEmpresa = document.getElementById('modalDetalhesEmpresa');
        if (!modalDetalhesEmpresa) return;

        const selectElement = modalDetalhesEmpresa.querySelector(selector);
        if (!selectElement) return;

        if (tomSelectInstances[selector]) {
            tomSelectInstances[selector].destroy();
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
            onInitialize: function() {
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
            tomSelectInstances[selector].destroy();
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
    document.addEventListener('DOMContentLoaded', function() {
        const modalDetalhesEmpresa = document.getElementById('modalDetalhesEmpresa');
        if (!modalDetalhesEmpresa) return;

        // Phone input event listeners (replacing inline handlers)
        const telefoneInput = modalDetalhesEmpresa.querySelector('#modal-telefone_responsavel');
        if (telefoneInput) {
            telefoneInput.addEventListener('input', function() {
                if (window.formatarTelefone) window.formatarTelefone(this);
            });
            telefoneInput.addEventListener('blur', function() {
                if (window.validarTelefoneCompleto) window.validarTelefoneCompleto(this);
            });
        }

        // Modal Show Event
        modalDetalhesEmpresa.addEventListener('show.bs.modal', function(event) {
            const safeSet = function(selOrEl, value, root) {
                const el = typeof selOrEl === 'string' ? (root || document).querySelector(selOrEl) : selOrEl;
                if (!el) return;
                try {
                    // Handle checkbox/radio
                    if (el.type === 'checkbox' || el.type === 'radio') {
                        // Logic for checkbox/radio if needed, currently safeSet seems used for values
                    }
                    el.value = value;
                } catch (_) {}
            };

            const button = event.relatedTarget;
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

            // Populate fields
            safeSet('#modal-implantacao_id', implId, modal);
            safeSet('#modal-responsavel_cliente', getData('responsavel'), modal);
            safeSet('#modal-cargo_responsavel', getData('cargo'), modal);
            safeSet('#modal-telefone_responsavel', getData('telefone'), modal);
            safeSet('#modal-email_responsavel', getData('email'), modal);
            
            const inicioProducaoIsoAttr = getData('inicio-producao');
            const finalImplantacaoIsoAttr = getData('final-implantacao');
            
            safeSet('#modal-id_favorecido', getData('id-favorecido'), modal);
            safeSet('#modal-chave_oamd', getData('chave-oamd'), modal);
            safeSet('#modal-tela_apoio_link', getData('tela-apoio-link'), modal);
            safeSet('#modal-nivel_receita', getData('nivel-receita'), modal);

            // Initialize TomSelects
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
            safeSet('#modal-valor_atribuido', getData('valor-atribuido', '0.00'), modal);
            safeSet('#modal-resp_estrategico_nome', getData('resp-estrategico-nome'), modal);
            safeSet('#modal-resp_onb_nome', getData('resp-onb-nome'), modal);
            safeSet('#modal-contatos', getData('contatos'), modal);
            safeSet('#modal-resp_estrategico_obs', getData('resp-estrategico-obs'), modal);

            // Date Handling
            const inicioEfetivoIsoAttr = getData('inicio-efetivo-iso');

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

            // Set dates in Flatpickr instances (global variables from initModalCalendars)
            setFpDate(window.fpInicioEfetivo, inicioEfetivoIsoAttr);
            setFpDate(window.fpInicioProd, inicioProducaoIsoAttr);
            setFpDate(window.fpFinalImpl, finalImplantacaoIsoAttr);

            // Fallback if data attributes are missing but inputs have values
            if (!inicioEfetivoIsoAttr) {
                const v = (modal.querySelector('#modal-inicio_efetivo') || {}).value || '';
                if (v) setFpDate(window.fpInicioEfetivo, v);
            }
            if (!inicioProducaoIsoAttr) {
                const v = (modal.querySelector('#modal-data_inicio_producao') || {}).value || '';
                if (v) setFpDate(window.fpInicioProd, v);
            }
            if (!finalImplantacaoIsoAttr) {
                const v = (modal.querySelector('#modal-data_final_implantacao') || {}).value || '';
                if (v) setFpDate(window.fpFinalImpl, v);
            }

            // Data Cadastro
            const inicioImplantacaoIso = getData('inicio-implantacao');
            safeSet('#modal-data_cadastro', (function(iso) {
                if (!iso) return '';
                var p = iso.split('T')[0].split('-');
                if (p.length !== 3) return '';
                return p[2].padStart(2, '0') + '/' + p[1].padStart(2, '0') + '/' + p[0];
            })(inicioImplantacaoIso), modal);

            // Fetch detailed data if ID exists
            if (implId) {
                fetch(`/api/v1/implantacoes/${implId}`)
                    .then(r => r.ok ? r.json() : Promise.reject(new Error('Falha ao carregar implantação')))
                    .then(j => {
                        if (!j || !j.ok || !j.data || !j.data.implantacao) return;
                        const impl = j.data.implantacao;
                        setFpDate(window.fpInicioEfetivo, impl.data_inicio_efetivo);
                        setFpDate(window.fpInicioProd, impl.data_inicio_producao);
                        setFpDate(window.fpFinalImpl, impl.data_final_implantacao);
                    })
                    .catch(() => {});
            }

            // Format phone and set redirect
            if (window.formatarTelefone) {
                formatarTelefone(modal.querySelector('#modal-telefone_responsavel'));
            }
            
            const isDetailsPage = document.getElementById('checklist-area-treinamento');
            safeSet('#modal-redirect_to', isDetailsPage ? 'detalhes' : 'dashboard', modal);

            // Show/Hide modelo fields based on selections
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
                        // keep value but not required; backend não persiste se não for "Sim"
                        input.removeAttribute('aria-invalid');
                    }
                }
            };

            toggleModelo(catracaSel, catracaRow, catracaModelo);
            toggleModelo(facialSel, facialRow, facialModelo);

            if (window.__modalDetalhesInitDone) {
                window.__modalDetalhesInitDone();
            }
        });

        // Cleanup TomSelect somente após o modal ser realmente ocultado

        // Form Change Detection & Validation Logic
        (function() {
            let formInitialValues = {};
            let formHasChanges = false;
            let isClosingAfterConfirm = false;
            let initializing = false;
            const modalForm = modalDetalhesEmpresa.querySelector('form');

            if (!modalForm) return;

            function saveFormInitialValues() {
                formInitialValues = {};
                const inputs = modalForm.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        formInitialValues[input.name || input.id] = input.checked;
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
                    let currentValue;
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        currentValue = input.checked;
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

            if (window.fpInicioEfetivo && window.fpInicioEfetivo._input && typeof window.fpInicioEfetivo.setDate === 'function') {
                    const v = window.fpInicioEfetivo._input.value;
                    if (v) {
                        const iso = toIso(v);
                        if (iso) {
                            window.fpInicioEfetivo.setDate(iso, true, 'Y-m-d');
                        }
                    }
                }
            if (window.fpInicioProd && window.fpInicioProd._input && typeof window.fpInicioProd.setDate === 'function') {
                    const v = window.fpInicioProd._input.value;
                    if (v) {
                        const iso = toIso(v);
                        if (iso) {
                            window.fpInicioProd.setDate(iso, true, 'Y-m-d');
                        }
                    }
                }
            if (window.fpFinalImpl && window.fpFinalImpl._input && typeof window.fpFinalImpl.setDate === 'function') {
                    const v = window.fpFinalImpl._input.value;
                    if (v) {
                        const iso = toIso(v);
                        if (iso) {
                            window.fpFinalImpl.setDate(iso, true, 'Y-m-d');
                        }
                    }
                }
            }

            modalForm.addEventListener('submit', function(e) {
                if (isClosingAfterConfirm) {
                    e.preventDefault();
                    return false;
                }
                processarDatas();
            });

            modalDetalhesEmpresa.addEventListener('show.bs.modal', function() {
                isClosingAfterConfirm = false;
                initializing = true;
                const finishInit = () => { saveFormInitialValues(); initializing = false; };
                window.__modalDetalhesInitDone = finishInit;
                setTimeout(finishInit, 500);
            });

            modalDetalhesEmpresa.addEventListener('hide.bs.modal', async function(e) {
                if (isClosingAfterConfirm) {
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

            modalDetalhesEmpresa.addEventListener('hidden.bs.modal', function() {
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
                        try { tomSelectInstances[selector].destroy(); } catch(_) {}
                    }
                }
                tomSelectInstances = {};
            });

            modalForm.addEventListener('input', function() {
                if (!initializing) checkFormChanges();
            });

            modalForm.addEventListener('change', function() {
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

            document.addEventListener('click', function(e) {
                const submitBtn = e.target.closest('#modalDetalhesEmpresa .btn-salvar-detalhes');
                if (submitBtn && modalForm) {
                    e.preventDefault();
                    e.stopPropagation();

                    const validation = validateFormFields();
                    if (!validation.valid) {
                        if (validation.field) {
                            validation.field.focus();
                            validation.field.reportValidity();
                        }
                        if (window.showToast) {
                            showToast(validation.message, 'error');
                        }
                        return false;
                    }

                    processarDatas();
                    formHasChanges = false;
                    modalForm.submit();
                }
            });

            document.addEventListener('click', async function(e) {
                const consultarBtn = e.target.closest('#btn-consultar-oamd');
                if (!consultarBtn) return;
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
                if (!implId) return;
                const loader = document.getElementById('btn-consultar-oamd-loader');
                const icon = document.getElementById('btn-consultar-oamd-icon');
                if (loader) loader.classList.remove('d-none');
                if (icon) icon.classList.add('d-none');
                consultarBtn.disabled = true;
                try {
                    const res = await fetch(`/api/v1/oamd/implantacoes/${implId}/consulta`, { headers: { 'Accept': 'application/json' } });
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
                    setFp(window.fpInicioEfetivo, 'inicio_implantacao', '#modal-inicio_efetivo');
                    setFp(window.fpFinalImpl, 'final_implantacao', '#modal-data_final_implantacao');
                    setFp(window.fpInicioProd, 'inicio_producao', '#modal-data_inicio_producao');
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
                        }).catch(() => {});
                    } catch (_) {}
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
            var makeConfig = function() {
                return {
                    dateFormat: 'Y-m-d',
                    altInput: true,
                    altFormat: 'd/m/Y',
                    allowInput: false,
                    locale: flatpickr.l10ns.default || flatpickr.l10ns.pt,
                    parseDate: function(datestr) {
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
            var ensureInstance = function(selector) {
                var el = document.querySelector(selector);
                if (!el) return null;
                if (el._flatpickr) return el._flatpickr;
                return window.flatpickr(el, makeConfig());
            };

            window.fpInicioEfetivo = ensureInstance('#modal-inicio_efetivo');
            window.fpInicioProd = ensureInstance('#modal-data_inicio_producao');
            window.fpFinalImpl = ensureInstance('#modal-data_final_implantacao');
        })();
    });

})();
