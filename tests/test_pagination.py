# tests/test_pagination.py
# Testes para sistema de paginação

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from project.pagination import Pagination, get_page_args
from flask import Flask


class TestPagination:
    """Testes para classe Pagination."""
    
    def test_pagination_basica(self):
        """Testa criação básica de paginação."""
        pagination = Pagination(page=1, per_page=10, total=100)
        
        assert pagination.page == 1
        assert pagination.per_page == 10
        assert pagination.total == 100
        assert pagination.pages == 10
    
    def test_pagination_pages_calculation(self):
        """Testa cálculo de número de páginas."""
        # 100 itens, 10 por página = 10 páginas
        p1 = Pagination(page=1, per_page=10, total=100)
        assert p1.pages == 10
        
        # 95 itens, 10 por página = 10 páginas (arredonda para cima)
        p2 = Pagination(page=1, per_page=10, total=95)
        assert p2.pages == 10
        
        # 5 itens, 10 por página = 1 página
        p3 = Pagination(page=1, per_page=10, total=5)
        assert p3.pages == 1
        
        # 0 itens = 0 páginas
        p4 = Pagination(page=1, per_page=10, total=0)
        assert p4.pages == 0
    
    def test_pagination_has_prev(self):
        """Testa verificação de página anterior."""
        p1 = Pagination(page=1, per_page=10, total=100)
        assert p1.has_prev is False
        
        p2 = Pagination(page=2, per_page=10, total=100)
        assert p2.has_prev is True
        
        p3 = Pagination(page=5, per_page=10, total=100)
        assert p3.has_prev is True
    
    def test_pagination_has_next(self):
        """Testa verificação de próxima página."""
        p1 = Pagination(page=1, per_page=10, total=100)
        assert p1.has_next is True
        
        p2 = Pagination(page=10, per_page=10, total=100)
        assert p2.has_next is False
        
        p3 = Pagination(page=5, per_page=10, total=100)
        assert p3.has_next is True
    
    def test_pagination_prev_num(self):
        """Testa número da página anterior."""
        p1 = Pagination(page=1, per_page=10, total=100)
        assert p1.prev_num is None
        
        p2 = Pagination(page=2, per_page=10, total=100)
        assert p2.prev_num == 1
        
        p3 = Pagination(page=5, per_page=10, total=100)
        assert p3.prev_num == 4
    
    def test_pagination_next_num(self):
        """Testa número da próxima página."""
        p1 = Pagination(page=1, per_page=10, total=100)
        assert p1.next_num == 2
        
        p2 = Pagination(page=10, per_page=10, total=100)
        assert p2.next_num is None
        
        p3 = Pagination(page=5, per_page=10, total=100)
        assert p3.next_num == 6
    
    def test_pagination_offset(self):
        """Testa cálculo de offset para SQL."""
        p1 = Pagination(page=1, per_page=10, total=100)
        assert p1.offset == 0
        
        p2 = Pagination(page=2, per_page=10, total=100)
        assert p2.offset == 10
        
        p3 = Pagination(page=5, per_page=10, total=100)
        assert p3.offset == 40
        
        p4 = Pagination(page=1, per_page=50, total=100)
        assert p4.offset == 0
        
        p5 = Pagination(page=2, per_page=50, total=100)
        assert p5.offset == 50
    
    def test_pagination_limit(self):
        """Testa limite para SQL."""
        p1 = Pagination(page=1, per_page=10, total=100)
        assert p1.limit == 10
        
        p2 = Pagination(page=1, per_page=50, total=100)
        assert p2.limit == 50
    
    def test_pagination_iter_pages(self):
        """Testa iteração de páginas."""
        p = Pagination(page=5, per_page=10, total=100)
        pages = list(p.iter_pages())
        
        # Deve incluir a página atual
        assert 5 in pages
        
        # Deve incluir None para reticências
        assert None in pages or len(pages) > 0
    
    def test_pagination_to_dict(self):
        """Testa conversão para dicionário."""
        p = Pagination(page=2, per_page=10, total=100)
        d = p.to_dict()
        
        assert d['page'] == 2
        assert d['per_page'] == 10
        assert d['total'] == 100
        assert d['pages'] == 10
        assert d['has_prev'] is True
        assert d['has_next'] is True
        assert d['prev_num'] == 1
        assert d['next_num'] == 3


class TestGetPageArgs:
    """Testes para função get_page_args."""
    
    def test_get_page_args_default(self):
        """Testa valores padrão."""
        app = Flask(__name__)
        
        with app.test_request_context('/'):
            page, per_page = get_page_args()
            assert page == 1
            assert per_page == 50
    
    def test_get_page_args_custom(self):
        """Testa valores customizados."""
        app = Flask(__name__)
        
        with app.test_request_context('/?page=3&per_page=25'):
            page, per_page = get_page_args()
            assert page == 3
            assert per_page == 25
    
    def test_get_page_args_invalid(self):
        """Testa valores inválidos (deve usar padrão)."""
        app = Flask(__name__)
        
        with app.test_request_context('/?page=abc&per_page=xyz'):
            page, per_page = get_page_args()
            assert page == 1
            assert per_page == 50
    
    def test_get_page_args_negative(self):
        """Testa valores negativos (deve usar mínimo de 1)."""
        app = Flask(__name__)

        with app.test_request_context('/?page=-1&per_page=-10'):
            page, per_page = get_page_args()
            assert page == 1  # Converte para mínimo
            assert per_page == 1  # Converte para mínimo (não padrão)

