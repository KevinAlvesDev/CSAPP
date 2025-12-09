from datetime import datetime
from typing import Dict, List, Optional

from flask import current_app

from ..common.exceptions import DatabaseError, ValidationError
from ..db import db_connection, execute_db, query_db


def criar_plano_sucesso(nome: str, descricao: str, criado_por: str, estrutura: Dict, dias_duracao: int = None) -> int:
    if not nome or not nome.strip():
        raise ValidationError("Nome do plano é obrigatório")

    if not criado_por:
        raise ValidationError("Usuário criador é obrigatório")

    validar_estrutura_hierarquica(estrutura)

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        # Garantir que as colunas existam (migração automática para SQLite)
        if db_type == 'sqlite':
            try:
                cursor.execute("PRAGMA table_info(planos_sucesso)")
                colunas_existentes = [row[1] for row in cursor.fetchall()]

                if 'data_atualizacao' not in colunas_existentes:
                    cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP")
                    conn.commit()
                    current_app.logger.info("✅ Coluna data_atualizacao adicionada à tabela planos_sucesso")

                if 'dias_duracao' not in colunas_existentes:
                    cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN dias_duracao INTEGER")
                    conn.commit()
                    current_app.logger.info("✅ Coluna dias_duracao adicionada à tabela planos_sucesso")
            except Exception as mig_error:
                current_app.logger.warning(f"Erro ao verificar/migrar colunas de planos_sucesso: {mig_error}")

        try:
            sql_plano = """
                INSERT INTO planos_sucesso (nome, descricao, criado_por, data_criacao, data_atualizacao, dias_duracao)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            if db_type == 'sqlite':
                sql_plano = sql_plano.replace('%s', '?')

            now = datetime.now()
            cursor.execute(sql_plano, (nome.strip(), descricao or '', criado_por, now, now, dias_duracao))

            if db_type == 'postgres':
                cursor.execute("SELECT lastval()")
                plano_id = cursor.fetchone()[0]
            else:
                plano_id = cursor.lastrowid

            _criar_estrutura_plano(cursor, db_type, plano_id, estrutura)

            conn.commit()

            current_app.logger.info(f"Plano de sucesso '{nome}' criado com ID {plano_id} por {criado_por}")
            return plano_id

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao criar plano de sucesso: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao criar plano de sucesso: {e}") from e


def _criar_estrutura_plano(cursor, db_type: str, plano_id: int, estrutura: Dict):
    """
    Cria estrutura do plano usando checklist_items (consolidado).
    """
    fases = estrutura.get('fases', [])

    for fase_data in fases:
        sql_fase = """
            INSERT INTO checklist_items 
            (parent_id, title, completed, comment, level, ordem, plano_id, tipo_item, descricao, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        if db_type == 'sqlite':
            sql_fase = sql_fase.replace('%s', '?')

        cursor.execute(sql_fase, (
            None,  # parent_id (fase é raiz)
            fase_data['nome'],
            False,  # completed
            fase_data.get('descricao', ''),  # comment
            0,  # level (fase é nível 0)
            fase_data.get('ordem', 0),
            plano_id,
            'plano_fase',  # tipo_item
            fase_data.get('descricao', '')  # descricao
        ))

        if db_type == 'postgres':
            cursor.execute("SELECT lastval()")
            fase_id = cursor.fetchone()[0]
        else:
            fase_id = cursor.lastrowid

        grupos = fase_data.get('grupos', [])
        for grupo_data in grupos:
            sql_grupo = """
                INSERT INTO checklist_items 
                (parent_id, title, completed, comment, level, ordem, plano_id, tipo_item, descricao, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            if db_type == 'sqlite':
                sql_grupo = sql_grupo.replace('%s', '?')

            cursor.execute(sql_grupo, (
                fase_id,  # parent_id (grupo pertence à fase)
                grupo_data['nome'],
                False,  # completed
                grupo_data.get('descricao', ''),  # comment
                1,  # level (grupo é nível 1)
                grupo_data.get('ordem', 0),
                plano_id,
                'plano_grupo',  # tipo_item
                grupo_data.get('descricao', '')  # descricao
            ))

            if db_type == 'postgres':
                cursor.execute("SELECT lastval()")
                grupo_id = cursor.fetchone()[0]
            else:
                grupo_id = cursor.lastrowid

            tarefas = grupo_data.get('tarefas', [])
            for tarefa_data in tarefas:
                sql_tarefa = """
                    INSERT INTO checklist_items 
                    (parent_id, title, completed, comment, level, ordem, plano_id, tipo_item, descricao, obrigatoria, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
                if db_type == 'sqlite':
                    sql_tarefa = sql_tarefa.replace('%s', '?')

                cursor.execute(sql_tarefa, (
                    grupo_id,  # parent_id (tarefa pertence ao grupo)
                    tarefa_data['nome'],
                    False,  # completed
                    tarefa_data.get('descricao', ''),  # comment
                    2,  # level (tarefa é nível 2)
                    tarefa_data.get('ordem', 0),
                    plano_id,
                    'plano_tarefa',  # tipo_item
                    tarefa_data.get('descricao', ''),  # descricao
                    tarefa_data.get('obrigatoria', False),  # obrigatoria
                    'pendente'  # status padrão
                ))

                if db_type == 'postgres':
                    cursor.execute("SELECT lastval()")
                    tarefa_id = cursor.fetchone()[0]
                else:
                    tarefa_id = cursor.lastrowid

                subtarefas = tarefa_data.get('subtarefas', [])
                for subtarefa_data in subtarefas:
                    sql_subtarefa = """
                        INSERT INTO checklist_items 
                        (parent_id, title, completed, comment, level, ordem, plano_id, tipo_item, descricao, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                    if db_type == 'sqlite':
                        sql_subtarefa = sql_subtarefa.replace('%s', '?')

                    cursor.execute(sql_subtarefa, (
                        tarefa_id,  # parent_id (subtarefa pertence à tarefa)
                        subtarefa_data['nome'],
                        False,  # completed
                        subtarefa_data.get('descricao', ''),  # comment
                        3,  # level (subtarefa é nível 3)
                        subtarefa_data.get('ordem', 0),
                        plano_id,
                        'plano_subtarefa',  # tipo_item
                        subtarefa_data.get('descricao', '')  # descricao
                    ))


def atualizar_plano_sucesso(plano_id: int, dados: Dict) -> bool:
    if not plano_id:
        raise ValidationError("ID do plano é obrigatório")

    plano_existente = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)
    if not plano_existente:
        raise ValidationError(f"Plano com ID {plano_id} não encontrado")

    with db_connection() as (conn, db_type):
        if db_type == 'sqlite':
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(planos_sucesso)")
                colunas_existentes = [row[1] for row in cursor.fetchall()]

                if 'data_atualizacao' not in colunas_existentes:
                    cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP")
                    conn.commit()
                    current_app.logger.info("✅ Coluna data_atualizacao adicionada à tabela planos_sucesso")

                if 'dias_duracao' not in colunas_existentes:
                    cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN dias_duracao INTEGER")
                    conn.commit()
                    current_app.logger.info("✅ Coluna dias_duracao adicionada à tabela planos_sucesso")
            except Exception as mig_error:
                current_app.logger.warning(f"Erro ao verificar/migrar colunas de planos_sucesso: {mig_error}")

    campos_atualizaveis = []
    valores = []

    if 'nome' in dados and dados['nome']:
        campos_atualizaveis.append("nome = %s")
        valores.append(dados['nome'].strip())

    if 'descricao' in dados:
        campos_atualizaveis.append("descricao = %s")
        valores.append(dados['descricao'] or '')

    if 'ativo' in dados:
        campos_atualizaveis.append("ativo = %s")
        valores.append(bool(dados['ativo']))

    if 'dias_duracao' in dados:
        campos_atualizaveis.append("dias_duracao = %s")
        valores.append(int(dados['dias_duracao']) if dados['dias_duracao'] else None)

    if not campos_atualizaveis:
        return True

    campos_atualizaveis.append("data_atualizacao = %s")
    valores.append(datetime.now())
    valores.append(plano_id)

    sql = f"UPDATE planos_sucesso SET {', '.join(campos_atualizaveis)} WHERE id = %s"

    result = execute_db(sql, tuple(valores), raise_on_error=True)

    current_app.logger.info(f"Plano de sucesso ID {plano_id} atualizado")
    return result is not None


def atualizar_estrutura_plano(plano_id: int, estrutura: Dict) -> bool:
    """
    Atualiza a estrutura do plano (itens) removendo os antigos e criando os novos.
    """
    if not plano_id:
        raise ValidationError("ID do plano é obrigatório")

    if not estrutura:
        raise ValidationError("Estrutura é obrigatória")

    validar_estrutura_checklist(estrutura)

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()
        try:
            sql_delete = "DELETE FROM checklist_items WHERE plano_id = %s"
            if db_type == 'sqlite':
                sql_delete = sql_delete.replace('%s', '?')
            cursor.execute(sql_delete, (plano_id,))

            _criar_estrutura_plano_checklist(cursor, db_type, plano_id, estrutura)

            conn.commit()
            current_app.logger.info(f"Estrutura do plano {plano_id} atualizada com sucesso")
            return True
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao atualizar estrutura do plano {plano_id}: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao atualizar estrutura do plano: {e}")


def excluir_plano_sucesso(plano_id: int) -> bool:
    if not plano_id:
        raise ValidationError("ID do plano é obrigatório")

    plano = query_db("SELECT nome FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)
    if not plano:
        raise ValidationError(f"Plano com ID {plano_id} não encontrado")

    implantacoes_usando = query_db(
        "SELECT COUNT(*) as count FROM implantacoes WHERE plano_sucesso_id = %s",
        (plano_id,),
        one=True
    )

    if implantacoes_usando and implantacoes_usando['count'] > 0:
        raise ValidationError(
            f"Não é possível excluir o plano '{plano['nome']}' pois está sendo usado por {implantacoes_usando['count']} implantação(ões)"
        )

    result = execute_db("DELETE FROM planos_sucesso WHERE id = %s", (plano_id,), raise_on_error=True)

    current_app.logger.info(f"Plano de sucesso '{plano['nome']}' (ID {plano_id}) excluído")
    return result is not None


def listar_planos_sucesso(ativo_apenas: bool = True, busca: str = None) -> List[Dict]:
    sql = "SELECT * FROM planos_sucesso WHERE 1=1"
    params = []

    if ativo_apenas:
        sql += " AND ativo = %s"
        params.append(True)

    if busca:
        sql += " AND (nome LIKE %s OR descricao LIKE %s)"
        busca_pattern = f"%{busca}%"
        params.extend([busca_pattern, busca_pattern])

    sql += " ORDER BY nome ASC"

    planos = query_db(sql, tuple(params) if params else ())
    return planos or []


def obter_plano_completo(plano_id: int) -> Optional[Dict]:
    """
    Retorna plano completo usando checklist_items (estrutura consolidada).
    Retorna no formato 'items' para compatibilidade com o editor moderno.
    """
    plano = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)

    if not plano:
        return None

    items = query_db(
        """
        SELECT id, parent_id, title, completed, comment, level, ordem, tipo_item, descricao, obrigatoria, status, tag
        FROM checklist_items 
        WHERE plano_id = %s
        ORDER BY ordem, id
        """,
        (plano_id,)
    )

    if not items:
        plano['items'] = []
        plano['fases'] = []
        return plano

    from .checklist_service import build_nested_tree

    flat_items = []
    for item in items:
        flat_items.append({
            'id': item['id'],
            'parent_id': item['parent_id'],
            'title': item['title'],
            'completed': item['completed'],
            'comment': item.get('comment', '') or item.get('descricao', ''),
            'level': item.get('level', 0),
            'ordem': item.get('ordem', 0),
            'obrigatoria': item.get('obrigatoria', False),
            'tag': item.get('tag')
        })

    nested_items = build_nested_tree(flat_items)
    plano['items'] = nested_items
    plano['estrutura'] = {'items': nested_items}

    items_map = {item['id']: item for item in items}

    tipo_item_val = lambda x: x.get('tipo_item') or ''
    fases_items = [item for item in items if tipo_item_val(item) == 'plano_fase' and item['parent_id'] is None]
    grupos_items = {item['parent_id']: [] for item in items if tipo_item_val(item) == 'plano_grupo'}
    tarefas_items = {item['parent_id']: [] for item in items if tipo_item_val(item) == 'plano_tarefa'}
    subtarefas_items = {item['parent_id']: [] for item in items if tipo_item_val(item) == 'plano_subtarefa'}

    for item in items:
        tipo_item = tipo_item_val(item)
        if tipo_item == 'plano_grupo' and item['parent_id']:
            grupos_items[item['parent_id']].append(item)
        elif tipo_item == 'plano_tarefa' and item['parent_id']:
            tarefas_items[item['parent_id']].append(item)
        elif tipo_item == 'plano_subtarefa' and item['parent_id']:
            subtarefas_items[item['parent_id']].append(item)

    plano['fases'] = []
    for fase_item in sorted(fases_items, key=lambda x: x.get('ordem', 0)):
        fase = {
            'id': fase_item['id'],
            'nome': fase_item['title'],
            'descricao': fase_item.get('descricao') or fase_item.get('comment', ''),
            'ordem': fase_item.get('ordem', 0),
            'grupos': []
        }

        grupos_fase = sorted(grupos_items.get(fase_item['id'], []), key=lambda x: x.get('ordem', 0))
        for grupo_item in grupos_fase:
            grupo = {
                'id': grupo_item['id'],
                'nome': grupo_item['title'],
                'descricao': grupo_item.get('descricao') or grupo_item.get('comment', ''),
                'ordem': grupo_item.get('ordem', 0),
                'tarefas': []
            }

            tarefas_grupo = sorted(tarefas_items.get(grupo_item['id'], []), key=lambda x: x.get('ordem', 0))
            for tarefa_item in tarefas_grupo:
                tarefa = {
                    'id': tarefa_item['id'],
                    'nome': tarefa_item['title'],
                    'descricao': tarefa_item.get('descricao') or tarefa_item.get('comment', ''),
                    'obrigatoria': tarefa_item.get('obrigatoria', False),
                    'status': tarefa_item.get('status', 'pendente'),
                    'ordem': tarefa_item.get('ordem', 0),
                    'subtarefas': []
                }

                subtarefas_tarefa = sorted(subtarefas_items.get(tarefa_item['id'], []), key=lambda x: x.get('ordem', 0))
                for subtarefa_item in subtarefas_tarefa:
                    subtarefa = {
                        'id': subtarefa_item['id'],
                        'nome': subtarefa_item['title'],
                        'descricao': subtarefa_item.get('descricao') or subtarefa_item.get('comment', ''),
                        'ordem': subtarefa_item.get('ordem', 0)
                    }
                    tarefa['subtarefas'].append(subtarefa)

                grupo['tarefas'].append(tarefa)

            fase['grupos'].append(grupo)

        plano['fases'].append(fase)

    return plano


def aplicar_plano_a_implantacao(implantacao_id: int, plano_id: int, usuario: str) -> bool:
    from datetime import timedelta

    if not implantacao_id or not plano_id:
        raise ValidationError("ID da implantação e do plano são obrigatórios")

    implantacao = query_db(
        "SELECT id, data_inicio_efetivo, data_criacao FROM implantacoes WHERE id = %s",
        (implantacao_id,),
        one=True
    )
    if not implantacao:
        raise ValidationError(f"Implantação com ID {implantacao_id} não encontrada")

    plano = obter_plano_completo(plano_id)
    if not plano:
        raise ValidationError(f"Plano com ID {plano_id} não encontrado")

    if not plano.get('ativo'):
        raise ValidationError(f"Plano '{plano['nome']}' está inativo")

    data_previsao_termino = None
    dias_duracao = plano.get('dias_duracao')

    if dias_duracao:
        data_inicio = implantacao.get('data_inicio_efetivo') or implantacao.get('data_criacao')
        if data_inicio:
            if isinstance(data_inicio, str):
                try:
                    data_inicio = datetime.strptime(data_inicio[:10], '%Y-%m-%d')
                except Exception:
                    data_inicio = datetime.now()
            data_previsao_termino = data_inicio + timedelta(days=int(dias_duracao))

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        try:
            sql_limpar = "DELETE FROM checklist_items WHERE implantacao_id = %s"
            if db_type == 'sqlite':
                sql_limpar = sql_limpar.replace('%s', '?')
            cursor.execute(sql_limpar, (implantacao_id,))

            _clonar_plano_para_implantacao(cursor, db_type, plano, implantacao_id, usuario)

            sql_update = """
                UPDATE implantacoes 
                SET plano_sucesso_id = %s, data_atribuicao_plano = %s, data_previsao_termino = %s
                WHERE id = %s
            """
            if db_type == 'sqlite':
                sql_update = sql_update.replace('%s', '?')

            cursor.execute(sql_update, (plano_id, datetime.now(), data_previsao_termino, implantacao_id))

            conn.commit()

            current_app.logger.info(
                f"Plano '{plano['nome']}' aplicado à implantação {implantacao_id} por {usuario}. Previsão de término: {data_previsao_termino}"
            )
            return True

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao aplicar plano: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao aplicar plano: {e}") from e


def _clonar_plano_para_implantacao(cursor, db_type: str, plano: Dict, implantacao_id: int, responsavel: str = None):
    """
    Clona a estrutura do plano para a implantação usando checklist_items.
    Converte itens do plano (tipo_item='plano_*') para itens de implantação (tipo_item='fase'/'grupo'/'tarefa'/'subtarefa').
    """
    plano_id = plano.get('id')
    if not plano_id:
        raise ValidationError("Plano deve ter um ID válido")

    if db_type == 'postgres':
        cursor.execute("""
            SELECT id, parent_id, title, completed, comment, level, ordem, tipo_item, descricao, obrigatoria, status, tag
            FROM checklist_items 
            WHERE plano_id = %s
            ORDER BY ordem, id
        """, (plano_id,))
    else:
        cursor.execute("""
            SELECT id, parent_id, title, completed, comment, level, ordem, tipo_item, descricao, obrigatoria, status, tag
            FROM checklist_items 
            WHERE plano_id = ?
            ORDER BY ordem, id
        """, (plano_id,))

    items_plano = cursor.fetchall()

    if not items_plano:
        return

    id_map = {}

    def clonar_item(item_plano, parent_id_implantacao):
        item_id_plano = item_plano[0] if isinstance(item_plano, tuple) else item_plano['id']
        parent_id_plano = item_plano[1] if isinstance(item_plano, tuple) else item_plano.get('parent_id')
        title = item_plano[2] if isinstance(item_plano, tuple) else item_plano['title']
        completed = item_plano[3] if isinstance(item_plano, tuple) else item_plano.get('completed', False)
        comment = item_plano[4] if isinstance(item_plano, tuple) else item_plano.get('comment', '')
        level = item_plano[5] if isinstance(item_plano, tuple) else item_plano.get('level', 0)
        ordem = item_plano[6] if isinstance(item_plano, tuple) else item_plano.get('ordem', 0)
        tipo_item_plano = item_plano[7] if isinstance(item_plano, tuple) else item_plano.get('tipo_item', '')
        descricao = item_plano[8] if isinstance(item_plano, tuple) else item_plano.get('descricao', '')
        obrigatoria = item_plano[9] if isinstance(item_plano, tuple) else item_plano.get('obrigatoria', False)
        status = item_plano[10] if isinstance(item_plano, tuple) else item_plano.get('status', 'pendente')
        tag = item_plano[11] if isinstance(item_plano, tuple) and len(item_plano) > 11 else item_plano.get('tag')

        tipo_item_implantacao = tipo_item_plano.replace('plano_', '') if tipo_item_plano.startswith('plano_') else tipo_item_plano

        if db_type == 'postgres':
            sql_insert = """
                INSERT INTO checklist_items 
                (parent_id, title, completed, comment, level, ordem, implantacao_id, tipo_item, descricao, obrigatoria, status, responsavel, tag, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """
            cursor.execute(sql_insert, (
                parent_id_implantacao,
                title,
                completed,
                comment or descricao,
                level,
                ordem,
                implantacao_id,
                tipo_item_implantacao,
                descricao,
                obrigatoria,
                status,
                responsavel,
                tag
            ))
            novo_id = cursor.fetchone()[0]
        else:
            sql_insert = """
                INSERT INTO checklist_items 
                (parent_id, title, completed, comment, level, ordem, implantacao_id, tipo_item, descricao, obrigatoria, status, responsavel, tag, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            cursor.execute(sql_insert, (
                parent_id_implantacao,
                title,
                1 if completed else 0,
                comment or descricao,
                level,
                ordem,
                implantacao_id,
                tipo_item_implantacao,
                descricao,
                1 if obrigatoria else 0,
                status,
                responsavel,
                tag
            ))
            novo_id = cursor.lastrowid

        id_map[item_id_plano] = novo_id

        if db_type == 'postgres':
            cursor.execute("""
                SELECT id, parent_id, title, completed, comment, level, ordem, tipo_item, descricao, obrigatoria, status, tag
                FROM checklist_items
                WHERE plano_id = %s AND parent_id = %s
                ORDER BY ordem, id
            """, (plano_id, item_id_plano))
        else:
            cursor.execute("""
                SELECT id, parent_id, title, completed, comment, level, ordem, tipo_item, descricao, obrigatoria, status, tag
                FROM checklist_items
                WHERE plano_id = ? AND parent_id = ?
                ORDER BY ordem, id
            """, (plano_id, item_id_plano))

        filhos = cursor.fetchall()
        for filho in filhos:
            clonar_item(filho, novo_id)

    for item in items_plano:
        parent_id_plano = item[1] if isinstance(item, tuple) else item.get('parent_id')
        if parent_id_plano is None:
            clonar_item(item, None)


VALID_TAGS = {"Ação interna", "Reunião"}

def validar_estrutura_hierarquica(estrutura: Dict) -> bool:
    if not isinstance(estrutura, dict):
        raise ValidationError("Estrutura deve ser um dicionário")

    fases = estrutura.get('fases', [])
    if not isinstance(fases, list):
        raise ValidationError("'fases' deve ser uma lista")

    if not fases:
        raise ValidationError("Plano deve ter pelo menos uma fase")

    ordens_fases = set()
    for i, fase in enumerate(fases):
        if not isinstance(fase, dict):
            raise ValidationError(f"Fase {i+1} deve ser um dicionário")

        if 'nome' not in fase or not fase['nome']:
            raise ValidationError(f"Fase {i+1} deve ter um nome")

        ordem = fase.get('ordem', 0)
        if ordem in ordens_fases:
            raise ValidationError(f"Ordem {ordem} duplicada nas fases")
        ordens_fases.add(ordem)

        grupos = fase.get('grupos', [])
        if not isinstance(grupos, list):
            raise ValidationError(f"'grupos' da fase '{fase['nome']}' deve ser uma lista")

        for j, grupo in enumerate(grupos):
            if not isinstance(grupo, dict):
                raise ValidationError(f"Grupo {j+1} da fase '{fase['nome']}' deve ser um dicionário")

            if 'nome' not in grupo or not grupo['nome']:
                raise ValidationError(f"Grupo {j+1} da fase '{fase['nome']}' deve ter um nome")

            tarefas = grupo.get('tarefas', [])
            if not isinstance(tarefas, list):
                raise ValidationError(
                    f"'tarefas' do grupo '{grupo['nome']}' deve ser uma lista"
                )

            for k, tarefa in enumerate(tarefas):
                if not isinstance(tarefa, dict):
                    raise ValidationError(
                        f"Tarefa {k+1} do grupo '{grupo['nome']}' deve ser um dicionário"
                    )

                if 'nome' not in tarefa or not tarefa['nome']:
                    raise ValidationError(
                        f"Tarefa {k+1} do grupo '{grupo['nome']}' deve ter um nome"
                    )

                tag = tarefa.get('tag')
                if tag and tag not in VALID_TAGS:
                    raise ValidationError(
                        f"Tarefa '{tarefa['nome']}' tem tag inválida '{tag}'. Tags permitidas: {', '.join(VALID_TAGS)}"
                    )

                subtarefas = tarefa.get('subtarefas', [])
                if not isinstance(subtarefas, list):
                    raise ValidationError(
                        f"'subtarefas' da tarefa '{tarefa['nome']}' deve ser uma lista"
                    )

                for idx, subtarefa in enumerate(subtarefas):
                    if not isinstance(subtarefa, dict):
                        raise ValidationError(
                            f"Subtarefa {idx+1} da tarefa '{tarefa['nome']}' deve ser um dicionário"
                        )

                    if 'nome' not in subtarefa or not subtarefa['nome']:
                        raise ValidationError(
                            f"Subtarefa {idx+1} da tarefa '{tarefa['nome']}' deve ter um nome"
                        )

                    tag_sub = subtarefa.get('tag')
                    if tag_sub and tag_sub not in VALID_TAGS:
                        raise ValidationError(
                            f"Subtarefa '{subtarefa['nome']}' tem tag inválida '{tag_sub}'. Tags permitidas: {', '.join(VALID_TAGS)}"
                        )

    return True


def remover_plano_de_implantacao(implantacao_id: int, usuario: str) -> bool:
    if not implantacao_id:
        raise ValidationError("ID da implantação é obrigatório")

    implantacao = query_db(
        "SELECT plano_sucesso_id FROM implantacoes WHERE id = %s",
        (implantacao_id,),
        one=True
    )

    if not implantacao:
        raise ValidationError(f"Implantação com ID {implantacao_id} não encontrada")

    if not implantacao.get('plano_sucesso_id'):
        return True

    sql = """
        UPDATE implantacoes
        SET plano_sucesso_id = NULL, data_atribuicao_plano = NULL
        WHERE id = %s
    """

    result = execute_db(sql, (implantacao_id,), raise_on_error=True)

    current_app.logger.info(
        f"Plano removido da implantação {implantacao_id} por {usuario}"
    )

    try:
        from ..db import logar_timeline
        logar_timeline(implantacao_id, usuario, 'plano_removido', f"Plano de sucesso removido da implantação por {usuario}.")
    except Exception:
        pass

    return result is not None


def obter_plano_da_implantacao(implantacao_id: int) -> Optional[Dict]:
    implantacao = query_db(
        "SELECT plano_sucesso_id FROM implantacoes WHERE id = %s",
        (implantacao_id,),
        one=True
    )

    if not implantacao or not implantacao.get('plano_sucesso_id'):
        return None

    return obter_plano_completo(implantacao['plano_sucesso_id'])


def criar_plano_sucesso_checklist(nome: str, descricao: str, criado_por: str, estrutura: Dict, dias_duracao: int = None) -> int:
    """
    Cria um plano de sucesso usando a tabela checklist_items (hierarquia infinita).
    A estrutura é salva como uma árvore de itens na tabela checklist_items, vinculada ao plano.
    Aceita estrutura no formato antigo (fases/grupos) ou novo (items hierárquicos).
    """
    if not nome or not nome.strip():
        raise ValidationError("Nome do plano é obrigatório")

    if not criado_por:
        raise ValidationError("Usuário criador é obrigatório")

    validar_estrutura_checklist(estrutura)

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        # Garantir que as colunas existam (migração automática para SQLite)
        if db_type == 'sqlite':
            try:
                cursor.execute("PRAGMA table_info(planos_sucesso)")
                colunas_existentes = [row[1] for row in cursor.fetchall()]

                if 'data_atualizacao' not in colunas_existentes:
                    cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP")
                    conn.commit()
                    current_app.logger.info("✅ Coluna data_atualizacao adicionada à tabela planos_sucesso")

                if 'dias_duracao' not in colunas_existentes:
                    cursor.execute("ALTER TABLE planos_sucesso ADD COLUMN dias_duracao INTEGER")
                    conn.commit()
                    current_app.logger.info("✅ Coluna dias_duracao adicionada à tabela planos_sucesso")
            except Exception as mig_error:
                current_app.logger.warning(f"Erro ao verificar/migrar colunas de planos_sucesso: {mig_error}")

        try:
            sql_plano = """
                INSERT INTO planos_sucesso (nome, descricao, criado_por, data_criacao, data_atualizacao, dias_duracao)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            if db_type == 'sqlite':
                sql_plano = sql_plano.replace('%s', '?')

            now = datetime.now()
            cursor.execute(sql_plano, (nome.strip(), descricao or '', criado_por, now, now, dias_duracao))

            if db_type == 'postgres':
                cursor.execute("SELECT lastval()")
                plano_id = cursor.fetchone()[0]
            else:
                plano_id = cursor.lastrowid

            _criar_estrutura_plano_checklist(cursor, db_type, plano_id, estrutura)

            conn.commit()

            current_app.logger.info(f"Plano de sucesso '{nome}' criado com ID {plano_id} usando checklist_items por {criado_por}")
            return plano_id

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao criar plano de sucesso: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao criar plano de sucesso: {e}")


def _criar_estrutura_plano_checklist(cursor, db_type: str, plano_id: int, estrutura: Dict):
    """
    Cria a estrutura do plano na tabela checklist_items.
    Usa campo 'plano_id' para vincular itens ao plano.
    Usa campo 'implantacao_id' como NULL (é um plano, não uma implantação).
    """
    if 'items' in estrutura:
        _criar_items_recursivo(cursor, db_type, plano_id, estrutura['items'], None, 0)
    else:
        fases = estrutura.get('fases', [])
        parent_map = {}
        ordem_global = 0

        for fase_data in fases:
            ordem_global += 1
            sql_item = """
                INSERT INTO checklist_items (parent_id, title, completed, comment, level, ordem, implantacao_id, plano_id, obrigatoria)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            if db_type == 'sqlite':
                sql_item = sql_item.replace('%s', '?')

            cursor.execute(sql_item, (
                None,
                fase_data['nome'],
                False,
                fase_data.get('descricao', ''),
                0,
                fase_data.get('ordem', ordem_global),
                None,
                plano_id,
                fase_data.get('obrigatoria', False)
            ))

            if db_type == 'postgres':
                cursor.execute("SELECT lastval()")
                fase_id = cursor.fetchone()[0]
            else:
                fase_id = cursor.lastrowid

            parent_map['fase_' + str(fase_data.get('ordem', ordem_global))] = fase_id

            grupos = fase_data.get('grupos', [])
            for grupo_data in grupos:
                ordem_global += 1
                cursor.execute(sql_item, (
                    fase_id,
                    grupo_data['nome'],
                    False,
                    grupo_data.get('descricao', ''),
                    1,
                    grupo_data.get('ordem', ordem_global),
                    None,
                    plano_id,
                    grupo_data.get('obrigatoria', False)
                ))

                if db_type == 'postgres':
                    cursor.execute("SELECT lastval()")
                    grupo_id = cursor.fetchone()[0]
                else:
                    grupo_id = cursor.lastrowid

                tarefas = grupo_data.get('tarefas', [])
                for tarefa_data in tarefas:
                    ordem_global += 1
                    cursor.execute(sql_item, (
                        grupo_id,
                        tarefa_data['nome'],
                        False,
                        tarefa_data.get('descricao', ''),
                        2,
                        tarefa_data.get('ordem', ordem_global),
                        None,
                        plano_id,
                        tarefa_data.get('obrigatoria', False)
                    ))

                    if db_type == 'postgres':
                        cursor.execute("SELECT lastval()")
                        tarefa_id = cursor.fetchone()[0]
                    else:
                        tarefa_id = cursor.lastrowid

                    subtarefas = tarefa_data.get('subtarefas', [])
                    for subtarefa_data in subtarefas:
                        ordem_global += 1
                        cursor.execute(sql_item, (
                            tarefa_id,
                            subtarefa_data['nome'],
                            False,
                            subtarefa_data.get('descricao', ''),
                            3,
                            subtarefa_data.get('ordem', ordem_global),
                            None,
                            plano_id,
                            subtarefa_data.get('obrigatoria', False)
                        ))


def _criar_items_recursivo(cursor, db_type: str, plano_id: int, items: List[Dict], parent_id: Optional[int], current_level: int):
    """
    Cria itens recursivamente para suportar hierarquia infinita.
    """
    ordem = 0
    for item_data in items:
        ordem += 1
        tipo_item = item_data.get('tipo_item')
        if not tipo_item:
            if current_level == 0:
                tipo_item = 'plano_fase'
            elif current_level == 1:
                tipo_item = 'plano_grupo'
            elif current_level == 2:
                tipo_item = 'plano_tarefa'
            else:
                tipo_item = 'plano_subtarefa'

        sql_item = """
            INSERT INTO checklist_items (parent_id, title, completed, comment, level, ordem, implantacao_id, plano_id, obrigatoria, tipo_item, tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        if db_type == 'sqlite':
            sql_item = sql_item.replace('%s', '?')

        cursor.execute(sql_item, (
            parent_id,
            item_data.get('title', item_data.get('nome', '')),
            False,
            item_data.get('comment', item_data.get('descricao', '')),
            item_data.get('level', current_level),
            item_data.get('ordem', ordem),
            None,
            plano_id,
            item_data.get('obrigatoria', False),
            tipo_item,
            item_data.get('tag')
        ))

        if db_type == 'postgres':
            cursor.execute("SELECT lastval()")
            item_id = cursor.fetchone()[0]
        else:
            item_id = cursor.lastrowid

        children = item_data.get('children', [])
        if children:
            _criar_items_recursivo(cursor, db_type, plano_id, children, item_id, current_level + 1)


def aplicar_plano_a_implantacao_checklist(implantacao_id: int, plano_id: int, usuario: str, responsavel_nome: str | None = None) -> bool:
    """
    Aplica um plano de sucesso a uma implantação usando checklist_items.
    Clona a estrutura do plano (itens com implantacao_id = NULL) para a implantação.
    """
    from datetime import timedelta

    if not implantacao_id or not plano_id:
        raise ValidationError("ID da implantação e do plano são obrigatórios")

    implantacao = query_db(
        "SELECT id, data_inicio_efetivo, data_criacao FROM implantacoes WHERE id = %s",
        (implantacao_id,),
        one=True
    )
    if not implantacao:
        raise ValidationError(f"Implantação com ID {implantacao_id} não encontrada")

    plano = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)
    if not plano:
        raise ValidationError(f"Plano com ID {plano_id} não encontrado")

    if not plano.get('ativo', True):
        raise ValidationError(f"Plano '{plano['nome']}' está inativo")

    data_previsao_termino = None
    dias_duracao = plano.get('dias_duracao')

    if dias_duracao:
        data_inicio = implantacao.get('data_inicio_efetivo') or implantacao.get('data_criacao')
        if data_inicio:
            if isinstance(data_inicio, str):
                try:
                    data_inicio = datetime.strptime(data_inicio[:10], '%Y-%m-%d')
                except:
                    data_inicio = datetime.now()
            data_previsao_termino = data_inicio + timedelta(days=int(dias_duracao))

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()

        try:
            sql_limpar = "DELETE FROM checklist_items WHERE implantacao_id = %s"
            if db_type == 'sqlite':
                sql_limpar = sql_limpar.replace('%s', '?')
            cursor.execute(sql_limpar, (implantacao_id,))

            # Responsável padrão: nome completo do usuário (fallback: email)
            if responsavel_nome and isinstance(responsavel_nome, str) and responsavel_nome.strip():
                responsavel_padrao = responsavel_nome.strip()
            else:
                try:
                    perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario,), one=True)
                    responsavel_padrao = perfil.get('nome') if perfil and perfil.get('nome') else usuario
                except Exception:
                    responsavel_padrao = usuario

            _clonar_plano_para_implantacao_checklist(
                cursor,
                db_type,
                plano_id,
                implantacao_id,
                responsavel_padrao,
                data_inicio if 'data_inicio' in locals() else (implantacao.get('data_inicio_efetivo') or implantacao.get('data_criacao')),
                int(dias_duracao or 0),
                data_previsao_termino
            )

            # Contagem de itens existentes antes da aplicação
            try:
                if db_type == 'postgres':
                    cursor.execute("SELECT COUNT(*) FROM checklist_items WHERE implantacao_id = %s", (implantacao_id,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM checklist_items WHERE implantacao_id = ?", (implantacao_id,))
                count_before = cursor.fetchone()[0]
            except Exception:
                count_before = None

            sql_update = """
                UPDATE implantacoes
                SET plano_sucesso_id = %s, data_atribuicao_plano = %s, data_previsao_termino = %s
                WHERE id = %s
            """
            if db_type == 'sqlite':
                sql_update = sql_update.replace('%s', '?')

            cursor.execute(sql_update, (plano_id, datetime.now(), data_previsao_termino, implantacao_id))

            conn.commit()

            current_app.logger.info(
                f"Plano '{plano['nome']}' aplicado à implantação {implantacao_id} usando checklist_items por {usuario}. Previsão: {data_previsao_termino}"
            )

            try:
                from ..db import logar_timeline
                from ..common.utils import format_date_iso_for_json
                prev_txt = format_date_iso_for_json(data_previsao_termino) if data_previsao_termino else None
                # Contagem após aplicação
                try:
                    if db_type == 'postgres':
                        cursor.execute("SELECT COUNT(*) FROM checklist_items WHERE implantacao_id = %s", (implantacao_id,))
                    else:
                        cursor.execute("SELECT COUNT(*) FROM checklist_items WHERE implantacao_id = ?", (implantacao_id,))
                    count_after = cursor.fetchone()[0]
                except Exception:
                    count_after = None
                delta = None
                if isinstance(count_before, int) and isinstance(count_after, int):
                    delta = max(0, count_after - count_before)

                detalhe = f"Plano aplicado: '{plano.get('nome')}'"
                if prev_txt:
                    detalhe += f"; previsão de término: {prev_txt}"
                if delta is not None:
                    detalhe += f"; itens clonados: {delta}"
                logar_timeline(implantacao_id, usuario, 'plano_aplicado', detalhe)
            except Exception:
                pass

            return True

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erro ao aplicar plano: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao aplicar plano: {e}")


def _clonar_plano_para_implantacao_checklist(cursor, db_type: str, plano_id: int, implantacao_id: int, responsavel_padrao: str, data_base, dias_duracao: int, data_previsao_termino=None):
    """
    Clona a estrutura do plano (itens com implantacao_id = NULL) para a implantação.
    Usa abordagem iterativa para clonar toda a árvore mantendo a hierarquia.
    IMPORTANTE: Copia também o tipo_item convertendo de 'plano_*' para o tipo de implantação.
    """
    item_map = {}

    def clone_item_recursivo(plano_item_id, new_parent_id):
        if db_type == 'postgres':
            sql_item = "SELECT title, completed, comment, level, ordem, obrigatoria, tipo_item, descricao, status, responsavel, tag FROM checklist_items WHERE id = %s"
            cursor.execute(sql_item, (plano_item_id,))
            row = cursor.fetchone()
            if not row:
                return None

            title, completed, comment, level, ordem, obrigatoria = row[0], row[1], row[2], row[3], row[4], row[5]
            tipo_item_plano = row[6] or ''
            descricao = row[7] or ''
            status = row[8] or 'pendente'
            responsavel = row[9]
            tag = row[10]
        else:
            sql_item = "SELECT title, completed, comment, level, ordem, obrigatoria, tipo_item, descricao, status, responsavel, tag FROM checklist_items WHERE id = ?"
            cursor.execute(sql_item, (plano_item_id,))
            row = cursor.fetchone()
            if not row:
                return None

            title = row[0]
            completed = bool(row[1]) if row[1] is not None else False
            comment = row[2]
            level = row[3] if row[3] is not None else 0
            ordem = row[4] if row[4] is not None else 0
            obrigatoria = bool(row[5]) if row[5] is not None else False
            tipo_item_plano = row[6] or ''
            descricao = row[7] or ''
            status = row[8] or 'pendente'
            responsavel = row[9]
            tag = row[10]

        tipo_item_implantacao = tipo_item_plano.replace('plano_', '') if tipo_item_plano.startswith('plano_') else tipo_item_plano

        if not tipo_item_implantacao:
            if level == 0:
                tipo_item_implantacao = 'fase'
            elif level == 1:
                tipo_item_implantacao = 'grupo'
            elif level == 2:
                tipo_item_implantacao = 'tarefa'
            else:
                tipo_item_implantacao = 'subtarefa'

        if db_type == 'postgres':
            previsao_original = data_previsao_termino
            responsavel = responsavel_padrao
            sql_insert = """
                INSERT INTO checklist_items (parent_id, title, completed, comment, level, ordem, implantacao_id, obrigatoria, tipo_item, descricao, status, responsavel, tag, previsao_original, nova_previsao, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """
            cursor.execute(sql_insert, (new_parent_id, title, completed, comment, level, ordem, implantacao_id, obrigatoria, tipo_item_implantacao, descricao, status, responsavel, tag, previsao_original, None))
            result = cursor.fetchone()
            new_item_id = result[0] if result else None
        else:
            previsao_original = data_previsao_termino
            responsavel = responsavel_padrao
            sql_insert = """
                INSERT INTO checklist_items (parent_id, title, completed, comment, level, ordem, implantacao_id, obrigatoria, tipo_item, descricao, status, responsavel, tag, previsao_original, nova_previsao, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            cursor.execute(sql_insert, (new_parent_id, title, 1 if completed else 0, comment, level, ordem, implantacao_id, 1 if obrigatoria else 0, tipo_item_implantacao, descricao, status, responsavel, tag, previsao_original, None))
            new_item_id = cursor.lastrowid

        if not new_item_id:
            return None

        item_map[plano_item_id] = new_item_id

        if db_type == 'postgres':
            sql_filhos = "SELECT id FROM checklist_items WHERE parent_id = %s AND plano_id = %s ORDER BY ordem, id"
            cursor.execute(sql_filhos, (plano_item_id, plano_id))
            filhos = cursor.fetchall()
        else:
            sql_filhos = "SELECT id FROM checklist_items WHERE parent_id = ? AND plano_id = ? ORDER BY ordem, id"
            cursor.execute(sql_filhos, (plano_item_id, plano_id))
            filhos = cursor.fetchall()

        for filho_row in filhos:
            filho_plano_id = filho_row[0]
            clone_item_recursivo(filho_plano_id, new_item_id)

        return new_item_id

    if db_type == 'postgres':
        sql_raiz = "SELECT id FROM checklist_items WHERE plano_id = %s AND parent_id IS NULL ORDER BY ordem, id"
        cursor.execute(sql_raiz, (plano_id,))
        raizes = cursor.fetchall()
    else:
        sql_raiz = "SELECT id FROM checklist_items WHERE plano_id = ? AND parent_id IS NULL ORDER BY ordem, id"
        cursor.execute(sql_raiz, (plano_id,))
        raizes = cursor.fetchall()

    for raiz_row in raizes:
        clone_item_recursivo(raiz_row[0], None)


def obter_plano_completo_checklist(plano_id: int) -> Optional[Dict]:
    """
    Retorna plano completo usando checklist_items (hierarquia infinita).
    Retorna estrutura aninhada para compatibilidade com frontend.
    """
    plano = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)

    if not plano:
        return None

    count_items = query_db(
        "SELECT COUNT(*) as count FROM checklist_items WHERE plano_id = %s",
        (plano_id,),
        one=True
    )

    if not count_items or count_items.get('count', 0) == 0:
        return None

    items = query_db(
        """
        SELECT id, parent_id, title, completed, comment, level, ordem
        FROM checklist_items
        WHERE plano_id = %s
        ORDER BY ordem, id
        """,
        (plano_id,)
    )

    if not items:
        return plano

    from .checklist_service import build_nested_tree

    flat_items = []
    for item in items:
        flat_items.append({
            'id': item['id'],
            'parent_id': item['parent_id'],
            'title': item['title'],
            'completed': item['completed'],
            'comment': item['comment'],
            'level': item['level'],
            'ordem': item['ordem']
        })

    nested_items = build_nested_tree(flat_items)

    plano['items'] = nested_items
    plano['estrutura'] = {'items': nested_items}

    return plano


def _plano_usa_checklist_items(plano_id: int) -> bool:
    """
    Verifica se o plano usa checklist_items (novo formato) ou estrutura antiga.
    """
    count = query_db(
        "SELECT COUNT(*) as count FROM checklist_items WHERE plano_id = %s",
        (plano_id,),
        one=True
    )

    return count and count.get('count', 0) > 0


def validar_estrutura_checklist(estrutura: Dict) -> bool:
    """
    Valida estrutura de checklist_items (hierarquia infinita).
    Aceita estrutura aninhada ou plana com parent_id.
    """
    if not isinstance(estrutura, dict):
        raise ValidationError("Estrutura deve ser um dicionário")

    if 'items' in estrutura:
        items = estrutura['items']
        if not isinstance(items, list):
            raise ValidationError("'items' deve ser uma lista")

        if len(items) > 0:
            _validar_items_recursivo(items, set(), 0)
        return True
    elif 'fases' in estrutura:
        return validar_estrutura_hierarquica(estrutura)
    else:
        raise ValidationError("Estrutura deve conter 'items' ou 'fases'")


def _validar_items_recursivo(items: List[Dict], titles_set: set, depth: int, max_depth: int = 100):
    """
    Valida itens recursivamente, verificando loops e profundidade máxima.
    """
    if depth > max_depth:
        raise ValidationError(f"Hierarquia muito profunda (máximo {max_depth} níveis)")

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValidationError(f"Item {i+1} deve ser um dicionário")

        title = item.get('title') or item.get('nome', '')
        if not title or not str(title).strip():
            raise ValidationError(f"Item {i+1} deve ter um título (title ou nome)")

        tag = item.get('tag')
        if tag and tag not in VALID_TAGS:
            raise ValidationError(
                 f"Item '{title}' tem tag inválida '{tag}'. Tags permitidas: {', '.join(VALID_TAGS)}"
            )

        children = item.get('children', [])
        if children:
            if not isinstance(children, list):
                raise ValidationError(f"Children do item '{title}' deve ser uma lista")
            _validar_items_recursivo(children, titles_set, depth + 1, max_depth)


def converter_estrutura_editor_para_checklist(estrutura_editor: Dict) -> List[Dict]:
    """
    Converte estrutura do editor (fases/grupos OU items aninhados) para formato plano de checklist_items.
    Retorna lista plana com parent_id, level, ordem.
    """
    resultado = []

    if 'items' in estrutura_editor:
        items = estrutura_editor['items']
        _converter_items_para_plano(items, None, 0, 0, resultado)
    elif 'fases' in estrutura_editor:
        fases = estrutura_editor['fases']
        ordem_global = 0

        for fase in fases:
            ordem_global += 1
            fase_item = {
                'title': fase.get('nome', ''),
                'comment': fase.get('descricao', ''),
                'level': 0,
                'ordem': fase.get('ordem', ordem_global),
                'parent_id': None
            }
            resultado.append(fase_item)

            grupos = fase.get('grupos', [])
            for grupo in grupos:
                ordem_global += 1
                grupo_item = {
                    'title': grupo.get('nome', ''),
                    'comment': grupo.get('descricao', ''),
                    'level': 1,
                    'ordem': grupo.get('ordem', ordem_global),
                    'parent_id': fase_item.get('temp_id')
                }
                resultado.append(grupo_item)

                tarefas = grupo.get('tarefas', [])
                for tarefa in tarefas:
                    ordem_global += 1
                    tarefa_item = {
                        'title': tarefa.get('nome', ''),
                        'comment': tarefa.get('descricao', ''),
                        'level': 2,
                        'ordem': tarefa.get('ordem', ordem_global),
                        'parent_id': grupo_item.get('temp_id')
                    }
                    resultado.append(tarefa_item)

                    subtarefas = tarefa.get('subtarefas', [])
                    for subtarefa in subtarefas:
                        ordem_global += 1
                        subtarefa_item = {
                            'title': subtarefa.get('nome', ''),
                            'comment': subtarefa.get('descricao', ''),
                            'level': 3,
                            'ordem': subtarefa.get('ordem', ordem_global),
                            'parent_id': tarefa_item.get('temp_id')
                        }
                        resultado.append(subtarefa_item)
    else:
        raise ValidationError("Estrutura deve conter 'items' ou 'fases'")

    return resultado


def _converter_items_para_plano(items: List[Dict], parent_id: Optional[int], current_level: int, ordem_start: int, resultado: List[Dict]):
    """
    Converte items aninhados para formato plano recursivamente.
    """
    ordem = ordem_start
    for item in items:
        ordem += 1
        item_plano = {
            'title': item.get('title', item.get('nome', '')),
            'comment': item.get('comment', item.get('descricao', '')),
            'level': item.get('level', current_level),
            'ordem': item.get('ordem', ordem),
            'parent_id': parent_id,
            'obrigatoria': item.get('obrigatoria', False),
            'tag': item.get('tag'),
            'children': []
        }
        resultado.append(item_plano)

        children = item.get('children', [])
        if children:
            _converter_items_para_plano(children, None, current_level + 1, ordem, resultado)
