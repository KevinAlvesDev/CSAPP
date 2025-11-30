#!/usr/bin/env python3
"""
Script para verificar se há colunas faltantes em tabelas que podem causar erros.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project import create_app
from project.database.db_pool import get_db_connection

def verificar_colunas():
    """Verifica colunas faltantes em tabelas críticas."""
    app = create_app()
    with app.app_context():
        conn, db_type = None, None
        try:
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            
            if db_type == 'sqlite':
                print("🔍 Verificando colunas em tabelas críticas...\n")
                
                # Verificar planos_sucesso
                print("📋 Tabela: planos_sucesso")
                cursor.execute("PRAGMA table_info(planos_sucesso)")
                colunas_planos = [row[1] for row in cursor.fetchall()]
                print(f"   Colunas existentes: {', '.join(colunas_planos)}")
                
                colunas_esperadas_planos = ['id', 'nome', 'descricao', 'criado_por', 'data_criacao', 
                                           'data_atualizacao', 'dias_duracao', 'ativo']
                faltantes_planos = [c for c in colunas_esperadas_planos if c not in colunas_planos]
                if faltantes_planos:
                    print(f"   ❌ Colunas faltantes: {', '.join(faltantes_planos)}")
                else:
                    print("   ✅ Todas as colunas esperadas estão presentes")
                
                print()
                
                # Verificar implantacoes (pode ter muitas colunas)
                print("📋 Tabela: implantacoes")
                cursor.execute("PRAGMA table_info(implantacoes)")
                colunas_impl = [row[1] for row in cursor.fetchall()]
                print(f"   Total de colunas: {len(colunas_impl)}")
                
                # Verificar algumas colunas críticas que foram adicionadas recentemente
                colunas_criticas_impl = ['wellhub', 'totalpass', 'modelo_catraca', 'modelo_facial',
                                        'cargo_responsavel', 'telefone_responsavel']
                faltantes_impl = [c for c in colunas_criticas_impl if c not in colunas_impl]
                if faltantes_impl:
                    print(f"   ❌ Colunas críticas faltantes: {', '.join(faltantes_impl)}")
                else:
                    print("   ✅ Colunas críticas estão presentes")
                
                print()
                
                # Verificar timeline_log
                print("📋 Tabela: timeline_log")
                cursor.execute("PRAGMA table_info(timeline_log)")
                colunas_timeline = [row[1] for row in cursor.fetchall()]
                print(f"   Colunas existentes: {', '.join(colunas_timeline)}")
                
                if 'detalhes' not in colunas_timeline:
                    print("   ❌ Coluna 'detalhes' faltante")
                else:
                    print("   ✅ Coluna 'detalhes' presente")
                
            else:
                print("⚠️  Este script é apenas para SQLite.")
        
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if conn and db_type == 'sqlite':
                conn.close()

if __name__ == '__main__':
    verificar_colunas()

