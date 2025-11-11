# testo/CSAPP/backend/project/email_utils.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
from .db import query_db, execute_db
from .logging_config import security_logger, app_logger

# --- CRIPTOGRAFIA (Simples) ---
# Em um cenário ideal, usaríamos uma biblioteca de criptografia real (ex: cryptography.fernet)
# Mas para manter a simplicidade e evitar dependências de chaves, usaremos hash + verificação
# NOTA: Isto é apenas para ofuscar, NÃO é criptografia reversível.
# A senha SÓ PODE SER INSERIDA, não pode ser lida de volta para o formulário.

def _hash_password(password):
    """Gera um hash para a senha."""
    if not password:
        return None
    return generate_password_hash(password)

def _check_password(hashed_password, provided_password):
    """Verifica a senha fornecida contra o hash."""
    if not hashed_password or not provided_password:
        return False
    return check_password_hash(hashed_password, provided_password)

# --- FUNÇÕES DE LÓGICA DE E-MAIL ---

def load_smtp_settings(user_email):
    """
    Carrega as configurações SMTP para um usuário específico.
    NOTA: A senha retornada é o HASH, não a senha real.
    """
    if not user_email:
        return None
        
    try:
        # --- CORREÇÃO AQUI ---
        # A coluna "user" precisa de aspas no SQL
        settings = query_db(
            'SELECT host, port, "user", password as hashed_password, use_tls, use_ssl FROM smtp_settings WHERE usuario_email = %s',
            (user_email,),
            one=True
        )
        return settings
    except Exception as e:
        app_logger.error(f"Erro ao carregar settings SMTP para {user_email}: {e}")
        return None

def save_smtp_settings(user_email, data):
    """
    Salva ou atualiza as configurações SMTP para um usuário específico.
    Armazena um hash da senha.
    """
    host = data.get('host')
    port = data.get('port')
    user = data.get('user') # O nome do campo do formulário (que será salvo na coluna "user")
    password = data.get('password') # Senha em texto plano do formulário
    use_tls = data.get('use_tls', 'true').lower() == 'true'
    use_ssl = data.get('use_ssl', 'false').lower() == 'true'

    if not all([user_email, host, port, user]):
        raise ValueError("Dados de SMTP incompletos para salvar.")

    try:
        # Se uma nova senha foi fornecida, faz o hash dela.
        # Se a senha estiver vazia, tentamos manter a antiga.
        if password:
            hashed_password_to_save = _hash_password(password)
            
            # --- CORREÇÃO AQUI ---
            # A coluna "user" precisa de aspas no SQL
            sql = """
                INSERT INTO smtp_settings (usuario_email, host, port, "user", password, use_tls, use_ssl)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (usuario_email) DO UPDATE SET
                    host = EXCLUDED.host,
                    port = EXCLUDED.port,
                    "user" = EXCLUDED."user",
                    password = EXCLUDED.password,
                    use_tls = EXCLUDED.use_tls,
                    use_ssl = EXCLUDED.use_ssl;
            """
            params = (user_email, host, int(port), user, hashed_password_to_save, use_tls, use_ssl)
        
        else:
            # Query para salvar SEM atualizar a senha (mantém a existente)
            # --- CORREÇÃO AQUI ---
            sql = """
                INSERT INTO smtp_settings (usuario_email, host, port, "user", use_tls, use_ssl)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (usuario_email) DO UPDATE SET
                    host = EXCLUDED.host,
                    port = EXCLUDED.port,
                    "user" = EXCLUDED."user",
                    use_tls = EXCLUDED.use_tls,
                    use_ssl = EXCLUDED.use_ssl;
            """
            params = (user_email, host, int(port), user, use_tls, use_ssl)

        execute_db(sql, params)
        app_logger.info(f"Configurações SMTP salvas para o usuário: {user_email}")

    except Exception as e:
        app_logger.error(f"Erro ao salvar settings SMTP para {user_email}: {e}")
        raise

def test_smtp_connection(settings, plain_password):
    """
    Testa a conexão SMTP e a autenticação usando as configurações e a senha em texto plano.
    'settings' deve vir de load_smtp_settings (contém o HASH da senha).
    'plain_password' deve vir do formulário de teste.
    """
    if not settings:
        raise ValueError("Configurações não encontradas.")
        
    hashed_password = settings.get('hashed_password')
    
    # Etapa 1: Verificar se a senha fornecida no teste corresponde ao hash salvo
    if not _check_password(hashed_password, plain_password):
        security_logger.warning(f"Falha no teste SMTP (Senha não confere com o HASH salvo) para usuário {settings.get('user')}")
        raise smtplib.SMTPAuthenticationError(535, b"Senha invalida. Nao corresponde a configuracao salva.")

    # Etapa 2: Se a senha bate com o HASH, tentamos a conexão real com o provedor
    host = settings.get('host')
    port = int(settings.get('port', 587))
    user = settings.get('user') # O Python.get() lê a chave 'user' do dicionário (correto)
    use_tls = settings.get('use_tls', True)
    use_ssl = settings.get('use_ssl', False)
    
    app_logger.info(f"Testando conexão SMTP para {user} em {host}:{port} (SSL: {use_ssl}, TLS: {use_tls})")

    try:
        if use_ssl:
            context = smtplib.ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            if use_tls:
                server.starttls()
        
        # Usamos a senha em texto plano (verificada) para o login real
        server.login(user, plain_password)
        server.quit()
        app_logger.info(f"Autenticação SMTP bem-sucedida para {user}")
        return True
    
    except smtplib.SMTPAuthenticationError as e:
        security_logger.warning(f"Falha de autenticacao SMTP (provedor rejeitou) para {user}: {e}")
        raise # Re-lança a exceção original do smtplib
        
    except Exception as e:
        app_logger.error(f"Erro inesperado no teste SMTP para {user}: {e}")
        raise ValueError(f"Erro de conexao: {e}")


def send_email(subject, body_html, recipients, smtp_settings, plain_password, from_name=None, reply_to=None):
    """
    Envia um e-mail real usando as configurações validadas.
    Requer a senha em texto plano, pois ela não é armazenada de forma reversível.
    """
    
    # Esta função só pode ser chamada se a autenticação (teste) foi bem-sucedida
    # e a senha em texto plano está disponível na memória (vinda do formulário).
    
    host = smtp_settings.get('host')
    port = int(smtp_settings.get('port', 587))
    user = smtp_settings.get('user')
    use_tls = smtp_settings.get('use_tls', True)
    use_ssl = smtp_settings.get('use_ssl', False)
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"{from_name} <{user}>" if from_name else user
    msg['To'] = ", ".join(recipients)
    if reply_to:
        msg['Reply-To'] = reply_to
    
    msg.attach(MIMEText(body_html, 'html'))
    
    try:
        if use_ssl:
            context = smtplib.ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            if use_tls:
                server.starttls()
        
        server.login(user, plain_password)
        server.sendmail(user, recipients, msg.as_string())
        server.quit()
        app_logger.info(f"E-mail enviado com sucesso por {user} para {recipients}")
        return True
        
    except Exception as e:
        app_logger.error(f"Falha ao enviar e-mail real por {user}: {e}")
        raise
    

# -------------------------------------------------------------------
# FUNÇÃO ANTIGA (LEGADO) - REQUER REVISÃO
# -------------------------------------------------------------------
def send_external_comment_notification(implantacao, comentario):
    """
    Envia notificação de um novo comentário externo.
    
    *** ATENÇÃO: Esta função está quebrada ***
    Ela foi desenhada para um SMTP GLOBAL (id=1).
    Agora, ela precisa ser redesenhada. Qual usuário deve enviar o e-mail?
    O 'implantador_email' da implantação?
    
    Esta função precisa ser refatorada para:
    1. Obter o `implantador_email` da `implantacao`.
    2. Carregar as configurações SMTP desse implantador (load_smtp_settings(implantador_email)).
    3. Ela NÃO PODE ENVIAR, pois não temos a senha de texto plano do implantador.
    
    A funcionalidade de "notificação por e-mail" precisa ser repensada.
    Por enquanto, vamos apenas logar e falhar silenciosamente.
    """
    
    implantador_email = implantacao.get('implantador_email')
    
    app_logger.warning(
        f"Tentativa de envio de notificacao de comentario para {implantador_email} (RECURSO DESATIVADO). "
        f"A funcao 'send_external_comment_notification' precisa ser refatorada para o sistema de SMTP por usuario."
    )
    return False

    # --- CÓDIGO ANTIGO E QUEBRADO ---
    # settings = load_smtp_settings() # <-- Isto não funciona mais, espera user_email
    # if not settings:
    #     app_logger.error("Falha ao enviar notificacao de comentario: SMTP global nao configurado.")
    #     return False
        
    # ... (logica de envio) ...