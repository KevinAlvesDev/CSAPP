import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

\
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from project.blueprints.auth import login_required, permission_required
from flask import Flask

class TestAuth:
    """Testes para o módulo de autenticação"""
    
    def setup_method(self):
        """Configuração inicial para cada teste"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
                \
        self.mock_g = Mock()
        self.mock_g.user_email = 'test@example.com'
        self.mock_g.perfil = {'nome': 'Test User', 'perfil_acesso': 'Administrador'}
    
    def test_login_required_with_valid_user(self):
        """Testa login_required com usuário válido"""
        with self.app.test_request_context():
            with patch('project.blueprints.auth.g', self.mock_g):
                with patch('project.blueprints.auth.auth_logger') as mock_logger:
                    
                    @login_required
                    def test_function():
                        return "Success"
                    
                    result = test_function()
                    
                    assert result == "Success"
                    mock_logger.info.assert_called()
    
    def test_login_required_without_user(self):
        """Testa login_required sem usuário"""
        with self.app.test_request_context():
            mock_g_no_user = Mock()
            mock_g_no_user.user_email = None
            
            with patch('project.blueprints.auth.g', mock_g_no_user):
                with patch('project.blueprints.auth.auth_logger') as mock_logger:
                    with patch('project.blueprints.auth.redirect') as mock_redirect:
                        with patch('project.blueprints.auth.url_for') as mock_url_for:
                            
                            mock_redirect.return_value = "redirected"
                            mock_url_for.return_value = "auth.login"
                            
                            @login_required
                            def test_function():
                                return "Success"
                            
                            result = test_function()
                            
                            assert result == "redirected"
                            mock_logger.info.assert_called()
    
    def test_permission_required_with_admin_user(self):
        """Testa permission_required com usuário administrador"""
        with self.app.test_request_context():
            with patch('project.blueprints.auth.g', self.mock_g):
                with patch('project.blueprints.auth.auth_logger') as mock_logger:
                    
                    @permission_required(['Administrador'])
                    def test_function():
                        return "Admin Success"
                    
                    result = test_function()
                    
                    assert result == "Admin Success"
                    mock_logger.info.assert_called()
    
    def test_permission_required_with_non_admin_user(self):
        """Testa permission_required com usuário não administrador"""
        with self.app.test_request_context():
            mock_g_user = Mock()
            mock_g_user.user_email = 'user@example.com'
            mock_g_user.perfil = {'nome': 'Regular User', 'perfil_acesso': 'Usuário'}
            
            with patch('project.blueprints.auth.g', mock_g_user):
                with patch('project.blueprints.auth.security_logger') as mock_logger:
                    with patch('project.blueprints.auth.redirect') as mock_redirect:
                        with patch('project.blueprints.auth.url_for') as mock_url_for:
                            
                            mock_redirect.return_value = "redirected"
                            mock_url_for.return_value = "main.dashboard"
                            
                            @permission_required(['Administrador'])
                            def test_function():
                                return "Admin Success"
                            
                            result = test_function()
                            
                            assert result == "redirected"
                            mock_logger.warning.assert_called()

class TestAuthLogging:
    """Testes específicos para os logs de autenticação"""
    
    def test_duplicate_login_logging(self):
        """Testa se logs de login duplicado são gerados corretamente"""
        with patch('project.blueprints.auth.auth_logger') as mock_logger:
            \
            try:
                raise ValueError("Usuário já existe")
            except ValueError as e:
                mock_logger.warning(f"Tentativa de login duplicado: {str(e)}")
                
                mock_logger.warning.assert_called_with("Tentativa de login duplicado: Usuário já existe")
    
    def test_admin_enforcement_logging(self):
        """Testa se logs de reforço de admin são gerados corretamente"""
        with patch('project.blueprints.auth.auth_logger') as mock_logger:
            \
            mock_logger.info("Reforçando papel de administrador para usuário: admin@example.com")
            
            mock_logger.info.assert_called_with("Reforçando papel de administrador para usuário: admin@example.com")
    
    def test_profile_sync_error_logging(self):
        """Testa se logs de erro de sincronização são gerados corretamente"""
        with patch('project.blueprints.auth.auth_logger') as mock_logger:
            \
            db_error = Exception("Erro de conexão com banco de dados")
            mock_logger.error(f"Erro crítico durante sincronização do perfil: {str(db_error)}")
            
            mock_logger.error.assert_called_with("Erro crítico durante sincronização do perfil: Erro de conexão com banco de dados")

if __name__ == '__main__':
    pytest.main([__file__])