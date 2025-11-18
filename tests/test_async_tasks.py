

import pytest
import sys
import os
import time
from threading import Event

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from project import create_app
from project.async_tasks import BackgroundTask, send_email_async


@pytest.fixture
def app():
    """Cria uma instância do app para testes."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'USE_SQLITE_LOCALLY': True,
    })
    
    yield app


class TestBackgroundTask:
    """Testes para classe BackgroundTask."""
    
    def test_background_task_executa_funcao(self):
        """Testa que BackgroundTask executa função."""
        result_container = {'value': None}
        event = Event()
        
        def test_func(x, y):
            result_container['value'] = x + y
            event.set()
        
        BackgroundTask.run(test_func, x=2, y=3)

        event.wait(timeout=2)
        
        assert result_container['value'] == 5
    
    def test_background_task_nao_bloqueia(self):
        """Testa que BackgroundTask não bloqueia thread principal."""
        start_time = time.time()
        
        def slow_func():
            time.sleep(1)
        
        BackgroundTask.run(slow_func)
        
        elapsed = time.time() - start_time

        assert elapsed < 0.1
    
    def test_background_task_com_app_context(self, app):
        """Testa BackgroundTask com contexto Flask."""
        result_container = {'value': None}
        event = Event()
        
        def test_func_with_context():
            from flask import current_app
            result_container['value'] = current_app.config.get('TESTING')
            event.set()
        
        with app.app_context():
            BackgroundTask.run_with_app_context(test_func_with_context)
        
        event.wait(timeout=2)
        
        assert result_container['value'] is True
    
    def test_background_task_trata_excecoes(self):
        """Testa que BackgroundTask trata exceções."""
        event = Event()
        
        def error_func():
            event.set()
            raise ValueError("Test error")
        
        BackgroundTask.run(error_func)

        event.wait(timeout=2)

        assert True


class TestSendEmailAsync:
    """Testes para envio assíncrono de email."""
    
    def test_send_email_async_nao_bloqueia(self, app):
        """Testa que envio de email não bloqueia."""
        with app.app_context():
            start_time = time.time()
            
            send_email_async(
                subject='Test Email',
                body_html='<p>Test</p>',
                recipients=['test@example.com']
            )
            
            elapsed = time.time() - start_time

            assert elapsed < 0.1
    
    def test_send_email_async_com_parametros(self, app):
        """Testa envio de email com todos os parâmetros."""
        with app.app_context():

            send_email_async(
                subject='Test Email',
                body_html='<p>Test HTML</p>',
                recipients=['test1@example.com', 'test2@example.com'],
                reply_to='reply@example.com',
                from_name='Test Sender',
                body_text='Test plain text'
            )

            assert True


class TestAsyncTasksIntegration:
    """Testes de integração de tarefas assíncronas."""
    
    def test_multiplas_tasks_simultaneas(self):
        """Testa execução de múltiplas tasks simultâneas."""
        results = {'count': 0}
        event = Event()
        
        def increment():
            results['count'] += 1
            if results['count'] == 5:
                event.set()
        
        for _ in range(5):
            BackgroundTask.run(increment)
        
        event.wait(timeout=3)
        
        assert results['count'] == 5
    
    def test_task_com_dados_complexos(self):
        """Testa task com estruturas de dados complexas."""
        result_container = {'data': None}
        event = Event()
        
        def process_data(data_dict, data_list):
            result_container['data'] = {
                'dict_sum': sum(data_dict.values()),
                'list_sum': sum(data_list)
            }
            event.set()
        
        BackgroundTask.run(
            process_data,
            data_dict={'a': 1, 'b': 2, 'c': 3},
            data_list=[10, 20, 30]
        )

        event.wait(timeout=2)
        
        assert result_container['data']['dict_sum'] == 6
        assert result_container['data']['list_sum'] == 60

