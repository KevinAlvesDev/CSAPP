// Test script to verify modal save button functionality
console.log('=== TESTE DO BOTÃO SALVAR ===');

// 1. Verificar se a função global existe
if (window.__submitModalFormDetalhes) {
    console.log('✅ window.__submitModalFormDetalhes existe');
} else {
    console.log('❌ window.__submitModalFormDetalhes NÃO existe');
}

// 2. Verificar se o botão existe
const saveBtn = document.querySelector('#modalDetalhesEmpresa .btn-salvar-detalhes');
if (saveBtn) {
    console.log('✅ Botão "Salvar Alterações" encontrado');
    console.log('   Texto do botão:', saveBtn.textContent);
    console.log('   Classes:', saveBtn.className);
} else {
    console.log('❌ Botão "Salvar Alterações" NÃO encontrado');
}

// 3. Verificar se o modal form existe
const modalForm = document.querySelector('#modalDetalhesEmpresa form');
if (modalForm) {
    console.log('✅ Form do modal encontrado');
    console.log('   Action:', modalForm.action);
} else {
    console.log('❌ Form do modal NÃO encontrado');
}

// 4. Adicionar listener de teste
document.addEventListener('click', function (e) {
    const btn = e.target.closest('#modalDetalhesEmpresa .btn-salvar-detalhes');
    if (btn) {
        console.log('🔔 CLIQUE DETECTADO no botão Salvar!');
        console.log('   Event:', e);
        console.log('   Target:', e.target);
        console.log('   CurrentTarget:', e.currentTarget);
    }
}, true); // Use capture phase

console.log('=== FIM DO TESTE ===');
