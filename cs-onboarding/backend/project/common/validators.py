"""
Validadores de dados aprimorados para maior robustez
"""

import re
from datetime import datetime
from typing import Any, Optional, Union


class DataValidator:
    """Classe com métodos estáticos para validação de dados"""
    
    @staticmethod
    def validate_email(email: str, required: bool = True) -> Optional[str]:
        """
        Valida formato de email.
        
        Args:
            email: Email a validar
            required: Se True, lança exceção se vazio
            
        Returns:
            Email normalizado ou None
            
        Raises:
            ValueError: Se email inválido
        """
        if not email or not email.strip():
            if required:
                raise ValueError("Email é obrigatório")
            return None
        
        email = email.strip().lower()
        
        # Regex básico para email
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError(f"Email inválido: {email}")
        
        return email
    
    @staticmethod
    def validate_cnpj(cnpj: str, required: bool = False) -> Optional[str]:
        """
        Valida e formata CNPJ.
        
        Args:
            cnpj: CNPJ a validar
            required: Se True, lança exceção se vazio
            
        Returns:
            CNPJ formatado ou None
        """
        if not cnpj or not cnpj.strip():
            if required:
                raise ValueError("CNPJ é obrigatório")
            return None
        
        # Remover caracteres não numéricos
        cnpj_digits = re.sub(r'\D', '', cnpj)
        
        if len(cnpj_digits) != 14:
            raise ValueError(f"CNPJ deve ter 14 dígitos: {cnpj}")
        
        # Formatar: 00.000.000/0000-00
        return f"{cnpj_digits[:2]}.{cnpj_digits[2:5]}.{cnpj_digits[5:8]}/{cnpj_digits[8:12]}-{cnpj_digits[12:]}"
    
    @staticmethod
    def validate_phone(phone: str, required: bool = False) -> Optional[str]:
        """
        Valida e formata telefone brasileiro.
        
        Args:
            phone: Telefone a validar
            required: Se True, lança exceção se vazio
            
        Returns:
            Telefone formatado ou None
        """
        if not phone or not phone.strip():
            if required:
                raise ValueError("Telefone é obrigatório")
            return None
        
        # Remover caracteres não numéricos
        phone_digits = re.sub(r'\D', '', phone)
        
        # Aceitar 10 ou 11 dígitos (com ou sem 9)
        if len(phone_digits) not in [10, 11]:
            raise ValueError(f"Telefone deve ter 10 ou 11 dígitos: {phone}")
        
        # Formatar: (00) 00000-0000 ou (00) 0000-0000
        if len(phone_digits) == 11:
            return f"({phone_digits[:2]}) {phone_digits[2:7]}-{phone_digits[7:]}"
        else:
            return f"({phone_digits[:2]}) {phone_digits[2:6]}-{phone_digits[6:]}"
    
    @staticmethod
    def validate_date(date_str: str, required: bool = False) -> Optional[datetime]:
        """
        Valida e converte string de data para datetime.
        Aceita formatos: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
        
        Args:
            date_str: Data em string
            required: Se True, lança exceção se vazio
            
        Returns:
            Objeto datetime ou None
        """
        if not date_str or not str(date_str).strip():
            if required:
                raise ValueError("Data é obrigatória")
            return None
        
        date_str = str(date_str).strip()
        
        # Tentar diferentes formatos
        formats = [
            '%Y-%m-%d',      # 2024-01-15
            '%d/%m/%Y',      # 15/01/2024
            '%d-%m-%Y',      # 15-01-2024
            '%Y/%m/%d',      # 2024/01/15
            '%d.%m.%Y',      # 15.01.2024
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Formato de data inválido: {date_str}. Use YYYY-MM-DD ou DD/MM/YYYY")
    
    @staticmethod
    def validate_integer(value: Any, min_value: Optional[int] = None, 
                        max_value: Optional[int] = None, required: bool = True) -> Optional[int]:
        """
        Valida e converte para inteiro.
        
        Args:
            value: Valor a validar
            min_value: Valor mínimo permitido
            max_value: Valor máximo permitido
            required: Se True, lança exceção se None/vazio
            
        Returns:
            Inteiro validado ou None
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                raise ValueError("Valor inteiro é obrigatório")
            return None
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Valor deve ser um número inteiro: {value}")
        
        if min_value is not None and int_value < min_value:
            raise ValueError(f"Valor deve ser maior ou igual a {min_value}: {int_value}")
        
        if max_value is not None and int_value > max_value:
            raise ValueError(f"Valor deve ser menor ou igual a {max_value}: {int_value}")
        
        return int_value
    
    @staticmethod
    def validate_float(value: Any, min_value: Optional[float] = None,
                      max_value: Optional[float] = None, required: bool = True) -> Optional[float]:
        """
        Valida e converte para float.
        
        Args:
            value: Valor a validar
            min_value: Valor mínimo permitido
            max_value: Valor máximo permitido
            required: Se True, lança exceção se None/vazio
            
        Returns:
            Float validado ou None
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                raise ValueError("Valor numérico é obrigatório")
            return None
        
        try:
            # Aceitar vírgula como separador decimal
            if isinstance(value, str):
                value = value.replace(',', '.')
            float_value = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Valor deve ser um número: {value}")
        
        if min_value is not None and float_value < min_value:
            raise ValueError(f"Valor deve ser maior ou igual a {min_value}: {float_value}")
        
        if max_value is not None and float_value > max_value:
            raise ValueError(f"Valor deve ser menor ou igual a {max_value}: {float_value}")
        
        return float_value
    
    @staticmethod
    def validate_string(value: Any, min_length: Optional[int] = None,
                       max_length: Optional[int] = None, required: bool = True,
                       pattern: Optional[str] = None) -> Optional[str]:
        """
        Valida string com opções de tamanho e padrão.
        
        Args:
            value: Valor a validar
            min_length: Tamanho mínimo
            max_length: Tamanho máximo
            required: Se True, lança exceção se vazio
            pattern: Regex pattern para validar
            
        Returns:
            String validada ou None
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                raise ValueError("Texto é obrigatório")
            return None
        
        str_value = str(value).strip()
        
        if min_length is not None and len(str_value) < min_length:
            raise ValueError(f"Texto deve ter pelo menos {min_length} caracteres")
        
        if max_length is not None and len(str_value) > max_length:
            raise ValueError(f"Texto deve ter no máximo {max_length} caracteres")
        
        if pattern and not re.match(pattern, str_value):
            raise ValueError(f"Formato inválido: {str_value}")
        
        return str_value
    
    @staticmethod
    def validate_choice(value: Any, choices: list, required: bool = True) -> Optional[Any]:
        """
        Valida se valor está em lista de opções permitidas.
        
        Args:
            value: Valor a validar
            choices: Lista de valores permitidos
            required: Se True, lança exceção se None
            
        Returns:
            Valor validado ou None
        """
        if value is None:
            if required:
                raise ValueError("Valor é obrigatório")
            return None
        
        if value not in choices:
            raise ValueError(f"Valor inválido. Opções: {', '.join(map(str, choices))}")
        
        return value
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Remove tags HTML perigosas do texto.
        
        Args:
            text: Texto a sanitizar
            
        Returns:
            Texto sanitizado
        """
        if not text:
            return ""
        
        # Remover tags script e style
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remover atributos perigosos
        text = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*javascript:', '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def validate_url(url: str, required: bool = False, allowed_schemes: list = None) -> Optional[str]:
        """
        Valida URL.
        
        Args:
            url: URL a validar
            required: Se True, lança exceção se vazio
            allowed_schemes: Lista de esquemas permitidos (http, https, etc)
            
        Returns:
            URL validada ou None
        """
        if not url or not url.strip():
            if required:
                raise ValueError("URL é obrigatória")
            return None
        
        url = url.strip()
        
        # Regex básico para URL
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(pattern, url, re.IGNORECASE):
            raise ValueError(f"URL inválida: {url}")
        
        if allowed_schemes:
            scheme = url.split('://')[0].lower()
            if scheme not in allowed_schemes:
                raise ValueError(f"Esquema de URL não permitido: {scheme}. Permitidos: {', '.join(allowed_schemes)}")
        
        return url
