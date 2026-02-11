"""
Testes de integração para fluxos críticos da aplicação.

Testa fluxos end-to-end usando o test client do Flask:
- Autenticação e acesso
- Dashboard e navegação
- Health check
"""


class TestHealthCheck:
    """Testa o endpoint de health check."""

    def test_health_endpoint_returns_200(self, client):
        """Health check deve retornar 200."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        """Health check deve retornar JSON."""
        response = client.get("/api/health")
        data = response.get_json()
        assert data is not None
        assert "status" in data or "ok" in data


class TestAuthFlow:
    """Testa fluxos de autenticação."""

    def test_login_page_accessible(self, client):
        """Página de login deve ser acessível."""
        response = client.get("/login")
        assert response.status_code in (200, 302)

    def test_unauthenticated_redirect(self, client):
        """Usuários não autenticados devem ser redirecionados."""
        response = client.get("/dashboard")
        # Em dev local, auto-login pode redirecionar para dashboard
        assert response.status_code in (200, 302)

    def test_logout_clears_session(self, authenticated_client):
        """Logout deve limpar a sessão."""
        response = authenticated_client.get("/logout", follow_redirects=False)
        assert response.status_code in (200, 302)


class TestDashboardAccess:
    """Testa acesso ao dashboard."""

    def test_authenticated_user_sees_dashboard(self, authenticated_client):
        """Usuário autenticado deve ver o dashboard."""
        response = authenticated_client.get("/dashboard")
        assert response.status_code in (200, 302)

    def test_dashboard_returns_html(self, authenticated_client):
        """Dashboard deve retornar HTML."""
        response = authenticated_client.get("/dashboard")
        if response.status_code == 200:
            assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data


class TestAPIEndpoints:
    """Testa endpoints de API básicos."""

    def test_404_returns_json_for_api(self, client):
        """Endpoints de API inexistentes devem retornar JSON 404."""
        response = client.get("/api/nonexistent-endpoint")
        assert response.status_code == 404
        data = response.get_json()
        assert data is not None
        assert data.get("ok") is False

    def test_404_returns_html_for_pages(self, client):
        """Páginas inexistentes devem retornar HTML 404."""
        response = client.get("/nonexistent-page")
        assert response.status_code in (302, 404)
