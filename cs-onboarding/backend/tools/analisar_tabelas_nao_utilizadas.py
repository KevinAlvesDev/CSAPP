#!/usr/bin/env python3
"""
Script para analisar todas as tabelas do banco de dados e identificar
quais não estão sendo mais utilizadas no código.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

def buscar_referencias_no_codigo():
    """
    Busca todas as referências a tabelas no código Python.
    Retorna um dicionário com tabela -> lista de arquivos que a referenciam.
    """
    backend_path = Path("backend")
    referencias = defaultdict(list)
    
    # Padrões de busca
    padroes = [
        "FROM {}",
        "INTO {}",
        "UPDATE {}",
        "DELETE FROM {}",
        "JOIN {}",
        "LEFT JOIN {}",
        "RIGHT JOIN {}",
        "INNER JOIN {}",
        "OUTER JOIN {}",
        "table_name = '{}'",
        "table_name = \"{}\"",
        "table_name='{}'",
        "table_name=\"{}\"",
    ]
    
    # Buscar em todos os arquivos Python
    for py_file in backend_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Ignorar comentários
                    if line.strip().startswith('#'):
                        continue
                    
                    # Buscar padrões SQL
                    for padrao in padroes:
                        # Tentar encontrar nomes de tabelas
                        # Assumir que nomes de tabelas são em minúsculas e podem ter underscore
                        pass
        except Exception:
            pass
    
    return referencias

def listar_todas_tabelas(conn, cursor, dialect):
    """
    Lista todas as tabelas do banco de dados.
    """
    tabelas = []
    
    if dialect == 'postgresql':
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tabelas = [row[0] for row in cursor.fetchall()]
    else:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tabelas = [row[0] for row in cursor.fetchall()]
    
    return tabelas

def buscar_referencias_simples(tabela, backend_path):
    """
    Busca referências simples a uma tabela no código.
    """
    referencias = []
    
    # Padrões de busca
    padroes = [
        f"FROM {tabela}",
        f"INTO {tabela}",
        f"UPDATE {tabela}",
        f"DELETE FROM {tabela}",
        f"JOIN {tabela}",
        f"LEFT JOIN {tabela}",
        f"RIGHT JOIN {tabela}",
        f"INNER JOIN {tabela}",
        f"OUTER JOIN {tabela}",
        f"'{tabela}'",
        f'"{tabela}"',
        f"`{tabela}`",
    ]
    
    for py_file in backend_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Ignorar comentários
                    if line.strip().startswith('#'):
                        continue
                    
                    for padrao in padroes:
                        if padrao in content:
                            referencias.append({
                                'arquivo': str(py_file),
                                'linha': line_num,
                                'conteudo': line.strip()[:100]
                            })
                            break
        except Exception:
            pass
    
    return referencias

def analisar_tabelas():
    """
    Analisa todas as tabelas do banco e identifica quais não estão sendo usadas.
    """
    print("=" * 80)
    print("ANÁLISE: Tabelas Não Utilizadas no Banco de Dados")
    print("=" * 80)
    print()
    
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada")
        return False
    
    try:
        parsed = urlparse(database_url)
        backend_path = Path("backend")
        
        if parsed.scheme == 'postgresql':
            import psycopg2
            from psycopg2.extras import DictCursor
            
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path.lstrip('/'),
                user=parsed.username,
                password=parsed.password
            )
            cursor = conn.cursor(cursor_factory=DictCursor)
            dialect = 'postgresql'
        else:
            import sqlite3
            db_path = parsed.path.replace('/', '') if parsed.path.startswith('/') else parsed.path
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            dialect = 'sqlite'
        
        print("✅ Conectado ao banco")
        print()
        
        # Listar todas as tabelas
        print("📊 Listando todas as tabelas do banco:")
        print("-" * 80)
        tabelas = listar_todas_tabelas(conn, cursor, dialect)
        
        print(f"   Total de tabelas encontradas: {len(tabelas)}")
        print()
        
        # Tabelas que já foram removidas (não devem aparecer)
        tabelas_removidas = [
            'fases', 'grupos', 'tarefas_h', 'subtarefas_h',
            'planos_fases', 'planos_grupos', 'planos_tarefas', 'planos_subtarefas'
        ]
        
        # Tabelas que são do sistema (não devem ser removidas)
        tabelas_sistema = [
            'alembic_version',  # Controle de migrations
        ]
        
        # Analisar cada tabela
        print("🔍 Analisando uso de cada tabela no código:")
        print("-" * 80)
        
        tabelas_nao_utilizadas = []
        tabelas_utilizadas = []
        tabelas_sistema_encontradas = []
        
        for tabela in tabelas:
            if tabela in tabelas_sistema:
                tabelas_sistema_encontradas.append(tabela)
                print(f"   ℹ️  {tabela} - Tabela do sistema (ignorada)")
                continue
            
            if tabela in tabelas_removidas:
                print(f"   ⚠️  {tabela} - DEVERIA TER SIDO REMOVIDA!")
                continue
            
            # Buscar referências no código
            referencias = buscar_referencias_simples(tabela, backend_path)
            
            if referencias:
                tabelas_utilizadas.append({
                    'tabela': tabela,
                    'referencias': len(referencias),
                    'arquivos': list(set([r['arquivo'] for r in referencias]))
                })
                print(f"   ✅ {tabela} - Utilizada ({len(referencias)} referências)")
            else:
                # Verificar se tem dados
                try:
                    if dialect == 'postgresql':
                        cursor.execute(f"SELECT COUNT(*) as total FROM {tabela}")
                        count = cursor.fetchone()['total']
                    else:
                        cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                        count = cursor.fetchone()[0]
                    
                    tabelas_nao_utilizadas.append({
                        'tabela': tabela,
                        'registros': count
                    })
                    
                    if count > 0:
                        print(f"   ⚠️  {tabela} - NÃO UTILIZADA (mas tem {count} registros)")
                    else:
                        print(f"   🗑️  {tabela} - NÃO UTILIZADA (vazia)")
                except Exception as e:
                    print(f"   ❌ {tabela} - Erro ao verificar: {e}")
        
        print()
        print("=" * 80)
        print("📋 RESUMO")
        print("=" * 80)
        print()
        
        print(f"✅ Tabelas utilizadas: {len(tabelas_utilizadas)}")
        print(f"⚠️  Tabelas não utilizadas: {len(tabelas_nao_utilizadas)}")
        print(f"ℹ️  Tabelas do sistema: {len(tabelas_sistema_encontradas)}")
        print()
        
        if tabelas_nao_utilizadas:
            print("🗑️  TABELAS NÃO UTILIZADAS:")
            print("-" * 80)
            
            tabelas_vazias = []
            tabelas_com_dados = []
            
            for item in tabelas_nao_utilizadas:
                if item['registros'] == 0:
                    tabelas_vazias.append(item['tabela'])
                else:
                    tabelas_com_dados.append(item)
            
            if tabelas_vazias:
                print("\n   Tabelas vazias (podem ser removidas com segurança):")
                for tabela in tabelas_vazias:
                    print(f"      - {tabela}")
            
            if tabelas_com_dados:
                print("\n   Tabelas com dados (verificar antes de remover):")
                for item in tabelas_com_dados:
                    print(f"      - {item['tabela']} ({item['registros']} registros)")
            
            print()
        
        # Listar todas as tabelas
        print("📊 TODAS AS TABELAS DO BANCO:")
        print("-" * 80)
        for tabela in sorted(tabelas):
            status = "✅" if any(t['tabela'] == tabela for t in tabelas_utilizadas) else "⚠️"
            print(f"   {status} {tabela}")
        
        print()
        print("=" * 80)
        
        if tabelas_nao_utilizadas:
            print("⚠️  RECOMENDAÇÃO:")
            print("   Verifique cada tabela não utilizada antes de removê-la.")
            print("   Algumas podem ser:")
            print("   - Tabelas de backup")
            print("   - Tabelas de logs antigos")
            print("   - Tabelas de cache")
            print("   - Tabelas que serão usadas no futuro")
        else:
            print("✅ Todas as tabelas estão sendo utilizadas!")
        
        print()
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    sucesso = analisar_tabelas()
    sys.exit(0 if sucesso else 1)

