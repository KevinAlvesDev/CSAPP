"""
Teste rápido do envio assíncrono de email
"""
import sys
import time
sys.path.insert(0, 'c:/Users/Usuário/Desktop/app-pacto/CSAPP/cs-onboarding/backend')

# Simular o app_logger
class FakeLogger:
    def info(self, msg):
        print(f"[INFO] {msg}")
    def warning(self, msg):
        print(f"[WARNING] {msg}")
    def error(self, msg):
        print(f"[ERROR] {msg}")

# Importar a função
from project.mail.email_utils import send_external_comment_notification
import project.mail.email_utils as email_utils

# Substituir o logger
email_utils.app_logger = FakeLogger()

# Dados de teste
implantacao = {
    'nome_empresa': 'Teste Empresa',
    'email_responsavel': 'kevinpereira@pactosolucoes.com.br'
}

comentario = {
    'texto': 'Este é um teste de envio assíncrono de email!',
    'tarefa_filho': 'Tarefa de Teste',
    'usuario_cs': 'Kevin (Teste)'
}

print("=" * 60)
print("TESTE DE ENVIO ASSINCRONO DE EMAIL")
print("=" * 60)
print()

print("Enviando email...")
start = time.time()
result = send_external_comment_notification(implantacao, comentario)
end = time.time()

print()
print(f"Resultado: {result}")
print(f"Tempo de execucao: {(end - start) * 1000:.2f}ms")
print()
print("Se o tempo for menor que 100ms, o envio e assincrono!")
print("Aguardando 5 segundos para o email ser enviado em background...")
time.sleep(5)
print()
print("Teste concluido!")
