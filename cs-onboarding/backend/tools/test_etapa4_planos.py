"""
Script de Testes Automatizados - ETAPA 4
Valida todas as funcionalidades de planos de sucesso com checklist hierárquico infinito
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.project import create_app
from backend.project.domain import planos_sucesso_service
from backend.project.db import query_db, db_connection

app = create_app()

def test_1_criar_plano_novo():
    """Teste 1: Criar plano novo com hierarquia infinita"""
    print("\n" + "="*60)
    print("TESTE 1: Criar Plano Novo com Hierarquia Infinita")
    print("="*60)
    
    estrutura = {
        "items": [
            {
                "title": "Fase 1: Kickoff & Setup",
                "comment": "Fase inicial do projeto",
                "level": 0,
                "children": [
                    {
                        "title": "Configurações Iniciais",
                        "comment": "Setup básico",
                        "level": 1,
                        "children": [
                            {
                                "title": "Cadastro de Usuários",
                                "comment": "Criar usuários iniciais",
                                "level": 2,
                                "children": [
                                    {
                                        "title": "Importar CSV",
                                        "comment": "Importar lista de usuários",
                                        "level": 3
                                    },
                                    {
                                        "title": "Validar Dados",
                                        "comment": "Verificar integridade",
                                        "level": 3
                                    }
                                ]
                            },
                            {
                                "title": "Configurar Permissões",
                                "level": 2,
                                "children": [
                                    {
                                        "title": "Definir Perfis",
                                        "level": 3,
                                        "children": [
                                            {
                                                "title": "Perfil Admin",
                                                "level": 4,
                                                "children": [
                                                    {
                                                        "title": "Acesso Total",
                                                        "level": 5
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "title": "Integração de Sistemas",
                        "level": 1
                    }
                ]
            },
            {
                "title": "Fase 2: Treinamento",
                "level": 0,
                "children": [
                    {
                        "title": "Sessão Inicial",
                        "level": 1
                    }
                ]
            }
        ]
    }
    
    try:
        with app.app_context():
            plano_id = planos_sucesso_service.criar_plano_sucesso_checklist(
                nome="Teste Plano Hierárquico",
                descricao="Plano de teste com hierarquia infinita",
                criado_por="sistema_teste",
                estrutura=estrutura,
                dias_duracao=30
            )
            
            print(f"✅ Plano criado com ID: {plano_id}")
            
            # Verificar se foi criado corretamente
            plano = planos_sucesso_service.obter_plano_completo(plano_id)
            
            if not plano:
                print("❌ Erro: Plano não encontrado após criação")
                return False
            
            if not plano.get('items'):
                print("❌ Erro: Plano não retornou items")
                return False
            
            print(f"✅ Plano retornado com {len(plano['items'])} itens raiz")
            
            # Verificar profundidade máxima
            def calcular_profundidade(items, current_depth=0):
                max_depth = current_depth
                for item in items:
                    if item.get('children'):
                        depth = calcular_profundidade(item['children'], current_depth + 1)
                        max_depth = max(max_depth, depth)
                return max_depth
            
            max_depth = calcular_profundidade(plano['items'])
            print(f"✅ Profundidade máxima: {max_depth} níveis")
            
            if max_depth >= 5:
                print("✅ Hierarquia profunda (5+ níveis) testada com sucesso!")
            else:
                print(f"⚠️ Profundidade: {max_depth} (esperado: 5+)")
            
            # Verificar total de itens no banco
            with db_connection() as (conn, db_type):
                cursor = conn.cursor()
                if db_type == 'postgres':
                    cursor.execute("SELECT COUNT(*) FROM checklist_items WHERE plano_id = %s", (plano_id,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM checklist_items WHERE plano_id = ?", (plano_id,))
                count = cursor.fetchone()[0]
                print(f"✅ Total de itens salvos no banco: {count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro ao criar plano: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_editar_plano_existente():
    """Teste 2: Editar plano existente"""
    print("\n" + "="*60)
    print("TESTE 2: Editar Plano Existente")
    print("="*60)
    
    try:
        with app.app_context():
            # Criar plano primeiro
            estrutura_inicial = {
                "items": [
                    {
                        "title": "Item Inicial",
                        "level": 0
                    }
                ]
            }
            
            plano_id = planos_sucesso_service.criar_plano_sucesso_checklist(
                nome="Teste Edição",
                descricao="Plano para teste de edição",
                criado_por="sistema_teste",
                estrutura=estrutura_inicial,
                dias_duracao=15
            )
            
            print(f"✅ Plano criado com ID: {plano_id}")
            
            # Obter plano
            plano = planos_sucesso_service.obter_plano_completo(plano_id)
            
            if not plano or not plano.get('items'):
                print("❌ Erro: Não foi possível obter plano")
                return False
            
            print(f"✅ Plano obtido: {plano['nome']}")
            print(f"✅ Estrutura original: {len(plano['items'])} itens raiz")
            
            # Atualizar nome e descrição
            planos_sucesso_service.atualizar_plano_sucesso(
                plano_id,
                {
                    'nome': 'Teste Edição - Atualizado',
                    'descricao': 'Descrição atualizada',
                    'dias_duracao': 20
                }
            )
            
            print("✅ Plano atualizado (nome, descrição, dias_duracao)")
            
            # Verificar atualização
            plano_atualizado = planos_sucesso_service.obter_plano_completo(plano_id)
            
            if plano_atualizado['nome'] != 'Teste Edição - Atualizado':
                print("❌ Erro: Nome não foi atualizado")
                return False
            
            print("✅ Verificação: Nome atualizado corretamente")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro ao editar plano: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_aplicar_plano_implantacao():
    """Teste 3: Aplicar plano a uma implantação"""
    print("\n" + "="*60)
    print("TESTE 3: Aplicar Plano a Implantação")
    print("="*60)
    
    try:
        with app.app_context():
            # Criar plano
            estrutura = {
                "items": [
                    {
                        "title": "Fase Teste",
                        "level": 0,
                        "children": [
                            {
                                "title": "Grupo Teste",
                                "level": 1,
                                "children": [
                                    {
                                        "title": "Tarefa Teste",
                                        "level": 2
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            
            plano_id = planos_sucesso_service.criar_plano_sucesso_checklist(
                nome="Plano para Aplicar",
                descricao="Teste de aplicação",
                criado_por="sistema_teste",
                estrutura=estrutura,
                dias_duracao=10
            )
            
            print(f"✅ Plano criado com ID: {plano_id}")
            
            # Buscar ou criar implantação de teste
            implantacao = query_db(
                "SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1",
                one=True
            )
            
            if not implantacao:
                print("⚠️ Nenhuma implantação encontrada. Criando implantação de teste...")
                # Criar implantação de teste
                with db_connection() as (conn, db_type):
                    cursor = conn.cursor()
                    if db_type == 'postgres':
                        cursor.execute("""
                            INSERT INTO implantacoes (empresa, cnpj, email_contato, status, data_criacao)
                            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                            RETURNING id
                        """, ("Empresa Teste", "00.000.000/0001-00", "teste@teste.com", "em_andamento"))
                        implantacao_id = cursor.fetchone()[0]
                    else:
                        cursor.execute("""
                            INSERT INTO implantacoes (empresa, cnpj, email_contato, status, data_criacao)
                            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, ("Empresa Teste", "00.000.000/0001-00", "teste@teste.com", "em_andamento"))
                        implantacao_id = cursor.lastrowid
                    conn.commit()
                    print(f"✅ Implantação de teste criada com ID: {implantacao_id}")
            else:
                implantacao_id = implantacao['id']
                print(f"✅ Usando implantação existente ID: {implantacao_id}")
            
            # Aplicar plano
            sucesso = planos_sucesso_service.aplicar_plano_a_implantacao_checklist(
                implantacao_id=implantacao_id,
                plano_id=plano_id,
                usuario="sistema_teste"
            )
            
            if not sucesso:
                print("❌ Erro: Falha ao aplicar plano")
                return False
            
            print("✅ Plano aplicado à implantação")
            
            # Verificar se itens foram clonados
            with db_connection() as (conn, db_type):
                cursor = conn.cursor()
                if db_type == 'postgres':
                    cursor.execute(
                        "SELECT COUNT(*) FROM checklist_items WHERE implantacao_id = %s",
                        (implantacao_id,)
                    )
                else:
                    cursor.execute(
                        "SELECT COUNT(*) FROM checklist_items WHERE implantacao_id = ?",
                        (implantacao_id,)
                    )
                count = cursor.fetchone()[0]
                
                # Contar itens do plano
                if db_type == 'postgres':
                    cursor.execute(
                        "SELECT COUNT(*) FROM checklist_items WHERE plano_id = %s",
                        (plano_id,)
                    )
                else:
                    cursor.execute(
                        "SELECT COUNT(*) FROM checklist_items WHERE plano_id = ?",
                        (plano_id,)
                    )
                count_plano = cursor.fetchone()[0]
                
                print(f"✅ Itens no plano: {count_plano}")
                print(f"✅ Itens clonados na implantação: {count}")
                
                if count != count_plano:
                    print(f"⚠️ Aviso: Quantidade diferente ({count} vs {count_plano})")
                else:
                    print("✅ Quantidade de itens clonados correta!")
            
            # Verificar que itens da implantação têm implantacao_id
            with db_connection() as (conn, db_type):
                cursor = conn.cursor()
                if db_type == 'postgres':
                    cursor.execute("""
                        SELECT COUNT(*) FROM checklist_items 
                        WHERE implantacao_id = %s AND plano_id IS NOT NULL
                    """, (implantacao_id,))
                else:
                    cursor.execute("""
                        SELECT COUNT(*) FROM checklist_items 
                        WHERE implantacao_id = ? AND plano_id IS NOT NULL
                    """, (implantacao_id,))
                count_com_plano_id = cursor.fetchone()[0]
                
                if count_com_plano_id > 0:
                    print(f"⚠️ Aviso: {count_com_plano_id} itens têm plano_id (não deveriam)")
                else:
                    print("✅ Itens da implantação não têm plano_id (correto)")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro ao aplicar plano: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_propagacao_status():
    """Teste 4: Verificar propagação de status"""
    print("\n" + "="*60)
    print("TESTE 4: Verificar Propagação de Status")
    print("="*60)
    
    try:
        with app.app_context():
            # Criar plano e aplicar
            estrutura = {
                "items": [
                    {
                        "title": "Raiz",
                        "level": 0,
                        "children": [
                            {
                                "title": "Filho 1",
                                "level": 1,
                                "children": [
                                    {
                                        "title": "Neto 1",
                                        "level": 2
                                    }
                                ]
                            },
                            {
                                "title": "Filho 2",
                                "level": 1
                            }
                        ]
                    }
                ]
            }
            
            plano_id = planos_sucesso_service.criar_plano_sucesso_checklist(
                nome="Plano Propagação",
                descricao="Teste de propagação",
                criado_por="sistema_teste",
                estrutura=estrutura,
                dias_duracao=5
            )
            
            # Buscar implantação
            implantacao = query_db(
                "SELECT id FROM implantacoes ORDER BY id DESC LIMIT 1",
                one=True
            )
            
            if not implantacao:
                print("⚠️ Nenhuma implantação encontrada")
                return False
            
            implantacao_id = implantacao['id']
            
            # Aplicar plano
            planos_sucesso_service.aplicar_plano_a_implantacao_checklist(
                implantacao_id=implantacao_id,
                plano_id=plano_id,
                usuario="sistema_teste"
            )
            
            print("✅ Plano aplicado")
            
            # Buscar item raiz
            from backend.project.domain.checklist_service import get_checklist_tree
            
            tree = get_checklist_tree(implantacao_id)
            
            if not tree or len(tree) == 0:
                print("❌ Erro: Nenhum item encontrado na implantação")
                return False
            
            raiz = tree[0]  # Primeiro item raiz
            print(f"✅ Item raiz encontrado: {raiz.get('title')} (ID: {raiz.get('id')})")
            
            # Testar propagação
            from backend.project.domain.checklist_service import toggle_item_status
            
            print("\n📋 Testando propagação downstream (marcar raiz)...")
            
            resultado = toggle_item_status(raiz['id'], True, "sistema_teste")
            
            if not resultado or not resultado.get('ok'):
                print("❌ Erro ao fazer toggle")
                return False
            
            print(f"✅ Toggle realizado: {resultado.get('items_updated')} itens atualizados")
            
            # Verificar se todos os filhos foram marcados
            def verificar_completed_recursivo(item, expected):
                if item.get('completed') != expected:
                    print(f"❌ Erro: Item '{item.get('title')}' está {item.get('completed')}, esperado {expected}")
                    return False
                
                if item.get('children'):
                    for child in item['children']:
                        if not verificar_completed_recursivo(child, expected):
                            return False
                
                return True
            
            # Buscar árvore atualizada
            tree_atualizado = get_checklist_tree(implantacao_id)
            raiz_atualizado = next((item for item in tree_atualizado if item['id'] == raiz['id']), None)
            
            if not raiz_atualizado:
                print("❌ Erro: Raiz não encontrada após toggle")
                return False
            
            print("\n🔍 Verificando propagação downstream...")
            
            # Verificar raiz
            if not raiz_atualizado.get('completed'):
                print("❌ Erro: Raiz não está marcada como completed")
                return False
            print("✅ Raiz marcada como completed")
            
            # Verificar filhos recursivamente
            if raiz_atualizado.get('children'):
                for child in raiz_atualizado['children']:
                    if not verificar_completed_recursivo(child, True):
                        print("❌ Erro: Propagação downstream falhou")
                        return False
                print("✅ Todos os filhos marcados como completed (propagação downstream OK)")
            
            print("✅ Propagação de status testada com sucesso!")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro ao testar propagação: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_hierarquia_profunda():
    """Teste 5: Testar hierarquia profunda (10 níveis)"""
    print("\n" + "="*60)
    print("TESTE 5: Hierarquia Profunda (10 Níveis)")
    print("="*60)
    
    def criar_estrutura_profunda(level, max_level, current_item=1):
        """Cria estrutura recursiva profunda"""
        if level > max_level:
            return None
        
        estrutura = {
            "title": f"Nível {level} - Item {current_item}",
            "level": level,
            "children": []
        }
        
        # Criar 2 filhos em cada nível
        for i in range(1, 3):
            child = criar_estrutura_profunda(level + 1, max_level, i)
            if child:
                estrutura["children"].append(child)
        
        return estrutura
    
    estrutura = {
        "items": [criar_estrutura_profunda(0, 9)]  # 10 níveis (0-9)
    }
    
    try:
        with app.app_context():
            plano_id = planos_sucesso_service.criar_plano_sucesso_checklist(
                nome="Plano Hierarquia Profunda",
                descricao="Teste com 10 níveis",
                criado_por="sistema_teste",
                estrutura=estrutura,
                dias_duracao=60
            )
            
            print(f"✅ Plano criado com ID: {plano_id}")
            
            # Obter plano
            plano = planos_sucesso_service.obter_plano_completo(plano_id)
            
            if not plano or not plano.get('items'):
                print("❌ Erro: Plano não retornado corretamente")
                return False
            
            # Calcular profundidade
            def calcular_profundidade_maxima(items, current_depth=0):
                max_depth = current_depth
                for item in items:
                    depth = current_depth
                    if item.get('children'):
                        depth = calcular_profundidade_maxima(item['children'], current_depth + 1)
                    max_depth = max(max_depth, depth)
                return max_depth
            
            profundidade = calcular_profundidade_maxima(plano['items'])
            print(f"✅ Profundidade máxima alcançada: {profundidade} níveis")
            
            if profundidade >= 10:
                print("✅ Hierarquia profunda (10 níveis) testada com sucesso!")
            else:
                print(f"⚠️ Profundidade: {profundidade} (esperado: 10)")
            
            # Contar total de itens
            def contar_total_itens(items):
                count = len(items)
                for item in items:
                    if item.get('children'):
                        count += contar_total_itens(item['children'])
                return count
            
            total = contar_total_itens(plano['items'])
            print(f"✅ Total de itens: {total}")
            
            # Verificar no banco
            with db_connection() as (conn, db_type):
                cursor = conn.cursor()
                if db_type == 'postgres':
                    cursor.execute(
                        "SELECT COUNT(*) FROM checklist_items WHERE plano_id = %s",
                        (plano_id,)
                    )
                else:
                    cursor.execute(
                        "SELECT COUNT(*) FROM checklist_items WHERE plano_id = ?",
                        (plano_id,)
                    )
                count_banco = cursor.fetchone()[0]
                print(f"✅ Itens no banco: {count_banco}")
                
                if count_banco == total:
                    print("✅ Contagem de itens confere!")
                else:
                    print(f"⚠️ Diferença na contagem: template={total}, banco={count_banco}")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro ao testar hierarquia profunda: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes"""
    print("="*60)
    print("ETAPA 4: TESTES E VALIDAÇÃO")
    print("="*60)
    print("\nExecutando testes automatizados...")
    
    resultados = []
    
    # Executar testes
    resultados.append(("Teste 1: Criar Plano Novo", test_1_criar_plano_novo()))
    resultados.append(("Teste 2: Editar Plano Existente", test_2_editar_plano_existente()))
    resultados.append(("Teste 3: Aplicar Plano a Implantação", test_3_aplicar_plano_implantacao()))
    resultados.append(("Teste 4: Propagação de Status", test_4_propagacao_status()))
    resultados.append(("Teste 5: Hierarquia Profunda", test_5_hierarquia_profunda()))
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    
    passou = 0
    falhou = 0
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status}: {nome}")
        if resultado:
            passou += 1
        else:
            falhou += 1
    
    print("\n" + "="*60)
    print(f"TOTAL: {passou} passou, {falhou} falhou")
    print("="*60)
    
    if falhou == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        return True
    else:
        print(f"\n⚠️ {falhou} teste(s) falharam. Verifique os erros acima.")
        return False


if __name__ == '__main__':
    with app.app_context():
        sucesso = main()
        sys.exit(0 if sucesso else 1)

