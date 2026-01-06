@echo off
chcp 65001 >nul
echo ============================================================
echo    TUNEL SOCKS5 PARA PRODUCAO - OAMD
echo ============================================================
echo.

REM Verificar e configurar SSH sem senha (apenas na primeira vez)
if not exist "%USERPROFILE%\.ssh\authorized_keys" (
    echo [CONFIGURANDO] Primeira execucao - configurando SSH sem senha...
    if not exist "%USERPROFILE%\.ssh\id_rsa" (
        ssh-keygen -t rsa -b 4096 -f "%USERPROFILE%\.ssh\id_rsa" -N "" >nul 2>&1
    )
    type "%USERPROFILE%\.ssh\id_rsa.pub" > "%USERPROFILE%\.ssh\authorized_keys" 2>nul
    echo [OK] SSH configurado!
    echo.
)

echo NAO FECHE ESTA JANELA!
echo Enquanto estiver aberta, a producao consegue acessar o OAMD.
echo.
echo Porta: 50022 (acessivel externamente)
echo ============================================================
echo.

"C:\Program Files\Git\usr\bin\ssh.exe" -D 0.0.0.0:50022 -N -o StrictHostKeyChecking=no Usuário@localhost

echo.
echo ============================================================
echo    TUNEL ENCERRADO
echo ============================================================
pause
