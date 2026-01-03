/**
 * Sistema de Ordenação de Tabelas do Dashboard
 * Permite ordenar colunas clicando nos headers
 */

document.addEventListener('DOMContentLoaded', function () {
    // Adicionar funcionalidade de ordenação a todas as tabelas do dashboard
    const tables = document.querySelectorAll('.table');

    tables.forEach(table => {
        const headers = table.querySelectorAll('thead th');
        const tbody = table.querySelector('tbody');

        if (!tbody) return;

        headers.forEach((header, index) => {
            // Ignorar colunas que não devem ter ordenação duplicada
            const headerText = header.textContent.trim();

            // Pular: Ações (não faz sentido ordenar por botão), vazias
            if (headerText === 'Ações' || headerText === '') {
                return;
            }

            // Adicionar cursor pointer e ícone
            header.style.cursor = 'pointer';
            header.style.userSelect = 'none';
            header.title = `Clique para ordenar por ${headerText}`;

            // Adicionar ícone de ordenação
            if (!header.querySelector('.sort-icon')) {
                const icon = document.createElement('i');
                icon.className = 'bi bi-arrow-down-up sort-icon ms-1';
                icon.style.fontSize = '0.8em';
                icon.style.opacity = '0.5';
                header.appendChild(icon);
            }

            let ascending = true;

            header.addEventListener('click', function () {
                // Remover indicadores de outras colunas
                headers.forEach(h => {
                    const icon = h.querySelector('.sort-icon');
                    if (icon && h !== header) {
                        icon.className = 'bi bi-arrow-down-up sort-icon ms-1';
                        icon.style.opacity = '0.5';
                    }
                });

                // Atualizar ícone da coluna atual
                const icon = header.querySelector('.sort-icon');
                if (icon) {
                    icon.className = ascending ? 'bi bi-arrow-up sort-icon ms-1' : 'bi bi-arrow-down sort-icon ms-1';
                    icon.style.opacity = '1';
                }

                // Obter todas as linhas
                const rows = Array.from(tbody.querySelectorAll('tr'));

                // Ordenar linhas
                rows.sort((a, b) => {
                    const cellA = a.cells[index];
                    const cellB = b.cells[index];

                    if (!cellA || !cellB) return 0;

                    let valueA = cellA.textContent.trim();
                    let valueB = cellB.textContent.trim();

                    // Detectar tipo de dado e ordenar apropriadamente

                    // Valores monetários (R$ X.XXX,XX)
                    if (valueA.startsWith('R$') && valueB.startsWith('R$')) {
                        valueA = parseFloat(valueA.replace('R$', '').replace(/\./g, '').replace(',', '.').trim()) || 0;
                        valueB = parseFloat(valueB.replace('R$', '').replace(/\./g, '').replace(',', '.').trim()) || 0;
                        return ascending ? valueA - valueB : valueB - valueA;
                    }

                    // Percentuais (XX%)
                    if (valueA.includes('%') && valueB.includes('%')) {
                        valueA = parseFloat(valueA.replace('%', '')) || 0;
                        valueB = parseFloat(valueB.replace('%', '')) || 0;
                        return ascending ? valueA - valueB : valueB - valueA;
                    }

                    // Números (dias, etc)
                    const numA = parseFloat(valueA.replace(/[^\d.-]/g, ''));
                    const numB = parseFloat(valueB.replace(/[^\d.-]/g, ''));
                    if (!isNaN(numA) && !isNaN(numB)) {
                        return ascending ? numA - numB : numB - numA;
                    }

                    // Texto (case-insensitive)
                    return ascending
                        ? valueA.localeCompare(valueB, 'pt-BR', { sensitivity: 'base' })
                        : valueB.localeCompare(valueA, 'pt-BR', { sensitivity: 'base' });
                });

                // Reordenar no DOM
                rows.forEach(row => tbody.appendChild(row));

                // Alternar direção para próximo clique
                ascending = !ascending;
            });
        });
    });
});
