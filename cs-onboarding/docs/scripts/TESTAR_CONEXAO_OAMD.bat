@echo off
chcp 65001 > nul
echo ============================================================
echo    TESTE DE CONEXAO COM BANCO OAMD
echo ============================================================
echo.
echo Este script testa a conexao com o banco OAMD usando o proxy.
echo.
echo PRE-REQUISITOS:
echo   1. O proxy SOCKS5 deve estar ATIVO (INICIAR_TUNEL_OAMD.bat)
echo   2. Python deve estar instalado
echo   3. Dependencias instaladas (pip install -r requirements.txt)
echo.
echo ============================================================
echo.

REM Verificar se Python está instalado
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Python nao encontrado!
    echo.
    echo Instale o Python 3.8+ e tente novamente.
    echo.
    pause
    exit /b 1
)

echo [INFO] Verificando se o proxy esta ativo...
netstat -an | findstr ":50022" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [AVISO] Porta 50022 nao esta em uso!
    echo.
    echo Certifique-se de que o proxy SOCKS5 esta ativo.
    echo Execute INICIAR_TUNEL_OAMD.bat em outra janela primeiro.
    echo.
    pause
    exit /b 1
)

echo [OK] Proxy detectado na porta 50022
echo.
echo [INFO] Configurando variaveis de ambiente...

REM Configurar variáveis de ambiente para o teste LOCAL
set EXTERNAL_DB_URL=postgresql://cs_pacto:pacto@db@oamd.pactosolucoes.com.br:5432/OAMD
set EXTERNAL_DB_PROXY_URL=socks5://localhost:50022
set EXTERNAL_DB_TIMEOUT=10

echo   EXTERNAL_DB_URL=%EXTERNAL_DB_URL%
echo   EXTERNAL_DB_PROXY_URL=%EXTERNAL_DB_PROXY_URL%
echo   EXTERNAL_DB_TIMEOUT=%EXTERNAL_DB_TIMEOUT%
echo.
echo [INFO] Executando teste de conexao...
echo ============================================================
echo.

REM Executar script de teste
python tests\run_oamd_consulta.py

echo.
echo ============================================================
echo    TESTE CONCLUIDO
echo ============================================================
pause

