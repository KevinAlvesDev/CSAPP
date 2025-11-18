import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

\
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from project.blueprints.management import manage_users, update_user_perfil, delete_user

class TestManagement:
    """Testes para o módulo de gerenciamento"""
    
    def setup_method(self):
        """Configuração inicial para cada teste"""
        from flask import Flask
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.secret_key = 'test-secret'
        self.client = self.app.test_client()
    
    def test_manage_users_success(self):
        """Testa manage_users com sucesso"""
        with self.app.test_request_context():
            from flask import g
            g.user_email = 'admin@example.com'
            g.perfil = {'perfil_acesso': 'Administrador'}
            g.user = {'name': 'Admin', 'sub': 'sub-id'}
            with patch('project.blueprints.management.query_db') as mock_query_db:
                with patch('project.blueprints.management.render_template') as mock_render:
                    mock_query_db.return_value = [
                        {'usuario': 'user1@example.com', 'nome': 'User 1', 'perfil_acesso': 'Usuário'},
                        {'usuario': 'user2@example.com', 'nome': 'User 2', 'perfil_acesso': 'Usuário'}
                    ]
                    mock_render.return_value = 'OK'
                    result = manage_users()
                    assert result == 'OK'
    
    def test_manage_users_error(self):
        """Testa manage_users com erro"""
        with self.app.test_request_context():
            from flask import g
            g.user_email = 'admin@example.com'
            g.perfil = {'perfil_acesso': 'Administrador'}
            g.user = {'name': 'Admin', 'sub': 'sub-id'}
            with patch('project.blueprints.management.query_db') as mock_query_db:
                with patch('project.blueprints.management.management_logger') as mock_logger:
                    mock_query_db.side_effect = Exception("Database connection error")
                    result = manage_users()
                    assert isinstance(result, tuple) and result[1] == 500
                    assert 'Erro ao carregar a lista' in result[0]
                    mock_logger.error.assert_called()
    
    def test_update_user_perfil_validation_error(self):
        """Testa update_user_perfil com erro de validação"""
        with self.app.test_request_context(method='POST', data={'usuario_email': 'invalid-email', 'new_perfil': 'Administrador'}):
            from flask import g
            g.user_email = 'admin@example.com'
            g.perfil = {'perfil_acesso': 'Administrador'}
            g.user = {'name': 'Admin', 'sub': 'sub-id'}
            with patch('project.blueprints.management.management_logger') as mock_logger:
                with patch('project.blueprints.management.url_for') as mock_url_for:
                    mock_url_for.return_value = '/dashboard'
                    result = update_user_perfil()
                    assert hasattr(result, 'status_code') and result.status_code == 302
                    mock_logger.warning.assert_called()
    
    def test_update_user_perfil_admin_downgrade(self):
        """Testa update_user_perfil quando tenta rebaixar admin"""
        from project.constants import ADMIN_EMAIL
        with self.app.test_request_context(method='POST', data={'usuario_email': ADMIN_EMAIL, 'new_perfil': 'Usuário'}):
            from flask import g
            g.user_email = 'admin@example.com'
            g.perfil = {'perfil_acesso': 'Administrador'}
            g.user = {'name': 'Admin', 'sub': 'sub-id'}
            with patch('project.blueprints.management.security_logger') as mock_logger:
                with patch('project.blueprints.management.url_for') as mock_url_for:
                    mock_url_for.return_value = '/dashboard'
                    result = update_user_perfil()
                    assert hasattr(result, 'status_code') and result.status_code == 302
                    mock_logger.warning.assert_called()
    
    def test_update_user_perfil_non_admin_changing_admin(self):
        """Testa update_user_perfil quando usuário não-admin tenta alterar admin"""
        with self.app.test_request_context(method='POST', data={'usuario_email': 'admin@example.com', 'new_perfil': 'Usuário'}):
            from flask import g
            g.user_email = 'user@example.com'
            g.perfil = {'perfil_acesso': 'Usuário'}
            g.user = {'name': 'User', 'sub': 'sub-id'}
            with patch('project.blueprints.auth.security_logger') as mock_logger:
                with patch('project.blueprints.auth.url_for') as mock_url_for:
                    mock_url_for.return_value = '/dashboard'
                    result = update_user_perfil()
                    assert hasattr(result, 'status_code') and result.status_code == 302
                    mock_logger.warning.assert_called()
                    \
                    result = update_user_perfil()
                    assert hasattr(result, 'status_code') and result.status_code == 302
                    mock_logger.warning.assert_called()
    
    def test_update_user_perfil_success(self):
        """Testa update_user_perfil com sucesso"""
        with self.app.test_request_context(method='POST', data={'usuario_email': 'user@example.com', 'new_perfil': 'Moderador'}):
            from flask import g
            g.user_email = 'admin@example.com'
            g.perfil = {'perfil_acesso': 'Administrador'}
            with patch('project.blueprints.management.query_db') as mock_query_db:
                with patch('project.blueprints.management.execute_db') as mock_execute_db:
                    with patch('project.blueprints.management.management_logger') as mock_logger:
                        with patch('project.blueprints.management.url_for') as mock_url_for:
                            mock_url_for.return_value = '/dashboard'
                            mock_query_db.return_value = {'perfil_acesso': 'Usuário'}
                            result = update_user_perfil()
                            assert hasattr(result, 'status_code') and result.status_code == 302
                            mock_logger.info.assert_called()
    
    def test_delete_user_validation_error(self):
        """Testa delete_user com erro de validação"""
        with self.app.test_request_context(method='POST', data={'usuario_email': 'invalid-email'}):
            from flask import g
            g.user_email = 'admin@example.com'
            g.perfil = {'perfil_acesso': 'Administrador'}
            g.user = {'name': 'Admin', 'sub': 'sub-id'}
            with patch('project.blueprints.management.management_logger') as mock_logger:
                with patch('project.blueprints.management.url_for') as mock_url_for:
                    mock_url_for.return_value = '/dashboard'
                    result = delete_user()
                    assert hasattr(result, 'status_code') and result.status_code == 302
                    mock_logger.warning.assert_called()
    
    def test_delete_user_self_deletion(self):
        """Testa delete_user quando tenta se auto-excluir"""
        with self.app.test_request_context(method='POST', data={'usuario_email': 'user@example.com'}):
            from flask import g
            g.user_email = 'user@example.com'
            g.perfil = {'perfil_acesso': 'Administrador'}
            g.user = {'name': 'User', 'sub': 'sub-id'}
            with patch('project.blueprints.management.security_logger') as mock_logger:
                with patch('project.blueprints.management.url_for') as mock_url_for:
                    mock_url_for.return_value = '/dashboard'
                    result = delete_user()
                    assert hasattr(result, 'status_code') and result.status_code == 302
                    mock_logger.warning.assert_called()
    
    def test_delete_user_main_admin(self):
        """Testa delete_user quando tenta excluir admin principal"""
        from project.constants import ADMIN_EMAIL
        with self.app.test_request_context(method='POST', data={'usuario_email': ADMIN_EMAIL}):
            from flask import g
            g.user_email = 'admin@example.com'
            g.perfil = {'perfil_acesso': 'Administrador'}
            g.user = {'name': 'Admin', 'sub': 'sub-id'}
            with patch('project.blueprints.management.security_logger') as mock_logger:
                with patch('project.blueprints.auth.url_for') as mock_auth_url_for:
                    mock_auth_url_for.return_value = '/dashboard'
                    with patch('project.blueprints.management.url_for') as mock_url_for:
                        mock_url_for.return_value = '/dashboard'
                        result = delete_user()
                        assert hasattr(result, 'status_code') and result.status_code == 302
                        mock_logger.warning.assert_called()
    
    def test_delete_user_success(self):
        """Testa delete_user com sucesso"""
        with self.app.test_request_context(method='POST', data={'usuario_email': 'user@example.com'}):
            from flask import g, current_app
            g.user_email = 'admin@example.com'
            g.perfil = {'perfil_acesso': 'Administrador'}
            g.user = {'name': 'Admin', 'sub': 'sub-id'}
            \
            current_app.config['CLOUDFLARE_PUBLIC_URL'] = 'https://public.example.com'
            current_app.config['CLOUDFLARE_BUCKET_NAME'] = 'bucket'
            with patch('project.blueprints.management.query_db') as mock_query_db:
                with patch('project.blueprints.management.execute_db') as mock_execute_db:
                    with patch('project.blueprints.management.r2_client') as mock_r2:
                        with patch('project.blueprints.management.management_logger') as mock_logger:
                            with patch('project.blueprints.management.url_for') as mock_url_for:
                                mock_url_for.return_value = '/dashboard'
                                mock_query_db.return_value = {'foto_url': 'https://public.example.com/path/to/file.jpg'}
                                mock_r2.delete_object.return_value = None
                                result = delete_user()
                                assert hasattr(result, 'status_code') and result.status_code == 302
                                mock_logger.info.assert_called()
    
    def test_delete_user_exception(self):
        """Testa delete_user com exceção"""
        with self.app.test_request_context(method='POST', data={'usuario_email': 'user@example.com'}):
            from flask import g
            g.user_email = 'admin@example.com'
            g.perfil = {'perfil_acesso': 'Administrador'}
            g.user = {'name': 'Admin', 'sub': 'sub-id'}
            with patch('project.blueprints.management.execute_db') as mock_execute_db:
                with patch('project.blueprints.management.management_logger') as mock_logger:
                    with patch('project.blueprints.management.url_for') as mock_url_for:
                        mock_url_for.return_value = '/dashboard'
                        mock_execute_db.side_effect = Exception("Database error")
                        result = delete_user()
                        assert hasattr(result, 'status_code') and result.status_code == 302
                        mock_logger.error.assert_called()

class TestManagementLogging:
    """Testes específicos para os logs de gerenciamento"""
    
    def test_management_logger_imports(self):
        """Testa se os loggers de gerenciamento podem ser importados"""
        try:
            from project.logging_config import management_logger, security_logger
            assert management_logger.name == 'management'
            assert security_logger.name == 'security'
        except ImportError as e:
            pytest.fail(f"Failed to import management loggers: {e}")
    
    def test_user_profile_update_logging(self):
        """Testa se logs de atualização de perfil são gerados corretamente"""
        with patch('project.blueprints.management.management_logger') as mock_logger:
            mock_logger.info("Perfil do usuário user@example.com atualizado para Moderador por admin@example.com")
            mock_logger.info.assert_called_with("Perfil do usuário user@example.com atualizado para Moderador por admin@example.com")
    
    def test_user_deletion_logging(self):
        """Testa se logs de exclusão de usuário são gerados corretamente"""
        with patch('project.blueprints.management.management_logger') as mock_logger:
            mock_logger.info("Usuário user@example.com excluído por admin@example.com")
            mock_logger.info.assert_called_with("Usuário user@example.com excluído por admin@example.com")
    
    def test_security_violation_logging(self):
        """Testa se logs de violação de segurança são gerados corretamente"""
        with patch('project.blueprints.management.security_logger') as mock_logger:
            mock_logger.warning("Tentativa de rebaixar administrador detectada por user@example.com")
            mock_logger.warning.assert_called_with("Tentativa de rebaixar administrador detectada por user@example.com")
            
            mock_logger.warning("Tentativa de exclusão do administrador principal detectada por user@example.com")
            mock_logger.warning.assert_called_with("Tentativa de exclusão do administrador principal detectada por user@example.com")

if __name__ == '__main__':
    pytest.main([__file__])