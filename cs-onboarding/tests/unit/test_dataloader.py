"""
Testes unitários para o DataLoader.

Testa:
- ChecklistDataLoader: batch loading, indexação, filtros por tipo
- ComentariosDataLoader: carregamento em batch
- ImplantacaoDataLoader: carregamento combinado
"""

from unittest.mock import patch

from tests.fixtures import make_checklist_tree, make_comentario


class TestChecklistDataLoader:
    """Testes para o ChecklistDataLoader."""

    @patch("backend.project.common.dataloader.query_db")
    def test_loads_all_items_in_one_query(self, mock_query_db):
        """Verifica que o DataLoader faz apenas 1 query para tudo."""
        from backend.project.common.dataloader import ChecklistDataLoader

        mock_items = make_checklist_tree(implantacao_id=42)
        mock_query_db.return_value = mock_items

        loader = ChecklistDataLoader(42)
        items = loader.get_all_items()

        # Deve ter chamado query_db exatamente 1 vez
        assert mock_query_db.call_count == 1
        assert len(items) == len(mock_items)

    @patch("backend.project.common.dataloader.query_db")
    def test_get_fases(self, mock_query_db):
        """Testa busca de fases (items root sem parent)."""
        from backend.project.common.dataloader import ChecklistDataLoader

        mock_query_db.return_value = make_checklist_tree()

        loader = ChecklistDataLoader(1)
        fases = loader.get_fases()

        assert len(fases) == 1
        assert fases[0]["title"] == "Fase 1"
        assert fases[0]["tipo_item"] == "fase"

    @patch("backend.project.common.dataloader.query_db")
    def test_get_grupos(self, mock_query_db):
        """Testa busca de grupos dentro de uma fase."""
        from backend.project.common.dataloader import ChecklistDataLoader

        mock_query_db.return_value = make_checklist_tree()

        loader = ChecklistDataLoader(1)
        fases = loader.get_fases()
        grupos = loader.get_grupos(fases[0]["id"])

        assert len(grupos) == 2  # Grupo A e Grupo B
        assert all(g["tipo_item"] == "grupo" for g in grupos)

    @patch("backend.project.common.dataloader.query_db")
    def test_get_tarefas(self, mock_query_db):
        """Testa busca de tarefas dentro de um grupo."""
        from backend.project.common.dataloader import ChecklistDataLoader

        mock_query_db.return_value = make_checklist_tree()

        loader = ChecklistDataLoader(1)
        tarefas = loader.get_tarefas(2)  # Grupo A

        assert len(tarefas) == 2  # Tarefa 1 e Tarefa 2

    @patch("backend.project.common.dataloader.query_db")
    def test_get_subtarefas(self, mock_query_db):
        """Testa busca de subtarefas dentro de uma tarefa."""
        from backend.project.common.dataloader import ChecklistDataLoader

        mock_query_db.return_value = make_checklist_tree()

        loader = ChecklistDataLoader(1)
        subtarefas = loader.get_subtarefas(4)  # Tarefa 2

        assert len(subtarefas) == 2  # Subtarefa 2.1 e 2.2

    @patch("backend.project.common.dataloader.query_db")
    def test_progress_percentage(self, mock_query_db):
        """Testa cálculo de progresso."""
        from backend.project.common.dataloader import ChecklistDataLoader

        mock_query_db.return_value = make_checklist_tree()

        loader = ChecklistDataLoader(1)
        progress = loader.progress_percentage

        # 2 concluídas (Tarefa 1 + Subtarefa 2.2) de 5 leaf items
        # (Tarefa 1, Tarefa 2, Subtarefa 2.1, Subtarefa 2.2, Tarefa 3)
        # DataLoader conta tipo_item in {"tarefa", "subtarefa"} como leaves
        assert progress == 40.0

    @patch("backend.project.common.dataloader.query_db")
    def test_caches_after_first_load(self, mock_query_db):
        """Verifica que não refaz query após primeira carga."""
        from backend.project.common.dataloader import ChecklistDataLoader

        mock_query_db.return_value = make_checklist_tree()

        loader = ChecklistDataLoader(1)
        loader.get_fases()
        loader.get_grupos(1)
        loader.get_tarefas(2)
        loader.get_subtarefas(4)

        # Deve ter chamado query_db apenas 1 vez
        assert mock_query_db.call_count == 1

    @patch("backend.project.common.dataloader.query_db")
    def test_handles_empty_result(self, mock_query_db):
        """Testa comportamento com implantação sem items."""
        from backend.project.common.dataloader import ChecklistDataLoader

        mock_query_db.return_value = []

        loader = ChecklistDataLoader(999)
        assert loader.get_fases() == []
        assert loader.total_items == 0
        assert loader.progress_percentage == 0.0

    @patch("backend.project.common.dataloader.query_db")
    def test_handles_db_error(self, mock_query_db):
        """Testa tratamento de erro de banco."""
        from backend.project.common.dataloader import ChecklistDataLoader

        mock_query_db.side_effect = Exception("Connection lost")

        loader = ChecklistDataLoader(1)
        assert loader.get_fases() == []
        assert loader.total_items == 0


class TestComentariosDataLoader:
    """Testes para o ComentariosDataLoader."""

    @patch("backend.project.common.dataloader.query_db")
    def test_loads_all_comentarios_in_one_query(self, mock_query_db):
        """Verifica carregamento em batch."""
        from backend.project.common.dataloader import ComentariosDataLoader

        mock_query_db.return_value = [
            {**make_comentario(id=1, item_id=10), "autor_nome": "User", "autor_foto": None},
            {**make_comentario(id=2, item_id=10), "autor_nome": "User", "autor_foto": None},
            {**make_comentario(id=3, item_id=20), "autor_nome": "User 2", "autor_foto": None},
        ]

        loader = ComentariosDataLoader(1)
        by_item = loader.get_all()

        assert mock_query_db.call_count == 1
        assert len(by_item[10]) == 2
        assert len(by_item[20]) == 1

    @patch("backend.project.common.dataloader.query_db")
    def test_get_by_item(self, mock_query_db):
        """Testa busca de comentários por item."""
        from backend.project.common.dataloader import ComentariosDataLoader

        mock_query_db.return_value = [
            {**make_comentario(id=1, item_id=10), "autor_nome": "User", "autor_foto": None},
        ]

        loader = ComentariosDataLoader(1)
        comentarios = loader.get_by_item(10)

        assert len(comentarios) == 1
        assert loader.get_by_item(999) == []

    @patch("backend.project.common.dataloader.query_db")
    def test_total_comentarios(self, mock_query_db):
        """Testa contagem total."""
        from backend.project.common.dataloader import ComentariosDataLoader

        mock_query_db.return_value = [
            {**make_comentario(id=i, item_id=10 + (i % 3)), "autor_nome": "U", "autor_foto": None} for i in range(5)
        ]

        loader = ComentariosDataLoader(1)
        assert loader.total_comentarios == 5


class TestImplantacaoDataLoader:
    """Testes para o ImplantacaoDataLoader combinado."""

    @patch("backend.project.common.dataloader.query_db")
    def test_load_all_returns_complete_structure(self, mock_query_db):
        """Testa que load_all retorna a estrutura completa."""
        from backend.project.common.dataloader import ImplantacaoDataLoader

        # Primeira chamada: checklist items, segunda: comentários
        mock_query_db.side_effect = [
            make_checklist_tree(),  # checklist items
            [],  # comentários
        ]

        loader = ImplantacaoDataLoader(1)
        data = loader.load_all()

        assert "tarefas_agrupadas" in data
        assert "progress" in data
        assert "total_comentarios" in data
        assert "todos_modulos" in data

    @patch("backend.project.common.dataloader.query_db")
    def test_progress_in_load_all(self, mock_query_db):
        """Testa dados de progresso no resultado."""
        from backend.project.common.dataloader import ImplantacaoDataLoader

        mock_query_db.side_effect = [
            make_checklist_tree(),
            [],
        ]

        loader = ImplantacaoDataLoader(1)
        data = loader.load_all()

        assert data["progress"]["percentage"] == 40.0
        assert data["progress"]["completed"] == 2
