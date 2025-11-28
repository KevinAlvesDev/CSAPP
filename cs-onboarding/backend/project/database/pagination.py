from flask import request


class Pagination:
    """
    Classe helper para paginação de resultados.
    
    Uso:
        pagination = Pagination(page=1, per_page=50, total=1000)
        
        # Propriedades úteis:
        pagination.has_prev  # True se há página anterior
        pagination.has_next  # True se há próxima página
        pagination.pages     # Total de páginas
        pagination.offset    # Offset para SQL LIMIT/OFFSET
    """
    
    def __init__(self, page=1, per_page=50, total=0):
        """
        Inicializa objeto de paginação.
        
        Args:
            page: Número da página atual (1-based)
            per_page: Itens por página
            total: Total de itens
        """
        self.page = max(1, page)                                
        self.per_page = max(1, per_page)                                  
        self.total = max(0, total)                               
        
    @property
    def pages(self):
        """Retorna o número total de páginas."""
        if self.per_page == 0:
            return 0
        return (self.total + self.per_page - 1) // self.per_page
    
    @property
    def has_prev(self):
        """Retorna True se há página anterior."""
        return self.page > 1
    
    @property
    def has_next(self):
        """Retorna True se há próxima página."""
        return self.page < self.pages
    
    @property
    def prev_num(self):
        """Retorna o número da página anterior (ou None)."""
        return self.page - 1 if self.has_prev else None
    
    @property
    def next_num(self):
        """Retorna o número da próxima página (ou None)."""
        return self.page + 1 if self.has_next else None
    
    @property
    def offset(self):
        """Retorna o offset para SQL LIMIT/OFFSET."""
        return (self.page - 1) * self.per_page
    
    @property
    def limit(self):
        """Retorna o limit para SQL LIMIT/OFFSET."""
        return self.per_page
    
    def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
        """
        Itera sobre os números de página para exibir na UI.
        
        Exemplo: [1, 2, None, 8, 9, 10, 11, 12, None, 99, 100]
        Onde None representa "..."
        
        Args:
            left_edge: Páginas no início
            left_current: Páginas à esquerda da atual
            right_current: Páginas à direita da atual
            right_edge: Páginas no final
        """
        last = 0
        for num in range(1, self.pages + 1):
            if (
                num <= left_edge
                or (self.page - left_current <= num <= self.page + right_current)
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num
    
    def to_dict(self):
        """Retorna representação em dicionário."""
        return {
            'page': self.page,
            'per_page': self.per_page,
            'total': self.total,
            'pages': self.pages,
            'has_prev': self.has_prev,
            'has_next': self.has_next,
            'prev_num': self.prev_num,
            'next_num': self.next_num,
            'offset': self.offset,
            'limit': self.limit
        }


def get_page_args(page_param='page', per_page_param='per_page', default_per_page=50, max_per_page=200):
    """
    Extrai argumentos de paginação da request.
    
    Args:
        page_param: Nome do parâmetro de página na query string
        per_page_param: Nome do parâmetro de itens por página
        default_per_page: Valor padrão de itens por página
        max_per_page: Máximo de itens por página (segurança)
    
    Returns:
        Tupla (page, per_page)
    
    Exemplo:
        # URL: /dashboard?page=2&per_page=100
        page, per_page = get_page_args()
        # page = 2, per_page = 100
    """
    try:
        page = int(request.args.get(page_param, 1))
        page = max(1, page)                
    except (TypeError, ValueError):
        page = 1
    
    try:
        per_page = int(request.args.get(per_page_param, default_per_page))
        per_page = max(1, min(per_page, max_per_page))                          
    except (TypeError, ValueError):
        per_page = default_per_page
    
    return page, per_page
