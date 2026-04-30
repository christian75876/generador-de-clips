@echo off
cd /d %~dp0

if not exist ".venv\Scripts\python.exe" (
    echo No existe el entorno virtual .venv
    echo Ejecuta primero setup.bat
    pause
    exit /b 1
)

echo Iniciando Content Pipeline...

.venv\Scripts\python.exe -m streamlit run app.py --server.headless=false

pause