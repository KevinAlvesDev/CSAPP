
from flask import current_app
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..db import query_db, execute_db, execute_and_fetch_one, db_connection
from ..common.exceptions import DatabaseError, ValidationError


def criar_plano_sucesso(nome: str, descricao: str, criado_por: str, estrutura: Dict, dias_duracao: int = None) -> int:
    if not nome or not nome.strip():
        raise ValidationError("Nome do plano é obrigatório")
    
    if not criado_por:
        raise ValidationError("Usuário criador é obrigatório")
    
    validar_estrutura_hierarquica(estrutura)
    
    with db_connection() as (conn, db_type):
        cursor = conn.cursor()
        
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
            raise DatabaseError(f"Erro ao criar plano de sucesso: {e}")


def _criar_estrutura_plano(cursor, db_type: str, plano_id: int, estrutura: Dict):
    fases = estrutura.get('fases', [])
    
    for fase_data in fases:
        sql_fase = """
            INSERT INTO planos_fases (plano_id, nome, descricao, ordem)
            VALUES (%s, %s, %s, %s)
        """
        if db_type == 'sqlite':
            sql_fase = sql_fase.replace('%s', '?')
        
        cursor.execute(sql_fase, (
            plano_id,
            fase_data['nome'],
            fase_data.get('descricao', ''),
            fase_data.get('ordem', 0)
        ))
        
        if db_type == 'postgres':
            cursor.execute("SELECT lastval()")
            fase_id = cursor.fetchone()[0]
        else:
            fase_id = cursor.lastrowid
        
        grupos = fase_data.get('grupos', [])
        for grupo_data in grupos:
            sql_grupo = """
                INSERT INTO planos_grupos (fase_id, nome, descricao, ordem)
                VALUES (%s, %s, %s, %s)
            """
            if db_type == 'sqlite':
                sql_grupo = sql_grupo.replace('%s', '?')
            
            cursor.execute(sql_grupo, (
                fase_id,
                grupo_data['nome'],
                grupo_data.get('descricao', ''),
                grupo_data.get('ordem', 0)
            ))
            
            if db_type == 'postgres':
                cursor.execute("SELECT lastval()")
                grupo_id = cursor.fetchone()[0]
            else:
                grupo_id = cursor.lastrowid
            
            tarefas = grupo_data.get('tarefas', [])
            for tarefa_data in tarefas:
                sql_tarefa = """
                    INSERT INTO planos_tarefas (grupo_id, nome, descricao, obrigatoria, ordem)
                    VALUES (%s, %s, %s, %s, %s)
                """
                if db_type == 'sqlite':
                    sql_tarefa = sql_tarefa.replace('%s', '?')
                
                cursor.execute(sql_tarefa, (
                    grupo_id,
                    tarefa_data['nome'],
                    tarefa_data.get('descricao', ''),
                    tarefa_data.get('obrigatoria', False),
                    tarefa_data.get('ordem', 0)
                ))
                
                if db_type == 'postgres':
                    cursor.execute("SELECT lastval()")
                    tarefa_id = cursor.fetchone()[0]
                else:
                    tarefa_id = cursor.lastrowid
                
                subtarefas = tarefa_data.get('subtarefas', [])
                for subtarefa_data in subtarefas:
                    sql_subtarefa = """
                        INSERT INTO planos_subtarefas (tarefa_id, nome, descricao, ordem)
                        VALUES (%s, %s, %s, %s)
                    """
                    if db_type == 'sqlite':
                        sql_subtarefa = sql_subtarefa.replace('%s', '?')
                    
                    cursor.execute(sql_subtarefa, (
                        tarefa_id,
                        subtarefa_data['nome'],
                        subtarefa_data.get('descricao', ''),
                        subtarefa_data.get('ordem', 0)
                    ))


def atualizar_plano_sucesso(plano_id: int, dados: Dict) -> bool:
    if not plano_id:
        raise ValidationError("ID do plano é obrigatório")
    
    plano_existente = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)
    if not plano_existente:
        raise ValidationError(f"Plano com ID {plano_id} não encontrado")
    
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
    plano = query_db("SELECT * FROM planos_sucesso WHERE id = %s", (plano_id,), one=True)
    
    if not plano:
        return None
    
    fases = query_db(
        "SELECT * FROM planos_fases WHERE plano_id = %s ORDER BY ordem ASC",
        (plano_id,)
    )
    
    plano['fases'] = []
    for fase in fases or []:
        grupos = query_db(
            "SELECT * FROM planos_grupos WHERE fase_id = %s ORDER BY ordem ASC",
            (fase['id'],)
        )
        
        fase['grupos'] = []
        for grupo in grupos or []:
            tarefas = query_db(
                "SELECT * FROM planos_tarefas WHERE grupo_id = %s ORDER BY ordem ASC",
                (grupo['id'],)
            )
            
            grupo['tarefas'] = []
            for tarefa in tarefas or []:
                subtarefas = query_db(
                    "SELECT * FROM planos_subtarefas WHERE tarefa_id = %s ORDER BY ordem ASC",
                    (tarefa['id'],)
                )
                tarefa['subtarefas'] = subtarefas or []
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
    
    # Calcular previsão de término baseada na data de início e dias de duração
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
            sql_limpar_fases = "DELETE FROM fases WHERE implantacao_id = %s"
            if db_type == 'sqlite':
                sql_limpar_fases = sql_limpar_fases.replace('%s', '?')
            cursor.execute(sql_limpar_fases, (implantacao_id,))
            
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
            raise DatabaseError(f"Erro ao aplicar plano: {e}")


def _clonar_plano_para_implantacao(cursor, db_type: str, plano: Dict, implantacao_id: int, responsavel: str = None):
    """Clona a estrutura do plano para a implantação, adicionando o responsável a todos os itens."""
    
    # Verificar se a coluna responsavel existe (tentar inserir com ela primeiro)
    usar_responsavel = True
    
    for fase in plano.get('fases', []):
        if usar_responsavel:
            sql_fase = """
                INSERT INTO fases (implantacao_id, nome, ordem, responsavel)
                VALUES (%s, %s, %s, %s)
            """
            if db_type == 'sqlite':
                sql_fase = sql_fase.replace('%s', '?')
            try:
                cursor.execute(sql_fase, (implantacao_id, fase['nome'], fase['ordem'], responsavel))
            except Exception:
                # Coluna responsavel não existe, usar versão sem ela
                usar_responsavel = False
                sql_fase = """
                    INSERT INTO fases (implantacao_id, nome, ordem)
                    VALUES (%s, %s, %s)
                """
                if db_type == 'sqlite':
                    sql_fase = sql_fase.replace('%s', '?')
                cursor.execute(sql_fase, (implantacao_id, fase['nome'], fase['ordem']))
        else:
            sql_fase = """
                INSERT INTO fases (implantacao_id, nome, ordem)
                VALUES (%s, %s, %s)
            """
            if db_type == 'sqlite':
                sql_fase = sql_fase.replace('%s', '?')
            cursor.execute(sql_fase, (implantacao_id, fase['nome'], fase['ordem']))
        
        if db_type == 'postgres':
            cursor.execute("SELECT lastval()")
            fase_inst_id = cursor.fetchone()[0]
        else:
            fase_inst_id = cursor.lastrowid
        
        for grupo in fase.get('grupos', []):
            if usar_responsavel:
                sql_grupo = """
                    INSERT INTO grupos (fase_id, nome, responsavel)
                    VALUES (%s, %s, %s)
                """
                if db_type == 'sqlite':
                    sql_grupo = sql_grupo.replace('%s', '?')
                cursor.execute(sql_grupo, (fase_inst_id, grupo['nome'], responsavel))
            else:
                sql_grupo = """
                    INSERT INTO grupos (fase_id, nome)
                    VALUES (%s, %s)
                """
                if db_type == 'sqlite':
                    sql_grupo = sql_grupo.replace('%s', '?')
                cursor.execute(sql_grupo, (fase_inst_id, grupo['nome']))
            
            if db_type == 'postgres':
                cursor.execute("SELECT lastval()")
                grupo_inst_id = cursor.fetchone()[0]
            else:
                grupo_inst_id = cursor.lastrowid
            
            for tarefa in grupo.get('tarefas', []):
                if usar_responsavel:
                    sql_tarefa = """
                        INSERT INTO tarefas_h (grupo_id, nome, status, percentual_conclusao, ordem, responsavel)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    if db_type == 'sqlite':
                        sql_tarefa = sql_tarefa.replace('%s', '?')
                    cursor.execute(sql_tarefa, (
                        grupo_inst_id,
                        tarefa['nome'],
                        'pendente',
                        0,
                        tarefa['ordem'],
                        responsavel
                    ))
                else:
                    sql_tarefa = """
                        INSERT INTO tarefas_h (grupo_id, nome, status, percentual_conclusao, ordem)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    if db_type == 'sqlite':
                        sql_tarefa = sql_tarefa.replace('%s', '?')
                    cursor.execute(sql_tarefa, (
                        grupo_inst_id,
                        tarefa['nome'],
                        'pendente',
                        0,
                        tarefa['ordem']
                    ))
                
                if db_type == 'postgres':
                    cursor.execute("SELECT lastval()")
                    tarefa_inst_id = cursor.fetchone()[0]
                else:
                    tarefa_inst_id = cursor.lastrowid
                
                for subtarefa in tarefa.get('subtarefas', []):
                    if usar_responsavel:
                        sql_subtarefa = """
                            INSERT INTO subtarefas_h (tarefa_id, nome, concluido, ordem, responsavel)
                            VALUES (%s, %s, %s, %s, %s)
                        """
                        if db_type == 'sqlite':
                            sql_subtarefa = sql_subtarefa.replace('%s', '?')
                        cursor.execute(sql_subtarefa, (
                            tarefa_inst_id,
                            subtarefa['nome'],
                            False,
                            subtarefa['ordem'],
                            responsavel
                        ))
                    else:
                        sql_subtarefa = """
                            INSERT INTO subtarefas_h (tarefa_id, nome, concluido, ordem)
                            VALUES (%s, %s, %s, %s)
                        """
                        if db_type == 'sqlite':
                            sql_subtarefa = sql_subtarefa.replace('%s', '?')
                        cursor.execute(sql_subtarefa, (
                            tarefa_inst_id,
                            subtarefa['nome'],
                            False,
                            subtarefa['ordem']
                        ))


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
                
                subtarefas = tarefa.get('subtarefas', [])
                if not isinstance(subtarefas, list):
                    raise ValidationError(
                        f"'subtarefas' da tarefa '{tarefa['nome']}' deve ser uma lista"
                    )
                
                for l, subtarefa in enumerate(subtarefas):
                    if not isinstance(subtarefa, dict):
                        raise ValidationError(
                            f"Subtarefa {l+1} da tarefa '{tarefa['nome']}' deve ser um dicionário"
                        )
                    
                    if 'nome' not in subtarefa or not subtarefa['nome']:
                        raise ValidationError(
                            f"Subtarefa {l+1} da tarefa '{tarefa['nome']}' deve ter um nome"
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
