\
\

import pytest
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from project.utils import (
    format_date_br, 
    format_date_iso_for_json,
    calcular_progresso,
    calcular_dias_decorridos,
    gerar_cor_status
)


class TestFormatDateBr:
    """Testes para formatação de data brasileira."""
    
    def test_format_date_br_with_datetime(self):
        """Testa formatação com objeto datetime."""
        dt = datetime(2025, 1, 13, 15, 30, 45)
        result = format_date_br(dt)
        assert result == '13/01/2025'
    
    def test_format_date_br_with_string_iso(self):
        """Testa formatação com string ISO."""
        result = format_date_br('2025-01-13')
        assert result == '13/01/2025'
    
    def test_format_date_br_with_string_datetime(self):
        """Testa formatação com string datetime completa."""
        result = format_date_br('2025-01-13 15:30:45')
        assert result == '13/01/2025'
    
    def test_format_date_br_with_none(self):
        """Testa formatação com None."""
        result = format_date_br(None)
        assert result == 'N/A'                                  

    def test_format_date_br_with_empty_string(self):
        """Testa formatação com string vazia."""
        result = format_date_br('')
        assert result == 'N/A'                                          


class TestFormatDateIsoForJson:
    """Testes para formatação de data ISO para JSON."""
    
    def test_format_date_iso_with_datetime(self):
        """Testa formatação ISO com datetime."""
        dt = datetime(2025, 1, 13, 15, 30, 45)
        result = format_date_iso_for_json(dt)
        assert result == '2025-01-13 15:30:45'                               

    def test_format_date_iso_with_string(self):
        """Testa formatação ISO com string."""
        result = format_date_iso_for_json('2025-01-13')
        assert result == '2025-01-13 00:00:00'                                   
    
    def test_format_date_iso_with_none(self):
        """Testa formatação ISO com None."""
        result = format_date_iso_for_json(None)
        assert result is None


class TestCalcularProgresso:
    """Testes para cálculo de progresso."""
    
    def test_progresso_zero_tarefas(self):
        """Testa progresso com zero tarefas."""
        result = calcular_progresso(0, 0)
        assert result == 0
    
    def test_progresso_todas_concluidas(self):
        """Testa progresso com todas tarefas concluídas."""
        result = calcular_progresso(10, 10)
        assert result == 100
    
    def test_progresso_metade_concluida(self):
        """Testa progresso com metade concluída."""
        result = calcular_progresso(5, 10)
        assert result == 50
    
    def test_progresso_um_terco_concluido(self):
        """Testa progresso com um terço concluído."""
        result = calcular_progresso(1, 3)
        assert result == 33               
    
    def test_progresso_arredondamento(self):
        """Testa arredondamento de progresso."""
        result = calcular_progresso(2, 3)
        assert result == 67                         


class TestCalcularDiasDecorridos:
    """Testes para cálculo de dias decorridos."""
    
    def test_dias_decorridos_hoje(self):
        """Testa dias decorridos desde hoje."""
        hoje = datetime.now()
        result = calcular_dias_decorridos(hoje)
        assert result == 0
    
    def test_dias_decorridos_ontem(self):
        """Testa dias decorridos desde ontem."""
        ontem = datetime.now() - timedelta(days=1)
        result = calcular_dias_decorridos(ontem)
        assert result == 1
    
    def test_dias_decorridos_semana_passada(self):
        """Testa dias decorridos desde semana passada."""
        semana_passada = datetime.now() - timedelta(days=7)
        result = calcular_dias_decorridos(semana_passada)
        assert result == 7
    
    def test_dias_decorridos_com_string(self):
        """Testa dias decorridos com string ISO."""
        ontem = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        result = calcular_dias_decorridos(ontem)
        assert result == 1
    
    def test_dias_decorridos_com_none(self):
        """Testa dias decorridos com None."""
        result = calcular_dias_decorridos(None)
        assert result == 0


class TestGerarCorStatus:
    """Testes para geração de cor por status."""
    
    def test_cor_status_andamento(self):
        """Testa cor para status 'andamento'."""
        result = gerar_cor_status('andamento')
        assert result in ['#3498db', '#007bff', 'blue']
    
    def test_cor_status_finalizada(self):
        """Testa cor para status 'finalizada'."""
        result = gerar_cor_status('finalizada')
        assert result in ['#2ecc71', '#28a745', 'green']
    
    def test_cor_status_pausada(self):
        """Testa cor para status 'pausada'."""
        result = gerar_cor_status('pausada')
        assert result in ['#f39c12', '#ffc107', 'orange']
    
    def test_cor_status_cancelada(self):
        """Testa cor para status 'cancelada'."""
        result = gerar_cor_status('cancelada')
        assert result in ['#e74c3c', '#dc3545', 'red']
    
    def test_cor_status_desconhecido(self):
        """Testa cor para status desconhecido."""
        result = gerar_cor_status('status_invalido')
        assert result in ['#95a5a6', '#6c757d', 'gray']

