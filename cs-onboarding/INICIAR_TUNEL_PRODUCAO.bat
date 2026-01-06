@echo off
chcp 65001 >nul
echo ============================================================
echo    TUNEL SOCKS5 PARA PRODUCAO - OAMD
echo ============================================================
echo.
echo NAO FECHE ESTA JANELA!
echo Enquanto estiver aberta, a producao consegue acessar o OAMD.
echo.
echo Porta: 50022 (acessivel externamente)
echo ============================================================
echo.

"C:\Program Files\Git\usr\bin\ssh.exe" -D 0.0.0.0:50022 -N -o StrictHostKeyChecking=no pacto@pactosolucoes.com.br

echo.
echo ============================================================
echo    TUNEL ENCERRADO
echo ============================================================
pause
