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
    const STORAGE_KEY = 'cs_notifications_hash';

    function getStoredHash() {
        return localStorage.getItem(STORAGE_KEY) || '';
    }

    function setStoredHash(hash) {
        localStorage.setItem(STORAGE_KEY, hash);
    }

    // Gerar hash simples das notificações
    function generateHash(notifications) {
        if (!notifications || notifications.length === 0) return 'empty';
        // Usa os títulos para gerar um hash simples
        const titles = notifications.map(n => n.title || '').join('|');
        let hash = 0;
        for (let i = 0; i < titles.length; i++) {
            const char = titles.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        return hash.toString();
    }

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
            loadNotifications(true); // true = marcar como visto
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
    async function loadNotifications(markAsViewed = false) {
        showLoading();

        try {
            const data = await window.apiFetch('/api/notifications');

            // apiFetch já verifica response.ok

            if (!data.ok) {
                // Se a API retornar JSON mas com campo ok: false
                throw new Error(data.error || 'Erro desconhecido');
            }

            const notifications = data.notifications || [];
            renderNotifications(notifications);

            // Se abriu o dropdown, marcar como visualizado
            if (markAsViewed && notifications.length > 0) {
                const currentHash = generateHash(notifications);
                setStoredHash(currentHash);
                updateBadge(0);
            }

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

    // Renderizar notificações (Versão Premium Interativa)
    function renderNotifications(notifications) {
        if (notifications.length === 0) {
            notificationDropdown.innerHTML = `
                <div class="d-flex flex-column align-items-center justify-content-center" style="padding: 40px 20px; color: var(--text-muted); min-height: 200px;">
                    <div class="rounded-circle d-flex align-items-center justify-content-center mb-3" style="width: 60px; height: 60px; background: rgba(16, 185, 129, 0.1);">
                        <i class="bi bi-check-lg fs-2 text-success"></i>
                    </div>
                    <p class="mb-1 fw-semibold fs-6">Tudo limpo por aqui!</p>
                    <small class="text-muted">Você está em dia com suas tarefas.</small>
                </div>
            `;
            return;
        }

        let html = `
            <div class="d-flex align-items-center justify-content-between" style="padding: 16px 20px; border-bottom: 1px solid var(--border-color); background: var(--header-bg); border-radius: 12px 12px 0 0;">
                <h6 class="mb-0 fw-bold">Notificações</h6>
                <span class="badge rounded-pill bg-primary bg-opacity-10 text-primary">${notifications.length} nova${notifications.length > 1 ? 's' : ''}</span>
            </div>
            <div class="notification-list">
        `;

        notifications.forEach(notif => {
            const config = {
                'danger': { icon: 'bi-exclamation-circle-fill', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)' },
                'warning': { icon: 'bi-exclamation-triangle-fill', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)' },
                'success': { icon: 'bi-check-circle-fill', color: '#10b981', bg: 'rgba(16, 185, 129, 0.1)' },
                'info': { icon: 'bi-info-circle-fill', color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)' }
            }[notif.type] || { icon: 'bi-bell-fill', color: '#6366f1', bg: 'rgba(99, 102, 241, 0.1)' };

            const actionUrl = notif.action_url || '#';
            const isClickable = actionUrl !== '#';

            html += `
                <a href="${actionUrl}" class="notification-item d-flex align-items-start text-decoration-none" 
                   style="padding: 16px 20px; border-bottom: 1px solid var(--border-color); transition: background 0.2s; border-left: 3px solid ${config.color}; background: var(--card-bg);"
                   onmouseover="this.style.backgroundColor = 'var(--hover-bg)'"
                   onmouseout="this.style.backgroundColor = 'var(--card-bg)'">
                   
                    <div class="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0 me-3" 
                         style="width: 36px; height: 36px; background: ${config.bg}; color: ${config.color};">
                        <i class="bi ${config.icon} fs-6"></i>
                    </div>
                    
                    <div class="flex-grow-1" style="min-width: 0;">
                        <div class="d-flex justify-content-between align-items-start">
                            <p class="mb-1 fw-semibold text-truncate" style="font-size: 0.9rem; color: var(--text-primary, #333); width: 100%; transition: color 0.2s;">
                                ${notif.title}
                            </p>
                            ${isClickable ? '<i class="bi bi-chevron-right text-muted ms-2" style="font-size: 0.75rem;"></i>' : ''}
                        </div>
                        <p class="mb-0 text-muted" style="font-size: 0.85rem; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                            ${notif.message}
                        </p>
                    </div>
                </a>
            `;
        });

        html += `</div>`; // fecha notification-list

        // Footer com ações (futuro)
        html += `
             <div class="text-center py-2 bg-light bg-opacity-25" style="border-top: 1px solid var(--border-color); border-radius: 0 0 12px 12px;">
                <a href="/dashboard" class="text-decoration-none" style="font-size: 0.8rem; fw-medium;">Ver Dashboard Completo</a>
             </div>
        `;

        notificationDropdown.innerHTML = html;

        // Ajustar cores se estiver em dark mode (via CSS vars ou style inline defensivo)
        // Como o sistema usa classes, o ideal seria ter classes, mas style inline garante consistência imediata
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
                const notifications = data.notifications || [];
                const currentHash = generateHash(notifications);
                const storedHash = getStoredHash();

                // Só mostra badge se o conteúdo das notificações mudou
                if (notifications.length > 0 && currentHash !== storedHash) {
                    updateBadge(notifications.length);
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
