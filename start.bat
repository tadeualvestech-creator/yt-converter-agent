@echo off
title YTConvert — Servidor
color 0A

echo ============================================
echo   YTConvert - Iniciando servidor...
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale em https://python.org
    pause & exit /b 1
)

:: Install/upgrade dependencies
echo [1/3] Verificando dependencias...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause & exit /b 1
)

:: Check yt-dlp
echo [2/3] Verificando yt-dlp...
python -m yt_dlp --version >nul 2>&1
if errorlevel 1 (
    echo [AVISO] yt-dlp nao encontrado no PATH. Tentando via python -m yt_dlp...
)

:: Create required directories
echo [3/3] Criando pastas necessarias...
if not exist "app\sessions" mkdir "app\sessions"
if not exist "app\auth"     mkdir "app\auth"
if not exist "static"       mkdir "static"

echo.
echo ============================================
echo   Servidor rodando em: http://localhost:5000
echo   Pressione Ctrl+C para parar.
echo ============================================
echo.

python app\server.py

pause
