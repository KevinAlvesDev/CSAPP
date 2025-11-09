import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Adiciona o diretório CSAPP ao path do Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from project.validation import validate_email, validate_integer, sanitize_string, validate_date, ValidationError

class TestValidation:
    """Testes para o módulo de validação"""
    
    def test_validate_email_valid(self):
        """Testa validação de email válido"""
        valid_emails = [
            'user@example.com',
            'test.email@domain.com.br',
            'user+tag@example.com',
            'user.name@example.com'
        ]
        
        for email in valid_emails:
            result = validate_email(email)
            assert result == email
    
    def test_validate_email_invalid(self):
        """Testa validação de email inválido"""
        invalid_emails = [
            'invalid-email',
            'user@',
            '@domain.com',
            'user@domain',
            '',
            'user@.com',
            'user@domain.'
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                validate_email(email)
    
    def test_validate_integer_valid(self):
        """Testa validação de inteiro válido"""
        valid_integers = [1, 42, 100, 0, -5]
        
        for integer in valid_integers:
            result = validate_integer(integer)
            assert result == integer
    
    def test_validate_integer_with_min_value(self):
        """Testa validação de inteiro com valor mínimo"""
        result = validate_integer(5, min_value=1)
        assert result == 5
        
        with pytest.raises(ValidationError):
            validate_integer(0, min_value=1)
    
    def test_validate_integer_with_max_value(self):
        """Testa validação de inteiro com valor máximo"""
        result = validate_integer(5, max_value=10)
        assert result == 5
        
        with pytest.raises(ValidationError):
            validate_integer(15, max_value=10)
    
    def test_validate_integer_invalid_types(self):
        """Testa validação de tipos inválidos para inteiro"""
        invalid_values = ['abc', [], {}]
        
        for value in invalid_values:
            # Tipos inválidos devem lançar ValidationError
            with pytest.raises(ValidationError):
                validate_integer(value)
        
        # None deve lançar ValidationError quando allow_none=False (padrão)
        with pytest.raises(ValidationError):
            validate_integer(None)
        
        # Float 1.5 deve funcionar (é convertido para 1)
        result = validate_integer(1.5)
        assert result == 1
    
    def test_sanitize_string_valid(self):
        """Testa sanitização de string válida"""
        test_cases = [
            ('Hello World', 'Hello World'),
            ('  Trim me  ', 'Trim me'),
            ('Special <chars>', 'Special &lt;chars&gt;'),
            ('Normal text', 'Normal text')
        ]
        
        for input_str, expected in test_cases:
            result = sanitize_string(input_str)
            assert result == expected
    
    def test_sanitize_string_with_length_constraints(self):
        """Testa sanitização de string com restrições de tamanho"""
        # Testa string dentro dos limites
        result = sanitize_string('Hello', min_length=3, max_length=10)
        assert result == 'Hello'
        
        # Testa string muito curta
        with pytest.raises(ValidationError):
            sanitize_string('Hi', min_length=3)
        
        # Testa string muito longa
        with pytest.raises(ValidationError):
            sanitize_string('This is a very long string', max_length=10)
    
    def test_sanitize_string_empty(self):
        """Testa sanitização de string vazia"""
        # String vazia deve ser aceita por padrão
        result = sanitize_string('')
        assert result == ''
        
        # String vazia com min_length > 0 deve falhar
        with pytest.raises(ValidationError):
            sanitize_string('', min_length=1)
    
    def test_validate_date_valid(self):
        """Testa validação de data válida"""
        valid_dates = [
            '2023-12-25',
            '2023-01-01',
            '2023-06-15'
        ]
        
        for date_str in valid_dates:
            result = validate_date(date_str)
            # validate_date retorna um objeto date, então verificamos se a data está correta
            expected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            assert result == expected_date
    
    def test_validate_date_invalid(self):
        """Testa validação de data inválida"""
        invalid_dates = [
            '2023-13-01',  # Mês inválido
            '2023-02-30',  # Dia inválido
            '2023/12/25',  # Formato errado
            '25-12-2023',  # Ordem errada
            'not-a-date',  # String aleatória
            '',            # String vazia
        ]
        
        for date_str in invalid_dates:
            with pytest.raises(ValidationError):
                validate_date(date_str)

class TestValidationEdgeCases:
    """Testes de casos extremos para validação"""
    
    def test_validate_email_edge_cases(self):
        """Testa casos extremos para validação de email"""
        # Email muito longo
        long_email = 'a' * 100 + '@example.com'
        result = validate_email(long_email)
        assert result == long_email
        
        # Email com caracteres especiais válidos
        special_email = 'user+tag.name@sub-domain.example.com'
        result = validate_email(special_email)
        assert result == special_email
    
    def test_sanitize_string_edge_cases(self):
        """Testa casos extremos para sanitização de string"""
        # String muito longa
        long_string = 'a' * 1000
        result = sanitize_string(long_string)
        assert result == long_string

        # String com múltiplos espaços - a função não remove espaços múltiplos, apenas espaços no início/fim
        multi_space = '   multiple   spaces   '
        result = sanitize_string(multi_space)
        assert result == 'multiple   spaces'  # A função mantém espaços múltiplos no meio
        
        # String com HTML
        html_string = '<script>alert("xss")</script>'
        result = sanitize_string(html_string)
        assert '&lt;script&gt;' in result
        assert '&lt;/script&gt;' in result
    
    def test_validate_integer_edge_cases(self):
        """Testa casos extremos para validação de inteiro"""
        # Valores limitrofes
        result = validate_integer(1, min_value=1)
        assert result == 1
        
        result = validate_integer(10, max_value=10)
        assert result == 10
        
        # Zero como valor mínimo
        result = validate_integer(0, min_value=0)
        assert result == 0

if __name__ == '__main__':
    pytest.main([__file__])