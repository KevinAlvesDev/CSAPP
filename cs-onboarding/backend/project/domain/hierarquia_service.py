"""
Serviço para manipulação de dados hierárquicos de implantações.
Estrutura: Fases → Grupos → Tarefas → Subtarefas
"""

from ..db import query_db, execute_db
from flask import current_app
from ..config.logging_config import get_logger

logger = get_logger('hierarquia_service')


def get_hierarquia_implantacao(implantacao_id):
    """
    Retorna a estrutura hierárquica completa de uma implantação.
    
    Returns:
        dict: {
            'fases': [
                {
                    'id': int,
                    'nome': str,
                    'ordem': int,
                    'grupos': [
                        {
                            'id': int,
                            'nome': str,
                            'tarefas': [
                                {
                                    'id': int,
                                    'nome': str,
                                    'status': str,
                                    'percentual_conclusao': int,
                                    'ordem': int,
                                    'subtarefas': [
                                        {
                                            'id': int,
                                            'nome': str,
                                            'concluido': bool,
                                            'ordem': int
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    """
    logger.info(f"[GET_HIERARQUIA] INÍCIO - implantacao_id={implantacao_id}")
    
    # Buscar todas as fases - tratamento robusto de erros
    fases = None
    try:
        logger.info(f"[GET_HIERARQUIA] Buscando fases...")
        fases = query_db(
            "SELECT id, nome, ordem, responsavel FROM fases WHERE implantacao_id = %s ORDER BY ordem, id",
            (implantacao_id,)
        )
        logger.info(f"[GET_HIERARQUIA] Fases encontradas: {len(fases) if fases else 0}")
    except Exception as e1:
        logger.warning(f"[GET_HIERARQUIA] Erro ao buscar fases com responsavel: {e1}")
        # Coluna responsavel pode não existir ainda
        try:
            fases = query_db(
                "SELECT id, nome, ordem FROM fases WHERE implantacao_id = %s ORDER BY ordem, id",
                (implantacao_id,)
            )
            logger.info(f"[GET_HIERARQUIA] Fases encontradas (sem responsavel): {len(fases) if fases else 0}")
        except Exception as e2:
            # Tabela pode não existir - retorna vazio
            logger.error(f"[GET_HIERARQUIA] Erro crítico ao buscar fases: {e2}")
            return {'fases': []}
    
    if not fases:
        logger.info(f"[GET_HIERARQUIA] Nenhuma fase encontrada, retornando vazio")
        return {'fases': []}
    
    resultado = {'fases': []}
    
    for fase in fases:
        fase_dict = {
            'id': fase['id'],
            'nome': fase['nome'],
            'ordem': fase.get('ordem', 0),
            'responsavel': fase.get('responsavel') if isinstance(fase, dict) else None,
            'grupos': []
        }
        
        # Buscar grupos (ações) da fase
        grupos = None
        try:
            grupos = query_db(
                "SELECT id, nome, responsavel FROM grupos WHERE fase_id = %s ORDER BY id",
                (fase['id'],)
            )
        except Exception:
            try:
                grupos = query_db(
                    "SELECT id, nome FROM grupos WHERE fase_id = %s ORDER BY id",
                    (fase['id'],)
                )
            except Exception:
                grupos = []
        
        if not grupos:
            grupos = []
        
        for grupo in grupos:
            grupo_dict = {
                'id': grupo['id'],
                'nome': grupo['nome'],
                'responsavel': grupo.get('responsavel') if isinstance(grupo, dict) else None,
                'tarefas': []
            }
            
            # Buscar tarefas do grupo
            tarefas = None
            try:
                # Garantir que status nunca seja NULL - usar COALESCE
                tarefas = query_db(
                    "SELECT id, nome, COALESCE(status, 'pendente') as status, percentual_conclusao, ordem, responsavel FROM tarefas_h WHERE grupo_id = %s ORDER BY ordem, id",
                    (grupo['id'],)
                )
            except Exception:
                try:
                    # Garantir que status nunca seja NULL - usar COALESCE
                    tarefas = query_db(
                        "SELECT id, nome, COALESCE(status, 'pendente') as status, percentual_conclusao, ordem FROM tarefas_h WHERE grupo_id = %s ORDER BY ordem, id",
                        (grupo['id'],)
                    )
                except Exception:
                    tarefas = []
            
            if not tarefas:
                tarefas = []
            
            for tarefa in tarefas:
                # Normalizar status: garantir que seja sempre 'pendente' ou 'concluida'
                status_raw = tarefa.get('status') or 'pendente'
                status_normalizado = str(status_raw).lower().strip()
                
                logger.info(f"[GET_HIERARQUIA] Tarefa {tarefa['id']} - status_raw='{status_raw}', status_normalizado='{status_normalizado}'")
                
                # Normalizar para 'concluida' ou 'pendente'
                if status_normalizado == 'concluida':
                    status_normalizado = 'concluida'
                elif status_normalizado == 'concluido' or 'conclui' in status_normalizado:
                    status_normalizado = 'concluida'
                    logger.info(f"[GET_HIERARQUIA] Tarefa {tarefa['id']} - normalizado de '{status_raw}' para '{status_normalizado}'")
                else:
                    status_normalizado = 'pendente'
                
                tarefa_dict = {
                    'id': tarefa['id'],
                    'nome': tarefa['nome'],
                    'status': status_normalizado,  # Sempre 'pendente' ou 'concluida'
                    'percentual_conclusao': tarefa.get('percentual_conclusao', 0),
                    'ordem': tarefa.get('ordem', 0),
                    'responsavel': tarefa.get('responsavel') if isinstance(tarefa, dict) else None,
                    'subtarefas': []
                }
                
                # Buscar subtarefas da tarefa
                subtarefas = None
                try:
                    subtarefas = query_db(
                        "SELECT id, nome, concluido, ordem, responsavel FROM subtarefas_h WHERE tarefa_id = %s ORDER BY ordem, id",
                        (tarefa['id'],)
                    )
                except Exception:
                    try:
                        subtarefas = query_db(
                            "SELECT id, nome, concluido, ordem FROM subtarefas_h WHERE tarefa_id = %s ORDER BY ordem, id",
                            (tarefa['id'],)
                        )
                    except Exception:
                        subtarefas = []
                
                if not subtarefas:
                    subtarefas = []
                
                for subtarefa in subtarefas:
                    tarefa_dict['subtarefas'].append({
                        'id': subtarefa['id'],
                        'nome': subtarefa['nome'],
                        'concluido': subtarefa.get('concluido', False),
                        'ordem': subtarefa.get('ordem', 0),
                        'responsavel': subtarefa.get('responsavel') if isinstance(subtarefa, dict) else None
                    })
                
                grupo_dict['tarefas'].append(tarefa_dict)
            
            fase_dict['grupos'].append(grupo_dict)
        
        resultado['fases'].append(fase_dict)
    
    return resultado


def toggle_subtarefa(subtarefa_id):
    """
    Alterna o estado de conclusão de uma subtarefa.
    Atualiza o percentual de conclusão da tarefa pai.
    
    Returns:
        dict: {'ok': bool, 'concluido': bool, 'percentual_tarefa': int}
    """
    
    # Buscar subtarefa e tarefa pai
    subtarefa = query_db(
        "SELECT id, tarefa_id, concluido FROM subtarefas_h WHERE id = %s",
        (subtarefa_id,),
        one=True
    )
    
    if not subtarefa:
        return {'ok': False, 'error': 'Subtarefa não encontrada'}
    
    # Alternar estado
    novo_estado = not subtarefa['concluido']
    execute_db(
        "UPDATE subtarefas_h SET concluido = %s WHERE id = %s",
        (novo_estado, subtarefa_id)
    )
    
    # Calcular percentual da tarefa pai
    tarefa_id = subtarefa['tarefa_id']
    stats = query_db(
        """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN concluido = true THEN 1 ELSE 0 END) as concluidas
        FROM subtarefas_h
        WHERE tarefa_id = %s
        """,
        (tarefa_id,),
        one=True
    )
    
    if stats and stats['total'] > 0:
        percentual = int((stats['concluidas'] / stats['total']) * 100)
    else:
        percentual = 0
    
    # Atualizar percentual e status da tarefa
    novo_status = 'concluida' if percentual == 100 else ('em_andamento' if percentual > 0 else 'pendente')
    execute_db(
        "UPDATE tarefas_h SET percentual_conclusao = %s, status = %s WHERE id = %s",
        (percentual, novo_status, tarefa_id)
    )
    
    return {
        'ok': True,
        'concluido': novo_estado,
        'percentual_tarefa': percentual,
        'status_tarefa': novo_status
    }


def calcular_progresso_implantacao(implantacao_id):
    """
    Calcula o progresso geral da implantação baseado nas subtarefas.
    
    Returns:
        int: Percentual de 0 a 100
    """
    
    stats = query_db(
        """
        SELECT 
            COUNT(st.id) as total_subtarefas,
            SUM(CASE WHEN st.concluido = true THEN 1 ELSE 0 END) as subtarefas_concluidas
        FROM subtarefas_h st
        JOIN tarefas_h t ON t.id = st.tarefa_id
        JOIN grupos g ON g.id = t.grupo_id
        JOIN fases f ON f.id = g.fase_id
        WHERE f.implantacao_id = %s
        """,
        (implantacao_id,),
        one=True
    )
    
    if not stats or not stats['total_subtarefas'] or stats['total_subtarefas'] == 0:
        return 0
    
    percentual = int((stats['subtarefas_concluidas'] / stats['total_subtarefas']) * 100)
    return percentual


def adicionar_comentario_tarefa(tarefa_h_id, usuario_cs, texto, visibilidade='interno', imagem_url=None):
    """
    Adiciona um comentário a uma tarefa hierárquica.
    
    Returns:
        dict: Dados do comentário criado ou erro
    """
    
    # Verificar se a tarefa existe
    tarefa = query_db(
        "SELECT id FROM tarefas_h WHERE id = %s",
        (tarefa_h_id,),
        one=True
    )
    
    if not tarefa:
        return {'ok': False, 'error': 'Tarefa não encontrada'}
    
    # Inserir comentário
    comentario_id = execute_db(
        """
        INSERT INTO comentarios_h (tarefa_h_id, usuario_cs, texto, visibilidade, imagem_url)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (tarefa_h_id, usuario_cs, texto, visibilidade, imagem_url)
    )
    
    if not comentario_id:
        # Fallback para SQLite
        execute_db(
            """
            INSERT INTO comentarios_h (tarefa_h_id, usuario_cs, texto, visibilidade, imagem_url)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (tarefa_h_id, usuario_cs, texto, visibilidade, imagem_url)
        )
        comentario = query_db(
            "SELECT id FROM comentarios_h WHERE tarefa_h_id = %s AND usuario_cs = %s ORDER BY id DESC LIMIT 1",
            (tarefa_h_id, usuario_cs),
            one=True
        )
        comentario_id = comentario['id'] if comentario else None
    
    if not comentario_id:
        return {'ok': False, 'error': 'Erro ao criar comentário'}
    
    # Buscar comentário criado
    comentario = query_db(
        """
        SELECT id, tarefa_h_id, usuario_cs, texto, visibilidade, imagem_url, data_criacao
        FROM comentarios_h
        WHERE id = %s
        """,
        (comentario_id,),
        one=True
    )
    
    return {'ok': True, 'comentario': comentario}


def get_comentarios_tarefa(tarefa_h_id):
    """
    Retorna todos os comentários de uma tarefa hierárquica.
    
    Returns:
        list: Lista de comentários
    """
    
    comentarios = query_db(
        """
        SELECT id, tarefa_h_id, usuario_cs, texto, visibilidade, imagem_url, data_criacao
        FROM comentarios_h
        WHERE tarefa_h_id = %s
        ORDER BY data_criacao ASC
        """,
        (tarefa_h_id,)
    )
    
    return comentarios or []
