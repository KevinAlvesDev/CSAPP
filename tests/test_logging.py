import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

\
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from project.logging_config import ContextFilter, setup_logging
import logging

class TestLoggingConfig:
    """Testes para o módulo de configuração de logs"""
    
    def test_context_filter_with_flask_context(self):
        """Testa ContextFilter com contexto Flask"""
        \
        mock_g = Mock()
        mock_g.user_email = 'test@example.com'
        mock_g.perfil = {'nome': 'Test User', 'perfil_acesso': 'Administrador'}
        
        with patch('project.logging_config.g', mock_g):
            filter_instance = ContextFilter()
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg='Test message',
                args=(),
                exc_info=None
            )
            
            result = filter_instance.filter(record)
            
            assert result is True
            assert hasattr(record, 'user_email')
            assert hasattr(record, 'user_profile')
            assert record.user_email == 'test@example.com'
            assert record.user_profile == 'Test User (Administrador)'
    
    def test_context_filter_without_flask_context(self):
        """Testa ContextFilter sem contexto Flask"""
        filter_instance = ContextFilter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        result = filter_instance.filter(record)
        
        assert result is True
        assert hasattr(record, 'user_email')
        assert hasattr(record, 'user_profile')
        assert record.user_email == 'system'
        assert record.user_profile == 'system'
    
    def test_context_filter_with_partial_context(self):
        """Testa ContextFilter com contexto parcial"""
        \
        mock_g = Mock()
        mock_g.user_email = 'test@example.com'
        mock_g.perfil = None
        
        with patch('project.logging_config.g', mock_g):
            filter_instance = ContextFilter()
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg='Test message',
                args=(),
                exc_info=None
            )
            
            result = filter_instance.filter(record)
            
            assert result is True
            assert record.user_email == 'test@example.com'
            assert record.user_profile == 'test@example.com'
    
    def test_setup_logging_creates_loggers(self):
        """Testa se setup_logging cria os loggers corretamente"""
        \
        mock_app = Mock()
        mock_app.config = {
            'LOG_LEVEL': 'INFO',
            'LOG_DIR': '/tmp/test_logs'
        }
        
        with patch('os.makedirs'), \
             patch('logging.getLogger'), \
             patch('logging.FileHandler'), \
             patch('logging.StreamHandler'), \
             patch('logging.Formatter'):
            
                        \
            mock_auth_logger = Mock()
            mock_api_logger = Mock()
            mock_db_logger = Mock()
            mock_security_logger = Mock()
            mock_management_logger = Mock()
            
            with patch('logging.getLogger') as mock_get_logger:
                def get_logger_side_effect(name):
                    loggers = {
                        'auth': mock_auth_logger,
                        'api': mock_api_logger,
                        'database': mock_db_logger,
                        'security': mock_security_logger,
                        'management': mock_management_logger
                    }
                    return loggers.get(name, Mock())
                
                mock_get_logger.side_effect = get_logger_side_effect
                
                                \
                setup_logging(mock_app)
                
                                \
                assert mock_get_logger.call_count >= 5
    
    def test_log_levels_configuration(self):
        """Testa configuração de níveis de log"""
        \
        mock_app = Mock()
        mock_app.config = {
            'LOG_LEVEL': 'DEBUG',
            'LOG_DIR': '/tmp/test_logs'
        }
        
        with patch('os.makedirs'), \
             patch('logging.getLogger') as mock_get_logger, \
             patch('logging.FileHandler'), \
             patch('logging.StreamHandler'), \
             patch('logging.Formatter'):
            
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            setup_logging(mock_app)
            
                        \
            mock_logger.setLevel.assert_called_with(logging.DEBUG)
    
    def test_log_directory_creation(self):
        """Testa criação do diretório de logs"""
        \
        mock_app = Mock()
        mock_app.config = {
            'LOG_LEVEL': 'INFO',
            'LOG_DIR': '/tmp/test_logs'
        }
        
        with patch('os.makedirs') as mock_makedirs, \
             patch('logging.getLogger'), \
             patch('logging.FileHandler'), \
             patch('logging.StreamHandler'), \
             patch('logging.Formatter'):
            
            setup_logging(mock_app)
            
                        \
            mock_makedirs.assert_called_with('/tmp/test_logs', exist_ok=True)

class TestLoggerIntegration:
    """Testes de integração com o sistema de logs"""
    
    def test_logger_imports(self):
        """Testa se os loggers podem ser importados corretamente"""
        try:
            from project.logging_config import auth_logger, api_logger, db_logger, security_logger, management_logger
            \
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import loggers: {e}")
    
    def test_logger_names(self):
        """Testa se os loggers têm os nomes corretos"""
        from project.logging_config import auth_logger, api_logger, db_logger, security_logger, management_logger
        
        assert auth_logger.name == 'auth'
        assert api_logger.name == 'api'
        assert db_logger.name == 'database'
        assert security_logger.name == 'security'
        assert management_logger.name == 'management'

if __name__ == '__main__':
    pytest.main([__file__])