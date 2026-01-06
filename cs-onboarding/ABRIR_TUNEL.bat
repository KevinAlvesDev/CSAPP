@echo off
title Tunel SSH - Banco OAMD
color 0A
cls

echo ============================================================
echo            TUNEL SSH - BANCO DE DADOS OAMD
echo ============================================================
echo.
echo Conectando ao servidor pactosolucoes.com.br...
echo Porta local: 5433
echo.
echo IMPORTANTE: Mantenha esta janela ABERTA enquanto usar o banco!
echo Pressione Ctrl+C para encerrar o tunel
echo.
echo ============================================================
echo.

REM Criar túnel SSH
ssh -N -L 5433:localhost:5432 pacto@pactosolucoes.com.br

echo.
echo Tunel encerrado.
pause
