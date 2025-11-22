# -*- coding: utf-8 -*-
"""
Script para popular o banco de dados com a estrutura hierárquica padrão.
Este script cria Fases -> Grupos -> Tarefas -> Subtarefas para cada implantação.
"""

import sys
import os
import importlib.util

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from project import create_app
from project.db import get_db_connection, execute_db, query_db

# Carregar estrutura hierárquica
estrutura_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'project', 'estrutura_hierarquica.py')
spec = importlib.util.spec_from_file_location("estrutura_hierarquica", estrutura_path)
estrutura_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(estrutura_module)
ESTRUTURA_PADRAO = estrutura_module.ESTRUTURA_PADRAO

def popular_estrutura_hierarquica(implantacao_id):
    """
    Popula a estrutura hierárquica completa para uma implantação.
    
    Args:
        implantacao_id: ID da implantação
    """
    print(f"\n>> Populando estrutura para implantacao ID {implantacao_id}...")
    
    # Limpar estrutura existente (se houver)
    print("  >> Limpando estrutura antiga...")
    execute_db("DELETE FROM subtarefas_h WHERE tarefa_id IN (SELECT id FROM tarefas_h WHERE grupo_id IN (SELECT id FROM grupos WHERE fase_id IN (SELECT id FROM fases WHERE implantacao_id = %s)))", (implantacao_id,))
    execute_db("DELETE FROM tarefas_h WHERE grupo_id IN (SELECT id FROM grupos WHERE fase_id IN (SELECT id FROM fases WHERE implantacao_id = %s))", (implantacao_id,))
    execute_db("DELETE FROM grupos WHERE fase_id IN (SELECT id FROM fases WHERE implantacao_id = %s)", (implantacao_id,))
    execute_db("DELETE FROM fases WHERE implantacao_id = %s", (implantacao_id,))
    
    # Criar fases
    for fase_def in ESTRUTURA_PADRAO["fases"]:
        print(f"  >> Criando fase: {fase_def['nome']}")
        
        fase_id = execute_db(
            "INSERT INTO fases (implantacao_id, nome, ordem) VALUES (%s, %s, %s) RETURNING id",
            (implantacao_id, fase_def['nome'], fase_def['ordem'])
        )
        
        if not fase_id:
            # Fallback para SQLite
            execute_db(
                "INSERT INTO fases (implantacao_id, nome, ordem) VALUES (%s, %s, %s)",
                (implantacao_id, fase_def['nome'], fase_def['ordem'])
            )
            fase_result = query_db(
                "SELECT id FROM fases WHERE implantacao_id = %s AND nome = %s",
                (implantacao_id, fase_def['nome']),
                one=True
            )
            fase_id = fase_result['id'] if fase_result else None
        
        if not fase_id:
            print(f"    [ERRO] Erro ao criar fase: {fase_def['nome']}")
            continue
        
        # Criar grupos dentro da fase
        for grupo_def in fase_def.get('grupos', []):
            print(f"    >> Criando grupo: {grupo_def['nome']}")
            
            grupo_id = execute_db(
                "INSERT INTO grupos (fase_id, nome) VALUES (%s, %s) RETURNING id",
                (fase_id, grupo_def['nome'])
            )
            
            if not grupo_id:
                # Fallback para SQLite
                execute_db(
                    "INSERT INTO grupos (fase_id, nome) VALUES (%s, %s)",
                    (fase_id, grupo_def['nome'])
                )
                grupo_result = query_db(
                    "SELECT id FROM grupos WHERE fase_id = %s AND nome = %s",
                    (fase_id, grupo_def['nome']),
                    one=True
                )
                grupo_id = grupo_result['id'] if grupo_result else None
            
            if not grupo_id:
                print(f"      [ERRO] Erro ao criar grupo: {grupo_def['nome']}")
                continue
            
            # Criar tarefas dentro do grupo
            for idx, tarefa_def in enumerate(grupo_def.get('tarefas', []), start=1):
                print(f"      >> Criando tarefa: {tarefa_def['nome']}")
                
                tarefa_id = execute_db(
                    "INSERT INTO tarefas_h (grupo_id, nome, status, percentual_conclusao, ordem) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (grupo_id, tarefa_def['nome'], 'pendente', 0, idx)
                )
                
                if not tarefa_id:
                    # Fallback para SQLite
                    execute_db(
                        "INSERT INTO tarefas_h (grupo_id, nome, status, percentual_conclusao, ordem) VALUES (%s, %s, %s, %s, %s)",
                        (grupo_id, tarefa_def['nome'], 'pendente', 0, idx)
                    )
                    tarefa_result = query_db(
                        "SELECT id FROM tarefas_h WHERE grupo_id = %s AND nome = %s",
                        (grupo_id, tarefa_def['nome']),
                        one=True
                    )
                    tarefa_id = tarefa_result['id'] if tarefa_result else None
                
                if not tarefa_id:
                    print(f"        [ERRO] Erro ao criar tarefa: {tarefa_def['nome']}")
                    continue
                
                # Criar subtarefas dentro da tarefa
                for sub_idx, subtarefa_nome in enumerate(tarefa_def.get('subtarefas', []), start=1):
                    print(f"        >> Criando subtarefa: {subtarefa_nome}")
                    
                    execute_db(
                        "INSERT INTO subtarefas_h (tarefa_id, nome, concluido, ordem) VALUES (%s, %s, %s, %s)",
                        (tarefa_id, subtarefa_nome, False, sub_idx)
                    )
    
    print(f"[OK] Estrutura criada com sucesso para implantacao ID {implantacao_id}!\n")


def popular_todas_implantacoes():
    """Popula a estrutura hierárquica para TODAS as implantações existentes."""
    
    print("\n" + "="*60)
    print("  POPULANDO ESTRUTURA HIERARQUICA PARA TODAS AS IMPLANTACOES")
    print("="*60)
    
    # Buscar todas as implantações
    implantacoes = query_db("SELECT id, nome_empresa FROM implantacoes ORDER BY id")
    
    if not implantacoes:
        print("[ERRO] Nenhuma implantacao encontrada no banco de dados.")
        return
    
    print(f"\n>> Encontradas {len(implantacoes)} implantacoes.\n")
    
    for impl in implantacoes:
        print(f"{'-'*60}")
        print(f">> Implantacao: {impl['nome_empresa']} (ID: {impl['id']})")
        print(f"{'-'*60}")
        popular_estrutura_hierarquica(impl['id'])
    
    # Estatísticas finais
    print("\n" + "="*60)
    print("  ESTATISTICAS FINAIS")
    print("="*60 + "\n")
    
    stats = query_db("""
        SELECT 
            'Fases' as item, COUNT(*) as total FROM fases
        UNION ALL
        SELECT 'Grupos', COUNT(*) FROM grupos
        UNION ALL
        SELECT 'Tarefas', COUNT(*) FROM tarefas_h
        UNION ALL
        SELECT 'Subtarefas', COUNT(*) FROM subtarefas_h
    """)
    
    for stat in stats:
        print(f"  {stat['item']:20} {stat['total']:>6}")
    
    print("\n" + "="*60)
    print("[OK] MIGRACAO CONCLUIDA COM SUCESSO!")
    print("="*60 + "\n")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        popular_todas_implantacoes()
