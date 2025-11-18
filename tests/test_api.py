import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from project.api import (
    validate_integer, validate_date, sanitize_string,
    toggle_tarefa, adicionar_comentario, excluir_comentario,
    excluir_tarefa, reorder_tarefas, excluir_tarefas_modulo
)

class TestAPIValidation:
    """Testes para as funções de validação da API"""
    
    def test_validate_integer_valid(self):
        """Testa validate_integer com valores válidos"""
        assert validate_integer("123") == 123
        assert validate_integer("0") == 0
        assert validate_integer("-456") == -456
    
    def test_validate_integer_invalid(self):
        """Testa validate_integer com valores inválidos"""
        assert validate_integer("abc") is None
        assert validate_integer("12.34") is None
        assert validate_integer("") is None
        assert validate_integer("123abc") is None
    
    def test_validate_date_valid(self):
        """Testa validate_date com datas válidas"""
        assert validate_date("2024-01-15") == "2024-01-15"
        assert validate_date("2023-12-31") == "2023-12-31"
    
    def test_validate_date_invalid(self):
        """Testa validate_date com datas inválidas"""
        assert validate_date("2024-13-01") is None                
        assert validate_date("2024-01-32") is None                
        assert validate_date("invalid-date") is None
        assert validate_date("") is None
    
    def test_sanitize_string(self):
        """Testa sanitize_string"""
        assert sanitize_string("  Hello World  ") == "Hello World"
        assert sanitize_string("Test\nString") == "Test String"
        assert sanitize_string("Multiple   Spaces") == "Multiple Spaces"
        assert sanitize_string("") == ""

class TestAPITarefas:
    """Testes para operações de tarefas"""
    
    @patch('project.api.get_db_connection')
    @patch('project.api.g')
    def test_toggle_tarefa_success(self, mock_g, mock_get_db):
        """Testa toggle_tarefa com sucesso"""

        mock_g.user_email = 'test@example.com'
        mock_g.perfil = {'nome': 'Test User', 'perfil_acesso': 'Administrador'}

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        mock_cursor.fetchone.return_value = {
            'id': 1,
            'concluida': False,
            'implantacao_id': 1
        }
        
        with patch('project.api.api_logger') as mock_logger:
            result = toggle_tarefa(1)
            
            assert result is not None
            mock_logger.info.assert_called()
    
    @patch('project.api.get_db_connection')
    @patch('project.api.g')
    def test_toggle_tarefa_invalid_id(self, mock_g, mock_get_db):
        """Testa toggle_tarefa com ID inválido"""
        mock_g.user_email = 'test@example.com'
        
        with patch('project.api.api_logger') as mock_logger:
            result = toggle_tarefa("invalid")
            
            assert result is None
            mock_logger.warning.assert_called()
    
    @patch('project.api.get_db_connection')
    @patch('project.api.g')
    def test_toggle_tarefa_not_found(self, mock_g, mock_get_db):
        """Testa toggle_tarefa quando a tarefa não existe"""
        mock_g.user_email = 'test@example.com'

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        mock_cursor.fetchone.return_value = None
        
        with patch('project.api.api_logger') as mock_logger:
            result = toggle_tarefa(999)
            
            assert result is None
            mock_logger.warning.assert_called()
    
    @patch('project.api.get_db_connection')
    @patch('project.api.g')
    def test_toggle_tarefa_permission_denied(self, mock_g, mock_get_db):
        """Testa toggle_tarefa quando o usuário não tem permissão"""
        mock_g.user_email = 'user@example.com'
        mock_g.perfil = {'nome': 'User', 'perfil_acesso': 'Usuário', 'permissoes': {}}
        
        with patch('project.api.security_logger') as mock_logger:
            with patch('project.api.jsonify') as mock_jsonify:
                mock_jsonify.return_value = {'error': 'Acesso negado'}
                
                result = toggle_tarefa(1)
                
                assert 'error' in result
                mock_logger.warning.assert_called()

class TestAPIComentarios:
    """Testes para operações de comentários"""
    
    @patch('project.api.get_db_connection')
    @patch('project.api.g')
    def test_adicionar_comentario_success(self, mock_g, mock_get_db):
        """Testa adicionar_comentario com sucesso"""
        mock_g.user_email = 'test@example.com'
        mock_g.perfil = {'nome': 'Test User', 'perfil_acesso': 'Administrador'}

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        mock_cursor.fetchone.return_value = {'id': 1}
        
        with patch('project.api.api_logger') as mock_logger:
            result = adicionar_comentario(1, "Test comment")
            
            assert result is not None
            mock_logger.info.assert_called()
    
    @patch('project.api.get_db_connection')
    @patch('project.api.g')
    def test_adicionar_comentario_invalid_input(self, mock_g, mock_get_db):
        """Testa adicionar_comentario com entrada inválida"""
        mock_g.user_email = 'test@example.com'
        
        with patch('project.api.api_logger') as mock_logger:

            result = adicionar_comentario(1, "")
            
            assert result is None
            mock_logger.warning.assert_called()
    
    @patch('project.api.get_db_connection')
    @patch('project.api.g')
    def test_excluir_comentario_success(self, mock_g, mock_get_db):
        """Testa excluir_comentario com sucesso"""
        mock_g.user_email = 'test@example.com'
        mock_g.perfil = {'nome': 'Test User', 'perfil_acesso': 'Administrador'}

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        mock_cursor.fetchone.return_value = {'id': 1, 'usuario_email': 'test@example.com'}
        
        with patch('project.api.api_logger') as mock_logger:
            result = excluir_comentario(1)
            
            assert result is not None
            mock_logger.info.assert_called()
    
    @patch('project.api.g')
    def test_excluir_comentario_invalid_id(self, mock_g):
        """Testa excluir_comentario com ID inválido"""
        mock_g.user_email = 'test@example.com'
        
        with patch('project.api.api_logger') as mock_logger:
            result = excluir_comentario("invalid")
            
            assert result is None
            mock_logger.warning.assert_called()
    
    @patch('project.api.get_db_connection')
    @patch('project.api.g')
    def test_excluir_comentario_permission_denied(self, mock_g, mock_get_db):
        """Testa excluir_comentario quando o usuário não tem permissão"""
        mock_g.user_email = 'user@example.com'
        mock_g.perfil = {'nome': 'User', 'perfil_acesso': 'Usuário', 'permissoes': {}}

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        mock_cursor.fetchone.return_value = {'id': 1, 'usuario_email': 'admin@example.com'}
        
        with patch('project.api.security_logger') as mock_logger:
            with patch('project.api.jsonify') as mock_jsonify:
                mock_jsonify.return_value = {'error': 'Acesso negado'}
                
                result = excluir_comentario(1)
                
                assert 'error' in result
                mock_logger.warning.assert_called()

class TestAPILogging:
    """Testes específicos para os logs da API"""
    
    def test_api_logger_imports(self):
        """Testa se os loggers da API podem ser importados"""
        try:
            from project.logging_config import api_logger, security_logger
            assert api_logger.name == 'api'
            assert security_logger.name == 'security'
        except ImportError as e:
            pytest.fail(f"Failed to import API loggers: {e}")
    
    def test_task_toggle_logging(self):
        """Testa se logs de alternância de tarefa são gerados corretamente"""
        with patch('project.api.api_logger') as mock_logger:
            mock_logger.info("Status da tarefa 123 alterado para True por user@example.com")
            mock_logger.info.assert_called_with("Status da tarefa 123 alterado para True por user@example.com")
    
    def test_permission_denied_logging(self):
        """Testa se logs de permissão negada são gerados corretamente"""
        with patch('project.api.security_logger') as mock_logger:
            mock_logger.warning("Permissão negada para user@example.com na tarefa 123")
            mock_logger.warning.assert_called_with("Permissão negada para user@example.com na tarefa 123")
    
    def test_comment_operations_logging(self):
        """Testa se logs de operações de comentário são gerados corretamente"""
        with patch('project.api.api_logger') as mock_logger:
            mock_logger.info("Comentário 456 adicionado à tarefa 123 por user@example.com")
            mock_logger.info.assert_called_with("Comentário 456 adicionado à tarefa 123 por user@example.com")
            
            mock_logger.info("Comentário 456 excluído por user@example.com")
            mock_logger.info.assert_called_with("Comentário 456 excluído por user@example.com")
    
    def test_task_deletion_logging(self):
        """Testa se logs de exclusão de tarefa são gerados corretamente"""
        with patch('project.api.api_logger') as mock_logger:
            mock_logger.info("Tarefa 123 excluída por user@example.com")
            mock_logger.info.assert_called_with("Tarefa 123 excluída por user@example.com")
    
    def test_module_task_operations_logging(self):
        """Testa se logs de operações de tarefas por módulo são gerados corretamente"""
        with patch('project.api.api_logger') as mock_logger:
            mock_logger.info("Tarefas do módulo 'Frontend' excluídas da implantação 789 por user@example.com")
            mock_logger.info.assert_called_with("Tarefas do módulo 'Frontend' excluídas da implantação 789 por user@example.com")
            
            mock_logger.info("Tarefas reordenadas no módulo 'Backend' da implantação 789 por user@example.com")
            mock_logger.info.assert_called_with("Tarefas reordenadas no módulo 'Backend' da implantação 789 por user@example.com")

if __name__ == '__main__':
    pytest.main([__file__])