@echo off
chcp 65001 > nul
echo ============================================================
echo    PROXY SOCKS5 PARA BANCO OAMD
echo ============================================================
echo.
echo Este script cria um proxy SOCKS5 LOCAL que permite que
echo o servidor de PRODUCAO acesse o banco OAMD atraves da
echo sua rede residencial.
echo.
echo IMPORTANTE: NAO FECHE ESTA JANELA!
echo Enquanto estiver aberta, a producao consegue consultar o OAMD.
echo ============================================================
echo.

REM Detectar caminho do SSH
set SSH_PATH=ssh
where ssh >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    REM SSH não está no PATH, tentar Git for Windows
    if exist "C:\Program Files\Git\usr\bin\ssh.exe" (
        set SSH_PATH="C:\Program Files\Git\usr\bin\ssh.exe"
        echo [INFO] Usando SSH do Git for Windows
    ) else (
        echo [ERRO] SSH nao encontrado!
        echo.
        echo Instale o Git for Windows ou OpenSSH.
        echo Download: https://git-scm.com/download/win
        echo.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Usando SSH do sistema
)

echo [INFO] Iniciando proxy SOCKS5 na porta 50022...
echo.
echo Configuracao:
echo   - Porta SOCKS5: 50022 (acessivel externamente)
echo   - Bind: 0.0.0.0 (aceita conexoes externas)
echo   - Destino: localhost (seu proprio PC)
echo   - Funcao: Rotear consultas da producao para o OAMD
echo.
echo ============================================================
echo.

REM Criar túnel SSH LOCAL para SOCKS5 proxy
REM -D 0.0.0.0:50022 = Proxy SOCKS5 acessível externamente na porta 50022
REM -N = Não executa comandos remotos (apenas túnel)
REM localhost = Conecta no próprio PC (que tem acesso ao OAMD)
%SSH_PATH% -D 0.0.0.0:50022 -N ^
    -o ServerAliveInterval=60 ^
    -o ServerAliveCountMax=3 ^
    %USERNAME%@localhost

echo.
echo ============================================================
echo    PROXY ENCERRADO
echo ============================================================
echo.
echo O proxy foi fechado. A producao nao consegue mais acessar o OAMD.
echo.
pause
