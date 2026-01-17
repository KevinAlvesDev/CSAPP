#!/usr/bin/env python3
"""
Script de teste para verificar conexão SMTP com Hostinger na porta 465 (SSL)
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configurações da Hostinger - PORTA 465 COM SSL
SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465  # Mudou de 587 para 465
SMTP_USER = "suporte@csimplantacaopacto.space"
SMTP_PASSWORD = "742141189Kwap@"
SMTP_FROM = "suporte@csimplantacaopacto.space"

# Email de teste
TEST_EMAIL = "kevinpereira@pactosolucoes.com.br"

def test_smtp_connection_ssl():
    """Testa a conexão SMTP com SSL na porta 465"""
    print("=" * 60)
    print("TESTE DE CONEXAO SMTP - HOSTINGER (PORTA 465 SSL)")
    print("=" * 60)
    print()
    
    print(f"Configuracoes:")
    print(f"   Host: {SMTP_HOST}")
    print(f"   Porta: {SMTP_PORT} (SSL)")
    print(f"   Usuario: {SMTP_USER}")
    print(f"   De: {SMTP_FROM}")
    print(f"   Para: {TEST_EMAIL}")
    print()
    
    try:
        print("Passo 1: Conectando ao servidor SMTP com SSL...")
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=30)
        print("   OK - Conexao SSL estabelecida!")
        
        print("Passo 2: Fazendo login...")
        server.login(SMTP_USER, SMTP_PASSWORD)
        print("   OK - Login bem-sucedido!")
        
        print("Passo 3: Preparando email de teste...")
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Teste SMTP - Hostinger Porta 465 (SSL)"
        msg['From'] = f"CS Onboarding <{SMTP_FROM}>"
        msg['To'] = TEST_EMAIL
        
        body_html = """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #007bff;">Teste de Email - Hostinger SMTP (Porta 465 SSL)</h2>
            <p>Este e um email de teste para verificar se o SMTP da Hostinger esta funcionando com SSL na porta 465.</p>
            <p><strong>Configuracoes:</strong></p>
            <ul>
                <li>Host: smtp.hostinger.com</li>
                <li>Porta: 465</li>
                <li>SSL: Ativado</li>
            </ul>
            <p style="color: #28a745;">Se voce recebeu este email, a configuracao com porta 465 esta funcionando!</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body_html, 'html'))
        
        print("Passo 4: Enviando email...")
        server.sendmail(SMTP_FROM, [TEST_EMAIL], msg.as_string())
        print("   OK - Email enviado com sucesso!")
        
        print("Passo 5: Fechando conexao...")
        server.quit()
        print("   OK - Conexao fechada!")
        
        print()
        print("=" * 60)
        print("TESTE CONCLUIDO COM SUCESSO!")
        print("=" * 60)
        print()
        print(f"Verifique a caixa de entrada de {TEST_EMAIL}")
        print("   (Pode estar na pasta de spam)")
        print()
        print("PROXIMOS PASSOS:")
        print("  1. Atualizar .env local: SMTP_PORT=465 e SMTP_USE_SSL=true")
        print("  2. Atualizar Railway: SMTP_PORT=465 e SMTP_USE_SSL=true")
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print()
        print("=" * 60)
        print("ERRO DE AUTENTICACAO")
        print("=" * 60)
        print(f"Detalhes: {e}")
        print()
        print("Possiveis causas:")
        print("  1. Senha incorreta")
        print("  2. Email nao existe na Hostinger")
        print("  3. Autenticacao SMTP nao habilitada")
        return False
        
    except smtplib.SMTPConnectError as e:
        print()
        print("=" * 60)
        print("ERRO DE CONEXAO")
        print("=" * 60)
        print(f"Detalhes: {e}")
        print()
        print("Possiveis causas:")
        print("  1. Firewall bloqueando porta 465")
        print("  2. Host incorreto")
        print("  3. Problemas de rede")
        return False
        
    except Exception as e:
        print()
        print("=" * 60)
        print("ERRO INESPERADO")
        print("=" * 60)
        print(f"Tipo: {type(e).__name__}")
        print(f"Detalhes: {e}")
        return False

if __name__ == "__main__":
    test_smtp_connection_ssl()
