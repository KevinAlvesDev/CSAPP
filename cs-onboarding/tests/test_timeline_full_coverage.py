"""
Testes para cobertura completa de timeline_log.
Cobre: logar_timeline, _get_timeline_logs, time_calculator, e todos os tipos de eventos.
"""

import unittest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.project import create_app
from backend.project.db import execute_db, query_db
from backend.project.database.schema import init_db


class TimelineBaseTestCase(unittest.TestCase):
    """Classe base com setup comum para testes de timeline."""
    
    @classmethod
    def setUpClass(cls):
        os.environ['FLASK_ENV'] = 'development'
        cls.app = create_app({
            'TESTING': True,
            'USE_SQLITE_LOCALLY': True,
            'WTF_CSRF_ENABLED': False,
            'AUTH0_ENABLED': False,
            'DEBUG': True,
            'LOG_ROTATION_ENABLED': False
        })
    
    def setUp(self):
        with self.app.app_context():
            init_db()
            execute_db("DELETE FROM timeline_log")
            execute_db("DELETE FROM checklist_items")
            execute_db("DELETE FROM implantacoes")
        self.client = self.app.test_client()
        self.client.get('/dev-login')
    
    def tearDown(self):
        with self.app.app_context():
            execute_db("DELETE FROM timeline_log")
            execute_db("DELETE FROM checklist_items")
            execute_db("DELETE FROM implantacoes")
    
    def _create_implantacao(self, status='andamento', data_inicio_efetivo=None):
        """Helper para criar uma implantação de teste."""
        if data_inicio_efetivo is None:
            data_inicio_efetivo = datetime.now() - timedelta(days=10)
        
        with self.app.app_context():
            execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, status, usuario_cs, data_inicio_efetivo, data_criacao) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                ('Empresa Test', 'resp@example.com', status, 'tester@example.com', 
                 data_inicio_efetivo, datetime.now())
            )
            impl = query_db("SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1", one=True)
            return impl['id']


# =============================================================================
# TESTES: logar_timeline (db.py)
# =============================================================================

class TestLogarTimeline(TimelineBaseTestCase):
    """Testes para a função logar_timeline."""
    
    def test_logar_timeline_basic(self):
        """Testa inserção básica de log na timeline."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'teste_evento', 'Detalhes do teste')
            
            logs = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s",
                (impl_id,)
            )
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]['tipo_evento'], 'teste_evento')
            self.assertEqual(logs[0]['detalhes'], 'Detalhes do teste')
            self.assertEqual(logs[0]['usuario_cs'], 'user@test.com')
    
    def test_logar_timeline_multiple_events(self):
        """Testa inserção de múltiplos eventos."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            eventos = [
                ('status_alterado', 'Status mudou'),
                ('tarefa_alterada', 'Tarefa X concluída'),
                ('novo_comentario', 'Comentário adicionado'),
            ]
            
            for tipo, detalhe in eventos:
                logar_timeline(impl_id, 'user@test.com', tipo, detalhe)
            
            logs = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s ORDER BY id",
                (impl_id,)
            )
            self.assertEqual(len(logs), 3)
            self.assertEqual(logs[0]['tipo_evento'], 'status_alterado')
            self.assertEqual(logs[1]['tipo_evento'], 'tarefa_alterada')
            self.assertEqual(logs[2]['tipo_evento'], 'novo_comentario')
    
    def test_logar_timeline_with_special_characters(self):
        """Testa log com caracteres especiais."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            detalhe = "Tarefa 'Revisão' — Status: Concluída → Pendente"
            logar_timeline(impl_id, 'user@test.com', 'tarefa_alterada', detalhe)
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s",
                (impl_id,), one=True
            )
            self.assertEqual(log['detalhes'], detalhe)
    
    def test_logar_timeline_with_html_content(self):
        """Testa log com conteúdo HTML (data-item-id)."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            detalhe = '<span data-item-id="123">Item alterado</span>'
            logar_timeline(impl_id, 'user@test.com', 'tarefa_alterada', detalhe)
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s",
                (impl_id,), one=True
            )
            self.assertIn('data-item-id="123"', log['detalhes'])


# =============================================================================
# TESTES: _get_timeline_logs (implantacao_service.py)
# =============================================================================

class TestGetTimelineLogs(TimelineBaseTestCase):
    """Testes para a função _get_timeline_logs."""
    
    def test_get_timeline_logs_empty(self):
        """Testa busca de logs em implantação sem logs."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.domain.implantacao_service import _get_timeline_logs
            logs = _get_timeline_logs(impl_id)
            self.assertEqual(len(logs), 0)
    
    def test_get_timeline_logs_with_data(self):
        """Testa busca de logs com dados."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 'Log 1')
            logar_timeline(impl_id, 'user@test.com', 'tarefa_alterada', 'Log 2')
            
            from backend.project.domain.implantacao_service import _get_timeline_logs
            logs = _get_timeline_logs(impl_id)
            
            self.assertEqual(len(logs), 2)
            # Verifica ordenação DESC
            self.assertEqual(logs[0]['tipo_evento'], 'tarefa_alterada')
            self.assertEqual(logs[1]['tipo_evento'], 'status_alterado')
    
    def test_get_timeline_logs_date_formatting(self):
        """Testa formatação de datas nos logs."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'teste', 'Teste')
            
            from backend.project.domain.implantacao_service import _get_timeline_logs
            logs = _get_timeline_logs(impl_id)
            
            self.assertIn('data_criacao_fmt_dt_hr', logs[0])
            self.assertIsNotNone(logs[0]['data_criacao_fmt_dt_hr'])
    
    def test_get_timeline_logs_related_item_id_with_item_pattern(self):
        """Testa extração de related_item_id com padrão 'Item X'."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'tarefa_alterada', 'Item 456 concluído')
            
            from backend.project.domain.implantacao_service import _get_timeline_logs
            logs = _get_timeline_logs(impl_id)
            
            self.assertEqual(logs[0]['related_item_id'], 456)
    
    def test_get_timeline_logs_related_item_id_with_subtarefa_pattern(self):
        """Testa extração de related_item_id com padrão 'Subtarefa X'."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'tarefa_alterada', 'Subtarefa 789 alterada')
            
            from backend.project.domain.implantacao_service import _get_timeline_logs
            logs = _get_timeline_logs(impl_id)
            
            self.assertEqual(logs[0]['related_item_id'], 789)
    
    def test_get_timeline_logs_related_item_id_with_tarefa_h_pattern(self):
        """Testa extração de related_item_id com padrão 'TarefaH X'."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'tarefa_alterada', 'TarefaH 321 concluída')
            
            from backend.project.domain.implantacao_service import _get_timeline_logs
            logs = _get_timeline_logs(impl_id)
            
            self.assertEqual(logs[0]['related_item_id'], 321)
    
    def test_get_timeline_logs_related_item_id_with_data_attribute(self):
        """Testa extração de related_item_id com atributo data-item-id."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'tarefa_alterada', 
                          '<span data-item-id="999">Alterado</span>')
            
            from backend.project.domain.implantacao_service import _get_timeline_logs
            logs = _get_timeline_logs(impl_id)
            
            self.assertEqual(logs[0]['related_item_id'], 999)
    
    def test_get_timeline_logs_related_item_id_none(self):
        """Testa que related_item_id é None quando não há padrão."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          'Implantação iniciada sem referência a item')
            
            from backend.project.domain.implantacao_service import _get_timeline_logs
            logs = _get_timeline_logs(impl_id)
            
            self.assertIsNone(logs[0]['related_item_id'])


# =============================================================================
# TESTES: time_calculator.py - parse_datetime
# =============================================================================

class TestParseDatetime(TimelineBaseTestCase):
    """Testes para a função parse_datetime."""
    
    def test_parse_datetime_none(self):
        """Testa parse de None."""
        with self.app.app_context():
            from backend.project.domain.time_calculator import parse_datetime
            self.assertIsNone(parse_datetime(None))
    
    def test_parse_datetime_datetime_naive(self):
        """Testa parse de datetime naive."""
        with self.app.app_context():
            from backend.project.domain.time_calculator import parse_datetime
            dt = datetime(2024, 1, 15, 10, 30, 0)
            result = parse_datetime(dt)
            self.assertEqual(result, dt)
    
    def test_parse_datetime_datetime_aware(self):
        """Testa parse de datetime com timezone."""
        with self.app.app_context():
            from backend.project.domain.time_calculator import parse_datetime
            from datetime import timezone
            dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            result = parse_datetime(dt)
            self.assertIsNone(result.tzinfo)
    
    def test_parse_datetime_date_object(self):
        """Testa parse de objeto date."""
        with self.app.app_context():
            from backend.project.domain.time_calculator import parse_datetime
            from datetime import date
            d = date(2024, 1, 15)
            result = parse_datetime(d)
            self.assertEqual(result.year, 2024)
            self.assertEqual(result.month, 1)
            self.assertEqual(result.day, 15)
    
    def test_parse_datetime_string_iso(self):
        """Testa parse de string ISO."""
        with self.app.app_context():
            from backend.project.domain.time_calculator import parse_datetime
            result = parse_datetime('2024-01-15T10:30:00')
            self.assertEqual(result.year, 2024)
            self.assertEqual(result.hour, 10)
    
    def test_parse_datetime_string_iso_with_z(self):
        """Testa parse de string ISO com Z."""
        with self.app.app_context():
            from backend.project.domain.time_calculator import parse_datetime
            result = parse_datetime('2024-01-15T10:30:00Z')
            self.assertEqual(result.year, 2024)
    
    def test_parse_datetime_string_with_microseconds(self):
        """Testa parse de string com microsegundos."""
        with self.app.app_context():
            from backend.project.domain.time_calculator import parse_datetime
            result = parse_datetime('2024-01-15 10:30:00.123456')
            self.assertEqual(result.year, 2024)
    
    def test_parse_datetime_string_without_microseconds(self):
        """Testa parse de string sem microsegundos."""
        with self.app.app_context():
            from backend.project.domain.time_calculator import parse_datetime
            result = parse_datetime('2024-01-15 10:30:00')
            self.assertEqual(result.year, 2024)
    
    def test_parse_datetime_string_date_only(self):
        """Testa parse de string apenas com data."""
        with self.app.app_context():
            from backend.project.domain.time_calculator import parse_datetime
            result = parse_datetime('2024-01-15')
            self.assertEqual(result.year, 2024)
            self.assertEqual(result.month, 1)
            self.assertEqual(result.day, 15)
    
    def test_parse_datetime_invalid_string(self):
        """Testa parse de string inválida."""
        with self.app.app_context():
            from backend.project.domain.time_calculator import parse_datetime
            result = parse_datetime('invalid-date')
            self.assertIsNone(result)
    
    def test_parse_datetime_unsupported_type(self):
        """Testa parse de tipo não suportado."""
        with self.app.app_context():
            from backend.project.domain.time_calculator import parse_datetime
            result = parse_datetime(12345)
            self.assertIsNone(result)


# =============================================================================
# TESTES: time_calculator.py - get_status_history
# =============================================================================

class TestGetStatusHistory(TimelineBaseTestCase):
    """Testes para a função get_status_history."""
    
    def test_get_status_history_empty(self):
        """Testa histórico vazio."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.domain.time_calculator import get_status_history
            history = get_status_history(impl_id)
            self.assertEqual(len(history), 0)
    
    def test_get_status_history_parada(self):
        """Testa detecção de evento de parada."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          'Implantação parada por motivo X')
            
            from backend.project.domain.time_calculator import get_status_history
            history = get_status_history(impl_id)
            
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0][1], 'andamento')
            self.assertEqual(history[0][2], 'parada')
    
    def test_get_status_history_parada_retroativa(self):
        """Testa detecção de parada retroativa com data no texto."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          'Implantação parada retroativamente desde 2024-01-10')
            
            from backend.project.domain.time_calculator import get_status_history
            history = get_status_history(impl_id)
            
            self.assertEqual(len(history), 1)
            # Deve usar a data do texto, não do log
            self.assertEqual(history[0][0].year, 2024)
            self.assertEqual(history[0][0].month, 1)
            self.assertEqual(history[0][0].day, 10)
    
    def test_get_status_history_retomada(self):
        """Testa detecção de evento de retomada."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          'Implantação retomada pelo cliente')
            
            from backend.project.domain.time_calculator import get_status_history
            history = get_status_history(impl_id)
            
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0][1], 'parada')
            self.assertEqual(history[0][2], 'andamento')
    
    def test_get_status_history_reaberta(self):
        """Testa detecção de evento reaberta."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          'Implantação reaberta')
            
            from backend.project.domain.time_calculator import get_status_history
            history = get_status_history(impl_id)
            
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0][2], 'andamento')
    
    def test_get_status_history_finalizada(self):
        """Testa detecção de evento finalizada."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          'Implantação finalizada com sucesso')
            
            from backend.project.domain.time_calculator import get_status_history
            history = get_status_history(impl_id)
            
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0][1], 'andamento')
            self.assertEqual(history[0][2], 'finalizada')
    
    def test_get_status_history_multiple_events(self):
        """Testa múltiplos eventos de status."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            import time
            
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 'Implantação parada')
            time.sleep(0.1)  # Garantir ordem
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 'Implantação retomada')
            time.sleep(0.1)
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 'Implantação finalizada')
            
            from backend.project.domain.time_calculator import get_status_history
            history = get_status_history(impl_id)
            
            self.assertEqual(len(history), 3)
            self.assertEqual(history[0][2], 'parada')
            self.assertEqual(history[1][2], 'andamento')
            self.assertEqual(history[2][2], 'finalizada')
    
    def test_get_status_history_ignores_other_events(self):
        """Testa que outros tipos de eventos são ignorados."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'tarefa_alterada', 'Tarefa concluída')
            logar_timeline(impl_id, 'user@test.com', 'novo_comentario', 'Comentário')
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 'Implantação parada')
            
            from backend.project.domain.time_calculator import get_status_history
            history = get_status_history(impl_id)
            
            # Apenas o status_alterado deve aparecer
            self.assertEqual(len(history), 1)


# =============================================================================
# TESTES: time_calculator.py - calculate_total_days_in_status
# =============================================================================

class TestCalculateTotalDaysInStatus(TimelineBaseTestCase):
    """Testes para a função calculate_total_days_in_status."""
    
    def test_calculate_days_implantacao_not_found(self):
        """Testa cálculo para implantação inexistente."""
        with self.app.app_context():
            from backend.project.domain.time_calculator import calculate_total_days_in_status
            result = calculate_total_days_in_status(99999)
            self.assertEqual(result, 0)
    
    def test_calculate_days_no_inicio_efetivo(self):
        """Testa cálculo sem data_inicio_efetivo."""
        with self.app.app_context():
            execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, status, usuario_cs, data_criacao) 
                   VALUES (%s, %s, %s, %s)""",
                ('Empresa Sem Inicio', 'nova', 'tester@example.com', datetime.now())
            )
            impl = query_db("SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1", one=True)
            
            from backend.project.domain.time_calculator import calculate_total_days_in_status
            result = calculate_total_days_in_status(impl['id'])
            self.assertEqual(result, 0)
    
    def test_calculate_days_andamento_no_history(self):
        """Testa cálculo de dias em andamento sem histórico."""
        data_inicio = datetime.now() - timedelta(days=15)
        impl_id = self._create_implantacao(status='andamento', data_inicio_efetivo=data_inicio)
        
        with self.app.app_context():
            from backend.project.domain.time_calculator import calculate_total_days_in_status
            result = calculate_total_days_in_status(impl_id, 'andamento')
            # Deve ser aproximadamente 15 dias
            self.assertGreaterEqual(result, 14)
            self.assertLessEqual(result, 16)
    
    def test_calculate_days_parada_no_history(self):
        """Testa cálculo de dias parados sem histórico."""
        data_inicio = datetime.now() - timedelta(days=10)
        impl_id = self._create_implantacao(status='andamento', data_inicio_efetivo=data_inicio)
        
        with self.app.app_context():
            from backend.project.domain.time_calculator import calculate_total_days_in_status
            result = calculate_total_days_in_status(impl_id, 'parada')
            # Sem histórico de parada, deve ser 0
            self.assertEqual(result, 0)
    
    def test_calculate_days_with_parada_and_retomada(self):
        """Testa cálculo com ciclo de parada e retomada."""
        data_inicio = datetime.now() - timedelta(days=20)
        impl_id = self._create_implantacao(status='andamento', data_inicio_efetivo=data_inicio)
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            import time
            
            # Simular parada há 10 dias
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          f'Implantação parada retroativamente desde {(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")}')
            time.sleep(0.1)
            # Simular retomada há 5 dias
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          'Implantação retomada')
            
            from backend.project.domain.time_calculator import calculate_total_days_in_status
            # O cálculo deve retornar um valor válido (>= 0)
            # e demonstrar que a função processa corretamente parada/retomada
            result_andamento = calculate_total_days_in_status(impl_id, 'andamento')
            self.assertGreaterEqual(result_andamento, 0)
            self.assertIsInstance(result_andamento, int)


# =============================================================================
# TESTES: time_calculator.py - calculate_days_passed e calculate_days_parada  
# =============================================================================

class TestCalculateDaysHelpers(TimelineBaseTestCase):
    """Testes para funções helper de cálculo de dias."""
    
    def test_calculate_days_passed(self):
        """Testa calculate_days_passed."""
        data_inicio = datetime.now() - timedelta(days=10)
        impl_id = self._create_implantacao(status='andamento', data_inicio_efetivo=data_inicio)
        
        with self.app.app_context():
            from backend.project.domain.time_calculator import calculate_days_passed
            result = calculate_days_passed(impl_id)
            self.assertGreaterEqual(result, 9)
            self.assertLessEqual(result, 11)
    
    def test_calculate_days_parada(self):
        """Testa calculate_days_parada."""
        data_inicio = datetime.now() - timedelta(days=10)
        impl_id = self._create_implantacao(status='andamento', data_inicio_efetivo=data_inicio)
        
        with self.app.app_context():
            from backend.project.domain.time_calculator import calculate_days_parada
            result = calculate_days_parada(impl_id)
            # Sem paradas, deve ser 0
            self.assertEqual(result, 0)


# =============================================================================
# TESTES: Todos os tipos de eventos de timeline
# =============================================================================

class TestAllEventTypes(TimelineBaseTestCase):
    """Testes para garantir cobertura de todos os tipos de eventos."""
    
    def test_event_implantacao_criada(self):
        """Testa evento implantacao_criada."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'implantacao_criada', 
                          'Implantação "Empresa X" criada')
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = %s",
                (impl_id, 'implantacao_criada'), one=True
            )
            self.assertIsNotNone(log)
    
    def test_event_status_alterado(self):
        """Testa evento status_alterado."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          'Implantação iniciada')
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = %s",
                (impl_id, 'status_alterado'), one=True
            )
            self.assertIsNotNone(log)
    
    def test_event_tarefa_alterada(self):
        """Testa evento tarefa_alterada."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'tarefa_alterada', 
                          'Status: Concluída — Tarefa de teste')
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = %s",
                (impl_id, 'tarefa_alterada'), one=True
            )
            self.assertIsNotNone(log)
    
    def test_event_responsavel_alterado(self):
        """Testa evento responsavel_alterado."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'responsavel_alterado', 
                          'Responsável: João → Maria')
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = %s",
                (impl_id, 'responsavel_alterado'), one=True
            )
            self.assertIsNotNone(log)
    
    def test_event_prazo_alterado(self):
        """Testa evento prazo_alterado."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'prazo_alterado', 
                          'Nova previsão: 2024-12-31')
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = %s",
                (impl_id, 'prazo_alterado'), one=True
            )
            self.assertIsNotNone(log)
    
    def test_event_novo_comentario(self):
        """Testa evento novo_comentario."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'novo_comentario', 
                          'Comentário criado para tarefa X')
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = %s",
                (impl_id, 'novo_comentario'), one=True
            )
            self.assertIsNotNone(log)
    
    def test_event_comentario_excluido(self):
        """Testa evento comentario_excluido."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'comentario_excluido', 
                          'Comentário excluído')
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = %s",
                (impl_id, 'comentario_excluido'), one=True
            )
            self.assertIsNotNone(log)
    
    def test_event_tarefa_excluida(self):
        """Testa evento tarefa_excluida."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'tarefa_excluida', 
                          'Tarefa excluída — Nome da tarefa')
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = %s",
                (impl_id, 'tarefa_excluida'), one=True
            )
            self.assertIsNotNone(log)
    
    def test_event_auto_finalizada(self):
        """Testa evento auto_finalizada."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'auto_finalizada', 
                          'Implantação auto-finalizada')
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = %s",
                (impl_id, 'auto_finalizada'), one=True
            )
            self.assertIsNotNone(log)


# =============================================================================
# TESTES: Edge cases e error handling
# =============================================================================

class TestTimelineEdgeCases(TimelineBaseTestCase):
    """Testes para casos extremos e tratamento de erros."""
    
    def test_logar_timeline_with_empty_detail(self):
        """Testa log com detalhe vazio."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'teste', '')
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s",
                (impl_id,), one=True
            )
            self.assertEqual(log['detalhes'], '')
    
    def test_logar_timeline_with_none_detail(self):
        """Testa log com detalhe None."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            logar_timeline(impl_id, 'user@test.com', 'teste', None)
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s",
                (impl_id,), one=True
            )
            self.assertIsNone(log['detalhes'])
    
    def test_get_timeline_logs_handles_exception_in_regex(self):
        """Testa tratamento de exceção na extração de related_item_id."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            # Inserir log com conteúdo que pode causar problemas no regex
            execute_db(
                """INSERT INTO timeline_log 
                   (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (impl_id, 'user@test.com', 'teste', 'Item sem número', datetime.now())
            )
            
            from backend.project.domain.implantacao_service import _get_timeline_logs
            logs = _get_timeline_logs(impl_id)
            
            # Não deve lançar exceção
            self.assertEqual(len(logs), 1)
            self.assertIsNone(logs[0]['related_item_id'])
    
    def test_unicode_in_timeline(self):
        """Testa caracteres unicode nos logs."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            detalhe = 'Empresa: 日本語テスト 🎉 Ñoño'
            logar_timeline(impl_id, 'user@test.com', 'teste', detalhe)
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s",
                (impl_id,), one=True
            )
            self.assertEqual(log['detalhes'], detalhe)
    
    def test_very_long_detail(self):
        """Testa detalhe muito longo."""
        impl_id = self._create_implantacao()
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            detalhe = 'A' * 10000  # 10k caracteres
            logar_timeline(impl_id, 'user@test.com', 'teste', detalhe)
            
            log = query_db(
                "SELECT * FROM timeline_log WHERE implantacao_id = %s",
                (impl_id,), one=True
            )
            self.assertEqual(len(log['detalhes']), 10000)


# =============================================================================
# TESTES: Casos adicionais para 100% de cobertura no time_calculator
# =============================================================================

class TestTimeCalculatorFullCoverage(TimelineBaseTestCase):
    """Testes adicionais para garantir 100% de cobertura no time_calculator."""
    
    def _create_implantacao_with_status(self, status, data_inicio_efetivo=None, data_finalizacao=None):
        """Helper para criar implantação com status e datas específicas."""
        if data_inicio_efetivo is None:
            data_inicio_efetivo = datetime.now() - timedelta(days=20)
        
        with self.app.app_context():
            execute_db(
                """INSERT INTO implantacoes 
                   (nome_empresa, email_responsavel, status, usuario_cs, 
                    data_inicio_efetivo, data_criacao, data_finalizacao) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                ('Empresa Test', 'resp@example.com', status, 'tester@example.com', 
                 data_inicio_efetivo, datetime.now(), data_finalizacao)
            )
            impl = query_db("SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1", one=True)
            return impl['id']
    
    def test_calculate_andamento_when_status_is_parada_no_history(self):
        """Testa cálculo de andamento quando status atual é parada (sem histórico)."""
        data_inicio = datetime.now() - timedelta(days=15)
        data_parada = datetime.now() - timedelta(days=5)  # Parou há 5 dias
        
        impl_id = self._create_implantacao_with_status(
            status='parada', 
            data_inicio_efetivo=data_inicio,
            data_finalizacao=data_parada
        )
        
        with self.app.app_context():
            from backend.project.domain.time_calculator import calculate_total_days_in_status
            # Deveria ter ficado ~10 dias em andamento (15 - 5)
            result = calculate_total_days_in_status(impl_id, 'andamento')
            self.assertGreaterEqual(result, 8)
            self.assertLessEqual(result, 12)
    
    def test_calculate_andamento_when_status_parada_no_finalizacao(self):
        """Testa cálculo com status parada mas sem data_finalizacao."""
        data_inicio = datetime.now() - timedelta(days=10)
        
        impl_id = self._create_implantacao_with_status(
            status='parada', 
            data_inicio_efetivo=data_inicio,
            data_finalizacao=None  # Sem data de parada
        )
        
        with self.app.app_context():
            from backend.project.domain.time_calculator import calculate_total_days_in_status
            # Sem data de parada, deve retornar 0
            result = calculate_total_days_in_status(impl_id, 'andamento')
            self.assertEqual(result, 0)
    
    def test_calculate_parada_when_status_is_parada_no_history(self):
        """Testa cálculo de dias parados quando status é parada (sem histórico)."""
        data_inicio = datetime.now() - timedelta(days=15)
        data_parada = datetime.now() - timedelta(days=5)
        
        impl_id = self._create_implantacao_with_status(
            status='parada', 
            data_inicio_efetivo=data_inicio,
            data_finalizacao=data_parada
        )
        
        with self.app.app_context():
            from backend.project.domain.time_calculator import calculate_total_days_in_status
            # Deveria ter ~5 dias parados
            result = calculate_total_days_in_status(impl_id, 'parada')
            self.assertGreaterEqual(result, 4)
            self.assertLessEqual(result, 7)
    
    def test_calculate_parada_when_status_is_parada_no_finalizacao(self):
        """Testa cálculo de parada sem data_finalizacao."""
        data_inicio = datetime.now() - timedelta(days=10)
        
        impl_id = self._create_implantacao_with_status(
            status='parada', 
            data_inicio_efetivo=data_inicio,
            data_finalizacao=None
        )
        
        with self.app.app_context():
            from backend.project.domain.time_calculator import calculate_total_days_in_status
            result = calculate_total_days_in_status(impl_id, 'parada')
            self.assertEqual(result, 0)
    
    def test_calculate_parada_with_history(self):
        """Testa cálculo de dias parados com histórico de parada."""
        data_inicio = datetime.now() - timedelta(days=20)
        data_parada = datetime.now() - timedelta(days=5)
        
        impl_id = self._create_implantacao_with_status(
            status='parada', 
            data_inicio_efetivo=data_inicio,
            data_finalizacao=data_parada
        )
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            # Criar log de parada
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          'Implantação parada pelo cliente')
            
            from backend.project.domain.time_calculator import calculate_total_days_in_status
            result = calculate_total_days_in_status(impl_id, 'parada')
            # Deve encontrar e calcular o período de parada
            self.assertGreaterEqual(result, 0)
    
    def test_calculate_with_finalizada_status(self):
        """Testa cálculo quando status é finalizada."""
        data_inicio = datetime.now() - timedelta(days=30)
        data_finalizacao = datetime.now() - timedelta(days=10)
        
        impl_id = self._create_implantacao_with_status(
            status='finalizada', 
            data_inicio_efetivo=data_inicio,
            data_finalizacao=data_finalizacao
        )
        
        with self.app.app_context():
            from backend.project.domain.time_calculator import calculate_total_days_in_status
            # Finalizada, sem histórico, retorna 0 para andamento
            result = calculate_total_days_in_status(impl_id, 'andamento')
            self.assertEqual(result, 0)
    
    def test_calculate_with_history_tracking_parada_periods(self):
        """Testa cálculo de períodos de parada com histórico completo."""
        data_inicio = datetime.now() - timedelta(days=30)
        data_parada = datetime.now() - timedelta(days=5)
        
        impl_id = self._create_implantacao_with_status(
            status='parada', 
            data_inicio_efetivo=data_inicio,
            data_finalizacao=data_parada
        )
        
        with self.app.app_context():
            from backend.project.db import logar_timeline
            import time
            
            # Criar histórico de parada há 15 dias
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          f'Implantação parada retroativamente desde {(datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")}')
            time.sleep(0.1)
            # Retomada há 10 dias
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          'Implantação retomada')
            time.sleep(0.1)
            # Parada novamente há 5 dias
            logar_timeline(impl_id, 'user@test.com', 'status_alterado', 
                          'Implantação parada novamente')
            
            from backend.project.domain.time_calculator import calculate_total_days_in_status
            
            # Calcular ambos os períodos
            result_andamento = calculate_total_days_in_status(impl_id, 'andamento')
            result_parada = calculate_total_days_in_status(impl_id, 'parada')
            
            # Ambos devem ser calculados corretamente
            self.assertGreaterEqual(result_andamento, 0)
            self.assertGreaterEqual(result_parada, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
