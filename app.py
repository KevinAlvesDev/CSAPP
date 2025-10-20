import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify, send_from_directory, flash
from werkzeug.security import generate_password_hash, check_password_hash
import webbrowser
import threading
from collections import OrderedDict
from datetime import datetime
import os
from werkzeug.utils import secure_filename 

# ===============================================
# CONFIGURAÇÃO INICIAL
# ===============================================

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'chave_padrao_apenas_para_desenvolvimento_local')
DATABASE = 'dashboard_simples.db'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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

# Lista de justificativas genéricas
JUSTIFICATIVAS_PARADA = [
    "Pausa solicitada pelo cliente",
    "Aguardando dados / material do cliente",
    "Cliente em viagem / Férias",
    "Aguardando pagamento / Questões financeiras",
    "Revisão interna de processos",
    "Outro (detalhar nos comentários da implantação)"
]

# [NOVO] Opções de Cargo para o formulário
CARGOS_RESPONSAVEL = [
    "Proprietário(a)",
    "Sócio(a)",
    "Gerente",
    "Coordenador(a)",
    "Analista de TI",
    "Financeiro",
    "Outro"
]

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
                motivo_parada TEXT DEFAULT '', 
                FOREIGN KEY(usuario_cs) REFERENCES usuarios(usuario) ON DELETE NO ACTION
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
                ordem INTEGER DEFAULT 0,
                FOREIGN KEY(implantacao_id) REFERENCES implantacoes(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comentarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarefa_id INTEGER NOT NULL,
                usuario_cs TEXT NOT NULL,
                texto TEXT NOT NULL,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                imagem_url TEXT,
                FOREIGN KEY(tarefa_id) REFERENCES tarefas(id) ON DELETE CASCADE,
                FOREIGN KEY(usuario_cs) REFERENCES usuarios(usuario) ON DELETE NO ACTION
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timeline_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                implantacao_id INTEGER NOT NULL,
                usuario_cs TEXT NOT NULL,
                tipo_evento TEXT NOT NULL, 
                detalhes TEXT NOT NULL, 
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(implantacao_id) REFERENCES implantacoes(id) ON DELETE CASCADE,
                FOREIGN KEY(usuario_cs) REFERENCES usuarios(usuario) ON DELETE NO ACTION
            )
        """)

        # Adiciona colunas se não existirem
        try: cursor.execute("ALTER TABLE implantacoes ADD COLUMN tipo TEXT DEFAULT 'agora'")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE implantacoes ADD COLUMN motivo_parada TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE tarefas ADD COLUMN observacao TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE tarefas ADD COLUMN ordem INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE comentarios ADD COLUMN imagem_url TEXT")
        except sqlite3.OperationalError: pass
        
        # [NOVO] Adiciona colunas de detalhes da empresa
        try: cursor.execute("ALTER TABLE implantacoes ADD COLUMN responsavel_cliente TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE implantacoes ADD COLUMN cargo_responsavel TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE implantacoes ADD COLUMN telefone_responsavel TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE implantacoes ADD COLUMN email_responsavel TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE implantacoes ADD COLUMN data_inicio_producao TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE implantacoes ADD COLUMN data_final_implantacao TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE implantacoes ADD COLUMN chave_oamd TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE implantacoes ADD COLUMN catraca TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE implantacoes ADD COLUMN facial TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass

        
        try:
            cursor.execute("ALTER TABLE jornada_log RENAME TO timeline_log")
            print("MIGRAÇÃO: Tabela 'jornada_log' renomeada para 'timeline_log'.")
        except sqlite3.OperationalError:
            pass 

        db.commit() 

        # --- [CORREÇÃO] Script de migração de dados ---
        try:
            cursor.execute("PRAGMA table_info(tarefas)")
            cols = [col['name'] for col in cursor.fetchall()]
            
            if 'observacao' in cols:
                print("MIGRAÇÃO: Detectada coluna 'observacao' antiga. Iniciando migração...")
                cursor.execute("""
                    INSERT INTO comentarios (tarefa_id, usuario_cs, texto, data_criacao)
                    SELECT 
                        t.id, 
                        i.usuario_cs, 
                        '[OBSERVAÇÃO ANTIGA] ' || t.observacao,
                        i.data_criacao
                    FROM tarefas t
                    JOIN implantacoes i ON t.implantacao_id = i.id
                    WHERE t.observacao IS NOT NULL AND t.observacao != ''
                """)
                print(f"MIGRAÇÃO: {cursor.rowcount} observações movidas.")
                cursor.execute("ALTER TABLE tarefas RENAME COLUMN observacao TO _observacao_migrada")
                db.commit()
                print("MIGRAÇÃO: Coluna 'observacao' renomeada para '_observacao_migrada'. Migração concluída.")
        except sqlite3.Error as e:
            print(f"MIGRAÇÃO (Aviso): Não foi possível migrar observações (pode já ter sido feito). Erro: {e}")
            db.rollback()

# ===============================================
# FUNÇÕES DE LÓGICA
# ===============================================

def logar_timeline(db, implantacao_id, usuario_cs, tipo_evento, detalhes):
    """Insere um registro na tabela de log da linha do tempo."""
    try:
        db.execute("""
            INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao)
            VALUES (?, ?, ?, ?, ?)
        """, (implantacao_id, usuario_cs, tipo_evento, detalhes, datetime.now()))
    except Exception as e:
        print(f"Erro ao logar timeline (id: {implantacao_id}): {e}")
        pass

def get_dashboard_data(usuario, db):
    # [ATUALIZADO] Query agora seleciona todos os novos campos da implantação
    query = """
        WITH TaskProgress AS (
            SELECT
                implantacao_id,
                COUNT(*) AS total_tarefas,
                SUM(CASE WHEN concluida = 1 THEN 1 ELSE 0 END) AS tarefas_concluidas
            FROM tarefas
            GROUP BY implantacao_id
        )
        SELECT
            i.id, i.nome_empresa, i.status, i.tipo, i.data_criacao, i.data_finalizacao, i.motivo_parada,
            i.responsavel_cliente, i.cargo_responsavel, i.telefone_responsavel, i.email_responsavel,
            i.data_inicio_producao, i.data_final_implantacao, i.chave_oamd, i.catraca, i.facial,
            JULIANDAY('now') - JULIANDAY(i.data_criacao) AS dias_passados,
            COALESCE(tp.total_tarefas, 0) AS total,
            COALESCE(tp.tarefas_concluidas, 0) AS done
        FROM implantacoes i
        LEFT JOIN TaskProgress tp ON i.id = tp.implantacao_id
        WHERE i.usuario_cs = ?
        ORDER BY i.data_criacao DESC
    """
    implantacoes = db.execute(query, (usuario,)).fetchall()
    
    data = { 'andamento': [], 'futuras': [], 'finalizadas': [], 'paradas': [], 'atrasadas': [] }
    metrics = { 'impl_andamento_total': 0, 'implantacoes_futuras': 0, 'impl_finalizadas': 0, 'impl_paradas': 0, 'implantacoes_atrasadas': 0, 'progresso_total': 0, 'total_impl': 0 }
    
    for i in implantacoes:
        impl = dict(i)
        total = impl['total']
        done = impl['done']
        progresso = int(round((done / total) * 100)) if total > 0 else 0
        impl['progresso'] = progresso
        metrics['total_impl'] += 1
        metrics['progresso_total'] += progresso

        if impl['tipo'] == 'futura':
            data['futuras'].append(impl)
            metrics['implantacoes_futuras'] += 1
        elif impl['status'] == 'andamento':
            data['andamento'].append(impl)
            metrics['impl_andamento_total'] += 1
        elif impl['status'] == 'finalizada':
            data['finalizadas'].append(impl)
            metrics['impl_finalizadas'] += 1
        elif impl['status'] == 'parada':
            data['paradas'].append(impl)
            metrics['impl_paradas'] += 1
        
        if impl['tipo'] != 'futura' and impl['status'] != 'finalizada' and impl['dias_passados'] > 25:
            if impl not in data['atrasadas']:
                data['atrasadas'].append(impl)
            metrics['implantacoes_atrasadas'] += 1
            
    metrics['progresso_medio_carteira'] = int(round(metrics['progresso_total'] / metrics['total_impl'])) if metrics['total_impl'] > 0 else 0
    return data, metrics

def auto_finalizar_implantacao(db, impl_id, usuario_cs):
    implantacao = db.execute("SELECT status, tipo FROM implantacoes WHERE id = ?", (impl_id,)).fetchone()
    if not implantacao or implantacao['tipo'] == 'futura' or implantacao['status'] == 'finalizada':
        return False
    counts = db.execute(
        "SELECT COUNT(*) as total, SUM(concluida) as done FROM tarefas WHERE implantacao_id = ?",
        (impl_id,)
    ).fetchone()
    total_tarefas = counts['total'] or 0
    tarefas_concluidas = counts['done'] or 0
    if total_tarefas > 0 and total_tarefas == tarefas_concluidas:
        try:
            db.execute("UPDATE implantacoes SET status = 'finalizada', data_finalizacao = CURRENT_TIMESTAMP WHERE id = ?", (impl_id,))
            db.execute("UPDATE perfil_usuario SET impl_finalizadas = impl_finalizadas + 1, impl_andamento_total = MAX(0, impl_andamento_total - 1) WHERE usuario = ?", (usuario_cs,))
            
            # [LOG]
            logar_timeline(db, impl_id, usuario_cs, 'status_alterado', 'Implantação finalizada automaticamente (100% das tarefas concluídas).')
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Erro ao auto-finalizar implantação: {e}")
            return False
    return False

# ===============================================
# ROTAS PRINCIPAIS
# ===============================================
@app.route('/')
def home():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_cadastro'))

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))
    usuario = session['usuario']
    db = get_db()
    dashboard_data, metrics = get_dashboard_data(usuario, db)
    perfil = db.execute("SELECT * FROM perfil_usuario WHERE usuario = ?", (usuario,)).fetchone()
    perfil_data = dict(perfil) if perfil else {}
    default_metrics = {'nome': usuario, 'impl_andamento': 0, 'impl_finalizadas': 0, 'impl_paradas': 0, 'progresso_medio_carteira': 0, 'impl_andamento_total': 0, 'implantacoes_atrasadas': 0, 'implantacoes_futuras': 0}
    final_metrics = {**default_metrics, **perfil_data, **metrics}

    return render_template(
        'dashboard.html',
        usuario=usuario,
        metrics=final_metrics,
        implantacoes_andamento=dashboard_data['andamento'],
        implantacoes_futuras=dashboard_data['futuras'],
        implantacoes_finalizadas=dashboard_data['finalizadas'],
        implantacoes_paradas=dashboard_data['paradas'],
        implantacoes_atrasadas=dashboard_data['atrasadas'],
        cargos_responsavel=CARGOS_RESPONSAVEL # [NOVO] Passa a lista de cargos para o template
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
            nome_completo = request.form.get('nome_completo', usuario).strip()
            user_exists = db.execute("SELECT usuario FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
            if user_exists:
                return render_template('login.html', aba_ativa='cadastro', error="Usuário já existe.")
            if len(senha) < 6:
                 return render_template('login.html', aba_ativa='cadastro', error="Senha deve ter no mínimo 6 caracteres.")
                 
            try:
                senha_hash = generate_password_hash(senha)
                db.execute("INSERT INTO usuarios (usuario, senha) VALUES (?, ?)", (usuario, senha_hash))
                db.execute("INSERT INTO perfil_usuario (usuario, nome) VALUES (?, ?)", (usuario, nome_completo))
                db.commit()
                session['usuario'] = usuario
                return redirect(url_for('dashboard'))
            except Exception as e:
                db.rollback()
                print(f"Erro ao cadastrar usuário: {e}")
                return render_template('login.html', aba_ativa='cadastro', error="Erro ao criar usuário. Tente novamente.")

    return render_template('login.html', aba_ativa='login')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login_cadastro'))

# ===============================================
# IMPLANTAÇÃO
# ===============================================
@app.route('/criar_implantacao', methods=['POST'])
def criar_implantacao():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))
    usuario = session['usuario']
    nome_empresa = request.form.get('nome_empresa', '').strip()
    tipo = request.form.get('tipo', 'agora')

    if nome_empresa:
        db = get_db()
        try:
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor = db.execute(
                "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao) VALUES (?, ?, ?, ?)",
                (usuario, nome_empresa, tipo, created_at)
            )
            implantacao_id = cursor.lastrowid
            
            # [LOG]
            logar_timeline(db, implantacao_id, usuario, 'implantacao_criada', f'Implantação "{nome_empresa}" (Tipo: {tipo}) foi criada.')

            for tarefa_pai, tarefas_filho in TAREFAS_PADRAO.items():
                ordem_counter = 1
                for tarefa_filho in tarefas_filho:
                    db.execute("""
                        INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem)
                        VALUES (?, ?, ?, ?)
                    """, (implantacao_id, tarefa_pai, tarefa_filho, ordem_counter))
                    ordem_counter += 1
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Erro ao criar implantação: {e}")
            
    return redirect(url_for('dashboard'))

@app.route('/iniciar_implantacao', methods=['POST'])
def iniciar_implantacao():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))
    implantacao_id = request.form.get('implantacao_id')
    if not implantacao_id:
        return redirect(url_for('dashboard'))
    db = get_db()
    row = db.execute("SELECT usuario_cs, nome_empresa FROM implantacoes WHERE id = ?", (implantacao_id,)).fetchone()
    if not row or row['usuario_cs'] != session['usuario']:
        return redirect(url_for('dashboard'))
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.execute("UPDATE implantacoes SET tipo = 'agora', status = 'andamento', data_criacao = ? WHERE id = ?", (now, implantacao_id))
        
        # [LOG]
        logar_timeline(db, implantacao_id, session['usuario'], 'status_alterado', f'Implantação "{row["nome_empresa"]}" iniciada (movida de "Futura" para "Em Andamento").')
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erro ao iniciar implantação: {e}")
    return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

@app.route('/finalizar_implantacao', methods=['POST'])
def finalizar_implantacao():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))
    id_implantacao = request.form.get('implantacao_id')
    if id_implantacao:
        db = get_db()
        try:
            db.execute("""
                UPDATE implantacoes
                SET status = 'finalizada', data_finalizacao = CURRENT_TIMESTAMP
                WHERE id = ? AND usuario_cs = ? AND status = 'andamento'
            """, (id_implantacao, session['usuario']))
            db.execute("""
                UPDATE perfil_usuario
                SET impl_finalizadas = impl_finalizadas + 1,
                    impl_andamento_total = MAX(0, impl_andamento_total - 1)
                WHERE usuario = ?
            """, (session['usuario'],))
            
            # [LOG]
            logar_timeline(db, id_implantacao, session['usuario'], 'status_alterado', 'Implantação marcada como "Finalizada" manualmente.')

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Erro ao finalizar implantação: {e}")
    return redirect(url_for('dashboard'))

@app.route('/parar_implantacao', methods=['POST'])
def parar_implantacao():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))
        
    id_implantacao = request.form.get('implantacao_id')
    motivo = request.form.get('motivo_parada', 'Motivo não especificado')
    
    if id_implantacao:
        db = get_db()
        try:
            db.execute("""
                UPDATE implantacoes
                SET status = 'parada', 
                    data_finalizacao = CURRENT_TIMESTAMP,
                    motivo_parada = ?
                WHERE id = ? AND usuario_cs = ? AND status = 'andamento'
            """, (motivo, id_implantacao, session['usuario']))
            
            db.execute("""
                UPDATE perfil_usuario
                SET impl_paradas = impl_paradas + 1,
                    impl_andamento_total = MAX(0, impl_andamento_total - 1)
                WHERE usuario = ?
            """, (session['usuario'],))

            # [LOG]
            logar_timeline(db, id_implantacao, session['usuario'], 'status_alterado', f'Implantação marcada como "Parada". Motivo: {motivo}')

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Erro ao parar implantação: {e}")
            
    return redirect(url_for('ver_implantacao', impl_id=id_implantacao))

@app.route('/retomar_implantacao', methods=['POST'])
def retomar_implantacao():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))
        
    id_implantacao = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard')
    
    if id_implantacao:
        db = get_db()
        try:
            db.execute("""
                UPDATE implantacoes
                SET status = 'andamento', 
                    data_finalizacao = NULL,
                    motivo_parada = ''
                WHERE id = ? AND usuario_cs = ? AND status = 'parada'
            """, (id_implantacao, session['usuario']))
            
            db.execute("""
                UPDATE perfil_usuario
                SET impl_paradas = MAX(0, impl_paradas - 1),
                    impl_andamento_total = impl_andamento_total + 1
                WHERE usuario = ?
            """, (session['usuario'],))
            
            # [LOG]
            logar_timeline(db, id_implantacao, session['usuario'], 'status_alterado', 'Implantação retomada (status alterado de "Parada" para "Em Andamento").')
            
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Erro ao retomar implantação: {e}")

    if redirect_to == 'detalhes':
        return redirect(url_for('ver_implantacao', impl_id=id_implantacao))
        
    return redirect(url_for('dashboard'))

# [NOVO] Rota para salvar os detalhes da empresa vindos do modal
@app.route('/atualizar_detalhes_empresa', methods=['POST'])
def atualizar_detalhes_empresa():
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))
    
    implantacao_id = request.form.get('implantacao_id')
    db = get_db()
    
    # Verifica permissão
    impl = db.execute("SELECT id FROM implantacoes WHERE id = ? AND usuario_cs = ?", 
                      (implantacao_id, session['usuario'])).fetchone()
    
    if not impl:
        flash('Você não tem permissão para editar esta implantação.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Coleta dados do formulário
        dados = {
            "responsavel_cliente": request.form.get('responsavel_cliente', ''),
            "cargo_responsavel": request.form.get('cargo_responsavel', ''),
            "telefone_responsavel": request.form.get('telefone_responsavel', ''),
            "email_responsavel": request.form.get('email_responsavel', ''),
            "data_inicio_producao": request.form.get('data_inicio_producao', ''),
            "data_final_implantacao": request.form.get('data_final_implantacao', ''),
            "chave_oamd": request.form.get('chave_oamd', ''),
            "catraca": request.form.get('catraca', ''),
            "facial": request.form.get('facial', ''),
        }
        
        # Monta a query de UPDATE
        query = """
            UPDATE implantacoes SET
                responsavel_cliente = :responsavel_cliente,
                cargo_responsavel = :cargo_responsavel,
                telefone_responsavel = :telefone_responsavel,
                email_responsavel = :email_responsavel,
                data_inicio_producao = :data_inicio_producao,
                data_final_implantacao = :data_final_implantacao,
                chave_oamd = :chave_oamd,
                catraca = :catraca,
                facial = :facial
            WHERE id = :implantacao_id AND usuario_cs = :usuario_cs
        """
        dados["implantacao_id"] = implantacao_id
        dados["usuario_cs"] = session['usuario']
        
        db.execute(query, dados)
        
        # [LOG]
        logar_timeline(db, implantacao_id, session['usuario'], 'detalhes_alterados', 'Os detalhes da empresa foram atualizados.')
        
        db.commit()
        flash('Detalhes da empresa atualizados com sucesso!', 'success')
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar detalhes da empresa: {e}")
        flash('Erro ao atualizar detalhes.', 'error')

    return redirect(url_for('dashboard'))


@app.route('/implantacao/<int:impl_id>')
def ver_implantacao(impl_id):
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))

    usuario = session['usuario']
    db = get_db()

    # Query agora seleciona TUDO, incluindo os novos campos
    implantacao = db.execute(
        "SELECT * FROM implantacoes WHERE id = ? AND usuario_cs = ?", (impl_id, usuario)
    ).fetchone()

    if not implantacao:
        return redirect(url_for('dashboard'))

    counts = db.execute(
        "SELECT COUNT(*) as total, SUM(concluida) as done FROM tarefas WHERE implantacao_id = ?",
        (impl_id,)
    ).fetchone()
    total_tarefas = counts['total'] or 0
    tarefas_concluidas = counts['done'] or 0
    progresso_porcentagem = int(round((tarefas_concluidas / total_tarefas) * 100)) if total_tarefas > 0 else 0
    
    tarefas = db.execute(
        "SELECT * FROM tarefas WHERE implantacao_id = ? ORDER BY tarefa_pai, ordem",
        (impl_id,)
    ).fetchall()
    
    comentarios_raw = db.execute("""
        SELECT c.*, p.nome as usuario_nome
        FROM comentarios c
        JOIN perfil_usuario p ON c.usuario_cs = p.usuario
        WHERE c.tarefa_id IN (SELECT id FROM tarefas WHERE implantacao_id = ?)
        ORDER BY c.data_criacao ASC
    """, (impl_id,)).fetchall()

    comentarios_por_tarefa = {}
    for c in comentarios_raw:
        tid = c['tarefa_id']
        if tid not in comentarios_por_tarefa:
            comentarios_por_tarefa[tid] = []
        comentarios_por_tarefa[tid].append(dict(c))

    temp = {}
    for tarefa_row in tarefas:
        tarefa = dict(tarefa_row)
        pai = tarefa['tarefa_pai']
        if pai not in temp:
            temp[pai] = []
        
        tarefa['comentarios'] = comentarios_por_tarefa.get(tarefa['id'], [])
        temp[pai].append(tarefa)

    ordem = ["Welcome", "Estruturação de BD", "Importação de dados", 
             "Módulo ADM", "Módulo Treino", "Módulo CRM", 
             "Módulo Financeiro", "Conclusão"]
    
    tarefas_agrupadas = OrderedDict()
    for key in ordem:
        if key in temp:
            tarefas_agrupadas[key] = sorted(temp.pop(key), key=lambda x: x['ordem'])
    
    for k, v in temp.items():
        tarefas_agrupadas[k] = sorted(v, key=lambda x: x['ordem'])

    perfil_usuario = db.execute("SELECT nome FROM perfil_usuario WHERE usuario = ?", (usuario,)).fetchone()
    nome_usuario_logado = perfil_usuario['nome'] if perfil_usuario else usuario

    # Buscar logs da linha do tempo
    logs_timeline_raw = db.execute("""
        SELECT j.*, p.nome as usuario_nome
        FROM timeline_log j
        LEFT JOIN perfil_usuario p ON j.usuario_cs = p.usuario
        WHERE j.implantacao_id = ?
        ORDER BY j.data_criacao DESC
    """, (impl_id,)).fetchall()
    
    logs_timeline = [dict(log) for log in logs_timeline_raw]

    return render_template('implantacao_detalhes.html',
                           implantacao=dict(implantacao),
                           tarefas_agrupadas=tarefas_agrupadas,
                           progresso_porcentagem=progresso_porcentagem,
                           nome_usuario_logado=nome_usuario_logado,
                           email_usuario_logado=usuario,
                           justificativas_parada=JUSTIFICATIVAS_PARADA,
                           logs_timeline=logs_timeline) 

@app.route('/toggle_tarefa/<int:tarefa_id>', methods=['POST'])
def toggle_tarefa(tarefa_id):
    if 'usuario' not in session:
        return jsonify({'ok': False, 'error': 'login_required'}), 403

    db = get_db()
    tarefa_info = db.execute(
        "SELECT t.*, i.usuario_cs, i.id as implantacao_id FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id WHERE t.id = ?",
        (tarefa_id,)
    ).fetchone()

    if not tarefa_info or tarefa_info['usuario_cs'] != session['usuario']:
        return jsonify({'ok': False, 'error': 'forbidden'}), 403

    novo_status = 1 if tarefa_info['concluida'] == 0 else 0
    impl_id = tarefa_info['implantacao_id']
    
    try:
        db.execute("UPDATE tarefas SET concluida = ? WHERE id = ?", (novo_status, tarefa_id))
        
        agora_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        if novo_status == 1:
            detalhe_log = f"Atualização da tarefa: {tarefa_info['tarefa_filho']}.\nConcluída alterado(a) de: Sem valor para: {agora_str}."
        else:
            detalhe_log = f"Atualização da tarefa: {tarefa_info['tarefa_filho']}.\nStatus alterado(a) de: Concluída para: Sem valor."
        
        logar_timeline(db, impl_id, session['usuario'], 'tarefa_alterada', detalhe_log)

        db.commit() 

        finalizada = auto_finalizar_implantacao(db, impl_id, session['usuario'])
        
        counts_after = db.execute(
            "SELECT COUNT(*) as total, SUM(concluida) as done FROM tarefas WHERE implantacao_id = ?",
            (impl_id,)
        ).fetchone()
        total_tarefas_after = counts_after['total'] or 0
        tarefas_concluidas_after = counts_after['done'] or 0
        
        novo_progresso = int(round((tarefas_concluidas_after / total_tarefas_after) * 100)) if total_tarefas_after > 0 else 0
        
        perfil_usuario = db.execute("SELECT nome FROM perfil_usuario WHERE usuario = ?", (session['usuario'],)).fetchone()
        nome_usuario_logado = perfil_usuario['nome'] if perfil_usuario else session['usuario']

        log_tarefa = db.execute("""
            SELECT *, ? as usuario_nome FROM timeline_log 
            WHERE implantacao_id = ? AND tipo_evento = 'tarefa_alterada' 
            ORDER BY id DESC LIMIT 1
        """, (nome_usuario_logado, impl_id)).fetchone()

        log_finalizacao = None
        if finalizada:
            log_finalizacao = db.execute("""
                SELECT *, ? as usuario_nome FROM timeline_log 
                WHERE implantacao_id = ? AND tipo_evento = 'status_alterado' 
                ORDER BY id DESC LIMIT 1
            """, (nome_usuario_logado, impl_id)).fetchone()

        return jsonify({
            'ok': True, 
            'novo_status': novo_status, 
            'implantacao_finalizada': finalizada,
            'novo_progresso': novo_progresso,
            'log_tarefa': dict(log_tarefa) if log_tarefa else None,
            'log_finalizacao': dict(log_finalizacao) if log_finalizacao else None
        })
    except Exception as e:
        db.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/excluir_tarefa/<int:tarefa_id>', methods=['POST'])
def excluir_tarefa(tarefa_id):
    if 'usuario' not in session:
        return redirect(url_for('login_cadastro'))
        
    db = get_db()
    tarefa = db.execute(
        "SELECT t.implantacao_id, t.tarefa_filho, t.tarefa_pai, i.usuario_cs FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id WHERE t.id = ?", 
        (tarefa_id,)
    ).fetchone()
    
    if not tarefa or tarefa['usuario_cs'] != session['usuario']:
        return redirect(url_for('dashboard'))
        
    implantacao_id = tarefa['implantacao_id']
    try:
        db.execute("DELETE FROM tarefas WHERE id = ?", (tarefa_id,))
        
        # [LOG]
        detalhe_log = f"Tarefa '{tarefa['tarefa_filho']}' (do módulo '{tarefa['tarefa_pai']}') foi excluída."
        logar_timeline(db, implantacao_id, session['usuario'], 'tarefa_excluida', detalhe_log)

        db.commit()
        auto_finalizar_implantacao(db, implantacao_id, session['usuario'])
        return redirect(url_for('ver_implantacao', impl_id=implantacao_id))
    except Exception as e:
        db.rollback()
        return redirect(url_for('ver_implantacao', impl_id=implantacao_id))


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
    try:
        db.execute("DELETE FROM implantacoes WHERE id = ? AND usuario_cs = ?", (implantacao_id, session['usuario']))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erro ao excluir implantação: {e}")
    return redirect(url_for('dashboard'))

# ===============================================
# ROTAS DE COMENTÁRIOS
# ===============================================
@app.route('/adicionar_comentario/<int:tarefa_id>', methods=['POST'])
def adicionar_comentario(tarefa_id):
    if 'usuario' not in session:
        return jsonify({'ok': False, 'error': 'login_required'}), 403

    texto_comentario = request.form.get('comentario', '')[:8000].strip()
    imagem_url = None
    
    if 'imagem' in request.files:
        file = request.files['imagem']
        if file and file.filename != '' and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                nome_base, extensao = os.path.splitext(filename)
                nome_unico = f"{nome_base}_{int(datetime.now().timestamp())}{extensao}"
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], nome_unico)
                file.save(filepath)
                imagem_url = url_for('uploaded_file', filename=nome_unico)
            except Exception as e:
                print(f"Erro ao salvar imagem: {e}")
                pass 

    if not texto_comentario and not imagem_url:
        return jsonify({'ok': False, 'error': 'comentario_vazio_e_sem_imagem'}), 400

    db = get_db()
    tarefa = db.execute(
        "SELECT i.usuario_cs, i.id as implantacao_id, t.tarefa_filho FROM tarefas t JOIN implantacoes i ON t.implantacao_id = i.id WHERE t.id = ?", 
        (tarefa_id,)
    ).fetchone()
    
    if not tarefa or tarefa['usuario_cs'] != session['usuario']:
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    try:
        agora = datetime.now()
        cursor = db.execute(
            "INSERT INTO comentarios (tarefa_id, usuario_cs, texto, data_criacao, imagem_url) VALUES (?, ?, ?, ?, ?)",
            (tarefa_id, session['usuario'], texto_comentario, agora, imagem_url)
        )
        
        detalhe_log = ""
        if texto_comentario:
            detalhe_log += f"Novo comentário na tarefa '{tarefa['tarefa_filho']}':\n{texto_comentario}"
        if imagem_url:
            if detalhe_log: detalhe_log += "\n"
            detalhe_log += f"[Imagem adicionada]"
            
        logar_timeline(db, tarefa['implantacao_id'], session['usuario'], 'novo_comentario', detalhe_log)

        db.commit()
        
        novo_comentario_id = cursor.lastrowid
        perfil_usuario = db.execute("SELECT nome FROM perfil_usuario WHERE usuario = ?", (session['usuario'],)).fetchone()
        nome_usuario = perfil_usuario['nome'] if perfil_usuario else session['usuario']

        log_comentario = db.execute("""
            SELECT *, ? as usuario_nome FROM timeline_log
            WHERE implantacao_id = ? AND tipo_evento = 'novo_comentario'
            ORDER BY id DESC LIMIT 1
        """, (nome_usuario, tarefa['implantacao_id'])).fetchone()

        return jsonify({
            'ok': True,
            'comentario': {
                'id': novo_comentario_id,
                'tarefa_id': tarefa_id,
                'usuario_cs': session['usuario'],
                'usuario_nome': nome_usuario,
                'texto': texto_comentario,
                'imagem_url': imagem_url,
                'data_criacao': agora.strftime('%Y-%m-%d %H:%M:%S')
            },
            'log_comentario': dict(log_comentario) if log_comentario else None
        })

    except Exception as e:
        db.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/excluir_comentario/<int:comentario_id>', methods=['POST'])
def excluir_comentario(comentario_id):
    if 'usuario' not in session:
        return jsonify({'ok': False, 'error': 'login_required'}), 403

    db = get_db()
    
    comentario = db.execute(
        """SELECT c.usuario_cs, c.texto, c.imagem_url, t.implantacao_id, t.tarefa_filho 
           FROM comentarios c 
           JOIN tarefas t ON c.tarefa_id = t.id 
           WHERE c.id = ?""", 
        (comentario_id,)
    ).fetchone()
    
    if not comentario:
        return jsonify({'ok': False, 'error': 'not_found'}), 404
        
    if comentario['usuario_cs'] != session['usuario']:
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    try:
        if comentario['imagem_url']:
            try:
                filename = os.path.basename(comentario['imagem_url'])
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                print(f"Erro ao excluir arquivo de imagem: {e}")

        db.execute("DELETE FROM comentarios WHERE id = ?", (comentario_id,))
        
        detalhe_log = f"Comentário excluído da tarefa '{comentario['tarefa_filho']}': \"{comentario['texto'][:50]}...\""
        logar_timeline(db, comentario['implantacao_id'], session['usuario'], 'comentario_excluido', detalhe_log)

        db.commit()
        
        perfil_usuario = db.execute("SELECT nome FROM perfil_usuario WHERE usuario = ?", (session['usuario'],)).fetchone()
        nome_usuario = perfil_usuario['nome'] if perfil_usuario else session['usuario']
        log_exclusao = db.execute("""
            SELECT *, ? as usuario_nome FROM timeline_log
            WHERE implantacao_id = ? AND tipo_evento = 'comentario_excluido'
            ORDER BY id DESC LIMIT 1
        """, (nome_usuario, comentario['implantacao_id'])).fetchone()
        
        return jsonify({
            'ok': True,
            'log_exclusao': dict(log_exclusao) if log_exclusao else None
            })
    except Exception as e:
        db.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500

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
    impl = db.execute("SELECT usuario_cs FROM implantacoes WHERE id = ?", (implantacao_id,)).fetchone()
    if not impl or impl['usuario_cs'] != session['usuario']:
        return redirect(url_for('dashboard'))

    try:
        max_row = db.execute("SELECT MAX(ordem) as m FROM tarefas WHERE implantacao_id = ? AND tarefa_pai = ?", (implantacao_id, tarefa_pai)).fetchone()
        prox_ordem = (max_row['m'] or 0) + 1
        db.execute(
            "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem) VALUES (?, ?, ?, ?)",
            (implantacao_id, tarefa_pai, tarefa_filho, prox_ordem)
        )
        
        detalhe_log = f"Tarefa personalizada '{tarefa_filho}' adicionada ao módulo '{tarefa_pai}'."
        logar_timeline(db, implantacao_id, session['usuario'], 'tarefa_adicionada', detalhe_log)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erro ao adicionar tarefa: {e}")
        
    return redirect(url_for('ver_implantacao', impl_id=implantacao_id))

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
    impl = db.execute("SELECT usuario_cs FROM implantacoes WHERE id = ?", (implantacao_id,)).fetchone()
    if not impl or impl['usuario_cs'] != session['usuario']:
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    try:
        for idx, tarefa_id in enumerate(ordem_list, start=1):
            db.execute("UPDATE tarefas SET ordem = ? WHERE id = ? AND implantacao_id = ? AND tarefa_pai = ?", (idx, tarefa_id, implantacao_id, tarefa_pai))
        
        detalhe_log = f"Tarefas do módulo '{tarefa_pai}' foram reordenadas."
        logar_timeline(db, implantacao_id, session['usuario'], 'tarefa_reordenada', detalhe_log)

        db.commit()
        
        perfil_usuario = db.execute("SELECT nome FROM perfil_usuario WHERE usuario = ?", (session['usuario'],)).fetchone()
        nome_usuario = perfil_usuario['nome'] if perfil_usuario else session['usuario']
        log_reordenar = db.execute("""
            SELECT *, ? as usuario_nome FROM timeline_log
            WHERE implantacao_id = ? AND tipo_evento = 'tarefa_reordenada'
            ORDER BY id DESC LIMIT 1
        """, (nome_usuario, implantacao_id)).fetchone()

        return jsonify({
            'ok': True,
            'log_reordenar': dict(log_reordenar) if log_reordenar else None
        })
    except Exception as e:
        db.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        print(f"ERRO CRÍTICO DURANTE init_db(): {e}")
        import sys
        sys.exit(1)

    def _open_browser():
        import time
        time.sleep(1.0)
        try:
            webbrowser.open_new('http://127.0.0.1:5000/')
        except Exception:
            pass

    threading.Timer(1.0, _open_browser).start()
    app.run(debug=False, host='127.0.0.1', port=5000)