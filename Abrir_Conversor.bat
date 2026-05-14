@echo off
title YTConvert App Launcher
echo Iniciando YTConvert Premium...

:: Verifica se o servidor esta rodando na porta 5000
netstat -ano | findstr :5000 > nul
if %errorlevel% neq 0 (
    echo Iniciando o servidor backend...
    start /b python app\server.py
    timeout /t 5 > nul
)

:: Tenta abrir com o Chrome no modo App (sem bordas de navegador)
echo Abrindo interface...
start chrome --app=http://localhost:5000

:: Se nao tiver chrome, tenta o Edge (que tambem suporta modo app)
if %errorlevel% neq 0 (
    start msedge --app=http://localhost:5000
)

echo.
echo ==========================================
echo   YTConvert esta rodando como aplicativo!
echo ==========================================
echo.
timeout /t 3
exit
