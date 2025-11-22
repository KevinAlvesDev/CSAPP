"""
Script de diagnóstico para verificar configuração do Google OAuth
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

try:
    from project.config import Config

    print("=== DIAGNÓSTICO GOOGLE OAUTH ===\n")

    print("1. Variáveis de Ambiente:")
    print(
        f"   GOOGLE_CLIENT_ID: {'✅ Definido' if os.environ.get('GOOGLE_CLIENT_ID') else '❌ Não definido'}"
    )
    print(
        f"   GOOGLE_CLIENT_SECRET: {'✅ Definido' if os.environ.get('GOOGLE_CLIENT_SECRET') else '❌ Não definido'}"
    )
    print(
        f"   GOOGLE_REDIRECT_URI: {'✅ Definido' if os.environ.get('GOOGLE_REDIRECT_URI') else '❌ Não definido'}"
    )

    if os.environ.get("GOOGLE_REDIRECT_URI"):
        print(f"   Valor atual: {os.environ.get('GOOGLE_REDIRECT_URI')}")

    print("\n2. Configuração da Aplicação:")
    config = Config()
    print(f"   GOOGLE_OAUTH_ENABLED: {config.GOOGLE_OAUTH_ENABLED}")
    print(f"   REDIRECT_URI da config: {config.GOOGLE_REDIRECT_URI}")

    print("\n3. URLs Esperadas:")
    print("   Desenvolvimento: http://127.0.0.1:5000/agenda/callback")
    print("   Produção: https://csimplantacaopacto.up.railway.app/agenda/callback")

    print("\n4. Variáveis do Railway (se disponíveis):")
    railway_vars = [
        "RAILWAY_PUBLIC_DOMAIN",
        "RAILWAY_SERVICE_NAME",
        "RAILWAY_ENVIRONMENT_NAME",
    ]
    for var in railway_vars:
        value = os.environ.get(var)
        if value:
            print(f"   {var}: {value}")

    print("\n5. Verificação de Protocolo:")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "")
    if redirect_uri:
        if redirect_uri.startswith("https://"):
            print("   ✅ Usando HTTPS (correto para produção)")
        elif redirect_uri.startswith("http://"):
            print("   ⚠️  Usando HTTP (apenas para desenvolvimento)")
        else:
            print("   ❌ Protocolo não reconhecido")

    print("\n=== FIM DO DIAGNÓSTICO ===")

except Exception as e:
    print(f"Erro ao executar diagnóstico: {e}")
    print("Certifique-se de estar no diretório correto do projeto")
