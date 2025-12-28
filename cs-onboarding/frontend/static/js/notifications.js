/**
 * Sistema de Notificações do Dashboard
 * Com localStorage para rastrear visualizações e badge inteligente
 */

document.addEventListener('DOMContentLoaded', function () {
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationBadge = document.getElementById('notificationBadge');

    if (!notificationBtn) return;

    // Criar dropdown de notificações
    const notificationDropdown = document.createElement('div');
    notificationDropdown.className = 'notification-dropdown';
    notificationDropdown.style.cssText = `
        position: absolute;
        top: 100%;
        right: 0;
        margin-top: 10px;
        width: 380px;
        max-height: 450px;
        overflow-y: auto;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        display: none;
        z-index: 9999;
    `;

    notificationBtn.parentElement.style.position = 'relative';
    notificationBtn.parentElement.appendChild(notificationDropdown);

    // LocalStorage para rastrear visualizações
    const STORAGE_KEY = 'cs_notifications_last_viewed';

    function getLastViewed() {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? new Date(stored) : null;
    }

    function setLastViewed() {
        localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    }

    // Toggle dropdown
    notificationBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        const isVisible = notificationDropdown.style.display === 'block';

        if (isVisible) {
            notificationDropdown.style.display = 'none';
        } else {
            notificationDropdown.style.display = 'block';
            loadNotifications();
            // Marca como visualizado ao abrir
            setLastViewed();
            // Zera o badge imediatamente
            updateBadge(0);
        }
    });

    // Fechar ao clicar fora
    document.addEventListener('click', function () {
        notificationDropdown.style.display = 'none';
    });

    notificationDropdown.addEventListener('click', function (e) {
        e.stopPropagation();
    });

    // Mostrar loading
    function showLoading() {
        notificationDropdown.innerHTML = `
            <div style="padding: 40px 20px; text-align: center; color: var(--text-muted);">
                <div class="spinner-border spinner-border-sm" role="status"></div>
                <p class="mb-0 mt-3">Carregando...</p>
            </div>
        `;
    }

    // Carregar notificações da API
    // Carregar notificações da API
    async function loadNotifications() {
        showLoading();

        try {
            const data = await window.apiFetch('/api/notifications');

            // apiFetch já verifica response.ok

            if (!data.ok) {
                // Se a API retornar JSON mas com campo ok: false
                throw new Error(data.error || 'Erro desconhecido');
            }

            renderNotifications(data.notifications || []);

        } catch (error) {
            // Toast já foi mostrado pelo apiFetch, mas atualizamos a UI do dropdown também
            notificationDropdown.innerHTML = `
                <div style="padding: 40px 20px; text-align: center; color: var(--text-muted);">
                    <i class="bi bi-exclamation-triangle fs-1 text-warning"></i>
                    <p class="mb-0 mt-3">Erro ao carregar</p>
                    <small>Tente novamente</small>
                </div>
            `;
        }
    }

    // Renderizar notificações
    function renderNotifications(notifications) {
        if (notifications.length === 0) {
            notificationDropdown.innerHTML = `
                <div style="padding: 40px 20px; text-align: center; color: var(--text-muted);">
                    <i class="bi bi-check-circle fs-1 text-success"></i>
                    <p class="mb-0 mt-3 fw-semibold">Tudo em dia! 🎉</p>
                    <small class="text-muted">Nenhuma pendência</small>
                </div>
            `;
            return;
        }

        let html = `
            <div style="padding: 15px 20px; border-bottom: 1px solid var(--border-color); background: var(--header-bg); border-radius: 12px 12px 0 0;">
                <h6 class="mb-0 fw-bold">Notificações</h6>
                <small class="text-muted">${notifications.length} aviso${notifications.length > 1 ? 's' : ''}</small>
            </div>
        `;

        notifications.forEach(notif => {
            const iconMap = {
                'danger': 'bi-exclamation-circle-fill text-danger',
                'warning': 'bi-exclamation-triangle-fill text-warning',
                'success': 'bi-check-circle-fill text-success',
                'info': 'bi-info-circle-fill text-info'
            };
            const iconClass = iconMap[notif.type] || iconMap['info'];

            html += `
                <div class="notification-item" style="padding: 14px 20px; border-bottom: 1px solid var(--border-color);">
                    <div class="d-flex align-items-start">
                        <i class="bi ${iconClass} fs-5 me-3 mt-1 flex-shrink-0"></i>
                        <div class="flex-grow-1">
                            <p class="mb-1 fw-semibold" style="font-size: 0.9rem; line-height: 1.4;">${notif.title}</p>
                            <p class="mb-0 text-muted" style="font-size: 0.82rem;">${notif.message}</p>
                        </div>
                    </div>
                </div>
            `;
        });

        notificationDropdown.innerHTML = html;
    }

    // Atualizar badge
    function updateBadge(count) {
        if (count > 0) {
            notificationBadge.textContent = count > 9 ? '9+' : count;
            notificationBadge.style.display = 'block';
        } else {
            notificationBadge.style.display = 'none';
        }
    }

    // Buscar contagem de notificações novas
    async function fetchNotificationCount() {
        try {
            // Background poll: suppress error toasts
            const data = await window.apiFetch('/api/notifications', { showErrorToast: false });

            if (data.ok) {
                const lastViewed = getLastViewed();
                const apiTimestamp = data.timestamp ? new Date(data.timestamp) : new Date();

                // Se nunca visualizou OU se há notificações novas desde a última visualização
                if (!lastViewed || apiTimestamp > lastViewed) {
                    updateBadge(data.total || 0);
                } else {
                    updateBadge(0);
                }
            }
        } catch (error) {
            // Silently fail for background polling
            console.warn('Background notification check failed:', error.message);
        }
    }

    // Verificar a cada 5 minutos
    setInterval(fetchNotificationCount, 5 * 60 * 1000);

    // Carregar contagem inicial após 1 segundo
    setTimeout(fetchNotificationCount, 1000);

    // Adicionar estilos de scrollbar
    if (!document.getElementById('notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            .notification-dropdown::-webkit-scrollbar {
                width: 6px;
            }
            .notification-dropdown::-webkit-scrollbar-track {
                background: transparent;
            }
            .notification-dropdown::-webkit-scrollbar-thumb {
                background: var(--border-color);
                border-radius: 3px;
            }
            .notification-dropdown::-webkit-scrollbar-thumb:hover {
                background: var(--text-muted);
            }
        `;
        document.head.appendChild(style);
    }
});
