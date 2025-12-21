"""
Field Validators - Rigorous validation for critical fields
Prevents invalid data from being saved to database
"""

import re
from typing import Optional, Tuple


def validate_email(email: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not email:
        return True, None  # Email is optional
    
    email = email.strip()
    
    # RFC 5322 simplified regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "E-mail inválido. Use o formato: exemplo@dominio.com"
    
    # Additional checks
    if len(email) > 254:
        return False, "E-mail muito longo (máximo 254 caracteres)"
    
    local, domain = email.rsplit('@', 1)
    
    if len(local) > 64:
        return False, "Parte local do e-mail muito longa (máximo 64 caracteres)"
    
    if '..' in email:
        return False, "E-mail não pode conter pontos consecutivos"
    
    return True, None


def validate_telefone(telefone: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate Brazilian phone number format.
    
    Expected format: (XX) XXXXX-XXXX or (XX) XXXX-XXXX
    
    Args:
        telefone: Phone number to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not telefone:
        return True, None  # Phone is optional
    
    telefone = telefone.strip()
    
    # Pattern: (XX) XXXXX-XXXX or (XX) XXXX-XXXX
    pattern = r'^\(\d{2}\) \d{4,5}-\d{4}$'
    
    if not re.match(pattern, telefone):
        return False, "Telefone inválido. Use o formato: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX"
    
    # Extract digits
    digits = re.sub(r'\D', '', telefone)
    
    if len(digits) not in [10, 11]:
        return False, "Telefone deve ter 10 ou 11 dígitos"
    
    # Validate DDD (area code)
    ddd = int(digits[:2])
    valid_ddds = list(range(11, 100))  # All Brazilian DDDs
    
    if ddd not in valid_ddds:
        return False, f"DDD inválido: {ddd}"
    
    return True, None


def validate_cnpj(cnpj: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate Brazilian CNPJ (company tax ID).
    
    Expected format: XX.XXX.XXX/XXXX-XX
    
    Args:
        cnpj: CNPJ to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not cnpj:
        return True, None  # CNPJ is optional
    
    cnpj = cnpj.strip()
    
    # Remove formatting
    cnpj_digits = re.sub(r'\D', '', cnpj)
    
    if len(cnpj_digits) != 14:
        return False, "CNPJ deve ter 14 dígitos"
    
    # Check for known invalid CNPJs (all same digit)
    if cnpj_digits == cnpj_digits[0] * 14:
        return False, "CNPJ inválido"
    
    # Validate check digits
    def calculate_digit(cnpj_base, weights):
        total = sum(int(digit) * weight for digit, weight in zip(cnpj_base, weights))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder
    
    # First check digit
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    digit1 = calculate_digit(cnpj_digits[:12], weights1)
    
    if int(cnpj_digits[12]) != digit1:
        return False, "CNPJ inválido (dígito verificador incorreto)"
    
    # Second check digit
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    digit2 = calculate_digit(cnpj_digits[:13], weights2)
    
    if int(cnpj_digits[13]) != digit2:
        return False, "CNPJ inválido (dígito verificador incorreto)"
    
    return True, None


def validate_alunos_ativos(alunos: Optional[int]) -> Tuple[bool, Optional[str]]:
    """
    Validate number of active students.
    
    Args:
        alunos: Number of students
        
    Returns:
        (is_valid, error_message)
    """
    if alunos is None:
        return True, None
    
    if not isinstance(alunos, int):
        try:
            alunos = int(alunos)
        except (ValueError, TypeError):
            return False, "Número de alunos deve ser um número inteiro"
    
    if alunos < 0:
        return False, "Número de alunos não pode ser negativo"
    
    if alunos > 1000000:
        return False, "Número de alunos parece muito alto. Verifique o valor."
    
    return True, None


def validate_valor_monetario(valor: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate monetary value.
    
    Args:
        valor: Monetary value (can be string or float)
        
    Returns:
        (is_valid, error_message)
    """
    if not valor:
        return True, None
    
    try:
        valor_float = float(str(valor).replace(',', '.'))
    except (ValueError, TypeError):
        return False, "Valor monetário inválido"
    
    if valor_float < 0:
        return False, "Valor não pode ser negativo"
    
    if valor_float > 1000000000:  # 1 billion
        return False, "Valor parece muito alto. Verifique."
    
    return True, None


def validate_detalhes_empresa(campos: dict) -> Tuple[bool, list]:
    """
    Validate all company details fields.
    
    Args:
        campos: Dictionary of field values
        
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    # Validate email
    if 'email_responsavel' in campos:
        valid, error = validate_email(campos['email_responsavel'])
        if not valid:
            errors.append(error)
    
    # Validate phone
    if 'telefone_responsavel' in campos:
        valid, error = validate_telefone(campos['telefone_responsavel'])
        if not valid:
            errors.append(error)
    
    # Validate CNPJ
    if 'cnpj' in campos:
        valid, error = validate_cnpj(campos['cnpj'])
        if not valid:
            errors.append(error)
    
    # Validate alunos ativos
    if 'alunos_ativos' in campos:
        valid, error = validate_alunos_ativos(campos['alunos_ativos'])
        if not valid:
            errors.append(error)
    
    # Validate valor atribuido
    if 'valor_atribuido' in campos:
        valid, error = validate_valor_monetario(campos['valor_atribuido'])
        if not valid:
            errors.append(error)
    
    return len(errors) == 0, errors
