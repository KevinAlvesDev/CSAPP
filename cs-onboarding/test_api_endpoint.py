"""
Teste do endpoint de save que o frontend chama
"""
import requests

# URL do Railway
BASE_URL = "https://cs-onboarding-production.up.railway.app"

print("=== TESTE DO ENDPOINT DE SAVE ===\n")
print("IMPORTANTE: Voce precisa estar logado no navegador para este teste funcionar")
print("Vou tentar fazer uma requisicao como se fosse o formulario\n")

# Simular o que o formulario envia
impl_id = 74
data = {
    'chave_oamd': 'TESTE_VIA_API_123',
    'tela_apoio_link': 'https://teste-api.com/link'
}

print(f"Tentando salvar na implantacao ID {impl_id}:")
print(f"  chave_oamd: {data['chave_oamd']}")
print(f"  tela_apoio_link: {data['tela_apoio_link']}")
print("\nNOTA: Este teste vai falhar com 401 (nao autenticado) porque")
print("nao temos o cookie de sessao. Mas isso prova que o endpoint existe.\n")

try:
    response = requests.post(
        f"{BASE_URL}/implantacao/{impl_id}/salvar_detalhes",
        data=data,
        timeout=10
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Erro (esperado): {e}")

print("\n=== PROXIMOS PASSOS ===")
print("1. Abra o DevTools (F12) no navegador")
print("2. Va na aba Network")
print("3. Tente salvar os campos")
print("4. Veja se a requisicao POST /implantacao/XX/salvar_detalhes aparece")
print("5. Verifique o Status Code e a Response")
