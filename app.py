import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import webbrowser
import threading
from collections import OrderedDict
from datetime import datetime

# ===============================================
# CONFIGURAÇÃO INICIAL
# ===============================================
app = Flask(__name__)
app.secret_key = 'chave_secreta_dashboard_simples'
DATABASE = 'dashboard_simples.db'

# ===============================================
# PADRÃO DE TAREFAS DE IMPLANTAÇÃO
# ===============================================
TAREFAS_PADRAO = {
    "Welcome": [
        "Contato Inicial Whatsapp/Grupo",
        "Criar Banco de Dados",
        "Criar Usuário do Proprietário",
        "Reunião de Kick-Off"
    ],
    "Estruturação de BD": [
        "Configurar planos",
        "Configurar modelo de contrato",
        "Configurar logo da empresa",
        "Convênio de cobrança",
        "Criar App Treino",
        "Nota Fiscal"
    ],
    "Importação de dados": [
        "Jira de implantação de dados",
        "Importação de cartões de crédito"
    ],
    "Módulo ADM": [
        "Treinamento Operacional 1",
        "Treinamento Operacional 2",
        "Treinamento Gerencial",
        "Verificação de Importação",
        "Controle de acesso"
    ],
    "Módulo Treino": [
        "Estrutural",
        "Operacional",
        "Agenda",
        "Treino Gerencial"
    ],
    "Módulo CRM": [
        "Estrutural",
        "Operacional",
        "Gerencial"
    ],
    "Módulo Financeiro": [
        "Financeiro Simplificado",
        "Financeiro Avançado"
    ],
    "Conclusão": [
        "Tira dúvidas",
        "Concluir processos internos"
    ]
}

# ===============================================
# FUNÇÕES DE BANCO DE DADOS
# ===============================================
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Usando 'senha' para guardar o hash, mas o nome da coluna é mantido para compatibilidade
        cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT NOT NULL)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS perfil_usuario (
                usuario TEXT PRIMARY KEY,
                nome TEXT,
                impl_andamento INTEGER DEFAULT 0,
                impl_finalizadas INTEGER DEFAULT 0,
                impl_paradas INTEGER DEFAULT 0,
                progresso_medio_carteira INTEGER DEFAULT 0,
                impl_andamento_total INTEGER DEFAULT 0,
                implantacoes_atrasadas INTEGER DEFAULT 0,
                FOREIGN KEY(usuario) REFERENCES usuarios(usuario) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS implantacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_cs TEXT NOT NULL,
                nome_empresa TEXT NOT NULL,
                status TEXT DEFAULT 'andamento',
                tipo TEXT DEFAULT 'agora',
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_finalizacao DATETIME,
                FOREIGN KEY(usuario_cs) REFERENCES usuarios(usuario) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                implantacao_id INTEGER NOT NULL,
                tarefa_pai TEXT NOT NULL,
                tarefa_filho TEXT NOT NULL,
                concluida INTEGER DEFAULT 0,
                observacao TEXT DEFAULT '',
                FOREIGN KEY(implantacao_id) REFERENCES implantacoes(id) ON DELETE CASCADE
            )
        """)

        # Adiciona coluna tipo caso não exista (para bancos antigos)
        try:
            cursor.execute("ALTER TABLE implantacoes ADD COLUMN tipo TEXT DEFAULT 'agora'")
            db.commit()
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tarefas ADD COLUMN observacao TEXT DEFAULT ''")
            db.commit()
        except sqlite3.OperationalError:
            pass

        # --- NOVA COLUNA 'ordem' (para persistir ordem das sub-tarefas) ---
        try:
            cursor.execute("ALTER TABLE tarefas ADD COLUMN ordem INTEGER DEFAULT 0")
            db.commit()
        except sqlite3.OperationalError:
            pass

        db.commit()

# ===============================================
# SUPORTE DE DADOS
# ===============================================
def get_perfil_metrics(usuario):
    db = get_db()
    perfil = db.execute("SELECT * FROM perfil_usuario WHERE usuario = ?", (usuario,)).fetchone()
    metrics = dict(perfil) if perfil else {}
    if 'impl_andamento_total' not in metrics:
        metrics['impl_andamento_total'] = 0
    return metrics

def get_implantacoes_em_andamento(usuario):
    db = get_db()
    implantacoes = db.execute(
        "SELECT id, nome_empresa FROM implantacoes WHERE usuario_cs = ? AND status = 'andamento' AND tipo='agora'",
        (usuario,)
    ).fetchall()
    result = []
    for i in implantacoes:
        impl = dict(i)
        # calcula progresso baseado nas tarefas
        counts = db.execute(
            "SELECT COUNT(*) as total, SUM(concluida) as done FROM tarefas WHERE implantacao_id = ?",
            (impl['id'],)
        ).fetchone()
        total = counts['total'] or 0
        done = counts['done'] or 0
        progresso = int(round((done / total) * 100)) if total > 0 else 0
        impl['progresso'] = progresso
        impl['tarefas_total'] = total
        impl['tarefas_concluidas'] = done
        result.append(impl)
    return result

def get_implantacoes_futuras(usuario):
    db = get_db()
    implantacoes = db.execute(
        "SELECT id, nome_empresa FROM implantacoes WHERE usuario_cs = ? AND tipo='futura'",
        (usuario,)
    ).fetchall()
    result = []
    for i in implantacoes:
        impl = dict(i)
        counts = db.execute(
            "SELECT COUNT(*) as total, SUM(concluida) as done FROM tarefas WHERE implantacao_id = ?",
            (impl['id'],)
        ).fetchone()
        total = counts['total'] or 0
        done = counts['done'] or 0
        progresso = int(round((done / total) * 100)) if total > 0 else 0
        impl['progresso'] = progresso
        impl['tarefas_total'] = total
        impl['tarefas_concluidas'] = done
        result.append(impl)
    return result

def get_implantacoes_finalizadas(usuario):
    db = get_db()
    implantacoes = db.execute(
        "SELECT id, nome_empresa FROM implantacoes WHERE usuario_cs = ? AND status = 'finalizada'",
        (usuario,)
    ).fetchall()
    result = []
    for i in implantacoes:
        impl = dict(i)
        counts = db.execute(
            "SELECT COUNT(*) as total, SUM(concluida) as done FROM tarefas WHERE implantacao_id = ?",
            (impl['id'],)
        ).fetchone()
        total = counts['total'] or 0
        done = counts['done'] or 0
        progresso = int(round((done / total) * 100)) if total > 0 else 0
        impl['progresso'] = progresso
        impl['tarefas_total'] = total
        impl['tarefas_concluidas'] = done
        result.append(impl)
    return result

def get_implantacoes_paradas(usuario):
    db = get_db()
    implantacoes = db.execute(
        "SELECT id, nome_empresa FROM implantacoes WHERE usuario_cs = ? AND status = 'parada'",
        (usuario,)
    ).fetchall()
    result = []
    for i in implantacoes:
        impl = dict(i)
        counts = db.execute(
            "SELECT COUNT(*) as total, SUM(concluida) as done FROM tarefas WHERE implantacao_id = ?",
            (impl['id'],)
        ).fetchone()
        total = counts['total'] or 0
        done = counts['done'] or 0
        progresso = int(round((done / total) * 100)) if total > 0 else 0
        impl['progresso'] = progresso
        impl['tarefas_total'] = total
        impl['tarefas_concluidas'] = done
        result.append(impl)
    return result

def get_implantacoes_atrasadas(usuario, dias=25):
    db = get_db()
    rows = db.execute(
        "SELECT id, nome_empresa, data_criacao FROM implantacoes "
        "WHERE usuario_cs = ? AND tipo = 'agora' AND status = 'andamento' "
        "AND (julianday('now') - julianday(data_criacao)) > ?",
        (usuario, dias)
    ).fetchall()

    result = []
    for r in rows:
        impl = dict(r)
        counts = db.execute(
            "SELECT COUNT(*) as total, SUM(concluida) as done FROM tarefas WHERE implantacao_id = ?",
            (impl['id'],)
        ).fetchone()
        total = counts['total'] or 0
        done = counts['done'] or 0
        impl['progresso'] = int(round((done / total) * 100)) if total > 0 else 0
        impl['tarefas_total'] = total
        impl['tarefas_concluidas'] = done
        result.append(impl)
    return result

# ===============================================
# ROTAS PRINCIPAIS
# ===============================================
@app.route('/')
def home():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    # CORREÇÃO: Redireciona para o endpoint correto 'login_cadastro'
    return redirect(url_for('login_cadastro'))

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))

    usuario = session['usuario']
    metrics = get_perfil_metrics(usuario)
    implantacoes_andamento = get_implantacoes_em_andamento(usuario)
    implantacoes_futuras = get_implantacoes_futuras(usuario)
    implantacoes_finalizadas = get_implantacoes_finalizadas(usuario)
    implantacoes_paradas = get_implantacoes_paradas(usuario)

    # novas implantações atrasadas (apenas >25 dias desde data_criacao e em andamento)
    implantacoes_atrasadas = get_implantacoes_atrasadas(usuario, dias=25)

    metrics['impl_andamento_total'] = len(implantacoes_andamento)
    metrics['implantacoes_futuras'] = len(implantacoes_futuras)
    metrics['impl_finalizadas'] = len(implantacoes_finalizadas)
    metrics['implantacoes_atrasadas'] = len(implantacoes_atrasadas)

    default_metrics = {
        'nome': usuario,
        'impl_andamento': 0,
        'impl_finalizadas': 0,
        'impl_paradas': 0,
        'progresso_medio_carteira': 0,
        'impl_andamento_total': 0,
        'implantacoes_atrasadas': 0,
        'implantacoes_futuras': 0
    }

    final_metrics = {**default_metrics, **metrics}

    return render_template(
        'dashboard.html',
        usuario=usuario,
        metrics=final_metrics,
        implantacoes_andamento=implantacoes_andamento,
        implantacoes_futuras=implantacoes_futuras,
        implantacoes_finalizadas=implantacoes_finalizadas,
        implantacoes_paradas=implantacoes_paradas,
        implantacoes_atrasadas=implantacoes_atrasadas
    )

# ===============================================
# LOGIN / CADASTRO
# ===============================================
@app.route('/login', methods=['GET', 'POST'])
def login_cadastro():
    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        senha = request.form['senha']
        action = request.form.get('action', 'login')
        db = get_db()

        if action == 'login':
            user_data = db.execute("SELECT senha FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
            if not user_data:
                return render_template('login.html', aba_ativa='login', error="Usuário não encontrado.")
            if not check_password_hash(user_data['senha'], senha):
                return render_template('login.html', aba_ativa='login', error="Senha incorreta.")
            session['usuario'] = usuario
            return redirect(url_for('dashboard'))

        elif action == 'cadastro':
            nome_completo = request.form.get('nome_completo', usuario).strip() # NOVO: Captura nome completo
            user_exists = db.execute("SELECT usuario FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
            if user_exists:
                return render_template('login.html', aba_ativa='cadastro', error="Usuário já existe.")
            
            # Garante que a senha é forte o suficiente para hash (mínimo de verificação)
            if len(senha) < 6:
                 return render_template('login.html', aba_ativa='cadastro', error="Senha deve ter no mínimo 6 caracteres.")
                 
            senha_hash = generate_password_hash(senha)
            db.execute("INSERT INTO usuarios (usuario, senha) VALUES (?, ?)", (usuario, senha_hash))
            db.execute("INSERT INTO perfil_usuario (usuario, nome) VALUES (?, ?)", (usuario, nome_completo)) # Usa nome completo
            db.commit()
            session['usuario'] = usuario
            return redirect(url_for('dashboard'))

    return render_template('login.html', aba_ativa='login')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    # CORREÇÃO: Redireciona para o endpoint correto 'login_cadastro'
    return redirect(url_for('login_cadastro'))

# ===============================================
# MÉTRICAS
# ===============================================
@app.route('/salvar_metrics', methods=['POST'])
def salvar_metrics():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))

    usuario = session['usuario']
    nome = request.form.get('nome', usuario).strip()
    try:
        andamento = int(request.form.get('impl_andamento') or 0)
        finalizadas = int(request.form.get('impl_finalizadas') or 0)
        paradas = int(request.form.get('impl_paradas') or 0)
        prog_medio = int(request.form.get('progresso_medio_carteira') or 0)
        impl_andamento_total = int(request.form.get('impl_andamento_total') or 0)
        implantacoes_atrasadas = int(request.form.get('implantacoes_atrasadas') or 0)
    except ValueError:
        return redirect(url_for('dashboard'))

    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO perfil_usuario 
        (usuario, nome, impl_andamento, impl_finalizadas, impl_paradas,
         progresso_medio_carteira, impl_andamento_total, implantacoes_atrasadas)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (usuario, nome, andamento, finalizadas, paradas, prog_medio, impl_andamento_total, implantacoes_atrasadas))
    db.commit()
    return redirect(url_for('dashboard'))

# ===============================================
# IMPLANTAÇÃO
# ===============================================
@app.route('/criar_implantacao', methods=['POST'])
def criar_implantacao():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))
    usuario = session['usuario']
    nome_empresa = request.form.get('nome_empresa', '').strip()

    # agora usamos radio 'tipo' (deve ser 'agora' ou 'futura')
    tipo = request.form.get('tipo', 'agora')
    if tipo not in ('agora', 'futura'):
        tipo = 'agora'

    if nome_empresa:
        db = get_db()
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = db.execute(
            "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao) VALUES (?, ?, ?, ?)",
            (usuario, nome_empresa, tipo, created_at)
        )
        implantacao_id = cursor.lastrowid

        # inserir tarefas com ordem incremental por tarefa_pai
        for tarefa_pai, tarefas_filho in TAREFAS_PADRAO.items():
            ordem_counter = 1
            for tarefa_filho in tarefas_filho:
                db.execute("""
                    INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, observacao, ordem)
                    VALUES (?, ?, ?, ?, ?)
                """, (implantacao_id, tarefa_pai, tarefa_filho, '', ordem_counter))
                ordem_counter += 1
        db.commit()
    return redirect(url_for('dashboard'))


@app.route('/iniciar_implantacao', methods=['POST'])
def iniciar_implantacao():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))

    implantacao_id = request.form.get('implantacao_id')
    if not implantacao_id:
        return redirect(url_for('dashboard'))

    db = get_db()
    row = db.execute("SELECT usuario_cs FROM implantacoes WHERE id = ?", (implantacao_id,)).fetchone()
    if not row or row['usuario_cs'] != session['usuario']:
        return redirect(url_for('dashboard'))

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # marca como 'agora' e atualiza data_criacao para início
    db.execute("UPDATE implantacoes SET tipo = 'agora', data_criacao = ? WHERE id = ?", (now, implantacao_id))
    db.commit()
    return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

@app.route('/finalizar_implantacao', methods=['POST'])
def finalizar_implantacao():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))
    id_implantacao = request.form.get('implantacao_id')
    if id_implantacao:
        try:
            db = get_db()
            db.execute("""
                UPDATE implantacoes
                SET status = 'finalizada', data_finalizacao = CURRENT_TIMESTAMP
                WHERE id = ? AND usuario_cs = ? AND status = 'andamento'
            """, (id_implantacao, session['usuario']))
            
            # ATUALIZA A MÉTRICA DE FINALIZADAS NO PERFIL
            db.execute("""
                UPDATE perfil_usuario
                SET impl_finalizadas = impl_finalizadas + 1
                WHERE usuario = ?
            """, (session['usuario'],))
            db.commit()
        except Exception as e:
            print(f"Erro ao finalizar implantação: {e}")
    return redirect(url_for('dashboard'))

@app.route('/parar_implantacao', methods=['POST'])
def parar_implantacao():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))
    id_implantacao = request.form.get('implantacao_id')
    if id_implantacao:
        try:
            db = get_db()
            db.execute("""
                UPDATE implantacoes
                SET status = 'parada', data_finalizacao = CURRENT_TIMESTAMP
                WHERE id = ? AND usuario_cs = ? AND status = 'andamento'
            """, (id_implantacao, session['usuario']))
            db.commit()
            db.execute("""
                UPDATE perfil_usuario
                SET impl_paradas = impl_paradas + 1
                WHERE usuario = ?
            """, (session['usuario'],))
            db.commit()
        except Exception as e:
            print(f"Erro ao parar implantação: {e}")
    return redirect(url_for('dashboard'))

@app.route('/implantacao/<int:impl_id>')
def ver_implantacao(impl_id):
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))

    usuario = session['usuario']
    db = get_db()

    implantacao = db.execute(
        "SELECT * FROM implantacoes WHERE id = ? AND usuario_cs = ?", (impl_id, usuario)
    ).fetchone()

    if not implantacao:
        return redirect(url_for('dashboard'))

    tarefas = db.execute(
        "SELECT * FROM tarefas WHERE implantacao_id = ? ORDER BY tarefa_pai, ordem",
        (impl_id,)
    ).fetchall()

    # Ordem solicitada (Welcome ficará após, se existir)
    ordem = ["Estruturação de BD", "Importação de dados", "Módulo ADM",
             "Módulo Treino", "Módulo CRM", "Módulo Financeiro", "Conclusão"]

    temp = {}
    for tarefa in tarefas:
        pai = tarefa['tarefa_pai']
        if pai not in temp:
            temp[pai] = []
        temp[pai].append(dict(tarefa))

    tarefas_agrupadas = OrderedDict()
    for key in ordem:
        if key in temp:
            # Ordena as tarefas pelo campo 'ordem'
            tarefas_agrupadas[key] = sorted(temp.pop(key), key=lambda x: x['ordem'])
    
    # itens restantes (ex.: "Welcome") vão depois, também ordenados
    for k, v in temp.items():
        tarefas_agrupadas[k] = sorted(v, key=lambda x: x['ordem'])

    return render_template('implantacao_detalhes.html',
                           implantacao=dict(implantacao),
                           tarefas_agrupadas=tarefas_agrupadas)

# Toggle tarefa (rota correspondente ao formulário do checklist)
@app.route('/toggle_tarefa/<int:tarefa_id>', methods=['POST'])
def toggle_tarefa(tarefa_id):
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))

    db = get_db()
    tarefa_info = db.execute(
        "SELECT implantacao_id, concluida FROM tarefas WHERE id = ?", (tarefa_id,)
    ).fetchone()

    if tarefa_info:
        novo_status = 1 if tarefa_info['concluida'] == 0 else 0
        db.execute("UPDATE tarefas SET concluida = ? WHERE id = ?", (novo_status, tarefa_id))
        db.commit()

        # verifica se todas as tarefas da implantação foram concluídas
        impl_id = tarefa_info['implantacao_id']
        impl_row = db.execute("SELECT id, tipo, status FROM implantacoes WHERE id = ?", (impl_id,)).fetchone()

        counts = db.execute(
            "SELECT COUNT(*) as total, SUM(concluida) as done FROM tarefas WHERE implantacao_id = ?",
            (impl_id,)
        ).fetchone()
        total = int(counts['total'] or 0)
        done = int(counts['done'] or 0)

        # só finaliza automaticamente se for uma implantação do tipo 'agora' e ainda não estiver finalizada
        if impl_row and impl_row['tipo'] == 'agora' and impl_row['status'] != 'finalizada' and total > 0 and done == total:
            try:
                # marca implantação como finalizada e registra data_finalizacao
                db.execute("UPDATE implantacoes SET status = 'finalizada', data_finalizacao = CURRENT_TIMESTAMP WHERE id = ?", (impl_id,))
                # atualiza métricas do perfil: incrementa finalizadas e decrementa andamento (se >0)
                db.execute("UPDATE perfil_usuario SET impl_finalizadas = impl_finalizadas + 1 WHERE usuario = ?", (session['usuario'],))
                db.execute("UPDATE perfil_usuario SET impl_andamento = CASE WHEN impl_andamento > 0 THEN impl_andamento - 1 ELSE 0 END WHERE usuario = ?", (session['usuario'],))
                db.commit()
            except Exception:
                db.rollback()

        return redirect(url_for('ver_implantacao', impl_id=tarefa_info['implantacao_id']))

    return redirect(url_for('dashboard'))

@app.route('/excluir_tarefa/<int:tarefa_id>', methods=['POST'])
def excluir_tarefa(tarefa_id):
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))

    db = get_db()
    tarefa = db.execute("SELECT implantacao_id FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()
    if tarefa:
        implantacao_id = tarefa['implantacao_id']
        db.execute("DELETE FROM tarefas WHERE id = ?", (tarefa_id,))
        db.commit()
        return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

    return redirect(url_for('dashboard'))

@app.route('/excluir_implantacao', methods=['POST'])
def excluir_implantacao():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))

    implantacao_id = request.form.get('implantacao_id')
    if not implantacao_id:
        return redirect(url_for('dashboard'))

    db = get_db()
    row = db.execute("SELECT usuario_cs FROM implantacoes WHERE id = ?", (implantacao_id,)).fetchone()
    if not row or row['usuario_cs'] != session['usuario']:
        return redirect(url_for('dashboard'))

    db.execute("DELETE FROM implantacoes WHERE id = ? AND usuario_cs = ?", (implantacao_id, session['usuario']))
    db.commit()
    return redirect(url_for('dashboard'))

# ===============================================
# NOVA ROTA: salvar observação da tarefa
# ===============================================
@app.route('/salvar_observacao/<int:tarefa_id>', methods=['POST'])
def salvar_observacao(tarefa_id):
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))

    observacao = request.form.get('observacao', '')[:240]  # limite 240 chars
    db = get_db()
    # obtém implantacao_id para redirecionamento
    tarefa = db.execute("SELECT implantacao_id FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()
    if tarefa:
        db.execute("UPDATE tarefas SET observacao = ? WHERE id = ?", (observacao, tarefa_id))
        db.commit()
        return redirect(url_for('ver_implantacao', impl_id=tarefa['implantacao_id']))

    return redirect(url_for('dashboard'))

@app.route('/adicionar_tarefa', methods=['POST'])
def adicionar_tarefa():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))

    tarefa_pai = request.form.get('tarefa_pai').strip()
    tarefa_filho = request.form.get('tarefa_filho').strip()
    implantacao_id = request.form.get('implantacao_id')

    if not tarefa_pai or not tarefa_filho or not implantacao_id:
        return redirect(url_for('dashboard'))

    db = get_db()
    # valida propriedade da implantação
    impl = db.execute("SELECT usuario_cs FROM implantacoes WHERE id = ?", (implantacao_id,)).fetchone()
    if not impl or impl['usuario_cs'] != session['usuario']:
        return redirect(url_for('dashboard'))

    # calcula próxima ordem para esse pai
    max_row = db.execute("SELECT MAX(ordem) as m FROM tarefas WHERE implantacao_id = ? AND tarefa_pai = ?", (implantacao_id, tarefa_pai)).fetchone()
    prox_ordem = (max_row['m'] or 0) + 1
    db.execute(
        "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, observacao, ordem) VALUES (?, ?, ?, ?, ?)",
        (implantacao_id, tarefa_pai, tarefa_filho, '', prox_ordem)
    )
    db.commit()
    return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

# ===============================================
# NOVA ROTA: reordenar tarefas via drag-and-drop
# ===============================================
@app.route('/reordenar_tarefas', methods=['POST'])
def reordenar_tarefas():
    if 'usuario' not in session:
        return jsonify({'ok': False, 'error': 'login_required'}), 403

    data = request.get_json() or {}
    implantacao_id = data.get('implantacao_id')
    tarefa_pai = data.get('tarefa_pai')
    ordem_list = data.get('ordem', [])

    if not implantacao_id or not tarefa_pai or not isinstance(ordem_list, list):
        return jsonify({'ok': False, 'error': 'invalid_payload'}), 400

    db = get_db()
    # valida propriedade
    impl = db.execute("SELECT usuario_cs FROM implantacoes WHERE id = ?", (implantacao_id,)).fetchone()
    if not impl or impl['usuario_cs'] != session['usuario']:
        return jsonify({'ok': False, 'error': 'forbidden'}), 403

    try:
        # atualiza cada id com a nova posição (1-based)
        for idx, tarefa_id in enumerate(ordem_list, start=1):
            db.execute("UPDATE tarefas SET ordem = ? WHERE id = ? AND implantacao_id = ? AND tarefa_pai = ?", (idx, tarefa_id, implantacao_id, tarefa_pai))
        db.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    init_db()

    # abre o navegador padrão após um pequeno delay (opcional)
    def _open_browser():
        try:
            webbrowser.open_new('http://127.0.0.1:5000/')
        except Exception:
            pass

    threading.Timer(1.0, _open_browser).start()

    app.run(debug=True, host='127.0.0.1', port=5000)