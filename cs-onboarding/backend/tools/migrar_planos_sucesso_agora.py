#!/usr/bin/env python3
"""
Script para forçar a migração das colunas data_atualizacao e dias_duracao
na tabela planos_sucesso.
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project import create_app
from project.database.db_pool import get_db_connection

def migrar_planos_sucesso():
    """Força a migração das colunas faltantes em planos_sucesso."""
    app = create_app()
    with app.app_context():
        conn, db_type = None, None
        try:
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            
            if db_type == 'sqlite':
                # Verificar colunas existentes
                cursor.execute("PRAGMA table_info(planos_sucesso)")
                colunas_existentes = [row[1] for row in cursor.fetchall()]
                
                colunas_para_adicionar = {
                    'data_atualizacao': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
                    'dias_duracao': 'INTEGER'
                }
                
                colunas_adicionadas = 0
                for coluna, tipo in colunas_para_adicionar.items():
                    if coluna not in colunas_existentes:
                        try:
                            cursor.execute(f"ALTER TABLE planos_sucesso ADD COLUMN {coluna} {tipo}")
                            print(f"✅ Coluna '{coluna}' adicionada com sucesso!")
                            colunas_adicionadas += 1
                        except Exception as e:
                            print(f"❌ Erro ao adicionar coluna '{coluna}': {e}")
                
                if colunas_adicionadas > 0:
                    conn.commit()
                    print(f"\n✅ {colunas_adicionadas} coluna(s) adicionada(s) à tabela planos_sucesso!")
                else:
                    print("\n✅ Todas as colunas já existem na tabela planos_sucesso!")
            else:
                print("⚠️  Este script é apenas para SQLite. Para PostgreSQL, use migrations do Alembic.")
            
        except Exception as e:
            print(f"❌ Erro ao migrar: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn and db_type == 'sqlite':
                conn.close()

if __name__ == '__main__':
    print("🔄 Iniciando migração de planos_sucesso...\n")
    migrar_planos_sucesso()
    print("\n✅ Migração concluída!")

